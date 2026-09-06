import pandas as pd

from pathlib import Path


CSV_PATH = Path(
    "storage/dataset/metadata/bossbase_steganalysis_features.csv"
)


def main():
    df = pd.read_csv(CSV_PATH)

    df["source_group"] = df["file_name"].str.extract(r"^(\d+)")

    feature_columns = [
        column
        for column in df.columns
        if column not in {
            "file_name",
            "label",
            "source_group",
        }
    ]

    clean_df = (
        df[df["label"] == "CLEAN"]
        .set_index("source_group")
    )

    stego_df = df[df["label"] == "STEGO"]

    results = []

    for feature in feature_columns:
        relative_changes = []

        for _, stego_row in stego_df.iterrows():
            group = stego_row["source_group"]

            clean_value = float(
                clean_df.loc[group, feature]
            )
            stego_value = float(
                stego_row[feature]
            )

            # Relative change with respect to the
            # original clean source value.
            if abs(clean_value) > 1e-12:
                relative_change = (
                    abs(stego_value - clean_value)
                    / abs(clean_value)
                )
            else:
                relative_change = 0.0

            relative_changes.append(relative_change)

        results.append(
            {
                "feature": feature,
                "mean_relative_change": (
                    sum(relative_changes)
                    / len(relative_changes)
                ),
                "max_relative_change": max(
                    relative_changes
                ),
            }
        )

    result_df = pd.DataFrame(results)

    result_df = result_df.sort_values(
        "mean_relative_change",
        ascending=False,
    )

    print("SOURCE GROUPS:", df["source_group"].nunique())
    print("STEGO VARIANTS:", len(stego_df))
    print("FEATURES:", len(feature_columns))

    print("\nTOP 20 RELATIVE CHANGES:")
    print(
        result_df.head(20).to_string(index=False)
    )


if __name__ == "__main__":
    main()