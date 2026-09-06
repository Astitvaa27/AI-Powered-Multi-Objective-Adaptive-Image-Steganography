import csv
from pathlib import Path

from backend.app.services.steganalysis_service import extract_statistical_features


clean_files = sorted(Path("storage/dataset/clean").glob("*.tiff"))
stego_files = sorted(Path("storage/dataset/stego").glob("*.tiff"))

files = [(f, "CLEAN") for f in clean_files] + [
    (f, "STEGO") for f in stego_files
]

print("PROCESSING:", len(files), "images")

rows = []

for file_path, label in files:
    features = extract_statistical_features(str(file_path))

    rows.append({
        "file_name": file_path.name,
        "label": label,
        **features,
    })

output_path = Path(
    "storage/dataset/metadata/steganalysis_features.csv"
)

output_path.parent.mkdir(parents=True, exist_ok=True)

fieldnames = list(rows[0].keys())

with open(
    output_path,
    "w",
    newline="",
    encoding="utf-8",
) as csv_file:
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print("CSV CREATED:", output_path)
print("ROWS:", len(rows))
print("FEATURES:", len(fieldnames) - 2)