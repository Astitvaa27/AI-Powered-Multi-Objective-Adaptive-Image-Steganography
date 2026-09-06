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

    clean_df = df[df["label"] == "CLEAN"].set_index(
        "source_group"
    )

    stego_df = df[df["label"] == "STEGO"].copy()

    changes = []

    for feature in feature_columns:
        differences = []

        for _, stego_row in stego_df.iterrows():
            group = stego_row["source_group"]

            clean_value = clean_df.loc[group, feature]
            stego_value = stego_row[feature]

            differences.append(
                abs(stego_value - clean_value)
            )

        changes.append(
            {
                "feature": feature,
                "mean_absolute_change": sum(differences)
                / len(differences),
                "max_absolute_change": max(differences),
            }
        )

    result_df = pd.DataFrame(changes)

    result_df = result_df.sort_values(
        "mean_absolute_change",
        ascending=False,
    )

    print("SOURCE GROUPS:", df["source_group"].nunique())
    print("STEGO VARIANTS:", len(stego_df))
    print("FEATURES:", len(feature_columns))

    print("\nTOP 20 WITHIN-SOURCE FEATURE CHANGES:")
    print(
        result_df.head(20).to_string(index=False)
    )


if __name__ == "__main__":
    main()