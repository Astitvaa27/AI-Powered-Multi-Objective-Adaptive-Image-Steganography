"""
Data types shared by the automatic extraction pipeline.

Kept free of FastAPI and database imports so the pipeline can be unit
tested on raw bytes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class AutoExtractInputError(ValueError):
    """The upload cannot be analysed (unsupported, corrupted or too large)."""

    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class Validation(str, Enum):
    """
    How strongly a candidate payload is supported by evidence.

    VERIFIED   an integrity check passed (stored message hash, checksum).
    PLAUSIBLE  the format's framing is valid and the content is readable
               text or a recognised file type, but the format carries no
               checksum, so a coincidental match cannot be ruled out.
    UNVERIFIED something was recovered but the evidence is weak (very
               short text, unstructured binary).
    """

    VERIFIED = "VERIFIED"
    PLAUSIBLE = "PLAUSIBLE"
    UNVERIFIED = "UNVERIFIED"


VALIDATION_RANK = {
    Validation.VERIFIED: 0,
    Validation.PLAUSIBLE: 1,
    Validation.UNVERIFIED: 2,
}


class Framing(str, Enum):
    """How the payload boundary is defined; drives the validation rules."""

    # Explicit length field (binary or decimal).
    LENGTH = "LENGTH"
    # Payload ends at a delimiter; weaker than a length field.
    TERMINATOR = "TERMINATOR"
    # Bytes outside the image data (appended data, metadata field).
    CONTAINER = "CONTAINER"


@dataclass(frozen=True)
class Limits:
    max_file_bytes: int
    max_pixels: int
    max_transform_pixels: int
    max_payload_bytes: int
    time_budget_seconds: float

    @classmethod
    def from_settings(cls, settings: Any) -> "Limits":
        return cls(
            max_file_bytes=settings.AUTO_EXTRACT_MAX_FILE_BYTES,
            max_pixels=settings.AUTO_EXTRACT_MAX_PIXELS,
            max_transform_pixels=settings.AUTO_EXTRACT_MAX_TRANSFORM_PIXELS,
            max_payload_bytes=settings.AUTO_EXTRACT_MAX_PAYLOAD_BYTES,
            time_budget_seconds=settings.AUTO_EXTRACT_TIME_BUDGET_SECONDS,
        )


@dataclass
class MetadataText:
    """Readable text stored openly in the file's metadata."""

    location: str  # e.g. "PNG tEXt chunk", "JPEG comment", "EXIF"
    key: str
    text: str
    truncated: bool = False
    standard_key: bool = False

    def to_dict(self) -> dict:
        return {
            "location": self.location,
            "key": self.key,
            "text": self.text,
            "truncated": self.truncated,
            "standard_key": self.standard_key,
        }


@dataclass
class ImageInput:
    """A validated upload. `data` is the original, unmodified file bytes."""

    data: bytes
    sha256: str
    format: str
    mime_type: str
    width: int
    height: int
    mode: str
    bit_depth: int | None
    lossy: bool
    frame_count: int
    # Flat row-major uint8 samples (H*W*C) for LSB reading, or None when
    # the pixel format cannot be read without altering values.
    samples: np.ndarray | None
    samples_per_pixel: int
    sample_bands: tuple[str, ...]
    pixel_note: str | None
    # Byte offset where the image data structurally ends, when the
    # container can be parsed; bytes after it are appended data.
    image_end_offset: int | None
    container_notes: list[str] = field(default_factory=list)
    metadata_texts: list[MetadataText] = field(default_factory=list)
    exif_tags: dict[int, bytes] = field(default_factory=dict)

    @property
    def pixel_count(self) -> int:
        return self.width * self.height

    @property
    def trailing_bytes(self) -> int:
        if self.image_end_offset is None:
            return 0
        return max(0, len(self.data) - self.image_end_offset)

    def summary(self) -> dict:
        return {
            "format": self.format,
            "mime_type": self.mime_type,
            "width": self.width,
            "height": self.height,
            "mode": self.mode,
            "bit_depth": self.bit_depth,
            "channels": list(self.sample_bands),
            "file_size_bytes": len(self.data),
            "sha256": self.sha256,
            "lossy": self.lossy,
            "frame_count": self.frame_count,
            "pixels_readable": self.samples is not None,
            "pixel_note": self.pixel_note,
            "image_end_offset": self.image_end_offset,
            "trailing_bytes": self.trailing_bytes,
            "container_notes": list(self.container_notes),
        }


@dataclass(frozen=True)
class RecordedConfig:
    """Embedding parameters StegoLab stored when it created an image."""

    method: str
    channel_mode: str
    lsb_bits: int
    embedding_mode: str
    # How the record was found: IMAGE_RECORD (the selected image itself)
    # or HASH_MATCH (identical bytes to one of the user's stego images).
    source: str
    payload_sha256: str | None = None


@dataclass
class Evidence:
    check: str
    passed: bool
    detail: str

    def to_dict(self) -> dict:
        return {"check": self.check, "passed": self.passed, "detail": self.detail}


@dataclass
class Configuration:
    """One concrete parameter set an adapter can try."""

    key: str
    label: str
    parameters: dict[str, Any]
    priority: int = 0


@dataclass
class RawExtraction:
    """
    Outcome of running one adapter configuration, before validation.

    payload is None when the framing itself was invalid; `reason` then
    says why (e.g. the length field exceeds the capacity).
    """

    payload: bytes | None
    framing: Framing
    evidence: list[Evidence] = field(default_factory=list)
    integrity: Evidence | None = None
    reason: str | None = None
    payload_truncated: bool = False
    extra: dict[str, Any] = field(default_factory=dict)
