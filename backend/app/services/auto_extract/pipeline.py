"""
Automatic hidden-message detection and extraction pipeline.

run_auto_extraction() is a generator: it yields progress events as each
stage actually starts and finishes, then a final {"type": "result"} event.
The API streams these events to the browser, or collects only the result.

Stages
  validate             (done by load_image_input before the generator runs)
  records              exact settings stored by StegoLab, checked by hash
  containers           appended data, EXIF formats, metadata text
  search               bounded LSB / DCT / DWT configuration search
  validate_candidates  framing, integrity and content checks
  steganalysis         optional classifier signal (never decides the result)
  result               ranking and the final report
"""

from __future__ import annotations

import base64
import tempfile
import time
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from backend.app.services.auto_extract.adapters import (
    ExtractionAdapter,
    ExtractionContext,
    default_adapters,
)
from backend.app.services.auto_extract.types import (
    VALIDATION_RANK,
    Configuration,
    Framing,
    ImageInput,
    Limits,
    RawExtraction,
    RecordedConfig,
    Validation,
)
from backend.app.services.auto_extract.validation import (
    MAX_TEXT_CHARS_RETURNED,
    AssessedPayload,
    assess,
    explain,
    payload_digest,
)

STAGES = (
    ("validate", "Validating image"),
    ("records", "Checking StegoLab records"),
    ("containers", "Checking known formats"),
    ("search", "Searching supported extraction methods"),
    ("validate_candidates", "Validating candidate payloads"),
    ("steganalysis", "Steganalysis (supporting signal)"),
    ("result", "Preparing the result"),
)
STAGE_LABELS = dict(STAGES)

_STAGE_OF_SOURCE = {"FILE_STRUCTURE": "containers", "PIXELS": "search"}

_FRAMING_RANK = {Framing.LENGTH: 0, Framing.CONTAINER: 1, Framing.TERMINATOR: 2}

MAX_CANDIDATES_RETURNED = 10

_CHANNEL_MEMBERS = {
    "RGB": {"R", "G", "B"},
    "RGBA": {"R", "G", "B", "A"},
    "R": {"R"},
    "G": {"G"},
    "B": {"B"},
    "Gray": {"Gray"},
}

STEGANALYSIS_NOTE = (
    "The classifier estimates whether the image's statistics resemble images that contain hidden data. "
    "It cannot recover a message, a high value does not prove one exists, and its probability is not "
    "calibrated for images from other tools or sources. It does not affect the extraction result."
)

LIMITATIONS = (
    "Only the methods listed under 'What was tested' are searched. No tool can detect every steganography "
    "format: tools differ in algorithms, bit order, encryption and keys.",
    "Formats without a checksum (StegoLab LSB/DCT/DWT, stegano LSB, delimiter text) are rated Plausible at most, "
    "unless the image matches a message stored in your StegoLab history.",
    "JPEG-domain tools (e.g. steghide, OutGuess, F5, JSteg), password-protected formats and methods that "
    "need a secret key or the original cover image are not supported.",
    "Steganalysis is a statistical estimate and is never used to decide whether a message was found.",
)


@dataclass
class _Attempt:
    adapter: ExtractionAdapter
    config: Configuration | None
    outcome: str  # CANDIDATE, REJECTED, ERROR, SKIPPED, NOT_TESTED, SUPERSEDED, DUPLICATE
    reason: str | None = None
    raw: RawExtraction | None = None

    def to_dict(self) -> dict:
        return {
            "adapter": self.adapter.id,
            "adapter_name": self.adapter.name,
            "configuration": self.config.label if self.config else None,
            "parameters": self.config.parameters if self.config else None,
            "outcome": self.outcome,
            "reason": self.reason,
        }


@dataclass
class _Candidate:
    adapter: ExtractionAdapter
    config: Configuration
    raw: RawExtraction
    assessed: AssessedPayload
    digest: str
    attempt: _Attempt
    also_found_by: list[tuple[ExtractionAdapter, Configuration]]

    @property
    def validation(self) -> Validation:
        assert self.assessed.validation is not None
        return self.assessed.validation

    def sort_key(self, order: dict[str, int]) -> tuple:
        return (
            VALIDATION_RANK[self.validation],
            0 if self.adapter.id == "STEGOLAB_RECORD" else 1,
            _FRAMING_RANK[self.raw.framing],
            order.get(self.adapter.id, 99),
            self.config.priority,
        )


def _stage(stage: str, status: str, detail: str | None = None, **extra) -> dict:
    event = {"type": "stage", "stage": stage, "label": STAGE_LABELS[stage], "status": status, "detail": detail}
    event.update(extra)
    return event


def _sanitise_model_error(error: str | None) -> str:
    if not error:
        return "The steganalysis model is unavailable."
    if "not found" in error.lower():
        return "The steganalysis model is not installed on this server."
    return "The steganalysis model could not be loaded."


def _default_probe_factory():
    from backend.app.services.adaptive_embedding_service import _SteganalysisProbe

    return _SteganalysisProbe()


def _serialise_candidate(candidate: _Candidate, index: int) -> dict:
    payload = candidate.raw.payload or b""
    assessed = candidate.assessed

    text = assessed.text
    text_truncated = False
    if text is not None and len(text) > MAX_TEXT_CHARS_RETURNED:
        text = text[:MAX_TEXT_CHARS_RETURNED]
        text_truncated = True

    include_base64 = assessed.kind == "BINARY" or text_truncated

    return {
        "id": f"c{index + 1}",
        "adapter": candidate.adapter.id,
        "adapter_name": candidate.adapter.name,
        "method": candidate.adapter.method,
        "family": candidate.adapter.family,
        "source": candidate.adapter.source,
        "configuration": candidate.config.label,
        "parameters": candidate.config.parameters,
        "validation": candidate.validation.value,
        "explanation": explain(candidate.validation, candidate.raw.framing),
        "evidence": [item.to_dict() for item in assessed.evidence],
        "notes": assessed.notes,
        "requires_key": assessed.requires_key,
        "key_hint": assessed.key_hint,
        "payload": {
            "kind": assessed.kind,
            "size_bytes": len(payload),
            "sha256": candidate.digest,
            "text": text,
            "text_truncated": text_truncated,
            "base64": base64.b64encode(payload).decode("ascii") if include_base64 else None,
            "detected_type": assessed.detected_type,
            "archive_entries": assessed.archive_entries,
            "truncated": candidate.raw.payload_truncated,
        },
        "also_found_by": [
            {"adapter": adapter.id, "adapter_name": adapter.name, "configuration": config.label}
            for adapter, config in candidate.also_found_by
        ],
    }


def _guidance(image: ImageInput, truncated: bool, not_tested: int, has_key_hint: bool) -> list[str]:
    tips: list[str] = []
    if image.lossy:
        tips.append(
            f"This is a lossy {image.format} file. Lossy compression rewrites pixel values, which destroys "
            "pixel-bit (LSB) messages. Ask the sender for the original PNG or BMP file."
        )
    tips.append(
        "Images that were resized, cropped, screenshotted, or re-saved by a chat app or social network usually "
        "lose hidden data. Use the exact file that was produced by the hiding tool."
    )
    if has_key_hint:
        tips.append(
            "Something encrypted or random-looking was recovered. It probably needs the password or key that was "
            "used to hide it, and the same tool to decrypt it; StegoLab does not bypass encryption."
        )
    else:
        tips.append(
            "Many tools encrypt the message with a password (for example steghide or OpenStego with a password). "
            "Those messages can only be read with the original tool and the password."
        )
    tips.append(
        "Some methods hide data using a secret key or need the original (cover) image to locate the bits; "
        "those cannot be found by searching."
    )
    tips.append(
        "If you know which tool and settings were used, try Manual extraction below or check the tool's own "
        "decoder. The formats StegoLab can search are listed under 'What was tested'."
    )
    if truncated:
        tips.insert(
            0,
            f"The search stopped at the time limit; {not_tested} configuration(s) were not tested. "
            "Try again with a smaller image.",
        )
    if image.samples is None and image.pixel_note:
        tips.insert(0, image.pixel_note)
    return tips


def run_auto_extraction(
    image: ImageInput,
    *,
    limits: Limits,
    record: RecordedConfig | None = None,
    image_path: str | None = None,
    run_steganalysis: bool = True,
    steganalysis_probe_factory: Callable[[], object] | None = None,
    adapters: list[ExtractionAdapter] | None = None,
    validate_ms: int = 0,
) -> Iterator[dict]:
    """
    Run every applicable adapter against `image` and yield progress events,
    ending with {"type": "result", "result": {...}}.

    image_path, when given, must point at a file with exactly image.data
    (e.g. the stored upload). Otherwise a private temporary copy is
    written on first use and removed when the generator finishes or is
    closed.
    """

    started = time.monotonic()
    adapters = adapters if adapters is not None else default_adapters()
    adapter_order = {adapter.id: index for index, adapter in enumerate(adapters)}

    stage_log: list[dict] = [
        {"stage": "validate", "label": STAGE_LABELS["validate"], "status": "completed", "duration_ms": validate_ms, "detail": None}
    ]

    validate_detail = f"{image.format}, {image.width}×{image.height}, {image.mode}"
    stage_log[0]["detail"] = validate_detail
    yield _stage("validate", "completed", validate_detail, duration_ms=validate_ms)

    with ExitStack() as stack:

        def provide_path() -> str:
            if image_path:
                return image_path
            work_dir = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="stegolab_auto_")))
            path = work_dir / f"input.{image.format.lower()}"
            path.write_bytes(image.data)
            return str(path)

        ctx = ExtractionContext(
            limits=limits,
            deadline=started + limits.time_budget_seconds,
            record=record,
            path_provider=provide_path,
        )

        attempts: list[_Attempt] = []
        results: list[tuple[ExtractionAdapter, Configuration, RawExtraction, _Attempt]] = []
        tested_methods: list[dict] = []
        truncated = False

        def run_adapter(adapter: ExtractionAdapter) -> int:
            nonlocal truncated
            skip_reason = adapter.applicability(image, ctx)
            entry = {**adapter.describe(), "applicable": skip_reason is None, "skipped_reason": skip_reason, "configurations_tested": 0, "configurations_total": 0}
            tested_methods.append(entry)

            if skip_reason is not None:
                attempts.append(_Attempt(adapter, None, "SKIPPED", skip_reason))
                return 0

            configs = adapter.configurations(image, ctx)
            entry["configurations_total"] = len(configs)

            for config in configs:
                if ctx.out_of_time():
                    truncated = True
                    attempts.append(_Attempt(adapter, config, "NOT_TESTED", "Time budget reached."))
                    continue
                try:
                    raw = adapter.extract(image, config, ctx)
                except Exception:
                    attempts.append(_Attempt(adapter, config, "ERROR", "This configuration could not be evaluated."))
                    entry["configurations_tested"] += 1
                    continue

                entry["configurations_tested"] += 1
                if raw.payload is None:
                    attempts.append(_Attempt(adapter, config, "REJECTED", raw.reason))
                else:
                    attempt = _Attempt(adapter, config, "CANDIDATE", None, raw)
                    attempts.append(attempt)
                    results.append((adapter, config, raw, attempt))

            return entry["configurations_tested"]

        # -- records --------------------------------------------------------
        t0 = time.monotonic()
        yield _stage("records", "running")
        record_adapters = [a for a in adapters if a.id == "STEGOLAB_RECORD"]
        for adapter in record_adapters:
            run_adapter(adapter)
        if record is None:
            records_detail = "No StegoLab record matches this image; continuing with format detection."
        else:
            records_detail = (
                f"Found a StegoLab record ({record.method}); its settings were tried first."
                if record.source == "IMAGE_RECORD"
                else f"This file is identical to a stego image in your history ({record.method}); its settings were tried first."
            )
        records_ms = int((time.monotonic() - t0) * 1000)
        stage_log.append({"stage": "records", "label": STAGE_LABELS["records"], "status": "completed", "duration_ms": records_ms, "detail": records_detail})
        yield _stage("records", "completed", records_detail, duration_ms=records_ms)

        # -- containers and pixel search -----------------------------------
        for stage, source in (("containers", "FILE_STRUCTURE"), ("search", "PIXELS")):
            t0 = time.monotonic()
            stage_adapters = [a for a in adapters if a.source == source and a.id != "STEGOLAB_RECORD"]
            total = sum(
                len(a.configurations(image, ctx)) if a.applicability(image, ctx) is None else 0
                for a in stage_adapters
            )
            done = 0
            yield _stage(stage, "running", progress={"done": 0, "total": total})

            for adapter in stage_adapters:
                done += run_adapter(adapter)
                yield _stage(
                    stage,
                    "running",
                    f"{adapter.name}: checked",
                    progress={"done": done, "total": total},
                )

            stage_ms = int((time.monotonic() - t0) * 1000)
            found = sum(1 for (a, *_rest) in results if a.source == source)
            if stage == "containers":
                detail = f"{done} file-structure check(s); {found} produced data."
            else:
                detail = f"{done} of {total} configuration(s) tested; {found} produced data."
                if truncated:
                    detail += " Stopped at the time limit."
            status = "completed" if not (truncated and stage == "search") else "partial"
            stage_log.append({"stage": stage, "label": STAGE_LABELS[stage], "status": status, "duration_ms": stage_ms, "detail": detail})
            yield _stage(stage, status, detail, duration_ms=stage_ms, progress={"done": done, "total": total})

        # -- validation -----------------------------------------------------
        t0 = time.monotonic()
        yield _stage("validate_candidates", "running")
        by_digest: dict[str, _Candidate] = {}

        for adapter, config, raw, attempt in results:
            assessed = assess(raw)
            if assessed.validation is None:
                attempt.outcome = "REJECTED"
                attempt.reason = assessed.reason
                continue

            digest = payload_digest(raw.payload or b"")
            candidate = _Candidate(adapter, config, raw, assessed, digest, attempt, [])
            existing = by_digest.get(digest)

            if existing is None:
                by_digest[digest] = candidate
                continue

            better = candidate.sort_key(adapter_order) < existing.sort_key(adapter_order)
            keep, other = (candidate, existing) if better else (existing, candidate)
            keep.also_found_by.append((other.adapter, other.config))
            keep.also_found_by.extend(other.also_found_by)
            other.attempt.outcome = "DUPLICATE"
            other.attempt.reason = "Same payload as another configuration."
            by_digest[digest] = keep

        candidates = list(by_digest.values())

        # A delimiter match that merely contains a length-framed payload
        # (plus whatever follows it in the bit stream) adds nothing.
        strong_payloads = [c.raw.payload for c in candidates if c.raw.framing != Framing.TERMINATOR and c.raw.payload]
        kept: list[_Candidate] = []
        for candidate in candidates:
            payload = candidate.raw.payload or b""
            if candidate.raw.framing == Framing.TERMINATOR and any(strong in payload for strong in strong_payloads):
                candidate.attempt.outcome = "SUPERSEDED"
                candidate.attempt.reason = "Contains a payload already recovered with a length-framed format."
                continue
            kept.append(candidate)

        # Reading an accepted LSB message with the wrong bit depth or channel
        # subset yields garbage (or short printable fragments) from the same
        # pixels. Drop such unverified readings when they share channels with
        # an accepted LSB candidate; readings of disjoint channels and
        # recognised file types are kept.
        accepted_lsb_channels = [
            _CHANNEL_MEMBERS.get(c.config.parameters.get("channel_mode"), set())
            for c in kept
            if c.adapter.method in {"LSB", "RECORD"} and c.validation != Validation.UNVERIFIED
        ]
        filtered: list[_Candidate] = []
        for candidate in kept:
            channels = _CHANNEL_MEMBERS.get(candidate.config.parameters.get("channel_mode"), set())
            if (
                candidate.validation == Validation.UNVERIFIED
                and candidate.adapter.method == "LSB"
                and candidate.assessed.detected_type is None
                and any(channels & accepted for accepted in accepted_lsb_channels)
            ):
                candidate.attempt.outcome = "SUPERSEDED"
                candidate.attempt.reason = "Weak reading of the same pixels as an accepted message (a misaligned reading)."
                continue
            filtered.append(candidate)
        kept = filtered

        kept.sort(key=lambda c: c.sort_key(adapter_order))
        for candidate in kept:
            candidate.attempt.outcome = "CANDIDATE"

        validate_ms_stage = int((time.monotonic() - t0) * 1000)
        counts = {level: sum(1 for c in kept if c.validation == level) for level in Validation}
        validation_detail = (
            f"{len(results)} raw result(s): {counts[Validation.VERIFIED]} verified, "
            f"{counts[Validation.PLAUSIBLE]} plausible, {counts[Validation.UNVERIFIED]} unverified."
        )
        stage_log.append({"stage": "validate_candidates", "label": STAGE_LABELS["validate_candidates"], "status": "completed", "duration_ms": validate_ms_stage, "detail": validation_detail})
        yield _stage("validate_candidates", "completed", validation_detail, duration_ms=validate_ms_stage)

        # -- steganalysis ---------------------------------------------------
        t0 = time.monotonic()
        steganalysis = {
            "requested": run_steganalysis,
            "available": False,
            "ran": False,
            "predicted_class": None,
            "stego_probability": None,
            "skipped_reason": None,
            "note": STEGANALYSIS_NOTE,
        }

        if not run_steganalysis:
            steganalysis["skipped_reason"] = "Not requested."
        elif image.pixel_count > limits.max_transform_pixels:
            steganalysis["skipped_reason"] = "The image is too large for the steganalysis step."
        elif ctx.out_of_time():
            steganalysis["skipped_reason"] = "Time budget reached."
        else:
            yield _stage("steganalysis", "running")
            try:
                probe = (steganalysis_probe_factory or _default_probe_factory)()
                if not getattr(probe, "available", False):
                    steganalysis["skipped_reason"] = _sanitise_model_error(getattr(probe, "error", None))
                else:
                    steganalysis["available"] = True
                    prediction = probe.predict(ctx.image_path())
                    steganalysis.update(
                        ran=True,
                        predicted_class=prediction.get("predicted_class"),
                        stego_probability=prediction.get("stego_probability"),
                    )
            except Exception:
                steganalysis["skipped_reason"] = "The steganalysis model could not analyse this image."

        stega_ms = int((time.monotonic() - t0) * 1000)
        stega_status = "completed" if steganalysis["ran"] else "skipped"
        stega_detail = (
            f"Classifier output: {steganalysis['predicted_class']}"
            if steganalysis["ran"]
            else steganalysis["skipped_reason"]
        )
        stage_log.append({"stage": "steganalysis", "label": STAGE_LABELS["steganalysis"], "status": stega_status, "duration_ms": stega_ms, "detail": stega_detail})
        yield _stage("steganalysis", stega_status, stega_detail, duration_ms=stega_ms)

    # Temporary files are gone from here on.

    # -- result -------------------------------------------------------------
    t0 = time.monotonic()
    yield _stage("result", "running")

    verified = [c for c in kept if c.validation == Validation.VERIFIED]
    plausible = [c for c in kept if c.validation == Validation.PLAUSIBLE]

    if verified:
        status = "VERIFIED"
        best = verified[0]
    elif len(plausible) == 1:
        status = "PLAUSIBLE"
        best = plausible[0]
    elif len(plausible) > 1:
        status = "AMBIGUOUS"
        best = None
    elif kept:
        status = "UNVERIFIED"
        best = None
    else:
        status = "NOT_FOUND"
        best = None

    serialised = [_serialise_candidate(c, i) for i, c in enumerate(kept[:MAX_CANDIDATES_RETURNED])]
    best_serialised = serialised[kept.index(best)] if best is not None else None

    custom_metadata = [m for m in image.metadata_texts if not m.standard_key and m.text.strip()]
    not_tested = sum(1 for a in attempts if a.outcome == "NOT_TESTED")

    if status == "VERIFIED":
        summary = f"A hidden message was found and verified ({best.adapter.name})."
    elif status == "PLAUSIBLE":
        summary = (
            f"A hidden message was found using {best.adapter.name}. Its structure is valid, "
            "but this format has no checksum, so it is not formally verified."
        )
    elif status == "AMBIGUOUS":
        summary = f"{len(plausible)} different plausible messages were found. Compare them below; StegoLab did not pick one for you."
    elif status == "UNVERIFIED":
        summary = "Some data was recovered, but none of it passed validation strongly enough to call it a hidden message."
    else:
        summary = "No supported hidden message was recovered using the methods tested."
        if custom_metadata:
            summary += " The file does contain readable metadata text (shown below)."

    warnings: list[str] = []
    if image.lossy:
        warnings.append(
            f"{image.format} is a lossy format. Pixel-bit (LSB) messages rarely survive lossy compression, "
            "so a negative result here is expected even if a message was hidden before compression."
        )
    if image.pixel_note:
        warnings.append(image.pixel_note)
    warnings.extend(image.container_notes)
    if truncated:
        warnings.append(f"The time limit was reached; {not_tested} configuration(s) were not tested.")
    if record is not None and record.payload_sha256 and not verified:
        warnings.append(
            "This image matches a StegoLab record, but the message read with the recorded settings does not match "
            "the stored message. The file may have been edited or re-saved."
        )

    has_key_hint = any(c.assessed.requires_key for c in kept)
    outcome_counts: dict[str, int] = {}
    for attempt in attempts:
        outcome_counts[attempt.outcome] = outcome_counts.get(attempt.outcome, 0) + 1

    result_ms = int((time.monotonic() - t0) * 1000)
    stage_log.append({"stage": "result", "label": STAGE_LABELS["result"], "status": "completed", "duration_ms": result_ms, "detail": None})

    result = {
        "status": status,
        "extraction_succeeded": status in {"VERIFIED", "PLAUSIBLE"},
        "summary": summary,
        "best_candidate": best_serialised,
        "candidates": serialised,
        "candidates_total": len(kept),
        "metadata_findings": [m.to_dict() for m in image.metadata_texts],
        "image": image.summary(),
        "record": (
            {
                "found": True,
                "source": record.source,
                "method": record.method,
                "channel_mode": record.channel_mode if record.method == "LSB" else None,
                "lsb_bits": record.lsb_bits if record.method == "LSB" else None,
                "embedding_mode": record.embedding_mode,
                "payload_hash_available": bool(record.payload_sha256),
            }
            if record
            else {"found": False}
        ),
        "methods_tested": tested_methods,
        "attempts": {
            "total": len(attempts),
            "by_outcome": outcome_counts,
            "details": [attempt.to_dict() for attempt in attempts],
        },
        "steganalysis": steganalysis,
        "warnings": warnings,
        "limitations": list(LIMITATIONS),
        "guidance": [] if status in {"VERIFIED", "PLAUSIBLE"} else _guidance(image, truncated, not_tested, has_key_hint),
        "ranking_basis": (
            "Candidates are ordered by validation level, then by how specific the format's framing is "
            "(StegoLab record, length field, container, delimiter). This is a heuristic ordering, not a probability."
        ),
        "time_budget_reached": truncated,
        "stages": stage_log,
        "processing_time_ms": int((time.monotonic() - started) * 1000) + validate_ms,
    }

    yield _stage("result", "completed", duration_ms=result_ms)
    yield {"type": "result", "result": result}


def collect_result(events: Iterator[dict]) -> dict:
    """Drain the event stream and return the final result."""

    result = None
    for event in events:
        if event.get("type") == "result":
            result = event["result"]
    if result is None:
        raise RuntimeError("The extraction pipeline ended without a result.")
    return result
