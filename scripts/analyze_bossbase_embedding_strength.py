from pathlib import Path

import numpy as np
from PIL import Image


CLEAN_DIR = Path("storage/dataset/bossbase/clean")
STEGO_DIR = Path("storage/dataset/bossbase/stego")


def main():
    clean_files = sorted(CLEAN_DIR.glob("*.pgm"))

    total_pixels = 0
    total_changed_pixels = 0
    variant_stats = {}

    for clean_path in clean_files:
        clean = np.asarray(
            Image.open(clean_path).convert("L"),
            dtype=np.uint8,
        )

        total_pixels += clean.size

        for lsb_bits in (1, 2, 3):
            stego_path = (
                STEGO_DIR
                / f"{clean_path.stem}_stego_lsb{lsb_bits}.pgm"
            )

            stego = np.asarray(
                Image.open(stego_path).convert("L"),
                dtype=np.uint8,
            )

            changed = np.count_nonzero(clean != stego)

            key = f"LSB{lsb_bits}"

            if key not in variant_stats:
                variant_stats[key] = {
                    "images": 0,
                    "changed_pixels": 0,
                }

            variant_stats[key]["images"] += 1
            variant_stats[key]["changed_pixels"] += changed

    print("SOURCE IMAGES:", len(clean_files))
    print("PIXELS PER IMAGE:", 512 * 512)
    print("PAYLOAD BYTES:", 21)
    print("PAYLOAD BITS:", 21 * 8)

    print("\nTHEORETICAL PAYLOAD BPP:")
    print(
        "21 bytes / 512x512 =",
        (21 * 8) / (512 * 512),
    )

    print("\nCHANGED PIXEL STATISTICS:")

    for key, stats in variant_stats.items():
        changed_pixels = stats["changed_pixels"]
        images = stats["images"]

        average_changed = changed_pixels / images

        change_rate = (
            changed_pixels
            / (images * 512 * 512)
        )

        print(f"\n{key}:")
        print("  IMAGES:", images)
        print(
            "  AVERAGE CHANGED PIXELS:",
            average_changed,
        )
        print(
            "  PIXEL CHANGE RATE:",
            change_rate,
        )

    print("\nTOTAL PIXELS ACROSS ALL CLEAN IMAGES:")
    print(total_pixels)


if __name__ == "__main__":
    main()