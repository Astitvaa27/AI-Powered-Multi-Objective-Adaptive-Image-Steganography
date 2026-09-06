import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity


def calculate_metrics(
    original_path: str,
    stego_path: str,
) -> dict:
    """
    Calculate MSE, PSNR and SSIM between
    the original and stego images.
    """

    original = np.asarray(
        Image.open(original_path).convert("RGB"),
        dtype=np.float64,
    )

    stego = np.asarray(
        Image.open(stego_path).convert("RGB"),
        dtype=np.float64,
    )

    if original.shape != stego.shape:
        raise ValueError(
            "Original and stego images must have the same dimensions."
        )

    # Mean Squared Error
    mse = float(np.mean((original - stego) ** 2))

    # Peak Signal-to-Noise Ratio
    if mse == 0:
        psnr = float("inf")
    else:
        psnr = float(10 * np.log10((255 ** 2) / mse))

    # Structural Similarity
    ssim = float(
        structural_similarity(
            original,
            stego,
            channel_axis=2,
            data_range=255,
        )
    )

    return {
        "mse": mse,
        "psnr": psnr,
        "ssim": ssim,
    }