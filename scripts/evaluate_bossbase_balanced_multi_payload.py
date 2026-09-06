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

    all_groups = sorted(
        df["source_group"].unique()
    )

    train_groups = set(all_groups[:160])
    test_groups = set(all_groups[160:])

    print("TOTAL DATASET:", len(df))
    print("FEATURES:", len(feature_columns))
    print("TRAIN SOURCE GROUPS:", len(train_groups))
    print("TEST SOURCE GROUPS:", len(test_groups))

    # ---------------------------------------------------------
    # CLEAN TRAINING SAMPLES
    # ---------------------------------------------------------

    clean_train = df[
        (df["label"] == "CLEAN")
        & df["source_group"].isin(train_groups)
    ].copy()

    # ---------------------------------------------------------
    # STEGO TRAINING SAMPLES
    # ---------------------------------------------------------
    #
    # Select 40 STEGO images from each payload level.
    # This gives:
    #
    # 40 x 4 = 160 STEGO
    #
    # Combined with 160 CLEAN:
    #
    # 160 CLEAN
    # 160 STEGO
    #
    # ---------------------------------------------------------

    stego_train_parts = []

    for payload in PAYLOAD_LEVELS:

        payload_df = df[
            (df["label"] == "STEGO")
            & df["source_group"].isin(train_groups)
            & df["file_name"].str.contains(
                f"_stego_{payload}.pgm",
                regex=False,
            )
        ].copy()

        payload_df = payload_df.sort_values(
            "source_group"
        ).head(40)

        stego_train_parts.append(
            payload_df
        )

    stego_train = pd.concat(
        stego_train_parts,
        ignore_index=True,
    )

    train_df = pd.concat(
        [
            clean_train,
            stego_train,
        ],
        ignore_index=True,
    )

    # ---------------------------------------------------------
    # TEST DATA
    # ---------------------------------------------------------

    clean_test = df[
        (df["label"] == "CLEAN")
        & df["source_group"].isin(test_groups)
    ].copy()

    stego_test = df[
        (df["label"] == "STEGO")
        & df["source_group"].isin(test_groups)
    ].copy()

    test_df = pd.concat(
        [
            clean_test,
            stego_test,
        ],
        ignore_index=True,
    )

    X_train = train_df[feature_columns]
    y_train = train_df["label"]

    X_test = test_df[feature_columns]
    y_test = test_df["label"]

    print("\n" + "=" * 75)
    print("BALANCED MULTI-PAYLOAD TRAINING")
    print("=" * 75)

    print("\nTRAIN SAMPLES:", len(train_df))
    print("TEST SAMPLES:", len(test_df))

    print("\nTRAIN LABELS:")
    print(y_train.value_counts())

    print("\nTEST LABELS:")
    print(y_test.value_counts())

    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )

    model.fit(
        X_train,
        y_train,
    )

    predictions = model.predict(
        X_test
    )

    accuracy = accuracy_score(
        y_test,
        predictions,
    )

    cm = confusion_matrix(
        y_test,
        predictions,
        labels=["CLEAN", "STEGO"],
    )

    print("\nTEST ACCURACY:", accuracy)

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

    # ---------------------------------------------------------
    # PAYLOAD-SPECIFIC TEST RESULTS
    # ---------------------------------------------------------

    print("\n" + "=" * 75)
    print("PAYLOAD-SPECIFIC TEST RESULTS")
    print("=" * 75)

    for payload in PAYLOAD_LEVELS:

        payload_stego_test = test_df[
            test_df["file_name"].str.contains(
                f"_stego_{payload}.pgm",
                regex=False,
            )
        ].copy()

        payload_test = pd.concat(
            [
                clean_test,
                payload_stego_test,
            ],
            ignore_index=True,
        )

        payload_predictions = model.predict(
            payload_test[feature_columns]
        )

        payload_accuracy = accuracy_score(
            payload_test["label"],
            payload_predictions,
        )

        print(
            f"{payload}: "
            f"{payload_accuracy:.4f}"
        )


if __name__ == "__main__":
    main()