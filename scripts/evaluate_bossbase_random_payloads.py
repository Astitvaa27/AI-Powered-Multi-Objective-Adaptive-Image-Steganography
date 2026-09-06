import pandas as pd
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    classification_report,
)


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


def main():
    df = pd.read_csv(CSV_PATH)

    df["source_group"] = df["file_name"].str.extract(
        r"^(\d+)"
    )[0]

    feature_columns = [
        column
        for column in df.columns
        if column not in {
            "file_name",
            "label",
            "source_group",
        }
    ]

    print("TOTAL DATASET:", len(df))
    print("FEATURES:", len(feature_columns))

    print("\n" + "=" * 75)
    print("BOSSBASE RANDOM-PAYLOAD DETECTION EXPERIMENT")
    print("=" * 75)

    all_groups = sorted(df["source_group"].unique())

    train_groups = set(all_groups[:160])
    test_groups = set(all_groups[160:])

    print("\nTRAIN SOURCE GROUPS:", len(train_groups))
    print("TEST SOURCE GROUPS:", len(test_groups))

    for payload in PAYLOAD_LEVELS:

        clean_df = df[
            df["label"] == "CLEAN"
        ].copy()

        stego_df = df[
            df["file_name"].str.contains(
                f"_stego_{payload}.pgm",
                regex=False,
            )
        ].copy()

        experiment_df = pd.concat(
            [clean_df, stego_df],
            ignore_index=True,
        )

        train_df = experiment_df[
            experiment_df["source_group"].isin(
                train_groups
            )
        ]

        test_df = experiment_df[
            experiment_df["source_group"].isin(
                test_groups
            )
        ]

        X_train = train_df[feature_columns]
        y_train = train_df["label"]

        X_test = test_df[feature_columns]
        y_test = test_df["label"]

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

        cm = confusion_matrix(
            y_test,
            predictions,
            labels=["CLEAN", "STEGO"],
        )

        print("\n" + "-" * 75)
        print(f"PAYLOAD: {payload}")
        print("-" * 75)

        print("TRAIN SAMPLES:", len(train_df))
        print("TEST SAMPLES:", len(test_df))
        print("TEST ACCURACY:", accuracy)

        print("\nCONFUSION MATRIX:")
        print(cm)

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