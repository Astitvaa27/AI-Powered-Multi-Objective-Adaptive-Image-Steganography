import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.services.steganalysis_service import (
    extract_statistical_features,
)


CLEAN_DIR = Path("storage/dataset/bossbase/clean")
STEGO_ROOT = Path("storage/dataset/bossbase/stego_payload")

OUTPUT_PATH = Path(
    "storage/dataset/metadata/bossbase_payload_steganalysis_features.csv"
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
            f"Expected 200 clean images, found {len(clean_files)}."
        )

    print("CLEAN IMAGES:", len(clean_files))

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
            f"[CLEAN {index}/200] "
            f"{image_path.name}"
        )

    for payload_level in PAYLOAD_LEVELS:
        payload_dir = (
            STEGO_ROOT / payload_level
        )

        stego_files = sorted(
            payload_dir.glob("*.pgm")
        )

        if len(stego_files) != 200:
            raise ValueError(
                f"Expected 200 images for "
                f"{payload_level}, found "
                f"{len(stego_files)}."
            )

        print(
            f"\n{payload_level} IMAGES:",
            len(stego_files),
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
                f"[{payload_level} "
                f"{index}/200] "
                f"{image_path.name}"
            )

    df = pd.DataFrame(rows)

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print(
        "\nCSV CREATED:",
        OUTPUT_PATH,
    )

    print("ROWS:", len(df))
    print(
        "FEATURES:",
        len(df.columns) - 2,
    )

    print("\nLABELS:")
    print(df["label"].value_counts())


if __name__ == "__main__":
    main()