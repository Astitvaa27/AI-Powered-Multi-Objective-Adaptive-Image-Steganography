import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.services.steganalysis_service import extract_statistical_features


CLEAN_DIR = Path("storage/dataset/bossbase/clean")
STEGO_DIR = Path("storage/dataset/bossbase/stego")
OUTPUT_PATH = Path(
    "storage/dataset/metadata/bossbase_steganalysis_features.csv"
)


def main():
    rows = []

    clean_files = sorted(CLEAN_DIR.glob("*.pgm"))
    stego_files = sorted(STEGO_DIR.glob("*.pgm"))

    print("CLEAN IMAGES:", len(clean_files))
    print("STEGO IMAGES:", len(stego_files))

    if len(clean_files) != 200:
        raise ValueError(
            f"Expected 200 clean images, found {len(clean_files)}."
        )

    if len(stego_files) != 600:
        raise ValueError(
            f"Expected 600 stego images, found {len(stego_files)}."
        )

    for image_path in clean_files:
        features = extract_statistical_features(str(image_path))

        row = {
            "file_name": image_path.name,
            "label": "CLEAN",
        }
        row.update(features)
        rows.append(row)

    for image_path in stego_files:
        features = extract_statistical_features(str(image_path))

        row = {
            "file_name": image_path.name,
            "label": "STEGO",
        }
        row.update(features)
        rows.append(row)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(rows[0].keys())

    with OUTPUT_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)

    print("CSV CREATED:", OUTPUT_PATH)
    print("ROWS:", len(rows))
    print("FEATURES:", len(fieldnames) - 2)


if __name__ == "__main__":
    main()