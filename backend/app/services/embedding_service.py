"""
Single dispatch point for the implemented embedding methods.

The manual /steganography endpoints and the adaptive optimiser both route
through these helpers so that every caller embeds, extracts and measures
capacity in exactly the same way.
"""

from PIL import Image

from backend.app.services.dct_service import (
    calculate_dct_capacity,
    embed_dct,
    extract_dct,
)
from backend.app.services.dwt_service import (
    calculate_dwt_capacity,
    embed_dwt,
    extract_dwt,
)
from backend.app.services.lsb_service import (
    calculate_capacity,
    embed_lsb,
    extract_lsb,
)


SUPPORTED_METHODS = ("LSB", "DCT", "DWT")

# Which request parameters each method actually consumes.
METHOD_PARAMETERS = {
    "LSB": {"channel_mode": True, "lsb_bits": True},
    "DCT": {"channel_mode": False, "lsb_bits": False},
    "DWT": {"channel_mode": False, "lsb_bits": False},
}


def normalise_method_code(method: str | None) -> str:
    """Upper-case a method code and reject anything not implemented."""

    normalised = (method or "").upper().strip()

    if normalised not in SUPPORTED_METHODS:
        raise ValueError(
            "Unsupported embedding method. Supported methods: "
            + ", ".join(SUPPORTED_METHODS)
        )

    return normalised


def calculate_method_capacity(
    method: str,
    image: Image.Image,
    channel_mode: str = "RGB",
    lsb_bits: int = 1,
) -> int:
    """Payload capacity in bytes for a method, without embedding anything."""

    if method == "LSB":
        return calculate_capacity(image, channel_mode, lsb_bits)

    if method == "DCT":
        return calculate_dct_capacity(image.width, image.height)

    if method == "DWT":
        return calculate_dwt_capacity(image.width, image.height)

    raise ValueError(f"Unsupported embedding method: {method}")


def embed_with_method(
    method: str,
    input_path: str,
    output_path: str,
    payload: bytes,
    channel_mode: str = "RGB",
    lsb_bits: int = 1,
) -> dict:
    """Embed a payload with the given method and return its result dict."""

    if method == "LSB":
        return embed_lsb(
            input_path=input_path,
            output_path=output_path,
            payload=payload,
            channel_mode=channel_mode,
            lsb_bits=lsb_bits,
        )

    if method == "DCT":
        return embed_dct(
            input_path=input_path,
            output_path=output_path,
            payload=payload,
        )

    if method == "DWT":
        return embed_dwt(
            input_path=input_path,
            output_path=output_path,
            payload=payload,
        )

    raise ValueError(f"Unsupported embedding method: {method}")


def extract_with_method(
    method: str,
    image_path: str,
    channel_mode: str = "RGB",
    lsb_bits: int = 1,
) -> bytes:
    """Recover a payload previously embedded with the given method."""

    if method == "LSB":
        return extract_lsb(
            image_path=image_path,
            channel_mode=channel_mode,
            lsb_bits=lsb_bits,
        )

    if method == "DCT":
        return extract_dct(image_path=image_path)

    if method == "DWT":
        return extract_dwt(image_path=image_path)

    raise ValueError(f"Unsupported embedding method: {method}")
