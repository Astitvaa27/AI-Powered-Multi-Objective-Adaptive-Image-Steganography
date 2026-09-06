import sys
from pathlib import Path

import pandas as pd

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from backend.app.services.steganalysis_service import (
    calculate_local_residual_statistics,
)


DATA_ROOT = Path("storage/dataset/bossbase")

CLEAN_DIR = DATA_ROOT / "clean"
STEGO_DIR = DATA_ROOT / "stego_random_payload"

PAYLOAD_LEVELS = (
    "0.01bpp",
    "0.05bpp",
    "0.10bpp",
    "0.20bpp",
)


def main():
    rows = []

    clean_files = sorted(CLEAN_DIR.glob("*.pgm"))

    for image_path in clean_files:
        features = calculate_local_residual_statistics(
            str(image_path)
        )

        rows.append(
            {
                "file_name": image_path.name,
                "label": "CLEAN",
                **features,
            }
        )

    for payload in PAYLOAD_LEVELS:

        payload_dir = STEGO_DIR / payload

        stego_files = sorted(
            payload_dir.glob("*.pgm")
        )

        for image_path in stego_files:
            features = calculate_local_residual_statistics(
                str(image_path)
            )

            rows.append(
                {
                    "file_name": image_path.name,
                    "label": "STEGO",
                    "payload": payload,
                    **features,
                }
            )

    df = pd.DataFrame(rows)

    feature_columns = [
        "residual_horizontal_mean",
        "residual_horizontal_std",
        "residual_horizontal_zero_ratio",
        "residual_vertical_mean",
        "residual_vertical_std",
        "residual_vertical_zero_ratio",
    ]

    print("TOTAL IMAGES:", len(df))
    print("FEATURES:", len(feature_columns))

    print("\n" + "=" * 80)
    print("LOCAL RESIDUAL FEATURE ANALYSIS")
    print("=" * 80)

    clean_df = df[
        df["label"] == "CLEAN"
    ]

    for payload in PAYLOAD_LEVELS:

        stego_df = df[
            df["payload"] == payload
        ]

        print("\n" + "-" * 80)
        print(f"PAYLOAD: {payload}")
        print("-" * 80)

        for feature in feature_columns:

            clean_mean = clean_df[feature].mean()
            stego_mean = stego_df[feature].mean()

            difference = abs(
                clean_mean - stego_mean
            )

            clean_std = clean_df[feature].std()
            stego_std = stego_df[feature].std()

            pooled_std = (
                clean_std + stego_std
            ) / 2

            if pooled_std > 0:
                standardized_difference = (
                    difference / pooled_std
                )
            else:
                standardized_difference = 0.0

            print(
                f"{feature:40s} "
                f"clean={clean_mean:.6f} "
                f"stego={stego_mean:.6f} "
                f"diff={difference:.6f} "
                f"std_diff={standardized_difference:.4f}"
            )


if __name__ == "__main__":
    main()