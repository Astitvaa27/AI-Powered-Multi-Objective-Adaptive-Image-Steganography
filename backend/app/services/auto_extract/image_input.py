"""
Stage A: validate an uploaded image and parse its container.

The original bytes are kept untouched. Pixel samples are read in the
image's own mode wherever that preserves the stored values; nothing is
re-encoded or converted to a lossy format.
"""

from __future__ import annotations

import hashlib
import io
import struct
import warnings
import zlib

import numpy as np
from PIL import Image, UnidentifiedImageError

from backend.app.services.auto_extract.types import (
    AutoExtractInputError,
    ImageInput,
    Limits,
    MetadataText,
)

# Pillow format name -> MIME type. Content sniffing decides the format;
# the filename extension is never trusted.
SUPPORTED_FORMATS = {
    "PNG": "image/png",
    "BMP": "image/bmp",
    "TIFF": "image/tiff",
    "PPM": "image/x-portable-anymap",
    "WEBP": "image/webp",
    "JPEG": "image/jpeg",
}

# Modes whose samples are 8-bit and can be read without changing values.
# Palette images are expanded to RGB, matching what the manual extractor
# (Image.convert("RGB")) reads.
_DIRECT_MODES = {"L": ("Gray",), "LA": ("Gray", "A"), "RGB": ("R", "G", "B"), "RGBA": ("R", "G", "B", "A")}

_MAX_METADATA_TEXT_CHARS = 4000
_MAX_METADATA_ITEMS = 50
_MAX_DECOMPRESSED_METADATA = 256 * 1024

STANDARD_METADATA_KEYS = {
    "software",
    "creation time",
    "author",
    "title",
    "description",
    "copyright",
    "comment",
    "disclaimer",
    "warning",
    "source",
    "date:create",
    "date:modify",
    "date:timestamp",
    "xml:com.adobe.xmp",
    "raw profile type exif",
    "raw profile type xmp",
    "raw profile type iptc",
    "raw profile type 8bim",
    "icc",
}

_KNOWN_PNG_CHUNKS = {
    b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS", b"cHRM", b"gAMA", b"iCCP",
    b"sBIT", b"sRGB", b"cICP", b"mDCv", b"cLLi", b"tEXt", b"zTXt", b"iTXt",
    b"bKGD", b"hIST", b"pHYs", b"sPLT", b"eXIf", b"tIME", b"acTL", b"fcTL",
    b"fdAT", b"oFFs", b"pCAL", b"sCAL", b"sTER", b"dSIG", b"iDOT", b"vpAg",
    b"caNv", b"orNT",
}

# EXIF tags inspected for text.
EXIF_IMAGE_DESCRIPTION = 0x010E
EXIF_XP_COMMENT = 0x9C9C
EXIF_IFD_POINTER = 0x8769
EXIF_USER_COMMENT = 0x9286


def _bounded_inflate(data: bytes, limit: int) -> tuple[bytes, bool]:
    """zlib-decompress at most `limit` bytes. Returns (data, truncated)."""

    decompressor = zlib.decompressobj()
    output = decompressor.decompress(data, limit)
    truncated = bool(decompressor.unconsumed_tail)
    return output, truncated


def _clip_text(text: str) -> tuple[str, bool]:
    if len(text) > _MAX_METADATA_TEXT_CHARS:
        return text[:_MAX_METADATA_TEXT_CHARS], True
    return text, False


def _metadata(location: str, key: str, text: str, truncated: bool = False) -> MetadataText:
    clipped, was_clipped = _clip_text(text)
    return MetadataText(
        location=location,
        key=key,
        text=clipped,
        truncated=truncated or was_clipped,
        standard_key=key.strip().lower() in STANDARD_METADATA_KEYS,
    )


# --------------------------------------------------------------------------
# Container parsers. Each returns (end_offset | None, notes, metadata, exif).
# --------------------------------------------------------------------------


def _parse_png(data: bytes):
    notes: list[str] = []
    texts: list[MetadataText] = []
    exif: bytes | None = None
    pos = 8

    while pos + 12 <= len(data):
        length = int.from_bytes(data[pos:pos + 4], "big")
        chunk_type = data[pos + 4:pos + 8]

        if length > len(data) - pos - 12:
            notes.append("A PNG chunk runs past the end of the file (truncated file).")
            return None, notes, texts, exif

        body = data[pos + 8:pos + 8 + length]
        stored_crc = int.from_bytes(data[pos + 8 + length:pos + 12 + length], "big")
        crc_ok = (zlib.crc32(chunk_type + body) & 0xFFFFFFFF) == stored_crc
        name = chunk_type.decode("latin-1")

        if not crc_ok:
            notes.append(f"PNG chunk {name!r} has a bad CRC (damaged or edited file).")

        if crc_ok and len(texts) < _MAX_METADATA_ITEMS:
            try:
                if chunk_type == b"tEXt":
                    key, _, value = body.partition(b"\x00")
                    texts.append(_metadata("PNG tEXt chunk", key.decode("latin-1"), value.decode("latin-1")))
                elif chunk_type == b"zTXt":
                    key, _, rest = body.partition(b"\x00")
                    value, cut = _bounded_inflate(rest[1:], _MAX_DECOMPRESSED_METADATA)
                    texts.append(_metadata("PNG zTXt chunk", key.decode("latin-1"), value.decode("latin-1"), cut))
                elif chunk_type == b"iTXt":
                    key, _, rest = body.partition(b"\x00")
                    compressed = rest[:1] == b"\x01"
                    rest = rest[2:]
                    _language, _, rest = rest.partition(b"\x00")
                    _translated, _, value = rest.partition(b"\x00")
                    cut = False
                    if compressed:
                        value, cut = _bounded_inflate(value, _MAX_DECOMPRESSED_METADATA)
                    texts.append(_metadata("PNG iTXt chunk", key.decode("latin-1"), value.decode("utf-8", "replace"), cut))
            except (zlib.error, UnicodeDecodeError):
                notes.append(f"PNG text chunk {name!r} could not be decoded.")

        if chunk_type == b"eXIf" and crc_ok:
            exif = body
        elif chunk_type not in _KNOWN_PNG_CHUNKS:
            notes.append(f"Non-standard PNG chunk {name!r} ({length} bytes).")

        pos += 12 + length

        if chunk_type == b"IEND":
            return pos, notes, texts, exif

    notes.append("No PNG IEND chunk found (truncated file).")
    return None, notes, texts, exif


def _parse_jpeg(data: bytes):
    notes: list[str] = []
    texts: list[MetadataText] = []
    exif: bytes | None = None
    n = len(data)
    pos = 2

    while pos < n:
        if data[pos] != 0xFF:
            notes.append("Unexpected bytes between JPEG segments.")
            return None, notes, texts, exif

        while pos < n and data[pos] == 0xFF:
            pos += 1
        if pos >= n:
            break

        marker = data[pos]
        pos += 1

        if marker == 0xD9:  # EOI
            return pos, notes, texts, exif
        if 0xD0 <= marker <= 0xD7 or marker == 0x01:
            continue

        if pos + 2 > n:
            break
        seg_len = int.from_bytes(data[pos:pos + 2], "big")
        if seg_len < 2 or pos + seg_len > n:
            notes.append("A JPEG segment runs past the end of the file (truncated file).")
            return None, notes, texts, exif

        segment = data[pos + 2:pos + seg_len]

        if marker == 0xFE and len(texts) < _MAX_METADATA_ITEMS:
            texts.append(_metadata("JPEG comment", "Comment", segment.decode("utf-8", "replace")))
        elif marker == 0xE1 and segment.startswith(b"Exif\x00\x00") and exif is None:
            exif = segment[6:]

        pos += seg_len

        if marker == 0xDA:  # start of scan: skip entropy-coded data
            while True:
                pos = data.find(b"\xff", pos)
                if pos < 0 or pos + 1 >= n:
                    notes.append("JPEG scan data has no end marker (truncated file).")
                    return None, notes, texts, exif
                follower = data[pos + 1]
                if follower == 0x00 or 0xD0 <= follower <= 0xD7:
                    pos += 2
                    continue
                if follower == 0xFF:
                    pos += 1
                    continue
                break

    notes.append("No JPEG end-of-image marker found (truncated file).")
    return None, notes, texts, exif


def _parse_bmp(data: bytes):
    notes: list[str] = []
    if len(data) < 54:
        return None, ["BMP header is truncated."], [], None

    declared_size = int.from_bytes(data[2:6], "little")
    pixel_offset = int.from_bytes(data[10:14], "little")
    header_size = int.from_bytes(data[14:18], "little")

    end: int | None = None
    if header_size >= 40:
        width = int.from_bytes(data[18:22], "little", signed=True)
        height = int.from_bytes(data[22:26], "little", signed=True)
        bit_count = int.from_bytes(data[28:30], "little")
        compression = int.from_bytes(data[30:34], "little")
        if compression in (0, 3) and bit_count:
            stride = ((abs(width) * bit_count + 31) // 32) * 4
            end = pixel_offset + stride * abs(height)

    if end is None:
        if 0 < declared_size <= len(data):
            end = declared_size
        else:
            notes.append("BMP layout could not be determined; trailing-data check skipped.")
            return None, notes, [], None
    elif declared_size > end and declared_size <= len(data):
        end = declared_size  # writer-declared padding

    return min(end, len(data)), notes, [], None


def _parse_webp(data: bytes):
    if len(data) < 12:
        return None, ["WebP header is truncated."], [], None
    riff_size = int.from_bytes(data[4:8], "little")
    end = 8 + riff_size + (riff_size & 1)
    if end > len(data):
        return None, ["WebP RIFF size exceeds the file (truncated file)."], [], None
    return end, [], [], None


def _webp_is_lossy(data: bytes) -> bool:
    pos = 12
    while pos + 8 <= len(data):
        fourcc = data[pos:pos + 4]
        size = int.from_bytes(data[pos + 4:pos + 8], "little")
        if fourcc == b"VP8L":
            return False
        if fourcc == b"VP8 ":
            return True
        pos += 8 + size + (size & 1)
    return True


_CONTAINER_PARSERS = {
    "PNG": _parse_png,
    "JPEG": _parse_jpeg,
    "BMP": _parse_bmp,
    "WEBP": _parse_webp,
}


# --------------------------------------------------------------------------
# EXIF (TIFF structure) parsing for a few text tags. Raw bytes are kept
# because some tools store binary data in ASCII-typed tags.
# --------------------------------------------------------------------------

_TIFF_TYPE_SIZES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8}


def parse_exif_tags(blob: bytes, wanted: set[int]) -> dict[int, bytes]:
    """Return raw values of the wanted tags from IFD0 and the Exif sub-IFD."""

    if blob.startswith(b"Exif\x00\x00"):
        blob = blob[6:]
    if len(blob) < 8:
        return {}

    if blob[:2] == b"II":
        endian = "<"
    elif blob[:2] == b"MM":
        endian = ">"
    else:
        return {}

    if struct.unpack(endian + "H", blob[2:4])[0] != 42:
        return {}

    found: dict[int, bytes] = {}

    def read_ifd(offset: int, depth: int) -> None:
        if depth > 2 or offset <= 0 or offset + 2 > len(blob):
            return
        count = struct.unpack(endian + "H", blob[offset:offset + 2])[0]
        for index in range(min(count, 512)):
            entry = offset + 2 + index * 12
            if entry + 12 > len(blob):
                return
            tag, field_type, value_count = struct.unpack(endian + "HHI", blob[entry:entry + 8])
            size = _TIFF_TYPE_SIZES.get(field_type, 1) * value_count
            raw = blob[entry + 8:entry + 12]
            if size <= 4:
                value = raw[:size]
            else:
                value_offset = struct.unpack(endian + "I", raw)[0]
                if value_offset + size > len(blob):
                    continue
                value = blob[value_offset:value_offset + size]

            if tag == EXIF_IFD_POINTER and len(value) == 4:
                read_ifd(struct.unpack(endian + "I", value)[0], depth + 1)
            elif tag in wanted:
                found[tag] = value

    read_ifd(struct.unpack(endian + "I", blob[4:8])[0], 0)
    return found


def _exif_metadata(tags: dict[int, bytes]) -> list[MetadataText]:
    texts: list[MetadataText] = []

    description = tags.get(EXIF_IMAGE_DESCRIPTION)
    if description:
        value = description.rstrip(b"\x00")
        try:
            texts.append(_metadata("EXIF", "ImageDescription", value.decode("utf-8")))
        except UnicodeDecodeError:
            pass  # binary content; inspected by the EXIF adapter instead

    comment = tags.get(EXIF_XP_COMMENT)
    if comment:
        texts.append(_metadata("EXIF", "XPComment", comment.decode("utf-16-le", "replace").rstrip("\x00")))

    user_comment = tags.get(EXIF_USER_COMMENT)
    if user_comment and len(user_comment) > 8:
        prefix, body = user_comment[:8], user_comment[8:]
        if prefix.startswith(b"ASCII"):
            text = body.decode("ascii", "replace")
        elif prefix.startswith(b"UNICODE"):
            text = body.decode("utf-16", "replace")
        else:
            text = body.decode("utf-8", "replace")
        text = text.rstrip("\x00 ")
        if text:
            texts.append(_metadata("EXIF", "UserComment", text))

    return texts


# --------------------------------------------------------------------------


def _bit_depth(mode: str) -> int | None:
    if mode == "1":
        return 1
    if mode in {"L", "LA", "P", "PA", "RGB", "RGBA", "CMYK", "YCbCr", "LAB", "HSV"}:
        return 8
    if mode.startswith("I;16"):
        return 16
    if mode in {"I", "F"}:
        return 32
    return None


def load_image_input(data: bytes, limits: Limits) -> ImageInput:
    """
    Validate untrusted image bytes and prepare them for extraction.

    Raises AutoExtractInputError for empty, oversized, unsupported or
    corrupted input. Never modifies `data`.
    """

    if not data:
        raise AutoExtractInputError("The uploaded file is empty.")

    if len(data) > limits.max_file_bytes:
        raise AutoExtractInputError(
            f"The file is larger than the {limits.max_file_bytes // (1024 * 1024)} MB limit "
            "for automatic extraction.",
            status_code=413,
        )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            opened = Image.open(io.BytesIO(data), formats=list(SUPPORTED_FORMATS))
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise AutoExtractInputError(
            "The image declares more pixels than the decompression safety limit allows.",
            status_code=413,
        )
    except UnidentifiedImageError:
        detected = None
        try:
            with Image.open(io.BytesIO(data)) as other:
                detected = other.format
        except Exception:
            pass
        if detected:
            raise AutoExtractInputError(
                f"{detected} images are not supported for extraction. "
                "Supported formats: PNG, BMP, TIFF, PGM/PPM, WebP and JPEG."
            )
        raise AutoExtractInputError(
            "The file is not a recognised image (its content does not match any supported image format)."
        )
    except Exception:
        raise AutoExtractInputError("The image header could not be read; the file may be corrupted.")

    with opened:
        image_format = (opened.format or "").upper()
        width, height = opened.size
        mode = opened.mode
        frame_count = int(getattr(opened, "n_frames", 1) or 1)

        if width <= 0 or height <= 0:
            raise AutoExtractInputError("The image reports invalid dimensions.")

        # Checked before decoding: a small file can declare a huge canvas.
        if width * height > limits.max_pixels:
            raise AutoExtractInputError(
                f"The image is {width}×{height} pixels, above the "
                f"{limits.max_pixels:,}-pixel limit for automatic extraction.",
                status_code=413,
            )

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                opened.load()
        except (Image.DecompressionBombError, Image.DecompressionBombWarning):
            raise AutoExtractInputError("The image exceeds the decompression safety limit.", status_code=413)
        except Exception:
            raise AutoExtractInputError(
                "The image data is truncated or corrupted and could not be decoded."
            )

        samples: np.ndarray | None = None
        bands: tuple[str, ...] = ()
        pixel_note: str | None = None

        if mode in _DIRECT_MODES:
            bands = _DIRECT_MODES[mode]
            samples = np.asarray(opened, dtype=np.uint8).reshape(-1)
        elif mode in {"P", "PA"}:
            bands = ("R", "G", "B")
            samples = np.asarray(opened.convert("RGB"), dtype=np.uint8).reshape(-1)
            pixel_note = (
                "Palette image: colours were expanded to RGB before reading bits "
                "(palette-index LSB embedding is not searched)."
            )
        else:
            pixel_note = (
                f"Pixel mode {mode} cannot be read as 8-bit samples without changing "
                "values, so pixel-based methods were skipped."
            )

    if samples is not None:
        samples.setflags(write=False)

    end_offset = None
    notes: list[str] = []
    texts: list[MetadataText] = []
    exif_blob: bytes | None = None

    parser = _CONTAINER_PARSERS.get(image_format)
    if parser:
        end_offset, notes, texts, exif_blob = parser(data)
    else:
        notes.append(f"Trailing-data check is not available for {image_format} files.")

    if exif_blob is None and image_format == "TIFF":
        exif_blob = data  # a TIFF file is itself an EXIF/TIFF structure

    exif_tags: dict[int, bytes] = {}
    if exif_blob:
        try:
            exif_tags = parse_exif_tags(
                exif_blob,
                {EXIF_IMAGE_DESCRIPTION, EXIF_XP_COMMENT, EXIF_USER_COMMENT},
            )
        except struct.error:
            notes.append("EXIF block is malformed and was ignored.")
        texts.extend(_exif_metadata(exif_tags))

    if frame_count > 1:
        notes.append(f"The file has {frame_count} frames; only the first frame was searched.")

    lossy = image_format == "JPEG" or (image_format == "WEBP" and _webp_is_lossy(data))

    return ImageInput(
        data=data,
        sha256=hashlib.sha256(data).hexdigest(),
        format=image_format,
        mime_type=SUPPORTED_FORMATS[image_format],
        width=width,
        height=height,
        mode=mode,
        bit_depth=_bit_depth(mode),
        lossy=lossy,
        frame_count=frame_count,
        samples=samples,
        samples_per_pixel=len(bands) if bands else 0,
        sample_bands=bands,
        pixel_note=pixel_note,
        image_end_offset=end_offset,
        container_notes=notes,
        metadata_texts=texts[:_MAX_METADATA_ITEMS],
        exif_tags=exif_tags,
    )
