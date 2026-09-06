import pandas as pd
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix


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


# For grayscale BOSSBase, RGB-derived features are duplicates.
# Keep only one representative from each duplicated group.
REDUNDANT_FEATURES = {
    "g_mean",
    "b_mean",
    "global_mean",

    "g_std",
    "b_std",
    "global_std",

    "g_min",
    "b_min",

    "g_max",
    "b_max",

    "g_lsb_ones_ratio",
    "b_lsb_ones_ratio",
    "global_lsb_ones_ratio",

    "g_lsb_horizontal_transition_rate",
    "b_lsb_horizontal_transition_rate",

    "g_lsb_vertical_transition_rate",
    "b_lsb_vertical_transition_rate",

    "g_horizontal_pair_rate",
    "b_horizontal_pair_rate",

    "g_vertical_pair_rate",
    "b_vertical_pair_rate",

    "g_rs_regular_ratio",
    "b_rs_regular_ratio",

    "g_rs_singular_ratio",
    "b_rs_singular_ratio",

    "g_rs_difference",
    "b_rs_difference",

    "g_early_lsb_one_ratio",
    "b_early_lsb_one_ratio",

    "g_remaining_lsb_one_ratio",
    "b_remaining_lsb_one_ratio",

    "g_sequential_lsb_difference",
    "b_sequential_lsb_difference",
}


def get_source_group(file_name):
    return file_name.split("_stego_")[0].replace(".pgm", "")


def main():
    df = pd.read_csv(CSV_PATH)

    df["source_group"] = df["file_name"].apply(
        get_source_group
    )

    train_groups = sorted(
        df["source_group"].unique()
    )[:160]

    test_groups = sorted(
        df["source_group"].unique()
    )[160:]

    train_df = df[
        df["source_group"].isin(train_groups)
    ].copy()

    test_df = df[
        df["source_group"].isin(test_groups)
    ].copy()

    feature_columns = [
        column
        for column in df.columns
        if column not in {
            "file_name",
            "label",
            "source_group",
        }
        and column not in REDUNDANT_FEATURES
    ]

    print("ORIGINAL FEATURES:", 51)
    print("REDUCED FEATURES:", len(feature_columns))
    print("REMOVED FEATURES:", len(REDUNDANT_FEATURES))

    print("\nTRAIN GROUPS:", len(train_groups))
    print("TEST GROUPS:", len(test_groups))

    print("\nSOURCE-GROUP OVERLAP:")
    print(
        len(
            set(train_groups)
            & set(test_groups)
        )
    )

    print("\n" + "=" * 80)
    print("REDUCED FEATURE EVALUATION")
    print("=" * 80)

    for payload in PAYLOAD_LEVELS:

        train_clean = train_df[
            train_df["label"] == "CLEAN"
        ]

        train_stego = train_df[
            train_df["file_name"].str.contains(
                f"_stego_{payload}.pgm",
                regex=False,
            )
        ]

        test_clean = test_df[
            test_df["label"] == "CLEAN"
        ]

        test_stego = test_df[
            test_df["file_name"].str.contains(
                f"_stego_{payload}.pgm",
                regex=False,
            )
        ]

        train_payload_df = pd.concat(
            [train_clean, train_stego],
            ignore_index=True,
        )

        test_payload_df = pd.concat(
            [test_clean, test_stego],
            ignore_index=True,
        )

        X_train = train_payload_df[
            feature_columns
        ]

        y_train = train_payload_df[
            "label"
        ]

        X_test = test_payload_df[
            feature_columns
        ]

        y_test = test_payload_df[
            "label"
        ]

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

        print("\n" + "-" * 80)
        print(f"PAYLOAD: {payload}")
        print("-" * 80)

        print(
            "TRAIN:",
            len(train_payload_df),
        )

        print(
            "TEST:",
            len(test_payload_df),
        )

        print(
            "ACCURACY:",
            f"{accuracy:.4f}",
        )

        print("CONFUSION MATRIX:")
        print(cm)


if __name__ == "__main__":
    main()