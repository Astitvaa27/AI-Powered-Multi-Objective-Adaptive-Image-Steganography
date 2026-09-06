import joblib
import pandas as pd

from pathlib import Path
from sklearn.ensemble import RandomForestClassifier


CSV_PATH = Path(
    "storage/dataset/metadata/"
    "bossbase_random_payload_steganalysis_features.csv"
)

MODEL_PATH = Path(
    "storage/models/"
    "steganalysis_random_forest_18.joblib"
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


def main():

    df = pd.read_csv(CSV_PATH)

    df["source_group"] = (
        df["file_name"]
        .str.extract(r"^(\d+)")
    )

    missing_features = [
        feature
        for feature in FEATURES
        if feature not in df.columns
    ]

    if missing_features:
        raise ValueError(
            f"Missing features: {missing_features}"
        )

    X = df[FEATURES]
    y = df["label"]

    print(
        "BOSSBASE 18-FEATURE PRODUCTION MODEL"
    )

    print("=" * 80)

    print(
        "DATASET:",
        CSV_PATH
    )

    print(
        "SAMPLES:",
        len(df)
    )

    print(
        "SOURCE GROUPS:",
        df["source_group"].nunique()
    )

    print(
        "FEATURES:",
        len(FEATURES)
    )

    print(
        "\nCLASS DISTRIBUTION:"
    )

    print(
        y.value_counts()
    )

    print(
        "\nPAYLOAD DISTRIBUTION:"
    )

    stego_df = df[
        df["label"] == "STEGO"
    ]

    for payload in (
        "0.01bpp",
        "0.05bpp",
        "0.10bpp",
        "0.20bpp",
    ):
        count = stego_df[
            stego_df["file_name"].str.contains(
                f"_stego_{payload}.pgm",
                regex=False,
            )
        ].shape[0]

        print(
            f"{payload}: {count}"
        )

    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )

    model.fit(X, y)

    MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        {
            "model": model,
            "feature_names": FEATURES,
            "dataset": "BOSSBase_1.01_random_payload",
            "feature_count": len(FEATURES),
            "payload_levels": [
                "0.01bpp",
                "0.05bpp",
                "0.10bpp",
                "0.20bpp",
            ],
        },
        MODEL_PATH,
    )

    print(
        "\nMODEL SAVED:",
        MODEL_PATH
    )

    print(
        "MODEL FEATURES:",
        len(model.feature_names_in_)
    )

    print(
        "MODEL CLASSES:",
        list(model.classes_)
    )


if __name__ == "__main__":
    main()