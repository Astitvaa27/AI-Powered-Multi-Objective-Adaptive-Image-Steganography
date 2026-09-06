import pandas as pd

CSV_PATH = "storage/dataset/metadata/steganalysis_features.csv"

df = pd.read_csv(CSV_PATH)

test_groups = ["sipi_4.1.06", "sipi_4.1.08"]

df["sample_group"] = df["file_name"].str.extract(r"(sipi_4\.1\.\d+)")

test_df = df[df["sample_group"].isin(test_groups)].copy()

feature_columns = [
    c for c in df.columns
    if c not in {"file_name", "label", "sample_group"}
]

clean_df = test_df[test_df["label"] == "CLEAN"]
stego_df = test_df[test_df["label"] == "STEGO"]

stego_mean = stego_df[feature_columns].mean()

results = []

for feature in feature_columns:
    clean_mean = clean_df[feature].mean()
    stego_average = stego_mean[feature]

    difference = abs(clean_mean - stego_average)

    results.append({
        "feature": feature,
        "clean_mean": clean_mean,
        "stego_mean": stego_average,
        "absolute_difference": difference,
    })

results_df = pd.DataFrame(results)

results_df = results_df.sort_values(
    "absolute_difference",
    ascending=False,
)

print("TEST CLEAN SAMPLES:")
print(clean_df[["file_name", "label"]].to_string(index=False))

print("\nTOP 20 FEATURES WHERE CLEAN DIFFERS FROM TEST STEGO:")
print(
    results_df.head(20).to_string(
        index=False,
        float_format=lambda x: f"{x:.6f}",
    )
)

print("\nCLEAN FEATURE VALUES:")
print(
    clean_df[
        ["file_name"] + feature_columns
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.6f}",
    )
)
