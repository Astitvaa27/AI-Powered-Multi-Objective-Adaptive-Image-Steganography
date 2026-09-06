from PIL import Image
import numpy as np
from pathlib import Path

base = Path("storage/dataset")

pairs = [
    ("05", "lsb1_rgb"),
    ("05", "lsb1_rgb_medium"),
    ("05", "lsb2_rgb_medium"),
    ("05", "lsb3_rgb_medium"),
    ("06", "lsb1_rgb"),
    ("06", "lsb1_rgb_medium"),
    ("06", "lsb2_rgb_medium"),
    ("06", "lsb3_rgb_medium"),
]

for source, variant in pairs:
    clean = np.asarray(
        Image.open(base / f"clean/sipi_4.1.{source}.tiff")
    ).astype(np.int16)

    stego = np.asarray(
        Image.open(
            base / f"stego/sipi_4.1.{source}_stego_{variant}.tiff"
        )
    ).astype(np.int16)

    changed_pixels = np.any(clean != stego, axis=2).sum()
    total_pixels = clean.shape[0] * clean.shape[1]

    percentage = (changed_pixels / total_pixels) * 100

    print(
        f"{source} {variant}: "
        f"changed_pixels={changed_pixels}, "
        f"percentage={percentage:.4f}%"
    )
