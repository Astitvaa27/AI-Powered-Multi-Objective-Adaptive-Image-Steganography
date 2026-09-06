import pandas as pd
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score


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

    print("\n" + "=" * 75)
    print("CROSS-PAYLOAD GENERALIZATION EXPERIMENT")
    print("=" * 75)

    for train_payload in PAYLOAD_LEVELS:

        print("\n" + "-" * 75)
        print(
            f"TRAIN PAYLOAD: {train_payload}"
        )
        print("-" * 75)

        clean_train = df[
            (df["label"] == "CLEAN")
            & df["source_group"].isin(train_groups)
        ].copy()

        stego_train = df[
            df["file_name"].str.contains(
                f"_stego_{train_payload}.pgm",
                regex=False,
            )
            & df["source_group"].isin(train_groups)
        ].copy()

        train_df = pd.concat(
            [clean_train, stego_train],
            ignore_index=True,
        )

        X_train = train_df[feature_columns]
        y_train = train_df["label"]

        model = RandomForestClassifier(
            n_estimators=200,
            random_state=42,
            class_weight="balanced",
            n_jobs=-1,
        )

        model.fit(X_train, y_train)

        print(
            "TRAIN SAMPLES:",
            len(train_df),
        )

        for test_payload in PAYLOAD_LEVELS:

            clean_test = df[
                (df["label"] == "CLEAN")
                & df["source_group"].isin(test_groups)
            ].copy()

            stego_test = df[
                df["file_name"].str.contains(
                    f"_stego_{test_payload}.pgm",
                    regex=False,
                )
                & df["source_group"].isin(test_groups)
            ].copy()

            test_df = pd.concat(
                [clean_test, stego_test],
                ignore_index=True,
            )

            X_test = test_df[feature_columns]
            y_test = test_df["label"]

            predictions = model.predict(
                X_test
            )

            accuracy = accuracy_score(
                y_test,
                predictions,
            )

            print(
                f"Test {test_payload}: "
                f"{accuracy:.4f}"
            )


if __name__ == "__main__":
    main()