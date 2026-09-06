import pandas as pd

from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split


CSV_PATH = Path(
    "storage/dataset/metadata/bossbase_steganalysis_features.csv"
)


def main():
    df = pd.read_csv(CSV_PATH)

    df["source_group"] = df["file_name"].str.extract(r"^(\d+)")

    groups = sorted(df["source_group"].unique())

    train_groups, test_groups = train_test_split(
        groups,
        test_size=0.20,
        random_state=42,
    )

    train_df = df[df["source_group"].isin(train_groups)].copy()
    test_df = df[df["source_group"].isin(test_groups)].copy()

    # Keep only steganalysis-specific features.
    feature_columns = [
        column
        for column in df.columns
        if (
            (
                "lsb" in column
                or "pair_rate" in column
                or "_rs_" in column
            )
            and column not in {
                "file_name",
                "label",
                "source_group",
            }
        )
    ]

    X_train = train_df[feature_columns]
    y_train = train_df["label"]

    X_test = test_df[feature_columns]
    y_test = test_df["label"]

    print("TRAIN SAMPLES:", len(train_df))
    print("TEST SAMPLES:", len(test_df))
    print("FEATURES:", len(feature_columns))

    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    accuracy = accuracy_score(
        y_test,
        predictions,
    )

    confusion = confusion_matrix(
        y_test,
        predictions,
        labels=["CLEAN", "STEGO"],
    )

    print("\nTEST ACCURACY:", accuracy)

    print("\nCONFUSION MATRIX:")
    print(confusion)

    print("\nCLASSIFICATION REPORT:")
    print(
        classification_report(
            y_test,
            predictions,
            labels=["CLEAN", "STEGO"],
            zero_division=0,
        )
    )


if __name__ == "__main__":
    main()