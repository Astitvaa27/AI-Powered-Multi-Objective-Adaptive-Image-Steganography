from pathlib import Path

import numpy as np
import pywt
from PIL import Image


QUANTIZATION_STEP = 20.0


def _bytes_to_bits(data: bytes) -> list[int]:
    bits = []

    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)

    return bits


def _bits_to_bytes(bits: list[int]) -> bytes:
    output = bytearray()

    for i in range(0, len(bits), 8):
        byte = 0

        for bit in bits[i:i + 8]:
            byte = (byte << 1) | bit

        output.append(byte)

    return bytes(output)


def _embed_bit(value: float, bit: int) -> float:
    magnitude = abs(value)

    base = np.floor(magnitude / QUANTIZATION_STEP)

    if bit == 0:
        quantized = base * QUANTIZATION_STEP + (
            QUANTIZATION_STEP * 0.25
        )
    else:
        quantized = base * QUANTIZATION_STEP + (
            QUANTIZATION_STEP * 0.75
        )

    return quantized if value >= 0 else -quantized


def _extract_bit(value: float) -> int:
    magnitude = abs(value)

    position = magnitude % QUANTIZATION_STEP

    if position >= QUANTIZATION_STEP / 2:
        return 1

    return 0


def embed_dwt(
    input_path: str,
    output_path: str,
    payload: bytes,
) -> dict:
    """
    Embed a byte payload into the blue channel using 1-level Haar DWT.

    A 32-bit header stores the payload length.
    One bit is embedded per coefficient in the HH sub-band.
    """

    image = Image.open(input_path).convert("RGB")
    image_array = np.asarray(image, dtype=np.float64)

    blue_channel = image_array[:, :, 2]

    approximation, (horizontal, vertical, diagonal) = pywt.dwt2(
        blue_channel,
        "haar",
    )

    coefficients = diagonal.flatten()

    capacity_bits = len(coefficients) - 32
    capacity_bytes = max(0, capacity_bits // 8)

    if len(payload) > capacity_bytes:
        raise ValueError(
            f"Payload too large. Maximum capacity is {capacity_bytes} bytes."
        )

    length_bits = _bytes_to_bits(
        len(payload).to_bytes(4, byteorder="big")
    )

    payload_bits = _bytes_to_bits(payload)

    all_bits = length_bits + payload_bits

    for index, bit in enumerate(all_bits):
        coefficients[index] = _embed_bit(
            coefficients[index],
            bit,
        )

    diagonal = coefficients.reshape(diagonal.shape)

    reconstructed_blue = pywt.idwt2(
        (
            approximation,
            (horizontal, vertical, diagonal),
        ),
        "haar",
    )

    reconstructed_blue = np.clip(
        reconstructed_blue,
        0,
        255,
    )

    image_array[:, :, 2] = reconstructed_blue[
        :image_array.shape[0],
        :image_array.shape[1],
    ]

    output_image = Image.fromarray(
        image_array.astype(np.uint8),
        mode="RGB",
    )

    Path(output_path).parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_image.save(output_path)

    return {
        "width": image.width,
        "height": image.height,
        "capacity_bytes": capacity_bytes,
        "payload_size_bytes": len(payload),
        "output_path": output_path,
    }


def extract_dwt(image_path: str) -> bytes:
    """
    Extract a byte payload from the blue channel using 1-level Haar DWT.
    """

    image = Image.open(image_path).convert("RGB")
    image_array = np.asarray(image, dtype=np.float64)

    blue_channel = image_array[:, :, 2]

    _, (_, _, diagonal) = pywt.dwt2(
        blue_channel,
        "haar",
    )

    coefficients = diagonal.flatten()

    if len(coefficients) < 32:
        raise ValueError(
            "Image is too small for a DWT payload."
        )

    header_bits = [
        _extract_bit(value)
        for value in coefficients[:32]
    ]

    length_bytes = _bits_to_bytes(header_bits)

    payload_length = int.from_bytes(
        length_bytes,
        byteorder="big",
    )

    total_bits = 32 + (payload_length * 8)

    if total_bits > len(coefficients):
        raise ValueError(
            "Invalid or corrupted DWT payload."
        )

    payload_bits = [
        _extract_bit(value)
        for value in coefficients[32:total_bits]
    ]

    return _bits_to_bytes(payload_bits)