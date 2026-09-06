import joblib
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

MODEL_PATH = Path(
    "storage/models/bossbase_steganalysis_random_forest.joblib"
)


def main():
    df = pd.read_csv(CSV_PATH)

    # Recover the original source-image ID.
    df["source_group"] = df["file_name"].str.extract(r"^(\d+)")

    # Split SOURCE GROUPS, not individual rows.
    groups = sorted(df["source_group"].unique())

    train_groups, test_groups = train_test_split(
        groups,
        test_size=0.20,
        random_state=42,
    )

    train_df = df[df["source_group"].isin(train_groups)].copy()
    test_df = df[df["source_group"].isin(test_groups)].copy()

    # Keep only actual feature columns.
    feature_columns = [
        column
        for column in df.columns
        if column not in {
            "file_name",
            "label",
            "source_group",
        }
    ]

    X_train = train_df[feature_columns]
    y_train = train_df["label"]

    X_test = test_df[feature_columns]
    y_test = test_df["label"]

    print("TRAIN SOURCE GROUPS:", len(train_groups))
    print("TEST SOURCE GROUPS:", len(test_groups))

    print("\nTRAIN SAMPLES:", len(train_df))
    print(y_train.value_counts())

    print("\nTEST SAMPLES:", len(test_df))
    print(y_test.value_counts())

    print("\nFEATURES:", len(feature_columns))

    # Train the same Random Forest configuration used by
    # the existing steganalysis detector.
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

    # Save this model separately from the existing USC-SIPI model.
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(
        {
            "model": model,
            "feature_names": feature_columns,
            "dataset": "BOSSBase_1.01",
            "train_groups": train_groups,
            "test_groups": test_groups,
        },
        MODEL_PATH,
    )

    print("MODEL SAVED:", MODEL_PATH)


if __name__ == "__main__":
    main()