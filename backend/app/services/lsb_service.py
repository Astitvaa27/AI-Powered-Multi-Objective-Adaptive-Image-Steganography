from pathlib import Path

import numpy as np
from PIL import Image


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


def _get_channel_indices(channel_mode: str) -> list[int]:
    channel_mode = channel_mode.upper()

    mapping = {
        "R": [0],
        "G": [1],
        "B": [2],
        "RGB": [0, 1, 2],
    }

    if channel_mode not in mapping:
        raise ValueError(
            "channel_mode must be one of: R, G, B, RGB"
        )

    return mapping[channel_mode]


def _get_target_indices(
    pixel_count: int,
    channel_indices: list[int],
) -> np.ndarray:
    """
    Flat sample indices used for embedding, ordered pixel by pixel and
    then by channel — e.g. R0, G0, B0, R1, G1, B1 ... for RGB mode.
    """

    pixel_offsets = np.arange(pixel_count, dtype=np.int64)[:, None] * 3

    return (
        pixel_offsets + np.asarray(channel_indices, dtype=np.int64)[None, :]
    ).reshape(-1)


def _validate_lsb_bits(lsb_bits: int) -> int:
    if lsb_bits < 1 or lsb_bits > 3:
        raise ValueError("lsb_bits must be between 1 and 3")

    return lsb_bits


def lsb_capacity_bits(
    pixel_count: int,
    channel_count: int,
    lsb_bits: int,
) -> int:
    """Total LSB bits available for a pixel count and channel selection."""

    return pixel_count * channel_count * lsb_bits


def read_lsb_bits(
    flat_samples: np.ndarray,
    samples_per_pixel: int,
    channel_indices: list[int],
    lsb_bits: int,
    bit_count: int,
) -> np.ndarray:
    """
    Read the first bit_count LSB bits from row-major, channel-interleaved
    uint8 samples (the layout of np.asarray(image).reshape(-1)).

    Samples are visited pixel by pixel and, within a pixel, in the order of
    channel_indices; the lsb_bits low bits of each sample are emitted from
    high to low. Only the samples needed for bit_count bits are touched,
    and flat_samples is never modified. This is the bit reader behind
    extract_lsb() and the automatic LSB search.
    """

    lsb_bits = _validate_lsb_bits(lsb_bits)

    if bit_count <= 0:
        return np.zeros(0, dtype=np.uint8)

    sample_count = -(-bit_count // lsb_bits)
    pixels_needed = -(-sample_count // len(channel_indices))

    pixels = flat_samples.reshape(-1, samples_per_pixel)[:pixels_needed]
    values = pixels[:, channel_indices].reshape(-1)[:sample_count]

    if values.size < sample_count:
        raise ValueError("Not enough samples for the requested bit count.")

    mask = np.uint8((1 << lsb_bits) - 1)
    shifts = np.arange(lsb_bits - 1, -1, -1, dtype=np.uint8)

    bits = (((values & mask)[:, None] >> shifts) & 1).astype(np.uint8)

    return bits.reshape(-1)[:bit_count]


def calculate_capacity(
    image: Image.Image,
    channel_mode: str = "RGB",
    lsb_bits: int = 1,
) -> int:
    """Return LSB payload capacity in bytes."""

    lsb_bits = _validate_lsb_bits(lsb_bits)

    channel_indices = _get_channel_indices(channel_mode)

    total_bits = (
        image.width
        * image.height
        * len(channel_indices)
        * lsb_bits
    )

    # 32 bits are reserved for the payload length.
    usable_bits = max(0, total_bits - 32)

    return usable_bits // 8


def embed_lsb(
    input_path: str,
    output_path: str,
    payload: bytes,
    channel_mode: str = "RGB",
    lsb_bits: int = 1,
) -> dict:
    """
    Embed a payload using configurable LSB substitution.
    """

    lsb_bits = _validate_lsb_bits(lsb_bits)

    image = Image.open(input_path).convert("RGB")

    channel_indices = _get_channel_indices(channel_mode)

    capacity = calculate_capacity(
        image,
        channel_mode,
        lsb_bits,
    )

    if len(payload) > capacity:
        raise ValueError(
            f"Payload too large. Maximum capacity is {capacity} bytes."
        )

    # 32-bit big-endian length header followed by the payload, MSB first.
    all_bits = np.unpackbits(
        np.frombuffer(
            len(payload).to_bytes(4, byteorder="big") + payload,
            dtype=np.uint8,
        )
    )

    # Row-major pixels with interleaved R, G, B samples — the same order
    # Image.getdata() yields, so the bit layout is unchanged.
    flat_pixels = np.asarray(image, dtype=np.uint8).reshape(-1).copy()

    target_indices = _get_target_indices(
        image.width * image.height,
        channel_indices,
    )

    total_capacity_bits = len(target_indices) * lsb_bits

    if len(all_bits) > total_capacity_bits:
        raise ValueError(
            "Payload exceeds available LSB capacity."
        )

    # Group the bit stream into lsb_bits-sized chunks. An incomplete
    # final chunk is padded on the right with zeros.
    chunk_count = -(-len(all_bits) // lsb_bits)
    padded_bits = np.zeros(chunk_count * lsb_bits, dtype=np.uint8)
    padded_bits[:len(all_bits)] = all_bits

    shifts = np.arange(lsb_bits - 1, -1, -1, dtype=np.uint8)
    values = (
        padded_bits.reshape(chunk_count, lsb_bits) << shifts
    ).sum(axis=1).astype(np.uint8)

    mask = (1 << lsb_bits) - 1
    keep_mask = np.uint8(0xFF & ~mask)

    selected = target_indices[:chunk_count]

    flat_pixels[selected] = (flat_pixels[selected] & keep_mask) | values

    stego_image = Image.fromarray(
        flat_pixels.reshape(image.height, image.width, 3)
    )

    Path(output_path).parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    stego_image.save(output_path)

    return {
        "width": image.width,
        "height": image.height,
        "channels": 3,
        "channel_mode": channel_mode.upper(),
        "lsb_bits": lsb_bits,
        "payload_size_bytes": len(payload),
        "capacity_bytes": capacity,
        "output_path": output_path,
    }

def embed_lsb_grayscale(
    input_path: str,
    output_path: str,
    payload: bytes,
    lsb_bits: int = 1,
) -> dict:
    """
    Embed a payload into an 8-bit grayscale image using LSB substitution.
    """

    lsb_bits = _validate_lsb_bits(lsb_bits)

    image = Image.open(input_path).convert("L")

    pixels = list(image.getdata())

    total_bits = len(pixels) * lsb_bits
    usable_bits = max(0, total_bits - 32)
    capacity = usable_bits // 8

    if len(payload) > capacity:
        raise ValueError(
            f"Payload too large. Maximum capacity is {capacity} bytes."
        )

    length_bits = _bytes_to_bits(
        len(payload).to_bytes(4, byteorder="big")
    )

    payload_bits = _bytes_to_bits(payload)

    all_bits = length_bits + payload_bits

    if len(all_bits) > total_bits:
        raise ValueError(
            "Payload exceeds available grayscale LSB capacity."
        )

    mask = (1 << lsb_bits) - 1

    modified_pixels = pixels.copy()

    bit_position = 0

    for pixel_index in range(len(modified_pixels)):

        if bit_position >= len(all_bits):
            break

        remaining_bits = len(all_bits) - bit_position

        chunk_size = min(lsb_bits, remaining_bits)

        value = 0

        for bit in all_bits[
            bit_position:
            bit_position + chunk_size
        ]:
            value = (value << 1) | bit

        if chunk_size < lsb_bits:
            value <<= (lsb_bits - chunk_size)

        modified_pixels[pixel_index] = (
            modified_pixels[pixel_index] & ~mask
        ) | value

        bit_position += chunk_size

    stego_image = Image.new(
        "L",
        image.size,
    )

    stego_image.putdata(modified_pixels)

    Path(output_path).parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    stego_image.save(output_path)

    return {
        "width": image.width,
        "height": image.height,
        "channels": 1,
        "channel_mode": "L",
        "lsb_bits": lsb_bits,
        "payload_size_bytes": len(payload),
        "capacity_bytes": capacity,
        "output_path": output_path,
    }

def extract_lsb(
    image_path: str,
    channel_mode: str = "RGB",
    lsb_bits: int = 1,
) -> bytes:
    """
    Extract a payload previously embedded using embed_lsb().
    """

    lsb_bits = _validate_lsb_bits(lsb_bits)

    image = Image.open(image_path).convert("RGB")

    channel_indices = _get_channel_indices(channel_mode)

    flat_pixels = np.asarray(image, dtype=np.uint8).reshape(-1)

    total_capacity_bits = lsb_capacity_bits(
        image.width * image.height,
        len(channel_indices),
        lsb_bits,
    )

    if total_capacity_bits < 32:
        raise ValueError(
            "Image is too small for an LSB payload."
        )

    def read_bits(bit_count: int) -> np.ndarray:
        return read_lsb_bits(
            flat_pixels,
            3,
            channel_indices,
            lsb_bits,
            bit_count,
        )

    length_bytes = np.packbits(read_bits(32)).tobytes()

    payload_length = int.from_bytes(
        length_bytes,
        byteorder="big",
    )

    payload_bits_count = payload_length * 8
    total_bits = 32 + payload_bits_count

    if total_bits > total_capacity_bits:
        raise ValueError(
            "Invalid or corrupted LSB payload."
        )

    payload_bits = read_bits(total_bits)[32:]

    return np.packbits(payload_bits).tobytes()

def extract_lsb_grayscale(
    image_path: str,
    lsb_bits: int = 1,
) -> bytes:
    """
    Extract a payload from an 8-bit grayscale image
    using LSB substitution.
    """

    lsb_bits = _validate_lsb_bits(lsb_bits)

    image = Image.open(image_path).convert("L")

    pixels = list(image.getdata())

    total_capacity_bits = len(pixels) * lsb_bits

    if total_capacity_bits < 32:
        raise ValueError(
            "Image is too small for an LSB payload."
        )

    mask = (1 << lsb_bits) - 1

    all_bits = []

    for pixel in pixels:
        value = pixel & mask

        for i in range(lsb_bits - 1, -1, -1):
            all_bits.append((value >> i) & 1)

    length_bits = all_bits[:32]

    length_bytes = _bits_to_bytes(length_bits)

    payload_length = int.from_bytes(
        length_bytes,
        byteorder="big",
    )

    payload_bits_count = payload_length * 8
    total_bits = 32 + payload_bits_count

    if total_bits > total_capacity_bits:
        raise ValueError(
            "Invalid or corrupted grayscale LSB payload."
        )

    payload_bits = all_bits[32:total_bits]

    return _bits_to_bytes(payload_bits)