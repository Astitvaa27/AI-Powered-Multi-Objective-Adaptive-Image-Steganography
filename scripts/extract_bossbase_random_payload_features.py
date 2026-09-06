import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from backend.app.services.steganalysis_service import (
    extract_statistical_features,
)


CLEAN_DIR = Path(
    "storage/dataset/bossbase/clean"
)

STEGO_ROOT = Path(
    "storage/dataset/bossbase/stego_random_payload"
)

OUTPUT_CSV = Path(
    "storage/dataset/metadata/"
    "bossbase_random_payload_steganalysis_features.csv"
)


PAYLOAD_LEVELS = (
    "0.01bpp",
    "0.05bpp",
    "0.10bpp",
    "0.20bpp",
)


def main():
    rows = []

    clean_files = sorted(
        CLEAN_DIR.glob("*.pgm")
    )

    if len(clean_files) != 200:
        raise ValueError(
            f"Expected 200 clean images, "
            f"found {len(clean_files)}."
        )

    print("PROCESSING CLEAN IMAGES:", len(clean_files))

    for index, image_path in enumerate(
        clean_files,
        start=1,
    ):
        features = extract_statistical_features(
            str(image_path)
        )

        rows.append(
            {
                "file_name": image_path.name,
                "label": "CLEAN",
                **features,
            }
        )

        print(
            f"[CLEAN] "
            f"[{index}/200] "
            f"{image_path.name}"
        )

    for payload in PAYLOAD_LEVELS:

        payload_dir = STEGO_ROOT / payload

        stego_files = sorted(
            payload_dir.glob("*.pgm")
        )

        if len(stego_files) != 200:
            raise ValueError(
                f"Expected 200 stego images for "
                f"{payload}, found {len(stego_files)}."
            )

        print(
            f"\nPROCESSING {payload}: "
            f"{len(stego_files)} images"
        )

        for index, image_path in enumerate(
            stego_files,
            start=1,
        ):
            features = extract_statistical_features(
                str(image_path)
            )

            rows.append(
                {
                    "file_name": image_path.name,
                    "label": "STEGO",
                    **features,
                }
            )

            print(
                f"[{payload}] "
                f"[{index}/200] "
                f"{image_path.name}"
            )

    df = pd.DataFrame(rows)

    OUTPUT_CSV.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        OUTPUT_CSV,
        index=False,
    )

    feature_columns = [
        column
        for column in df.columns
        if column not in {
            "file_name",
            "label",
        }
    ]

    print("\n" + "=" * 60)
    print("CSV CREATED:", OUTPUT_CSV)
    print("ROWS:", len(df))
    print("COLUMNS:", len(df.columns))
    print("FEATURES:", len(feature_columns))

    print("\nLABELS:")
    print(df["label"].value_counts())

    print("\nMISSING VALUES:", int(df.isna().sum().sum()))


if __name__ == "__main__":
    main()