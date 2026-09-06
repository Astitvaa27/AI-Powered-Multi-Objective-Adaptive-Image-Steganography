import pandas as pd
from pathlib import Path

from sklearn.metrics import roc_auc_score


CSV_PATH = Path(
    "storage/dataset/metadata/"
    "bossbase_random_payload_steganalysis_features.csv"
)

PAYLOAD_LEVELS = (
    "0.01bpp",
    "0.05bpp",
    "0.10bpp",
    "0.20bpp",
)


def calculate_auc(clean_values, stego_values):
    y_true = [0] * len(clean_values) + [1] * len(stego_values)
    values = list(clean_values) + list(stego_values)

    try:
        auc = roc_auc_score(y_true, values)

        # AUC below 0.5 can still represent useful separation
        # if the feature direction is reversed.
        return max(auc, 1.0 - auc)

    except ValueError:
        return 0.5


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

    clean_df = df[
        df["label"] == "CLEAN"
    ].copy()

    print("TOTAL ROWS:", len(df))
    print("FEATURES:", len(feature_columns))
    print("CLEAN SAMPLES:", len(clean_df))

    print("\n" + "=" * 80)
    print("RANDOM-PAYLOAD FEATURE SEPARABILITY")
    print("=" * 80)

    for payload in PAYLOAD_LEVELS:

        stego_df = df[
            df["file_name"].str.contains(
                f"_stego_{payload}.pgm",
                regex=False,
            )
        ].copy()

        results = []

        for feature in feature_columns:

            clean_values = clean_df[feature]
            stego_values = stego_df[feature]

            clean_mean = clean_values.mean()
            stego_mean = stego_values.mean()

            mean_difference = abs(
                clean_mean - stego_mean
            )

            clean_std = clean_values.std()
            stego_std = stego_values.std()

            pooled_std = (
                (clean_std + stego_std) / 2
            )

            if pooled_std > 0:
                standardized_difference = (
                    mean_difference / pooled_std
                )
            else:
                standardized_difference = 0.0

            auc = calculate_auc(
                clean_values,
                stego_values,
            )

            results.append(
                {
                    "feature": feature,
                    "clean_mean": clean_mean,
                    "stego_mean": stego_mean,
                    "mean_difference": mean_difference,
                    "standardized_difference":
                        standardized_difference,
                    "auc": auc,
                }
            )

        result_df = pd.DataFrame(results)

        result_df = result_df.sort_values(
            "auc",
            ascending=False,
        )

        print("\n" + "-" * 80)
        print(f"PAYLOAD: {payload}")
        print("-" * 80)

        print(
            result_df.head(15).to_string(
                index=False,
                formatters={
                    "clean_mean":
                        "{:.6f}".format,
                    "stego_mean":
                        "{:.6f}".format,
                    "mean_difference":
                        "{:.6f}".format,
                    "standardized_difference":
                        "{:.6f}".format,
                    "auc":
                        "{:.4f}".format,
                },
            )
        )


if __name__ == "__main__":
    main()