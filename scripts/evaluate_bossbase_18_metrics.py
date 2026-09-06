import pandas as pd
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
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


FEATURES = [
    "r_mean",
    "r_std",
    "r_min",
    "r_max",
    "r_lsb_ones_ratio",
    "r_lsb_horizontal_transition_rate",
    "r_lsb_vertical_transition_rate",
    "r_horizontal_pair_rate",
    "r_vertical_pair_rate",
    "r_rs_regular_ratio",
    "r_rs_singular_ratio",
    "r_rs_difference",
    "r_early_lsb_one_ratio",
    "r_remaining_lsb_one_ratio",
    "r_sequential_lsb_difference",
    "g_lsb_ones_ratio",
    "b_lsb_ones_ratio",
    "global_lsb_ones_ratio",
]


def get_source_group(file_name):
    return file_name.split("_stego_")[0].replace(
        ".pgm",
        ""
    )


def evaluate_split(
    df,
    train_groups,
    test_groups,
    payload,
):
    train_df = df[
        df["source_group"].isin(train_groups)
    ]

    test_df = df[
        df["source_group"].isin(test_groups)
    ]

    train_clean = train_df[
        train_df["label"] == "CLEAN"
    ]

    train_stego = train_df[
        train_df["label"] == "STEGO"
    ]

    train_stego = train_stego[
        train_stego["file_name"].str.contains(
            f"_stego_{payload}.pgm",
            regex=False,
        )
    ]

    test_clean = test_df[
        test_df["label"] == "CLEAN"
    ]

    test_stego = test_df[
        test_df["label"] == "STEGO"
    ]

    test_stego = test_stego[
        test_stego["file_name"].str.contains(
            f"_stego_{payload}.pgm",
            regex=False,
        )
    ]

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

    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )

    model.fit(
        train_data[FEATURES],
        train_data["label"],
    )

    predictions = model.predict(
        test_data[FEATURES],
    )

    y_true = test_data["label"]

    accuracy = accuracy_score(
        y_true,
        predictions,
    )

    precision = precision_score(
        y_true,
        predictions,
        pos_label="STEGO",
        zero_division=0,
    )

    recall = recall_score(
        y_true,
        predictions,
        pos_label="STEGO",
        zero_division=0,
    )

    f1 = f1_score(
        y_true,
        predictions,
        pos_label="STEGO",
        zero_division=0,
    )

    cm = confusion_matrix(
        y_true,
        predictions,
        labels=[
            "CLEAN",
            "STEGO",
        ],
    )

    return (
        accuracy,
        precision,
        recall,
        f1,
        cm,
    )


def main():

    df = pd.read_csv(CSV_PATH)

    df["source_group"] = df["file_name"].apply(
        get_source_group
    )

    groups = sorted(
        df["source_group"].unique()
    )

    splits = [
        (
            "SPLIT_1",
            groups[:160],
            groups[160:200],
        ),
        (
            "SPLIT_2",
            groups[40:200],
            groups[:40],
        ),
        (
            "SPLIT_3",
            groups[:40] + groups[80:200],
            groups[40:80],
        ),
    ]

    print(
        "BOSSBASE 18-FEATURE METRICS"
    )

    print("=" * 80)

    print(
        "FEATURES:",
        len(FEATURES)
    )

    print(
        "SOURCE GROUPS:",
        len(groups)
    )

    print(
        "SPLITS:",
        len(splits)
    )

    print(
        "\n" + "=" * 80
    )

    print(
        "PRECISION / RECALL / F1 VALIDATION"
    )

    print("=" * 80)

    results = []

    for split_name, train_groups, test_groups in splits:

        overlap = (
            set(train_groups)
            & set(test_groups)
        )

        print(
            f"\n{split_name}"
        )

        print(
            "-" * 80
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
            "OVERLAP:",
            len(overlap)
        )

        for payload in PAYLOAD_LEVELS:

            (
                accuracy,
                precision,
                recall,
                f1,
                cm,
            ) = evaluate_split(
                df,
                train_groups,
                test_groups,
                payload,
            )

            results.append({
                "split": split_name,
                "payload": payload,
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1": f1,
            })

            print(
                f"{payload}: "
                f"Accuracy={accuracy:.4f} "
                f"Precision={precision:.4f} "
                f"Recall={recall:.4f} "
                f"F1={f1:.4f}"
            )

            print(
                "Confusion Matrix:"
            )

            print(cm)

    results_df = pd.DataFrame(results)

    print(
        "\n" + "=" * 80
    )

    print(
        "VALIDATION SUMMARY"
    )

    print("=" * 80)

    summary = (
        results_df
        .groupby("payload")[
            [
                "accuracy",
                "precision",
                "recall",
                "f1",
            ]
        ]
        .agg(
            [
                "mean",
                "std",
                "min",
                "max",
            ]
        )
    )

    print(
        summary.to_string()
    )


if __name__ == "__main__":
    main()