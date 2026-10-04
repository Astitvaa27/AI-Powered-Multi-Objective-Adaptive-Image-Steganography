"""
Stage E: decide how much a recovered payload can be trusted.

A readable string alone is never treated as proof. The validation level
combines the format's framing (length field, terminator, container),
integrity checks (stored message hash, zlib checksum) and content
structure (strict UTF-8 text, known file signatures). The rules are
deterministic and explained in each candidate's evidence list; there is
no numeric confidence score.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import io
import math
import re
import zipfile
from collections import Counter
from dataclasses import dataclass, field

from backend.app.services.auto_extract.types import (
    Evidence,
    Framing,
    RawExtraction,
    Validation,
)

# Minimum characters before text counts as PLAUSIBLE, per framing type.
# Terminator framing needs more, because a short printable run followed by
# a zero byte occurs by chance far more often than a valid length field.
MIN_TEXT_CHARS = {
    Framing.LENGTH: 3,
    Framing.CONTAINER: 4,
    Framing.TERMINATOR: 8,
}

# Below this, delimiter-framed text is discarded rather than reported.
MIN_TERMINATOR_CANDIDATE_CHARS = 4

# Text payloads above this size are only partly returned as text.
MAX_TEXT_CHARS_RETURNED = 100_000


@dataclass(frozen=True)
class Signature:
    magic: bytes
    name: str
    encrypted: bool = False
    executable: bool = False
    offset: int = 0


SIGNATURES = (
    Signature(b"\x89PNG\r\n\x1a\n", "PNG image"),
    Signature(b"\xff\xd8\xff", "JPEG image"),
    Signature(b"GIF87a", "GIF image"),
    Signature(b"GIF89a", "GIF image"),
    Signature(b"%PDF-", "PDF document"),
    Signature(b"PK\x03\x04", "ZIP archive"),
    Signature(b"\x1f\x8b\x08", "gzip-compressed data"),
    Signature(b"7z\xbc\xaf\x27\x1c", "7-Zip archive"),
    Signature(b"Rar!\x1a\x07", "RAR archive"),
    Signature(b"Salted__", "OpenSSL-encrypted data", encrypted=True),
    Signature(b"-----BEGIN PGP MESSAGE-----", "PGP-encrypted message", encrypted=True),
    Signature(b"\x7fELF", "ELF executable", executable=True),
    Signature(b"MZ\x90\x00", "Windows executable", executable=True),
    Signature(b"RIFF", "RIFF media (WAV/AVI/WebP)"),
    Signature(b"ID3", "MP3 audio"),
    Signature(b"OggS", "Ogg media"),
)

_BASE64_RE = re.compile(r"^[A-Za-z0-9+/\s]+={0,2}\s*$")
_MARKUP_RE = re.compile(r"<\s*(script|html|iframe|svg|img|a)\b", re.IGNORECASE)


def detect_signature(payload: bytes) -> Signature | None:
    for signature in SIGNATURES:
        if payload[signature.offset:signature.offset + len(signature.magic)] == signature.magic:
            return signature
    return None


def decode_text(payload: bytes) -> str | None:
    """
    Strict UTF-8 text check: valid encoding, no NUL bytes, at least 97% of
    characters printable (tabs and newlines allowed) and at least one
    non-whitespace character.
    """

    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return None

    if not text or "\x00" in text:
        return None

    printable = sum(1 for ch in text if ch.isprintable() or ch in "\n\r\t")
    if printable / len(text) < 0.97:
        return None

    if not any(not ch.isspace() for ch in text):
        return None

    return text


def normalised_entropy(payload: bytes) -> float:
    """Byte entropy scaled to 0..1 by the maximum possible for its length."""

    if len(payload) < 2:
        return 0.0
    counts = Counter(payload)
    total = len(payload)
    entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
    return entropy / math.log2(min(total, 256))


def _inspect_zip(payload: bytes) -> tuple[list[Evidence], bool, list[str]]:
    """List a ZIP's entries from its central directory. Nothing is unpacked."""

    evidence: list[Evidence] = []
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            infos = archive.infolist()
    except (zipfile.BadZipFile, ValueError, OSError, EOFError):
        evidence.append(Evidence("ZIP structure", False, "The ZIP header is present but the archive directory is unreadable."))
        return evidence, False, []

    encrypted = any(info.flag_bits & 0x1 for info in infos)
    names = [info.filename[:200] for info in infos[:20]]
    evidence.append(
        Evidence("ZIP structure", True, f"Archive directory lists {len(infos)} entr{'y' if len(infos) == 1 else 'ies'}.")
    )
    if encrypted:
        evidence.append(Evidence("Encryption", True, "Archive entries are password-protected."))
    return evidence, encrypted, names


@dataclass
class AssessedPayload:
    validation: Validation | None  # None = rejected
    evidence: list[Evidence]
    reason: str | None
    kind: str  # TEXT | BINARY
    text: str | None
    detected_type: str | None
    requires_key: bool
    key_hint: str | None
    notes: list[str] = field(default_factory=list)
    archive_entries: list[str] = field(default_factory=list)


def assess(raw: RawExtraction) -> AssessedPayload:
    """Apply the validation rules to one raw extraction."""

    payload = raw.payload or b""
    evidence = list(raw.evidence)
    notes: list[str] = []

    def reject(reason: str) -> AssessedPayload:
        return AssessedPayload(None, evidence, reason, "BINARY", None, None, False, None)

    if not payload:
        return reject("The recovered payload is empty.")

    if len(payload) >= 2 and len(set(payload)) == 1:
        return reject("The recovered bytes are all identical, which is typical of flat image areas rather than a message.")

    integrity_passed = raw.integrity is not None and raw.integrity.passed
    integrity_failed = raw.integrity is not None and not raw.integrity.passed
    if raw.integrity is not None:
        evidence.append(raw.integrity)

    framing_ok = all(item.passed for item in raw.evidence)

    text = decode_text(payload)

    # Delimiter conventions only exist for text; binary bytes that happen
    # to precede a zero byte are just the image's own low bits.
    if raw.framing == Framing.TERMINATOR and text is None:
        return reject("The bytes before the delimiter are not readable text.")

    # Natural images routinely yield 1-3 printable bytes before a zero byte.
    if raw.framing == Framing.TERMINATOR and len(text.strip()) < MIN_TERMINATOR_CANDIDATE_CHARS:
        return reject("Only a few readable characters precede the delimiter, which natural images produce by chance.")

    signature =None if text is not None and not payload.startswith(b"-----BEGIN PGP") else detect_signature(payload)

    requires_key = False
    key_hint: str | None = None
    detected_type: str | None = None
    archive_entries: list[str] = []

    if signature:
        detected_type = signature.name
        evidence.append(Evidence("File signature", True, f"Payload starts with the signature of a {signature.name}."))
        if signature.encrypted:
            requires_key = True
            key_hint = f"The payload is {signature.name}; it can only be read with the password or key used to encrypt it."
        if signature.executable:
            notes.append("The payload is an executable file. StegoLab never runs recovered files; do not open it unless you trust its origin.")
        if signature.name == "ZIP archive":
            zip_evidence, encrypted, archive_entries = _inspect_zip(payload)
            evidence.extend(zip_evidence)
            if encrypted:
                requires_key = True
                key_hint = "The recovered ZIP archive is password-protected; StegoLab does not bypass encryption."

    if text is not None:
        evidence.append(Evidence("Text decoding", True, f"Decodes as UTF-8 text ({len(text)} characters, all printable)."))
        stripped = "".join(text.split())
        if len(stripped) >= 24 and _BASE64_RE.match(text):
            try:
                base64.b64decode(stripped, validate=True)
                notes.append("The text looks like Base64. It may be encoded or encrypted data that needs another tool or a key to read.")
            except (binascii.Error, ValueError):
                pass
        if _MARKUP_RE.search(text):
            notes.append("The text contains HTML or script markup. It is shown as plain text only and is never executed.")

    # Decide the level.
    if integrity_failed:
        level: Validation | None = Validation.UNVERIFIED if (text or signature) else None
    elif integrity_passed and framing_ok:
        level = Validation.VERIFIED
    elif not framing_ok:
        level = Validation.UNVERIFIED if (text or signature) else None
    elif text is not None:
        minimum = MIN_TEXT_CHARS[raw.framing]
        if len(text.strip()) >= minimum:
            level = Validation.PLAUSIBLE
        else:
            level = Validation.UNVERIFIED
            evidence.append(
                Evidence("Payload length", False, f"Only {len(text.strip())} characters; at least {minimum} are needed before a match is considered plausible for this format.")
            )
    elif signature is not None:
        level = Validation.PLAUSIBLE if raw.framing != Framing.TERMINATOR else Validation.UNVERIFIED
    else:
        entropy = normalised_entropy(payload)
        if len(payload) >= 32 and entropy >= 0.9:
            level = Validation.UNVERIFIED
            requires_key = True
            key_hint = "The payload is high-entropy binary data. It may be encrypted or compressed; a password or the original tool may be needed."
            evidence.append(Evidence("Content structure", False, "Not text and no known file signature; the bytes look random (possibly encrypted)."))
        else:
            return reject("The recovered bytes are neither text nor a recognised file type.")

    if level is None:
        return reject("The recovered bytes did not pass validation.")

    return AssessedPayload(
        validation=level,
        evidence=evidence,
        reason=None,
        kind="TEXT" if text is not None else "BINARY",
        text=text,
        detected_type=detected_type,
        requires_key=requires_key,
        key_hint=key_hint,
        notes=notes,
        archive_entries=archive_entries,
    )


def payload_digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def explain(validation: Validation, framing: Framing) -> str:
    """One-sentence plain-language basis for a validation level."""

    if validation == Validation.VERIFIED:
        return "Verified: an integrity check confirmed these exact bytes."
    if validation == Validation.PLAUSIBLE:
        if framing == Framing.LENGTH:
            return (
                "Plausible: the format's length field is valid for this image and the content is readable, "
                "but the format has no checksum, so a coincidental match cannot be fully ruled out."
            )
        if framing == Framing.CONTAINER:
            return "Plausible: extra data is stored in the file and its content is readable or a known file type."
        return "Plausible: readable text ends exactly at a known delimiter, but delimiter formats carry no checksum."
    return "Unverified: something was recovered, but the evidence is too weak to call it a hidden message."
