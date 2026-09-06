import pandas as pd
from pathlib import Path

CSV_PATH = Path("storage/dataset/metadata/steganalysis_features.csv")

df = pd.read_csv(CSV_PATH)

df["sample_group"] = df["file_name"].str.extract(r"(sipi_4\.1\.\d+)")

feature_columns = [
    c for c in df.columns
    if c not in {"file_name", "label", "sample_group"}
]

for group in ["sipi_4.1.06", "sipi_4.1.08"]:

    print("\n" + "=" * 90)
    print(f"SOURCE GROUP: {group}")
    print("=" * 90)

    group_df = df[df["sample_group"] == group].copy()

    clean = group_df[group_df["label"] == "CLEAN"].iloc[0]
    stego = group_df[group_df["label"] == "STEGO"].copy()

    print(f"\nCLEAN IMAGE: {clean['file_name']}")
    print(f"STego variants: {len(stego)}")

    results = []

    for feature in feature_columns:

        clean_value = float(clean[feature])
        stego_mean = float(stego[feature].mean())

        absolute_difference = abs(clean_value - stego_mean)

        results.append({
            "feature": feature,
            "clean_value": clean_value,
            "stego_mean": stego_mean,
            "absolute_difference": absolute_difference,
        })

    results_df = pd.DataFrame(results)

    results_df = results_df.sort_values(
        "absolute_difference",
        ascending=False,
    )

    print("\nTOP 20 FEATURES CHANGED BY EMBEDDING:")
    print(
        results_df.head(20).to_string(
            index=False,
            float_format=lambda x: f"{x:.6f}",
        )
    )

    print("\nALL STEGO VARIANT PREDICTIVE FEATURES:")
    print(
        stego[
            ["file_name", "label"] + feature_columns
        ].to_string(
            index=False,
            float_format=lambda x: f"{x:.6f}",
        )
    )
