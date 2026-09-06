from PIL import Image
import numpy as np
from pathlib import Path

base = Path("storage/dataset")

pairs = [
    ("05", "lsb1_rgb"),
    ("05", "lsb1_rgb_medium"),
    ("05", "lsb2_rgb_medium"),
    ("05", "lsb3_rgb_medium"),
]

for source, variant in pairs:
    clean = np.asarray(
        Image.open(base / f"clean/sipi_4.1.{source}.tiff")
    ).astype(np.int16)

    stego = np.asarray(
        Image.open(base / f"stego/sipi_4.1.{source}_stego_{variant}.tiff")
    ).astype(np.int16)

    changed = np.any(clean != stego, axis=2)

    ys, xs = np.where(changed)

    if len(xs) == 0:
        print(f"{source} {variant}: no changes")
        continue

    height, width = changed.shape

    print(
        f"{source} {variant}: "
        f"first_x={xs.min()}, "
        f"last_x={xs.max()}, "
        f"first_y={ys.min()}, "
        f"last_y={ys.max()}, "
        f"changed={len(xs)}"
    )
