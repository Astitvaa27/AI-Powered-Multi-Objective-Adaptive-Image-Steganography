"""
Format adapters for the automatic extraction pipeline.

Each adapter declares what it reads, when it applies, which parameter sets
it tries, which parameters it would need from the user, how its payload is
validated and what it cannot do. Adding a format means adding one adapter
to DEFAULT_ADAPTERS; the pipeline itself does not change.

Pixel-domain adapters read bits through lsb_service.read_lsb_bits, the
same reader the manual LSB extractor uses, and the StegoLab DCT/DWT
adapters call the existing extract_dct/extract_dwt functions.
"""

from __future__ import annotations

import base64
import binascii
import time
import zlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from backend.app.services.auto_extract.image_input import EXIF_IMAGE_DESCRIPTION
from backend.app.services.auto_extract.types import (
    Configuration,
    Evidence,
    Framing,
    ImageInput,
    Limits,
    RawExtraction,
    RecordedConfig,
)
from backend.app.services.auto_extract.validation import payload_digest
from backend.app.services.dct_service import calculate_dct_capacity, extract_dct
from backend.app.services.dwt_service import calculate_dwt_capacity, extract_dwt
from backend.app.services.embedding_service import extract_with_method
from backend.app.services.lsb_service import lsb_capacity_bits, read_lsb_bits


@dataclass
class ExtractionContext:
    limits: Limits
    deadline: float
    record: RecordedConfig | None = None
    path_provider: Callable[[], str] | None = None
    _path: str | None = field(default=None, init=False)

    def image_path(self) -> str:
        """Path of a file holding the original, unmodified bytes."""

        if self._path is None:
            if self.path_provider is None:
                raise RuntimeError("No image path available.")
            self._path = self.path_provider()
        return self._path

    def out_of_time(self) -> bool:
        return time.monotonic() >= self.deadline


class ExtractionAdapter(ABC):
    """Interface every supported format implements."""

    id: str
    name: str
    method: str  # LSB, DCT, DWT, APPENDED_DATA, EXIF
    family: str  # STEGOLAB, EXTERNAL, GENERIC
    source: str  # PIXELS or FILE_STRUCTURE
    supported_inputs: str
    detection: str
    validation_rules: str
    limitations: tuple[str, ...] = ()
    required_parameters: tuple[str, ...] = ()
    resource_cost: str = "low"
    # What automated tests demonstrate about compatibility. Kept factual.
    compatibility: str = ""

    def applicability(self, image: ImageInput, ctx: ExtractionContext) -> str | None:
        """None when the adapter applies, otherwise why it was skipped."""

        return None

    @abstractmethod
    def configurations(self, image: ImageInput, ctx: ExtractionContext) -> list[Configuration]:
        """Bounded, priority-ordered parameter sets to try."""

    @abstractmethod
    def extract(self, image: ImageInput, config: Configuration, ctx: ExtractionContext) -> RawExtraction:
        """Run one configuration. Must not modify image.data or image.samples."""

    def describe(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "method": self.method,
            "family": self.family,
            "source": self.source,
            "supported_inputs": self.supported_inputs,
            "detection": self.detection,
            "validation_rules": self.validation_rules,
            "required_parameters": list(self.required_parameters),
            "limitations": list(self.limitations),
            "resource_cost": self.resource_cost,
            "compatibility": self.compatibility,
        }


# --------------------------------------------------------------------------
# LSB helpers
# --------------------------------------------------------------------------

CHANNEL_LABELS = {
    "RGB": "all colours (R, G, B)",
    "RGBA": "all channels incl. alpha (R, G, B, A)",
    "R": "red channel",
    "G": "green channel",
    "B": "blue channel",
    "Gray": "grayscale",
}


def safe_reason(exc: Exception, fallback: str) -> str:
    """
    An extractor's error message, unless it might reveal server details
    (e.g. "Unable to read image: <path>"), in which case `fallback`.
    """

    message = str(exc)
    if not message or "/" in message or "\\" in message or len(message) > 200:
        return fallback
    return message


def lsb_channel_sets(image: ImageInput, include_alpha: bool) -> list[tuple[str, list[int]]]:
    bands = image.sample_bands
    if not bands:
        return []
    if bands[0] == "Gray":
        return [("Gray", [0])]
    sets = [("RGB", [0, 1, 2]), ("R", [0]), ("G", [1]), ("B", [2])]
    if include_alpha and "A" in bands:
        sets.insert(1, ("RGBA", [0, 1, 2, 3]))
    return sets


def _channel_indices(image: ImageInput, channel_mode: str) -> list[int]:
    return dict(lsb_channel_sets(image, include_alpha=True))[channel_mode]


def _capacity_bits(image: ImageInput, channels: list[int], bits: int) -> int:
    return lsb_capacity_bits(image.pixel_count, len(channels), bits)


def _read_lsb_bytes(
    image: ImageInput,
    channels: list[int],
    bits: int,
    bit_order: str,
    byte_count: int,
) -> bytes:
    stream = read_lsb_bits(
        image.samples,
        image.samples_per_pixel,
        channels,
        bits,
        byte_count * 8,
    )
    return np.packbits(stream, bitorder="little" if bit_order == "LSB_FIRST" else "big").tobytes()


def _lsb_label(channel_mode: str, bits: int, bit_order: str | None = None) -> str:
    label = f"{CHANNEL_LABELS[channel_mode]}, {bits} bit{'s' if bits > 1 else ''} per value"
    if bit_order == "LSB_FIRST":
        label += ", bytes packed LSB-first"
    return label


class _LsbAdapter(ExtractionAdapter):
    method = "LSB"
    source = "PIXELS"
    bits_options: tuple[int, ...] = (1, 2, 3)
    bit_orders: tuple[str, ...] = ("MSB_FIRST",)
    include_alpha = False

    def applicability(self, image, ctx):
        if image.samples is None:
            return image.pixel_note or "Pixel samples are not readable for this image."
        return None

    def configurations(self, image, ctx):
        configs = []
        channel_sets = lsb_channel_sets(image, self.include_alpha)
        # Common settings first: 1 bit per value before 2 and 3, all
        # channels before single channels.
        for bits in self.bits_options:
            for set_index, (channel_mode, _) in enumerate(channel_sets):
                for order_index, order in enumerate(self.bit_orders):
                    configs.append(
                        Configuration(
                            key=f"{self.id}:{channel_mode}:{bits}:{order}",
                            label=_lsb_label(channel_mode, bits, order),
                            parameters={
                                "channel_mode": channel_mode,
                                "lsb_bits": bits,
                                "bit_order": order,
                                "traversal": "row-major, pixel-interleaved",
                            },
                            priority=bits * 100 + set_index * 10 + order_index,
                        )
                    )
        return sorted(configs, key=lambda c: c.priority)


class StegoLabLsbAdapter(_LsbAdapter):
    id = "STEGOLAB_LSB"
    name = "StegoLab pixel bits (LSB)"
    family = "STEGOLAB"
    supported_inputs = "Lossless RGB/RGBA/grayscale images (PNG, BMP, TIFF, PPM, lossless WebP)."
    detection = "A 32-bit big-endian length header in the low bits must declare a size that fits the image."
    validation_rules = (
        "Length header within capacity; zero padding after the payload where StegoLab adds it; "
        "content must be strict UTF-8 text (3+ characters) or a known file type. Verified only when "
        "it matches a message StegoLab stored for your account."
    )
    limitations = (
        "No checksum in this format, so matches from other accounts or tools are rated Plausible at best.",
        "Destroyed by JPEG compression, resizing, cropping or colour changes.",
    )
    compatibility = "Round-trip tested with StegoLab's own embed_lsb for every channel mode and 1-3 bits."

    def extract(self, image, config, ctx):
        params = config.parameters
        channels = _channel_indices(image, params["channel_mode"])
        bits = params["lsb_bits"]
        capacity_bits = _capacity_bits(image, channels, bits)

        if capacity_bits < 32:
            return RawExtraction(None, Framing.LENGTH, reason="Image too small for a length header.")

        capacity_bytes = (capacity_bits - 32) // 8
        header = _read_lsb_bytes(image, channels, bits, "MSB_FIRST", 4)
        length = int.from_bytes(header, "big")

        if length == 0:
            return RawExtraction(None, Framing.LENGTH, reason="Length header is zero.")
        if length > capacity_bytes:
            return RawExtraction(
                None,
                Framing.LENGTH,
                reason=f"Length header ({length:,} bytes) exceeds this layout's capacity ({capacity_bytes:,} bytes).",
            )
        if length > ctx.limits.max_payload_bytes:
            return RawExtraction(
                None,
                Framing.LENGTH,
                reason=f"Declared payload ({length:,} bytes) is above the automatic-extraction limit.",
            )

        total_bits = 32 + length * 8
        sample_bits = -(-total_bits // bits) * bits
        stream = read_lsb_bits(image.samples, image.samples_per_pixel, channels, bits, sample_bits)
        payload = np.packbits(stream[32:total_bits]).tobytes()

        evidence = [
            Evidence(
                "Length header",
                True,
                f"Declares {length:,} bytes, which fits the {capacity_bytes:,}-byte capacity of this layout.",
            )
        ]

        padding = stream[total_bits:]
        if padding.size:
            evidence.append(
                Evidence(
                    "Padding bits",
                    not padding.any(),
                    "The unused bits after the payload are zero, as StegoLab writes them."
                    if not padding.any()
                    else "The unused bits after the payload are not zero, which StegoLab would not produce.",
                )
            )

        return RawExtraction(payload, Framing.LENGTH, evidence=evidence)


class SteganoLsbAdapter(_LsbAdapter):
    id = "STEGANO_LSB"
    name = "Decimal length prefix LSB (stegano library format)"
    family = "EXTERNAL"
    supported_inputs = "Lossless RGB/RGBA images."
    detection = "The low bits must start with an ASCII decimal byte count followed by ':' (e.g. '12:')."
    validation_rules = "Prefix syntax and declared length within capacity; content must be strict UTF-8 text (3+ characters) or a known file type."
    limitations = (
        "Only the default sequential pixel order is searched; stegano's optional pseudo-random generators "
        "(e.g. eratosthenes, fibonacci) and shift values are not.",
        "No checksum; matches are rated Plausible at best.",
    )
    compatibility = (
        "Tested against images produced by the stegano Python library 3.0.0 (stegano.lsb.hide, default "
        "generator): RGB 1 bit per value. Other channel/bit settings are searched as variants of the same framing."
    )

    _MAX_PREFIX_DIGITS = 10

    def extract(self, image, config, ctx):
        params = config.parameters
        channels = _channel_indices(image, params["channel_mode"])
        bits = params["lsb_bits"]
        capacity_bytes = _capacity_bits(image, channels, bits) // 8

        head_len = min(capacity_bytes, self._MAX_PREFIX_DIGITS + 1)
        if head_len < 3:
            return RawExtraction(None, Framing.LENGTH, reason="Image too small for a length prefix.")

        head = _read_lsb_bytes(image, channels, bits, "MSB_FIRST", head_len)
        colon = head.find(b":")
        digits = head[:colon] if colon > 0 else b""

        if colon <= 0 or not digits.isdigit():
            return RawExtraction(None, Framing.LENGTH, reason="No '<digits>:' length prefix at the start of the bit stream.")
        if len(digits) > 1 and digits.startswith(b"0"):
            return RawExtraction(None, Framing.LENGTH, reason="Length prefix has a leading zero.")

        length = int(digits)
        prefix_len = colon + 1

        if length == 0:
            return RawExtraction(None, Framing.LENGTH, reason="Length prefix is zero.")
        if prefix_len + length > capacity_bytes:
            return RawExtraction(None, Framing.LENGTH, reason=f"Length prefix ({length:,} bytes) exceeds this layout's capacity.")
        if length > ctx.limits.max_payload_bytes:
            return RawExtraction(None, Framing.LENGTH, reason="Declared payload is above the automatic-extraction limit.")

        data = _read_lsb_bytes(image, channels, bits, "MSB_FIRST", prefix_len + length)

        return RawExtraction(
            data[prefix_len:],
            Framing.LENGTH,
            evidence=[
                Evidence(
                    "Length prefix",
                    True,
                    f"Starts with '{length}:', declaring {length:,} bytes, which fits this layout's capacity.",
                )
            ],
        )


TERMINATORS = (
    (b"\x00", "zero byte"),
    (b"$t3g0", "'$t3g0'"),
    (b"#####", "'#####'"),
    (b"*^*^*", "'*^*^*'"),
)


class TerminatedTextLsbAdapter(_LsbAdapter):
    id = "TERMINATED_TEXT_LSB"
    name = "Delimiter-terminated text in pixel bits (generic)"
    family = "GENERIC"
    supported_inputs = "Lossless RGB/RGBA/grayscale images."
    detection = (
        "Readable text in the low bits that ends at a zero byte or a common delimiter "
        "('$t3g0', '#####', '*^*^*'), with MSB-first or LSB-first byte packing."
    )
    validation_rules = (
        "All bytes before the delimiter must be strict UTF-8 printable text; at least 8 characters for Plausible, "
        "shorter runs are reported as Unverified."
    )
    limitations = (
        "Heuristic: this is a common convention, not a specific tool. No checksum.",
        "Only 1-2 bits per value and the first 64 KB of the bit stream are searched.",
    )
    compatibility = "Tested with an independent reference embedder written for the test suite; no third-party tool is claimed."
    bits_options = (1, 2)
    bit_orders = ("MSB_FIRST", "LSB_FIRST")
    include_alpha = True
    resource_cost = "moderate"

    SCAN_BYTES = 64 * 1024

    def extract(self, image, config, ctx):
        params = config.parameters
        channels = _channel_indices(image, params["channel_mode"])
        bits = params["lsb_bits"]
        capacity_bytes = _capacity_bits(image, channels, bits) // 8
        scan = min(capacity_bytes, self.SCAN_BYTES, ctx.limits.max_payload_bytes + 8)

        if scan < 2:
            return RawExtraction(None, Framing.TERMINATOR, reason="Image too small.")

        buffer = _read_lsb_bytes(image, channels, bits, params["bit_order"], scan)

        best: tuple[int, str] | None = None
        for marker, name in TERMINATORS:
            index = buffer.find(marker)
            if index >= 0 and (best is None or index < best[0]):
                best = (index, name)

        if best is None:
            return RawExtraction(None, Framing.TERMINATOR, reason=f"No delimiter in the first {scan:,} bytes.")
        if best[0] == 0:
            return RawExtraction(None, Framing.TERMINATOR, reason="The bit stream starts with a delimiter (nothing before it).")

        return RawExtraction(
            buffer[:best[0]],
            Framing.TERMINATOR,
            evidence=[Evidence("Delimiter", True, f"The data ends at a {best[1]} delimiter after {best[0]:,} bytes.")],
        )


# --------------------------------------------------------------------------
# StegoLab transform-domain methods (existing implementations)
# --------------------------------------------------------------------------


class _StegoLabTransformAdapter(ExtractionAdapter):
    family = "STEGOLAB"
    source = "PIXELS"
    resource_cost = "moderate"
    supported_inputs = "Images produced by StegoLab (blue channel of an RGB image)."
    validation_rules = (
        "32-bit length header within capacity (checked by the extractor); content must be strict UTF-8 text "
        "(3+ characters) or a known file type."
    )

    def applicability(self, image, ctx):
        if image.pixel_count > ctx.limits.max_transform_pixels:
            return (
                f"Skipped: the image has more than {ctx.limits.max_transform_pixels:,} pixels, "
                "the limit for transform-domain search."
            )
        return None

    def configurations(self, image, ctx):
        return [Configuration(key=self.id, label="StegoLab default parameters", parameters={})]

    def _capacity(self, image: ImageInput) -> int:
        raise NotImplementedError

    def _run(self, path: str) -> bytes:
        raise NotImplementedError

    def extract(self, image, config, ctx):
        try:
            payload = self._run(ctx.image_path())
        except ValueError as exc:
            return RawExtraction(None, Framing.LENGTH, reason=safe_reason(exc, "The image could not be read with this method."))
        except Exception:
            return RawExtraction(None, Framing.LENGTH, reason="The image could not be read with this method.")

        if not payload:
            return RawExtraction(None, Framing.LENGTH, reason="Length header is zero.")

        return RawExtraction(
            payload,
            Framing.LENGTH,
            evidence=[
                Evidence(
                    "Length header",
                    True,
                    f"Declares {len(payload):,} bytes, which fits this image's {self._capacity(image):,}-byte capacity.",
                )
            ],
        )


class StegoLabDctAdapter(_StegoLabTransformAdapter):
    id = "STEGOLAB_DCT"
    name = "StegoLab frequency blocks (DCT)"
    method = "DCT"
    detection = "Sign of the (4,3) DCT coefficient in each 8×8 blue-channel block; 32-bit length header first."
    limitations = ("No checksum; matches from outside your account are rated Plausible at best.",)
    compatibility = "Round-trip tested with StegoLab's own embed_dct."

    def _capacity(self, image):
        return calculate_dct_capacity(image.width, image.height)

    def _run(self, path):
        return extract_dct(path)


class StegoLabDwtAdapter(_StegoLabTransformAdapter):
    id = "STEGOLAB_DWT"
    name = "StegoLab wavelet detail (DWT)"
    method = "DWT"
    detection = "Quantisation of 1-level Haar HH coefficients in the blue channel; 32-bit length header first."
    limitations = ("No checksum; matches from outside your account are rated Plausible at best.",)
    compatibility = "Round-trip tested with StegoLab's own embed_dwt."

    def _capacity(self, image):
        return calculate_dwt_capacity(image.width, image.height)

    def _run(self, path):
        return extract_dwt(path)


# --------------------------------------------------------------------------
# StegoLab record (exact configuration stored at embedding time)
# --------------------------------------------------------------------------


class StegoLabRecordAdapter(ExtractionAdapter):
    id = "STEGOLAB_RECORD"
    name = "StegoLab record (exact settings used to hide it)"
    method = "RECORD"
    family = "STEGOLAB"
    source = "PIXELS"
    supported_inputs = "Images created in your StegoLab account (matched by record or identical file bytes)."
    detection = "The image itself, or a byte-identical file, has a stored embedding record."
    validation_rules = "Verified when the extracted bytes match the SHA-256 of the message StegoLab stored when hiding it."
    limitations = ("A matching record is only a hint; the extraction is still checked against the stored message hash.",)
    compatibility = "Uses the same extractor as manual extraction."

    def applicability(self, image, ctx):
        if ctx.record is None:
            return "No StegoLab record matches this image."
        return None

    def configurations(self, image, ctx):
        record = ctx.record
        assert record is not None
        if record.method == "LSB":
            label = _lsb_label(record.channel_mode, record.lsb_bits)
            parameters = {"channel_mode": record.channel_mode, "lsb_bits": record.lsb_bits}
        else:
            label = "StegoLab default parameters"
            parameters = {}
        return [
            Configuration(
                key=f"{self.id}:{record.method}",
                label=f"{record.method}: {label}",
                parameters={"method": record.method, **parameters, "embedding_mode": record.embedding_mode},
            )
        ]

    def extract(self, image, config, ctx):
        record = ctx.record
        assert record is not None
        try:
            payload = extract_with_method(
                record.method,
                image_path=ctx.image_path(),
                channel_mode=record.channel_mode,
                lsb_bits=record.lsb_bits,
            )
        except ValueError as exc:
            detail = safe_reason(exc, "the file could not be read")
            return RawExtraction(None, Framing.LENGTH, reason=f"The recorded settings did not yield a payload: {detail}")
        except Exception:
            return RawExtraction(None, Framing.LENGTH, reason="The recorded settings could not be applied to this file.")

        if not payload:
            return RawExtraction(None, Framing.LENGTH, reason="Length header is zero.")

        source = "this image" if record.source == "IMAGE_RECORD" else "an identical image in your history"
        evidence = [Evidence("StegoLab record", True, f"Settings recorded by StegoLab for {source} were used.")]

        integrity = None
        if record.payload_sha256:
            matches = payload_digest(payload) == record.payload_sha256.lower()
            integrity = Evidence(
                "Stored message hash",
                matches,
                "Matches the SHA-256 of the message StegoLab stored when hiding it."
                if matches
                else "Does not match the message StegoLab stored for this image; the file may have been modified.",
            )

        return RawExtraction(payload, Framing.LENGTH, evidence=evidence, integrity=integrity)


# --------------------------------------------------------------------------
# File-structure adapters
# --------------------------------------------------------------------------


class AppendedDataAdapter(ExtractionAdapter):
    id = "APPENDED_DATA"
    name = "Data appended after the end of the image"
    method = "APPENDED_DATA"
    family = "GENERIC"
    source = "FILE_STRUCTURE"
    supported_inputs = "PNG (after IEND), JPEG (after EOI), BMP (after pixel data), WebP (after RIFF size)."
    detection = "Bytes found beyond the structural end of the image data."
    validation_rules = "Content must be text (4+ characters) or a known file signature; ZIP directories are listed, never unpacked."
    limitations = (
        "TIFF and PGM/PPM trailing data is not checked.",
        "Appended data is stripped by most image editors and upload services.",
    )
    compatibility = "Tested with files built by concatenating an image and a payload (the 'copy /b' technique)."

    def applicability(self, image, ctx):
        if image.image_end_offset is None:
            return "The end of the image data could not be determined for this file."
        trailing = image.data[image.image_end_offset:]
        if not trailing:
            return "No data follows the end of the image."
        if len(trailing) < 4 or len(set(trailing)) == 1:
            return f"{len(trailing)} byte(s) of padding follow the image; ignored."
        return None

    def configurations(self, image, ctx):
        return [Configuration(key=self.id, label=f"bytes after offset {image.image_end_offset:,}", parameters={"offset": image.image_end_offset})]

    def extract(self, image, config, ctx):
        offset = image.image_end_offset
        assert offset is not None
        trailing = image.data[offset:]
        truncated = len(trailing) > ctx.limits.max_payload_bytes
        return RawExtraction(
            trailing[:ctx.limits.max_payload_bytes],
            Framing.CONTAINER,
            evidence=[
                Evidence(
                    "End of image",
                    True,
                    f"The {image.format} image data ends at byte {offset:,}; {len(trailing):,} more bytes follow it.",
                )
            ],
            payload_truncated=truncated,
        )


class SteganoExifAdapter(ExtractionAdapter):
    id = "STEGANO_EXIF"
    name = "Compressed message in EXIF ImageDescription (stegano exifHeader format)"
    method = "EXIF"
    family = "EXTERNAL"
    source = "FILE_STRUCTURE"
    supported_inputs = "JPEG and TIFF files with EXIF (also PNG eXIf)."
    detection = "The EXIF ImageDescription field holds a zlib stream that inflates to Base64."
    validation_rules = "Verified: the zlib stream's Adler-32 checksum must match and the Base64 layer must decode strictly."
    limitations = ("Stored in metadata, not pixels: removed by most upload services and 'strip metadata' tools.",)
    compatibility = "Tested against JPEG files produced by the stegano Python library 3.0.0 (stegano.exifHeader.hide)."

    def applicability(self, image, ctx):
        if EXIF_IMAGE_DESCRIPTION not in image.exif_tags:
            return "The file has no EXIF ImageDescription field."
        return None

    def configurations(self, image, ctx):
        return [Configuration(key=self.id, label="EXIF ImageDescription, zlib + Base64", parameters={"tag": "ImageDescription"})]

    def extract(self, image, config, ctx):
        raw = image.exif_tags[EXIF_IMAGE_DESCRIPTION].rstrip(b"\x00")
        limit = ctx.limits.max_payload_bytes * 2

        decompressor = zlib.decompressobj()
        try:
            inflated = decompressor.decompress(raw, limit)
        except zlib.error:
            return RawExtraction(None, Framing.CONTAINER, reason="ImageDescription is not zlib data (an ordinary description; see metadata).")

        if decompressor.unconsumed_tail:
            return RawExtraction(None, Framing.CONTAINER, reason="The compressed field inflates beyond the automatic-extraction limit.")
        if not decompressor.eof:
            return RawExtraction(None, Framing.CONTAINER, reason="The zlib stream is incomplete, so its checksum could not be verified.")

        try:
            payload = base64.b64decode(inflated, validate=True)
        except (binascii.Error, ValueError):
            return RawExtraction(None, Framing.CONTAINER, reason="The inflated field is not valid Base64.")

        return RawExtraction(
            payload,
            Framing.CONTAINER,
            evidence=[Evidence("Base64 layer", True, "The inflated field is strictly valid Base64.")],
            integrity=Evidence("zlib checksum", True, "The zlib stream decompressed completely and its Adler-32 checksum matched."),
        )


def default_adapters() -> list[ExtractionAdapter]:
    """Adapters in pipeline order: record, file structure, then pixels."""

    return [
        StegoLabRecordAdapter(),
        AppendedDataAdapter(),
        SteganoExifAdapter(),
        StegoLabLsbAdapter(),
        SteganoLsbAdapter(),
        StegoLabDctAdapter(),
        StegoLabDwtAdapter(),
        TerminatedTextLsbAdapter(),
    ]
