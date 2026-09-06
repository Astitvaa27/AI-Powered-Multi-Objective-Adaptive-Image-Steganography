import pandas as pd
from pathlib import Path


CSV_PATH = Path(
    "storage/dataset/metadata/"
    "bossbase_payload_steganalysis_features.csv"
)


PAYLOAD_LEVELS = (
    "0.01bpp",
    "0.05bpp",
    "0.10bpp",
    "0.20bpp",
)


def main():
    df = pd.read_csv(CSV_PATH)

    feature_columns = [
        column
        for column in df.columns
        if column not in {"file_name", "label"}
    ]

    clean_df = df[df["label"] == "CLEAN"]

    print("TOTAL ROWS:", len(df))
    print("FEATURES:", len(feature_columns))
    print("CLEAN SAMPLES:", len(clean_df))

    print("\n" + "=" * 70)
    print("PAYLOAD FEATURE ANALYSIS")
    print("=" * 70)

    for payload in PAYLOAD_LEVELS:
        stego_df = df[
            df["file_name"].str.contains(
                f"_{payload}.pgm",
                regex=False,
            )
        ]

        print(f"\n--- CLEAN vs {payload} ---")
        print("CLEAN:", len(clean_df))
        print("STEGO:", len(stego_df))

        comparisons = []

        for feature in feature_columns:
            clean_mean = clean_df[feature].mean()
            stego_mean = stego_df[feature].mean()

            clean_std = clean_df[feature].std()
            stego_std = stego_df[feature].std()

            mean_difference = abs(
                stego_mean - clean_mean
            )

            pooled_std = (
                (clean_std ** 2 + stego_std ** 2) / 2
            ) ** 0.5

            if pooled_std > 0:
                standardized_difference = (
                    mean_difference / pooled_std
                )
            else:
                standardized_difference = 0.0

            comparisons.append(
                {
                    "feature": feature,
                    "clean_mean": clean_mean,
                    "stego_mean": stego_mean,
                    "mean_difference": mean_difference,
                    "standardized_difference":
                        standardized_difference,
                }
            )

        comparison_df = pd.DataFrame(comparisons)

        comparison_df = comparison_df.sort_values(
            "standardized_difference",
            ascending=False,
        )

        print("\nTOP 10 FEATURES:")
        print(
            comparison_df.head(10).to_string(
                index=False
            )
        )


if __name__ == "__main__":
    main()