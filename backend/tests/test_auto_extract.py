"""
Automatic detection and extraction pipeline tests.

Pure unit tests on synthetic images with known payloads; no database.

    python -m unittest backend.tests.test_auto_extract -v

The third-party compatibility tests need the `stegano` library
(3.0.0, GPL, test-only; not a project dependency). They are skipped
when it is not importable, e.g.:

    pip install --target .testdeps --no-deps stegano==3.0.0 piexif crayons colorama
    PYTHONPATH=.testdeps python -m unittest backend.tests.test_auto_extract -v
"""

from __future__ import annotations

import io
import os
import struct
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path

import numpy as np
from PIL import Image

from backend.app.services.auto_extract import (
    AutoExtractInputError,
    Limits,
    RecordedConfig,
    collect_result,
    load_image_input,
    run_auto_extraction,
)
from backend.app.services.auto_extract.validation import payload_digest
from backend.app.services.dct_service import embed_dct
from backend.app.services.dwt_service import embed_dwt
from backend.app.services.lsb_service import (
    embed_lsb,
    embed_lsb_grayscale,
    extract_lsb,
    extract_lsb_grayscale,
)

try:  # optional, test-only third-party tool
    from stegano import exifHeader as stegano_exif
    from stegano import lsb as stegano_lsb
except Exception:  # pragma: no cover - depends on the environment
    stegano_lsb = None
    stegano_exif = None

LIMITS = Limits(
    max_file_bytes=25 * 1024 * 1024,
    max_pixels=25_000_000,
    max_transform_pixels=12_000_000,
    max_payload_bytes=1024 * 1024,
    time_budget_seconds=30.0,
)

MESSAGE = "Meet at the old library at 7pm. Bring the blue notebook."

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


# -- fixtures ---------------------------------------------------------------


def natural_cover(height: int = 96, width: int = 128, seed: int = 0, channels: int = 3) -> np.ndarray:
    """Smooth gradients plus sensor-like noise: a stand-in for a photo."""

    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:height, 0:width]
    base = 128 + 60 * np.sin(x / 17 + seed) + 40 * np.cos(y / 23)
    stacked = np.stack([base + 15 * k for k in range(channels)], axis=-1)
    noisy = stacked + rng.normal(0, 6, (height, width, channels))
    return np.clip(noisy, 0, 255).astype(np.uint8)


def encode(array: np.ndarray, fmt: str = "PNG", mode: str | None = None, **save_kwargs) -> bytes:
    if array.ndim == 3 and array.shape[2] == 1:
        array = array[:, :, 0]
    image = Image.fromarray(array, mode=mode) if mode else Image.fromarray(array)
    buffer = io.BytesIO()
    image.save(buffer, format=fmt, **save_kwargs)
    return buffer.getvalue()


def reference_embed(
    array: np.ndarray,
    data: bytes,
    channels: list[int],
    bits: int = 1,
    bit_order: str = "MSB",
) -> np.ndarray:
    """
    Independent LSB embedder written only for these tests (plain loops,
    no shared code with lsb_service): row-major pixels, the given channels
    per pixel, `bits` low bits per value, bytes split MSB- or LSB-first.
    """

    out = array.copy()
    stream: list[int] = []
    for byte in data:
        order = range(7, -1, -1) if bit_order == "MSB" else range(8)
        stream.extend((byte >> i) & 1 for i in order)
    while len(stream) % bits:
        stream.append(0)

    height, width = out.shape[:2]
    index = 0
    for y in range(height):
        for x in range(width):
            for channel in channels:
                if index >= len(stream):
                    return out
                value = 0
                for bit in stream[index:index + bits]:
                    value = (value << 1) | bit
                keep = 0xFF & ~((1 << bits) - 1)
                out[y, x, channel] = (int(out[y, x, channel]) & keep) | value
                index += bits
    if index < len(stream):
        raise ValueError("payload too long for reference embedder")
    return out


def run(data: bytes, **kwargs) -> dict:
    limits = kwargs.pop("limits", LIMITS)
    kwargs.setdefault("run_steganalysis", False)
    image = load_image_input(data, limits)
    return collect_result(run_auto_extraction(image, limits=limits, **kwargs))


def texts(result: dict, *levels: str) -> list[str | None]:
    return [c["payload"]["text"] for c in result["candidates"] if not levels or c["validation"] in levels]


class _TempDirMixin:
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def stegolab_lsb(self, message: bytes, channel_mode: str, bits: int, seed: int = 0) -> bytes:
        cover = self.tmp / f"cover_{seed}.png"
        stego = self.tmp / f"stego_{channel_mode}_{bits}_{seed}.png"
        cover.write_bytes(encode(natural_cover(seed=seed)))
        embed_lsb(str(cover), str(stego), message, channel_mode, bits)
        return stego.read_bytes()


# -- 1-3: StegoLab images, independent LSB, channel/bit configurations -------


class StegoLabImagesTest(_TempDirMixin, unittest.TestCase):
    def test_every_stegolab_lsb_configuration_is_found_without_parameters(self):
        for channel_mode in ("RGB", "R", "G", "B"):
            for bits in (1, 2, 3):
                with self.subTest(channel_mode=channel_mode, bits=bits):
                    result = run(self.stegolab_lsb(MESSAGE.encode(), channel_mode, bits))
                    self.assertEqual(result["status"], "PLAUSIBLE")
                    best = result["best_candidate"]
                    self.assertEqual(best["adapter"], "STEGOLAB_LSB")
                    self.assertEqual(best["payload"]["text"], MESSAGE)
                    self.assertEqual(best["parameters"]["channel_mode"], channel_mode)
                    self.assertEqual(best["parameters"]["lsb_bits"], bits)

    def test_stegolab_grayscale_lsb(self):
        cover = self.tmp / "gray.png"
        stego = self.tmp / "gray_stego.png"
        cover.write_bytes(encode(natural_cover(channels=1), mode="L"))
        embed_lsb_grayscale(str(cover), str(stego), MESSAGE.encode(), 2)

        result = run(stego.read_bytes())

        self.assertEqual(result["status"], "PLAUSIBLE")
        self.assertEqual(result["best_candidate"]["parameters"]["channel_mode"], "Gray")
        self.assertEqual(result["best_candidate"]["payload"]["text"], MESSAGE)

    def test_stegolab_dct_and_dwt(self):
        # embed_dwt truncates reconstructed values instead of rounding, so it
        # only round-trips reliably on some covers (a pre-existing issue in
        # dwt_service); a flat mid-grey cover is used for DWT here.
        covers = {
            "DCT": natural_cover(256, 256, seed=3),
            "DWT": np.full((128, 128, 3), 120, dtype=np.uint8),
        }
        for method, embed in (("DCT", embed_dct), ("DWT", embed_dwt)):
            with self.subTest(method=method):
                cover = self.tmp / f"cover_{method}.png"
                cover.write_bytes(encode(covers[method]))
                stego = self.tmp / f"{method}.png"
                embed(str(cover), str(stego), b"Transform secret")
                result = run(stego.read_bytes())
                self.assertEqual(result["status"], "PLAUSIBLE")
                self.assertEqual(result["best_candidate"]["method"], method)
                self.assertEqual(result["best_candidate"]["payload"]["text"], "Transform secret")

    def test_record_with_matching_hash_is_verified(self):
        data = self.stegolab_lsb(MESSAGE.encode(), "B", 2)
        record = RecordedConfig("LSB", "B", 2, "ADAPTIVE", "IMAGE_RECORD", payload_digest(MESSAGE.encode()))

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
            handle.write(data)
        try:
            result = run(data, record=record, image_path=handle.name)
        finally:
            os.unlink(handle.name)

        self.assertEqual(result["status"], "VERIFIED")
        best = result["best_candidate"]
        self.assertEqual(best["adapter"], "STEGOLAB_RECORD")
        self.assertEqual(best["payload"]["text"], MESSAGE)
        self.assertTrue(any(e["check"] == "Stored message hash" and e["passed"] for e in best["evidence"]))
        # The blind search found the same payload and was merged into it.
        self.assertIn("STEGOLAB_LSB", [item["adapter"] for item in best["also_found_by"]])
        self.assertTrue(result["record"]["found"])

    def test_record_with_wrong_hash_is_not_verified(self):
        data = self.stegolab_lsb(MESSAGE.encode(), "RGB", 1)
        record = RecordedConfig("LSB", "RGB", 1, "MANUAL", "HASH_MATCH", payload_digest(b"something else"))

        result = run(data, record=record)

        self.assertNotEqual(result["status"], "VERIFIED")
        self.assertTrue(any("does not match the stored message" in w for w in result["warnings"]))

    def test_rgba_image_lsb_reads_only_colour_channels(self):
        rgba = natural_cover(channels=4)
        rgba[:, :, 3] = 255
        framed = len(MESSAGE).to_bytes(4, "big") + MESSAGE.encode()
        stego = reference_embed(rgba, framed, [0, 1, 2], bits=1)

        result = run(encode(stego, mode="RGBA"))

        self.assertEqual(result["best_candidate"]["payload"]["text"], MESSAGE)
        self.assertEqual(result["best_candidate"]["parameters"]["channel_mode"], "RGB")

    def test_source_bytes_and_samples_are_not_modified(self):
        data = self.stegolab_lsb(MESSAGE.encode(), "RGB", 1)
        original = bytes(data)
        image = load_image_input(data, LIMITS)
        samples_before = image.samples.copy()

        collect_result(run_auto_extraction(image, limits=LIMITS, run_steganalysis=False))

        self.assertEqual(image.data, original)
        self.assertTrue(np.array_equal(image.samples, samples_before))
        self.assertFalse(image.samples.flags.writeable)


class IndependentImplementationTest(unittest.TestCase):
    def test_length_header_written_by_reference_embedder(self):
        payload = "Independent implementation".encode()
        for channels, mode, bits in (([0, 1, 2], "RGB", 1), ([1], "G", 3), ([2], "B", 2)):
            with self.subTest(mode=mode, bits=bits):
                framed = len(payload).to_bytes(4, "big") + payload
                stego = reference_embed(natural_cover(seed=5), framed, channels, bits)
                result = run(encode(stego))
                self.assertEqual(result["best_candidate"]["payload"]["text"], payload.decode())
                self.assertEqual(result["best_candidate"]["parameters"]["channel_mode"], mode)

    def test_decimal_prefix_format_from_reference_embedder(self):
        message = "Prefixed message from another tool"
        framed = f"{len(message.encode())}:".encode() + message.encode()
        stego = reference_embed(natural_cover(seed=6), framed, [0, 1, 2], 1)

        result = run(encode(stego))

        self.assertEqual(result["status"], "PLAUSIBLE")
        self.assertEqual(result["best_candidate"]["adapter"], "STEGANO_LSB")
        self.assertEqual(result["best_candidate"]["payload"]["text"], message)

    def test_delimiter_terminated_text_variants(self):
        message = "Delimited secret text"
        cases = (
            (b"\x00", "MSB", [0, 1, 2], "RGB"),
            (b"$t3g0", "MSB", [0], "R"),
            (b"#####", "LSB", [0, 1, 2], "RGB"),
            (b"*^*^*", "LSB", [2], "B"),
        )
        for delimiter, order, channels, mode in cases:
            with self.subTest(delimiter=delimiter, order=order):
                stego = reference_embed(natural_cover(seed=7), message.encode() + delimiter, channels, 1, order)
                result = run(encode(stego))
                self.assertEqual(result["status"], "PLAUSIBLE")
                best = result["best_candidate"]
                self.assertEqual(best["adapter"], "TERMINATED_TEXT_LSB")
                self.assertEqual(best["payload"]["text"], message)
                self.assertEqual(best["parameters"]["channel_mode"], mode)
                self.assertEqual(best["parameters"]["bit_order"], "MSB_FIRST" if order == "MSB" else "LSB_FIRST")

    def test_bmp_and_lossless_webp_inputs(self):
        framed = len(MESSAGE).to_bytes(4, "big") + MESSAGE.encode()
        stego = reference_embed(natural_cover(seed=8), framed, [0, 1, 2], 1)
        for fmt, kwargs in (("BMP", {}), ("WEBP", {"lossless": True}), ("TIFF", {})):
            with self.subTest(fmt=fmt):
                result = run(encode(stego, fmt, **kwargs))
                self.assertEqual(result["image"]["format"], fmt)
                self.assertFalse(result["image"]["lossy"])
                self.assertEqual(result["best_candidate"]["payload"]["text"], MESSAGE)


@unittest.skipIf(stegano_lsb is None, "stegano library not installed (optional test dependency)")
class SteganoCompatibilityTest(unittest.TestCase):
    """Reproducible compatibility checks against a real third-party tool."""

    def test_stegano_lsb_hide(self):
        cover = io.BytesIO(encode(natural_cover(seed=9)))
        message = "Hidden with stegano.lsb — ünïcode too"
        stego = stegano_lsb.hide(cover, message)
        data = io.BytesIO()
        stego.save(data, format="PNG")

        # Sanity: stegano itself reads it back.
        self.assertEqual(stegano_lsb.reveal(io.BytesIO(data.getvalue())), message)

        result = run(data.getvalue())

        self.assertEqual(result["status"], "PLAUSIBLE")
        best = result["best_candidate"]
        self.assertEqual(best["adapter"], "STEGANO_LSB")
        self.assertEqual(best["payload"]["text"], message)
        self.assertEqual((best["parameters"]["channel_mode"], best["parameters"]["lsb_bits"]), ("RGB", 1))

    def test_stegano_exif_header_hide(self):
        with tempfile.TemporaryDirectory() as tmp:
            cover = Path(tmp) / "cover.jpg"
            stego = Path(tmp) / "stego.jpg"
            cover.write_bytes(encode(natural_cover(seed=10), "JPEG", quality=90))
            stegano_exif.hide(str(cover), str(stego), secret_message="EXIF secret from stegano")

            result = run(stego.read_bytes())

        self.assertEqual(result["status"], "VERIFIED")
        best = result["best_candidate"]
        self.assertEqual(best["adapter"], "STEGANO_EXIF")
        self.assertEqual(best["payload"]["text"], "EXIF secret from stegano")
        self.assertTrue(any(e["check"] == "zlib checksum" and e["passed"] for e in best["evidence"]))


# -- 4-6: clean images, noise, misleading strings, framing ----------------------


class NegativeCasesTest(unittest.TestCase):
    def test_clean_images_report_not_found(self):
        for seed in range(6):
            for fmt in ("PNG", "BMP"):
                with self.subTest(seed=seed, fmt=fmt):
                    result = run(encode(natural_cover(seed=seed), fmt))
                    self.assertEqual(result["status"], "NOT_FOUND")
                    self.assertFalse(result["extraction_succeeded"])
                    self.assertTrue(result["guidance"])

    def test_random_noise_never_yields_confirmed_messages(self):
        for seed in range(40):
            with self.subTest(seed=seed):
                noise = np.random.default_rng(1000 + seed).integers(0, 256, (64, 64, 3), dtype=np.uint8)
                result = run(encode(noise))
                self.assertFalse(texts(result, "VERIFIED", "PLAUSIBLE"))
                self.assertFalse(result["extraction_succeeded"])

    def test_flat_images_do_not_produce_candidates(self):
        for value in (0, 1, 254, 255, 128):
            with self.subTest(value=value):
                flat = np.full((64, 64, 3), value, dtype=np.uint8)
                self.assertEqual(run(encode(flat))["status"], "NOT_FOUND")

    def test_short_readable_run_before_delimiter_is_only_unverified(self):
        stego = reference_embed(natural_cover(seed=11), b"hey!!\x00", [0, 1, 2], 1)

        result = run(encode(stego))

        self.assertFalse(texts(result, "VERIFIED", "PLAUSIBLE"))
        self.assertIn("hey!!", texts(result, "UNVERIFIED"))
        self.assertEqual(result["status"], "UNVERIFIED")

    def test_tiny_readable_run_before_delimiter_is_discarded(self):
        stego = reference_embed(natural_cover(seed=11), b"hi!\x00", [0, 1, 2], 1)
        self.assertEqual(run(encode(stego))["status"], "NOT_FOUND")

    def test_misaligned_readings_of_an_accepted_message_are_suppressed(self):
        stego = reference_embed(natural_cover(seed=22), len(MESSAGE).to_bytes(4, "big") + MESSAGE.encode(), [0, 1, 2], 3)

        result = run(encode(stego))

        self.assertEqual(result["status"], "PLAUSIBLE")
        self.assertEqual(texts(result), [MESSAGE])

    def test_two_character_length_framed_text_is_unverified(self):
        stego = reference_embed(natural_cover(seed=12), (2).to_bytes(4, "big") + b"ok", [0, 1, 2], 1)

        result = run(encode(stego))

        self.assertEqual(result["status"], "UNVERIFIED")
        self.assertIn("ok", texts(result, "UNVERIFIED"))

    def test_length_header_beyond_capacity_is_rejected(self):
        stego = reference_embed(natural_cover(seed=13), (10_000_000).to_bytes(4, "big") + b"abc", [0, 1, 2], 1)

        result = run(encode(stego))
        reasons = [a["reason"] or "" for a in result["attempts"]["details"] if a["adapter"] == "STEGOLAB_LSB"]

        self.assertEqual(result["status"], "NOT_FOUND")
        self.assertTrue(any("exceeds this layout's capacity" in r for r in reasons))

    def test_zero_length_header_is_rejected(self):
        stego = reference_embed(natural_cover(seed=14), (0).to_bytes(4, "big") + b"text", [0, 1, 2], 1)
        result = run(encode(stego))
        self.assertFalse(texts(result, "VERIFIED", "PLAUSIBLE"))

    def test_invalid_decimal_prefix_is_rejected(self):
        for prefix in (b"012:", b"12;", b"x5:"):
            with self.subTest(prefix=prefix):
                stego = reference_embed(natural_cover(seed=15), prefix + b"hello world, abc", [0, 1, 2], 1)
                result = run(encode(stego))
                self.assertNotIn("STEGANO_LSB", [c["adapter"] for c in result["candidates"]])

    def test_corrupted_padding_downgrades_stegolab_candidate(self):
        # 56 framed bits in 3-bit values use 19 samples: one padding bit,
        # the lowest bit of the last sample. StegoLab always writes it as 0.
        payload = b"abc"
        framed = len(payload).to_bytes(4, "big") + payload
        stego = reference_embed(natural_cover(seed=16), framed, [0, 1, 2], 3)
        samples_used = -(-(len(framed) * 8) // 3)
        pixel, channel = divmod(samples_used - 1, 3)
        y, x = divmod(pixel, stego.shape[1])
        stego[y, x, channel] |= 0b001

        result = run(encode(stego))
        candidate = next(
            c for c in result["candidates"]
            if c["adapter"] == "STEGOLAB_LSB" and c["parameters"]["lsb_bits"] == 3
        )

        self.assertEqual(candidate["validation"], "UNVERIFIED")
        self.assertTrue(any(e["check"] == "Padding bits" and not e["passed"] for e in candidate["evidence"]))


# -- 7-10: corrupted, recompressed, unsupported, oversized ---------------------


class InputHandlingTest(_TempDirMixin, unittest.TestCase):
    def assertInputError(self, data: bytes, status: int, fragment: str, limits: Limits = LIMITS):
        with self.assertRaises(AutoExtractInputError) as raised:
            load_image_input(data, limits)
        self.assertEqual(raised.exception.status_code, status)
        self.assertIn(fragment.lower(), raised.exception.detail.lower())

    def test_corrupted_and_non_image_files(self):
        png = encode(natural_cover())
        self.assertInputError(b"", 400, "empty")
        self.assertInputError(b"just some text, not an image", 400, "not a recognised image")
        self.assertInputError(png[: len(png) // 2], 400, "truncated or corrupted")
        self.assertInputError(png[:30], 400, "")

    def test_bad_png_crc_is_reported(self):
        png = bytearray(encode(natural_cover(), pnginfo=None))
        # Append a tEXt chunk with a wrong CRC before IEND.
        iend = png.rfind(b"IEND") - 4
        chunk = struct.pack(">I", 5) + b"tEXt" + b"k\x00abc" + b"\x00\x00\x00\x00"
        damaged = bytes(png[:iend]) + chunk + bytes(png[iend:])

        result = run(damaged)

        self.assertTrue(any("bad CRC" in w for w in result["warnings"]))

    def test_jpeg_recompression_destroys_lsb_message(self):
        stego = self.stegolab_lsb(MESSAGE.encode(), "RGB", 1)
        recompressed = encode(np.asarray(Image.open(io.BytesIO(stego))), "JPEG", quality=95)

        result = run(recompressed)

        self.assertNotIn(MESSAGE, texts(result))
        self.assertTrue(result["image"]["lossy"])
        self.assertTrue(any("lossy" in w.lower() for w in result["warnings"]))
        self.assertTrue(any("lossy" in g.lower() for g in result["guidance"]))

    def test_resizing_destroys_lsb_message(self):
        stego = Image.open(io.BytesIO(self.stegolab_lsb(MESSAGE.encode(), "RGB", 1)))
        resized = stego.resize((stego.width // 2 + 7, stego.height // 2 + 3), Image.BILINEAR)
        buffer = io.BytesIO()
        resized.save(buffer, format="PNG")

        result = run(buffer.getvalue())

        self.assertNotIn(MESSAGE, texts(result))
        self.assertFalse(result["extraction_succeeded"])

    def test_unsupported_formats_are_named(self):
        self.assertInputError(encode(natural_cover(), "GIF"), 400, "GIF images are not supported")
        self.assertInputError(encode(natural_cover(), "ICO"), 400, "not supported")

    def test_sixteen_bit_image_skips_pixel_methods(self):
        deep = Image.fromarray((natural_cover(channels=1)[:, :, 0].astype(np.uint16) * 257), mode="I;16")
        buffer = io.BytesIO()
        deep.save(buffer, format="PNG")

        result = run(buffer.getvalue())

        self.assertFalse(result["image"]["pixels_readable"])
        skipped = {m["id"]: m["applicable"] for m in result["methods_tested"]}
        self.assertFalse(skipped["STEGOLAB_LSB"])
        self.assertEqual(result["status"], "NOT_FOUND")

    def test_oversized_file_is_rejected(self):
        small_limits = Limits(1000, LIMITS.max_pixels, LIMITS.max_transform_pixels, LIMITS.max_payload_bytes, 5.0)
        self.assertInputError(encode(natural_cover()), 413, "larger than", small_limits)

    def test_decompression_bomb_is_rejected_before_decoding(self):
        # A valid PNG header declaring 30000×30000 pixels with almost no data.
        ihdr = struct.pack(">IIBBBBB", 30000, 30000, 8, 2, 0, 0, 0)
        def chunk(kind: bytes, body: bytes) -> bytes:
            return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)
        bomb = PNG_SIGNATURE + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(b"\x00" * 1000)) + chunk(b"IEND", b"")

        self.assertInputError(bomb, 413, "pixel")

        # Moderately large canvases pass Pillow's own check; ours still applies.
        ihdr = struct.pack(">IIBBBBB", 6000, 5000, 8, 2, 0, 0, 0)
        big = PNG_SIGNATURE + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(1000))) + chunk(b"IEND", b"")
        self.assertInputError(big, 413, "pixel limit")

    def test_time_budget_stops_search_and_reports_untested_configurations(self):
        tiny = Limits(LIMITS.max_file_bytes, LIMITS.max_pixels, LIMITS.max_transform_pixels, LIMITS.max_payload_bytes, 0.0)

        result = run(encode(natural_cover()), limits=tiny)

        self.assertTrue(result["time_budget_reached"])
        self.assertGreater(result["attempts"]["by_outcome"].get("NOT_TESTED", 0), 0)
        self.assertTrue(any("time limit" in w for w in result["warnings"]))

    def test_payload_above_extraction_limit_is_rejected(self):
        capped = Limits(LIMITS.max_file_bytes, LIMITS.max_pixels, LIMITS.max_transform_pixels, 10, 30.0)
        stego = reference_embed(natural_cover(seed=17), len(MESSAGE).to_bytes(4, "big") + MESSAGE.encode(), [0, 1, 2], 1)

        result = run(encode(stego), limits=capped)
        reasons = " ".join(a["reason"] or "" for a in result["attempts"]["details"])

        self.assertNotIn(MESSAGE, texts(result))
        self.assertIn("automatic-extraction limit", reasons)


# -- container formats, keys and multiple candidates -----------------------------


class ContainerAndKeyTest(unittest.TestCase):
    def test_appended_text_after_png_and_jpeg(self):
        for fmt in ("PNG", "JPEG", "BMP", "WEBP"):
            with self.subTest(fmt=fmt):
                data = encode(natural_cover(), fmt) + b"Appended secret after the image end"
                result = run(data)
                self.assertEqual(result["status"], "PLAUSIBLE")
                self.assertEqual(result["best_candidate"]["adapter"], "APPENDED_DATA")
                self.assertEqual(result["best_candidate"]["payload"]["text"], "Appended secret after the image end")

    def test_jpeg_with_exif_thumbnail_markers_has_no_false_appended_data(self):
        # Progressive JPEG plus an EXIF block: inner FFD9 bytes must not end the scan.
        exif = Image.Exif()
        exif[0x010E] = "A normal camera description"
        data = encode(natural_cover(), "JPEG", quality=85, progressive=True, exif=exif.tobytes())

        result = run(data)

        self.assertEqual(result["image"]["trailing_bytes"], 0)
        self.assertEqual(result["status"], "NOT_FOUND")
        self.assertIn("A normal camera description", [m["text"] for m in result["metadata_findings"]])

    def test_appended_zip_is_listed_not_unpacked(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as handle:
            handle.writestr("secret.txt", "zip content")
        result = run(encode(natural_cover()) + archive.getvalue())

        best = result["best_candidate"]
        self.assertEqual(best["payload"]["detected_type"], "ZIP archive")
        self.assertEqual(best["payload"]["archive_entries"], ["secret.txt"])
        self.assertIsNotNone(best["payload"]["base64"])
        self.assertFalse(best["requires_key"])

    def test_png_text_chunks_are_metadata_not_messages(self):
        from PIL.PngImagePlugin import PngInfo

        info = PngInfo()
        info.add_text("Software", "SomeEditor 1.0")
        info.add_text("secret", "This is stored in plain metadata", zip=True)
        result = run(encode(natural_cover(), pnginfo=info))

        self.assertEqual(result["status"], "NOT_FOUND")
        findings = {m["key"]: m for m in result["metadata_findings"]}
        self.assertTrue(findings["Software"]["standard_key"])
        self.assertEqual(findings["secret"]["text"], "This is stored in plain metadata")
        self.assertIn("metadata", result["summary"])

    def test_openssl_encrypted_payload_requires_key(self):
        encrypted = b"Salted__" + np.random.default_rng(3).integers(0, 256, 64, dtype=np.uint8).tobytes()
        stego = reference_embed(natural_cover(seed=18), len(encrypted).to_bytes(4, "big") + encrypted, [0, 1, 2], 1)

        result = run(encode(stego))

        best = result["best_candidate"]
        self.assertEqual(best["payload"]["detected_type"], "OpenSSL-encrypted data")
        self.assertTrue(best["requires_key"])
        self.assertIn("password or key", best["key_hint"])

    def test_encrypted_zip_requires_key(self):
        archive = bytearray()
        local = struct.pack("<4sHHHHHIIIHH", b"PK\x03\x04", 20, 0x1, 0, 0, 0, 0, 5, 5, 1, 0) + b"a" + b"xxxxx"
        central = struct.pack("<4sHHHHHHIIIHHHHHII", b"PK\x01\x02", 20, 20, 0x1, 0, 0, 0, 0, 5, 5, 1, 0, 0, 0, 0, 0, 0) + b"a"
        end = struct.pack("<4sHHHHIIH", b"PK\x05\x06", 0, 0, 1, 1, len(central), len(local), 0)
        archive += local + central + end

        result = run(encode(natural_cover()) + bytes(archive))

        best = result["best_candidate"]
        self.assertTrue(best["requires_key"])
        self.assertIn("password-protected", best["key_hint"])

    def test_high_entropy_binary_is_unverified_and_flags_possible_key(self):
        blob = np.random.default_rng(4).integers(0, 256, 300, dtype=np.uint8).tobytes()
        stego = reference_embed(natural_cover(120, 160, seed=19), len(blob).to_bytes(4, "big") + blob, [0, 1, 2], 1)

        result = run(encode(stego))

        self.assertEqual(result["status"], "UNVERIFIED")
        candidate = result["candidates"][0]
        self.assertTrue(candidate["requires_key"])
        self.assertEqual(candidate["payload"]["kind"], "BINARY")
        self.assertTrue(any("password" in g for g in result["guidance"]))

    def test_multiple_plausible_candidates_are_ambiguous(self):
        first, second = b"Message in the red channel", b"Another one in the green channel"
        cover = natural_cover(seed=20)
        stego = reference_embed(cover, len(first).to_bytes(4, "big") + first, [0], 1)
        stego = reference_embed(stego, len(second).to_bytes(4, "big") + second, [1], 1)

        result = run(encode(stego))

        self.assertEqual(result["status"], "AMBIGUOUS")
        self.assertIsNone(result["best_candidate"])
        self.assertFalse(result["extraction_succeeded"])
        plausible = texts(result, "PLAUSIBLE")
        self.assertIn(first.decode(), plausible)
        self.assertIn(second.decode(), plausible)

    def test_extractor_errors_do_not_leak_server_paths(self):
        from unittest import mock

        from backend.app.services.auto_extract import adapters

        leaking = ValueError("Unable to read image: C:/server/tmp/stegolab_auto_x/input.png")
        with mock.patch.object(adapters.StegoLabDctAdapter, "_run", side_effect=leaking):
            result = run(encode(natural_cover()))

        serialised = repr(result)
        self.assertNotIn("stegolab_auto_", serialised)
        self.assertNotIn("C:/server", serialised)
        dct = next(a for a in result["attempts"]["details"] if a["adapter"] == "STEGOLAB_DCT")
        self.assertEqual(dct["reason"], "The image could not be read with this method.")

    def test_html_payload_is_flagged_as_markup(self):
        html = b"<script>alert('x')</script> hello"
        stego = reference_embed(natural_cover(seed=21), len(html).to_bytes(4, "big") + html, [0, 1, 2], 1)
        best = run(encode(stego))["best_candidate"]
        self.assertTrue(any("never executed" in note for note in best["notes"]))


# -- 13: steganalysis availability -----------------------------------------


class _UnavailableProbe:
    available = False
    error = "Steganalysis model not found: storage/models/secret_path.joblib"


class _BrokenProbe:
    available = True
    error = None

    def predict(self, path):
        raise RuntimeError("boom at C:/internal/path")


class _FixedProbe:
    available = True
    error = None

    def predict(self, path):
        assert Path(path).is_file()
        return {"predicted_class": "STEGO", "stego_probability": 0.97}


class SteganalysisSignalTest(_TempDirMixin, unittest.TestCase):
    def test_unavailable_model_is_reported_without_internal_paths(self):
        data = self.stegolab_lsb(MESSAGE.encode(), "RGB", 1)

        result = run(data, run_steganalysis=True, steganalysis_probe_factory=_UnavailableProbe)

        self.assertEqual(result["status"], "PLAUSIBLE")
        self.assertFalse(result["steganalysis"]["ran"])
        self.assertNotIn("storage", result["steganalysis"]["skipped_reason"])
        self.assertIn("not installed", result["steganalysis"]["skipped_reason"])

    def test_failing_model_does_not_break_extraction(self):
        data = self.stegolab_lsb(MESSAGE.encode(), "RGB", 1)
        result = run(data, run_steganalysis=True, steganalysis_probe_factory=_BrokenProbe)
        self.assertEqual(result["best_candidate"]["payload"]["text"], MESSAGE)
        self.assertNotIn("internal", result["steganalysis"]["skipped_reason"])

    def test_classifier_output_never_creates_a_message(self):
        result = run(encode(natural_cover()), run_steganalysis=True, steganalysis_probe_factory=_FixedProbe)

        self.assertTrue(result["steganalysis"]["ran"])
        self.assertEqual(result["steganalysis"]["predicted_class"], "STEGO")
        self.assertEqual(result["status"], "NOT_FOUND")
        self.assertFalse(result["extraction_succeeded"])


# -- progress events ------------------------------------------------------------


class ProgressEventsTest(unittest.TestCase):
    def test_stages_are_reported_in_order_and_end_with_result(self):
        image = load_image_input(encode(natural_cover()), LIMITS)
        events = list(run_auto_extraction(image, limits=LIMITS, run_steganalysis=False))

        self.assertEqual(events[-1]["type"], "result")
        completed = [e["stage"] for e in events if e["type"] == "stage" and e["status"] in {"completed", "partial", "skipped"}]
        self.assertEqual(
            completed,
            ["validate", "records", "containers", "search", "validate_candidates", "steganalysis", "result"],
        )
        search_progress = [e["progress"] for e in events if e.get("stage") == "search" and "progress" in e]
        self.assertEqual(search_progress[-1]["done"], search_progress[-1]["total"])
        self.assertGreater(search_progress[-1]["total"], 0)


# -- 14: manual extraction regression ----------------------------------------------


class ManualExtractionRegressionTest(_TempDirMixin, unittest.TestCase):
    def test_extract_lsb_round_trip_matches_reference_layout(self):
        for channel_mode, channels in (("RGB", [0, 1, 2]), ("R", [0]), ("G", [1]), ("B", [2])):
            for bits in (1, 2, 3):
                with self.subTest(channel_mode=channel_mode, bits=bits):
                    data = self.stegolab_lsb(MESSAGE.encode(), channel_mode, bits, seed=bits)
                    path = self.tmp / "roundtrip.png"
                    path.write_bytes(data)
                    self.assertEqual(extract_lsb(str(path), channel_mode, bits), MESSAGE.encode())

                    # Reference embedder output reads back identically.
                    framed = len(MESSAGE).to_bytes(4, "big") + MESSAGE.encode()
                    path.write_bytes(encode(reference_embed(natural_cover(seed=bits), framed, channels, bits)))
                    self.assertEqual(extract_lsb(str(path), channel_mode, bits), MESSAGE.encode())

    def test_extract_lsb_rejects_invalid_length(self):
        path = self.tmp / "clean.png"
        path.write_bytes(encode(np.full((32, 32, 3), 255, dtype=np.uint8)))
        with self.assertRaises(ValueError):
            extract_lsb(str(path), "RGB", 1)

    def test_grayscale_round_trip(self):
        cover = self.tmp / "g.png"
        stego = self.tmp / "gs.png"
        cover.write_bytes(encode(natural_cover(channels=1), mode="L"))
        embed_lsb_grayscale(str(cover), str(stego), b"gray", 1)
        self.assertEqual(extract_lsb_grayscale(str(stego), 1), b"gray")


if __name__ == "__main__":
    unittest.main()
