import pandas as pd

from pathlib import Path


CSV_PATH = Path(
    "storage/dataset/metadata/bossbase_steganalysis_features.csv"
)


def main():
    df = pd.read_csv(CSV_PATH)

    feature_columns = [
        column
        for column in df.columns
        if column not in {
            "file_name",
            "label",
        }
    ]

    clean_df = df[df["label"] == "CLEAN"]
    stego_df = df[df["label"] == "STEGO"]

    results = []

    for feature in feature_columns:
        clean_values = clean_df[feature]
        stego_values = stego_df[feature]

        clean_mean = clean_values.mean()
        stego_mean = stego_values.mean()

        clean_std = clean_values.std()
        stego_std = stego_values.std()

        mean_difference = abs(
            stego_mean - clean_mean
        )

        combined_std = (
            clean_std + stego_std
        ) / 2

        if combined_std > 0:
            standardized_difference = (
                mean_difference / combined_std
            )
        else:
            standardized_difference = 0.0

        results.append(
            {
                "feature": feature,
                "clean_mean": clean_mean,
                "stego_mean": stego_mean,
                "mean_difference": mean_difference,
                "clean_std": clean_std,
                "stego_std": stego_std,
                "standardized_difference": standardized_difference,
            }
        )

    results_df = pd.DataFrame(results)

    results_df = results_df.sort_values(
        "standardized_difference",
        ascending=False,
    )

    print("CLEAN SAMPLES:", len(clean_df))
    print("STEGO SAMPLES:", len(stego_df))
    print("FEATURES:", len(feature_columns))

    print("\nTOP 20 CLEAN vs STEGO DIFFERENCES:")
    print(
        results_df.head(20).to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()