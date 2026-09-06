import sys
from pathlib import Path

import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from backend.app.services.steganalysis_service import (
    calculate_lsb_pair_statistics,
)


CSV_PATH = Path(
    "storage/dataset/metadata/"
    "bossbase_random_payload_steganalysis_features.csv"
)

CLEAN_DIR = Path(
    "storage/dataset/bossbase/clean"
)

STEGO_ROOT = Path(
    "storage/dataset/bossbase/stego_random_payload"
)

PAYLOAD_LEVELS = (
    "0.01bpp",
    "0.05bpp",
    "0.10bpp",
    "0.20bpp",
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


PAIR_FEATURES = (
    "lsb_horizontal_pair_00_ratio",
    "lsb_horizontal_pair_01_ratio",
    "lsb_vertical_pair_00_ratio",
    "lsb_vertical_pair_01_ratio",
)


def get_source_group(file_name):
    return file_name.split("_stego_")[0].replace(
        ".pgm",
        ""
    )


def find_image_path(file_name):
    clean_path = CLEAN_DIR / file_name

    if clean_path.exists():
        return clean_path

    for payload in PAYLOAD_LEVELS:
        candidate = (
            STEGO_ROOT
            / payload
            / file_name
        )

        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        f"Could not find image: {file_name}"
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

    for feature in PAIR_FEATURES:
        df[feature] = 0.0

    print("CALCULATING PAIR FEATURES...")

    for index, row in df.iterrows():

        image_path = find_image_path(
            row["file_name"]
        )

        features = calculate_lsb_pair_statistics(
            str(image_path)
        )

        for feature in PAIR_FEATURES:
            df.at[
                index,
                feature
            ] = features[feature]

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

    print()
    print("ORIGINAL FEATURES:", 51)
    print(
        "FINAL FEATURE CANDIDATES:",
        len(feature_columns)
    )
    print(
        "PAIR FEATURES:",
        len(PAIR_FEATURES)
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

    # ---------------------------------------------------------
    # BALANCED TRAINING DATA
    # ---------------------------------------------------------

    train_clean = train_df[
        train_df["label"] == "CLEAN"
    ].copy()

    train_stego = train_df[
        train_df["label"] == "STEGO"
    ].copy()

    # There are 160 clean images.
    # Select 160 STEGO samples evenly across
    # the four payload levels.
    stego_per_payload = (
        len(train_clean) //
        len(PAYLOAD_LEVELS)
    )

    balanced_stego_parts = []

    for payload in PAYLOAD_LEVELS:

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

        balanced_stego_parts.append(
            payload_stego
        )

    balanced_stego = pd.concat(
        balanced_stego_parts,
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
    # TEST DATA
    # ---------------------------------------------------------

    test_clean = test_df[
        test_df["label"] == "CLEAN"
    ].copy()

    test_stego = test_df[
        test_df["label"] == "STEGO"
    ].copy()

    test_data = pd.concat(
        [
            test_clean,
            test_stego,
        ],
        ignore_index=True,
    )

    X_train = balanced_train[
        feature_columns
    ]

    y_train = balanced_train[
        "label"
    ]

    X_test = test_data[
        feature_columns
    ]

    y_test = test_data[
        "label"
    ]

    print(
        "\nTRAIN CLEAN:",
        len(train_clean)
    )

    print(
        "TRAIN STEGO:",
        len(balanced_stego)
    )

    print(
        "TRAIN TOTAL:",
        len(balanced_train)
    )

    print(
        "TEST CLEAN:",
        len(test_clean)
    )

    print(
        "TEST STEGO:",
        len(test_stego)
    )

    print(
        "TEST TOTAL:",
        len(test_data)
    )

    print(
        "\nTRAIN STEGO BY PAYLOAD:"
    )

    for payload in PAYLOAD_LEVELS:
        count = balanced_stego[
            balanced_stego["file_name"].str.contains(
                f"_stego_{payload}.pgm",
                regex=False,
            )
        ].shape[0]

        print(
            f"  {payload}: {count}"
        )

    # ---------------------------------------------------------
    # TRAIN
    # ---------------------------------------------------------

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
        "\n" + "=" * 80
    )

    print(
        "22-FEATURE MULTI-PAYLOAD EVALUATION"
    )

    print(
        "=" * 80
    )

    print(
        "FEATURES:",
        len(feature_columns)
    )

    print(
        "ACCURACY:",
        f"{accuracy:.4f}"
    )

    print(
        "\nCONFUSION MATRIX:"
    )

    print(cm)

    print(
        "\nCLASSIFICATION REPORT:"
    )

    print(
        classification_report(
            y_test,
            predictions,
            labels=[
                "CLEAN",
                "STEGO",
            ],
            zero_division=0,
        )
    )

    # ---------------------------------------------------------
    # PAYLOAD-SPECIFIC RESULTS
    # ---------------------------------------------------------

    print(
        "\n" + "=" * 80
    )

    print(
        "PAYLOAD-SPECIFIC RESULTS"
    )

    print(
        "=" * 80
    )

    for payload in PAYLOAD_LEVELS:

        payload_clean = test_clean

        payload_stego = test_stego[
            test_stego["file_name"].str.contains(
                f"_stego_{payload}.pgm",
                regex=False,
            )
        ]

        payload_test = pd.concat(
            [
                payload_clean,
                payload_stego,
            ],
            ignore_index=True,
        )

        payload_predictions = model.predict(
            payload_test[
                feature_columns
            ]
        )

        payload_accuracy = (
            accuracy_score(
                payload_test["label"],
                payload_predictions,
            )
        )

        print(
            f"{payload}: "
            f"{payload_accuracy:.4f}"
        )


if __name__ == "__main__":
    main()