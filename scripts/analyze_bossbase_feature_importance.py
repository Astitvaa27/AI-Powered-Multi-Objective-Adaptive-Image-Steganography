import pandas as pd
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance


CSV_PATH = Path(
    "storage/dataset/metadata/"
    "bossbase_random_payload_steganalysis_features.csv"
)

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
    return file_name.split("_stego_")[0].replace(
        ".pgm",
        ""
    )


def main():

    df = pd.read_csv(CSV_PATH)

    df["source_group"] = df["file_name"].apply(
        get_source_group
    )

    source_groups = sorted(
        df["source_group"].unique()
    )

    train_groups = source_groups[:160]
    test_groups = source_groups[160:]

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
            "payload",
            "source_group",
        }
        and column not in REDUNDANT_FEATURES
    ]

    # ---------------------------------------------------------
    # BALANCED TRAINING SET
    # ---------------------------------------------------------

    train_clean = train_df[
        train_df["label"] == "CLEAN"
    ].copy()

    train_stego = train_df[
        train_df["label"] == "STEGO"
    ].copy()

    stego_per_payload = (
        len(train_clean) // 4
    )

    balanced_parts = []

    for payload in (
        "0.01bpp",
        "0.05bpp",
        "0.10bpp",
        "0.20bpp",
    ):

        payload_stego = train_stego[
            train_stego["file_name"].str.contains(
                f"_stego_{payload}.pgm",
                regex=False,
            )
        ].sort_values(
            "file_name"
        ).head(
            stego_per_payload
        )

        balanced_parts.append(
            payload_stego
        )

    balanced_stego = pd.concat(
        balanced_parts,
        ignore_index=True,
    )

    balanced_train = pd.concat(
        [
            train_clean,
            balanced_stego,
        ],
        ignore_index=True,
    )

    # ---------------------------------------------------------
    # BALANCED PAYLOAD-SPECIFIC TEST SET
    # ---------------------------------------------------------

    test_clean = test_df[
        test_df["label"] == "CLEAN"
    ].copy()

    test_stego = test_df[
        test_df["label"] == "STEGO"
    ].copy()

    # Use one STEGO payload at a time for the importance
    # analysis so we can see which features matter for
    # individual payload strengths.

    print("FEATURE IMPORTANCE ANALYSIS")
    print("=" * 80)

    print(
        "FEATURES:",
        len(feature_columns)
    )

    print(
        "TRAIN GROUPS:",
        len(train_groups)
    )

    print(
        "TEST GROUPS:",
        len(test_groups)
    )

    print(
        "SOURCE-GROUP OVERLAP:",
        len(
            set(train_groups)
            & set(test_groups)
        )
    )

    for payload in (
        "0.01bpp",
        "0.05bpp",
        "0.10bpp",
        "0.20bpp",
    ):

        payload_stego = test_stego[
            test_stego["file_name"].str.contains(
                f"_stego_{payload}.pgm",
                regex=False,
            )
        ]

        payload_test = pd.concat(
            [
                test_clean,
                payload_stego,
            ],
            ignore_index=True,
        )

        X_train = balanced_train[
            feature_columns
        ]

        y_train = balanced_train[
            "label"
        ]

        X_test = payload_test[
            feature_columns
        ]

        y_test = payload_test[
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

        # -----------------------------------------------------
        # Built-in Random Forest importance
        # -----------------------------------------------------

        importance_df = pd.DataFrame({
            "feature": feature_columns,
            "importance": model.feature_importances_,
        })

        importance_df = importance_df.sort_values(
            "importance",
            ascending=False,
        )

        # -----------------------------------------------------
        # Held-out permutation importance
        # -----------------------------------------------------

        permutation = permutation_importance(
            model,
            X_test,
            y_test,
            n_repeats=10,
            random_state=42,
            scoring="accuracy",
            n_jobs=-1,
        )

        permutation_df = pd.DataFrame({
            "feature": feature_columns,
            "importance_mean": (
                permutation.importances_mean
            ),
            "importance_std": (
                permutation.importances_std
            ),
        })

        permutation_df = permutation_df.sort_values(
            "importance_mean",
            ascending=False,
        )

        print(
            "\n" + "=" * 80
        )

        print(
            f"PAYLOAD: {payload}"
        )

        print(
            "=" * 80
        )

        print(
            "\nTOP 10 RANDOM FOREST FEATURES:"
        )

        print(
            importance_df.head(10).to_string(
                index=False
            )
        )

        print(
            "\nTOP 10 HELD-OUT PERMUTATION FEATURES:"
        )

        print(
            permutation_df.head(10).to_string(
                index=False
            )
        )


if __name__ == "__main__":
    main()