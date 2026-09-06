import pandas as pd
from pathlib import Path


CSV_PATH = Path(
    "storage/dataset/metadata/"
    "bossbase_random_payload_steganalysis_features.csv"
)

CORRELATION_THRESHOLD = 0.95


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

    features = df[feature_columns]

    correlation_matrix = features.corr().abs()

    duplicate_pairs = []

    for i, feature_a in enumerate(feature_columns):
        for j in range(i + 1, len(feature_columns)):
            feature_b = feature_columns[j]
            correlation = correlation_matrix.loc[
                feature_a,
                feature_b,
            ]

            if correlation >= CORRELATION_THRESHOLD:
                duplicate_pairs.append(
                    (
                        feature_a,
                        feature_b,
                        correlation,
                    )
                )

    duplicate_pairs.sort(
        key=lambda item: item[2],
        reverse=True,
    )

    print("TOTAL FEATURES:", len(feature_columns))
    print(
        "CORRELATION THRESHOLD:",
        CORRELATION_THRESHOLD,
    )

    print("\n" + "=" * 80)
    print("HIGHLY CORRELATED FEATURE PAIRS")
    print("=" * 80)

    if not duplicate_pairs:
        print("No highly correlated feature pairs found.")
    else:
        for feature_a, feature_b, correlation in duplicate_pairs:
            print(
                f"{correlation:.4f}  "
                f"{feature_a}  <->  {feature_b}"
            )

    print("\nTOTAL HIGHLY CORRELATED PAIRS:")
    print(len(duplicate_pairs))


if __name__ == "__main__":
    main()