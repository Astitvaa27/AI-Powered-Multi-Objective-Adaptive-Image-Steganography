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


HYBRID_FEATURES = [
    "r_sequential_lsb_difference",
    "r_rs_difference",
    "r_rs_regular_ratio",
    "r_horizontal_pair_rate",
    "r_vertical_pair_rate",
    "r_lsb_horizontal_transition_rate",
    "r_lsb_ones_ratio",
    "r_early_lsb_one_ratio",
    "r_rs_singular_ratio",
    "r_std",
    "r_mean",
    "r_min",
]


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

    print("HYBRID FEATURE EVALUATION")
    print("=" * 80)

    print(
        "FEATURES:",
        len(HYBRID_FEATURES)
    )

    print(
        "\nSELECTED FEATURES:"
    )

    for feature in HYBRID_FEATURES:
        print(
            f"  {feature}"
        )

    print(
        "\nTRAIN GROUPS:",
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

    print(
        "\n" + "=" * 80
    )

    print(
        "PAYLOAD-SPECIFIC HYBRID EVALUATION"
    )

    print(
        "=" * 80
    )

    for payload in PAYLOAD_LEVELS:

        train_clean = train_df[
            train_df["label"] == "CLEAN"
        ].copy()

        train_stego = train_df[
            train_df["file_name"].str.contains(
                f"_stego_{payload}.pgm",
                regex=False,
            )
        ].copy()

        test_clean = test_df[
            test_df["label"] == "CLEAN"
        ].copy()

        test_stego = test_df[
            test_df["file_name"].str.contains(
                f"_stego_{payload}.pgm",
                regex=False,
            )
        ].copy()

        train_data = pd.concat(
            [
                train_clean,
                train_stego,
            ],
            ignore_index=True,
        )

        test_data = pd.concat(
            [
                test_clean,
                test_stego,
            ],
            ignore_index=True,
        )

        X_train = train_data[
            HYBRID_FEATURES
        ]

        y_train = train_data[
            "label"
        ]

        X_test = test_data[
            HYBRID_FEATURES
        ]

        y_test = test_data[
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
            labels=[
                "CLEAN",
                "STEGO",
            ],
        )

        print(
            "\n" + "-" * 80
        )

        print(
            f"PAYLOAD: {payload}"
        )

        print(
            "-" * 80
        )

        print(
            "TRAIN:",
            len(train_data)
        )

        print(
            "TEST:",
            len(test_data)
        )

        print(
            "ACCURACY:",
            f"{accuracy:.4f}"
        )

        print(
            "CONFUSION MATRIX:"
        )

        print(cm)


if __name__ == "__main__":
    main()