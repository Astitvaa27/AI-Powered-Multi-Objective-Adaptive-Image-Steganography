from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def embed_dct(
    input_path: str,
    output_path: str,
    payload: bytes,
) -> dict:
    """
    Embed a byte payload into the blue channel using DCT.

    A 32-bit header stores the payload length.
    One bit is embedded per 8x8 DCT block.
    """

    image = cv2.imread(input_path, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError(f"Unable to read image: {input_path}")

    blue_channel = image[:, :, 0].astype(np.float32)

    height, width = blue_channel.shape

    usable_width = width - (width % 8)
    usable_height = height - (height % 8)

    block_count = (usable_width // 8) * (usable_height // 8)
    capacity_bytes = max(0, (block_count - 32) // 8)

    if len(payload) > capacity_bytes:
        raise ValueError(
            f"Payload too large. Maximum capacity is {capacity_bytes} bytes."
        )

    length_bits = _bytes_to_bits(
        len(payload).to_bytes(4, byteorder="big")
    )
    payload_bits = _bytes_to_bits(payload)
    all_bits = length_bits + payload_bits

    bit_index = 0

    for y in range(0, usable_height, 8):
        for x in range(0, usable_width, 8):
            if bit_index >= len(all_bits):
                break

            block = blue_channel[y:y + 8, x:x + 8]

            dct_block = cv2.dct(block)

            coefficient = dct_block[4, 3]

            if all_bits[bit_index] == 1:
                dct_block[4, 3] = max(abs(coefficient), 50.0)
            else:
                dct_block[4, 3] = -max(abs(coefficient), 50.0)

            blue_channel[y:y + 8, x:x + 8] = cv2.idct(dct_block)

            bit_index += 1

        if bit_index >= len(all_bits):
            break

    image[:, :, 0] = np.clip(blue_channel, 0, 255).astype(np.uint8)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(output_path, image)

    return {
        "width": width,
        "height": height,
        "capacity_bytes": capacity_bytes,
        "payload_size_bytes": len(payload),
        "output_path": output_path,
    }


def extract_dct(
    image_path: str,
) -> bytes:
    """
    Extract a payload embedded using embed_dct().
    """

    image = cv2.imread(image_path, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError(f"Unable to read image: {image_path}")

    blue_channel = image[:, :, 0].astype(np.float32)

    height, width = blue_channel.shape

    usable_width = width - (width % 8)
    usable_height = height - (height % 8)

    block_count = (usable_width // 8) * (usable_height // 8)

    if block_count < 32:
        raise ValueError("Image is too small for a DCT payload.")

    bits = []

    for y in range(0, usable_height, 8):
        for x in range(0, usable_width, 8):
            block = blue_channel[y:y + 8, x:x + 8]

            dct_block = cv2.dct(block)

            coefficient = dct_block[4, 3]

            bits.append(1 if coefficient >= 0 else 0)

            if len(bits) >= 32:
                break

        if len(bits) >= 32:
            break

    length_bytes = _bits_to_bytes(bits[:32])
    payload_length = int.from_bytes(
        length_bytes,
        byteorder="big",
    )

    total_bits = 32 + (payload_length * 8)

    if total_bits > block_count:
        raise ValueError("Invalid or corrupted DCT payload.")

    bits = []

    for y in range(0, usable_height, 8):
        for x in range(0, usable_width, 8):
            block = blue_channel[y:y + 8, x:x + 8]

            dct_block = cv2.dct(block)

            coefficient = dct_block[4, 3]

            bits.append(1 if coefficient >= 0 else 0)

            if len(bits) >= total_bits:
                break

        if len(bits) >= total_bits:
            break

    return _bits_to_bytes(bits[32:total_bits])


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