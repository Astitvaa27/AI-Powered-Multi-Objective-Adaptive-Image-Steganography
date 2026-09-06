import joblib
import pandas as pd

from pathlib import Path
from sklearn.inspection import permutation_importance
from sklearn.model_selection import train_test_split


MODEL_PATH = Path(
    "storage/models/bossbase_steganalysis_random_forest.joblib"
)

CSV_PATH = Path(
    "storage/dataset/metadata/bossbase_steganalysis_features.csv"
)


def main():
    artifact = joblib.load(MODEL_PATH)

    model = artifact["model"]

    df = pd.read_csv(CSV_PATH)

    # Recover original source-image ID.
    df["source_group"] = df["file_name"].str.extract(r"^(\d+)")

    groups = sorted(df["source_group"].unique())

    # Recreate the exact same split used during training.
    train_groups, test_groups = train_test_split(
        groups,
        test_size=0.20,
        random_state=42,
    )

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
    ]

    X_test = test_df[feature_columns]
    y_test = test_df["label"]

    baseline_accuracy = model.score(X_test, y_test)

    print("HELD-OUT TEST SAMPLES:", len(test_df))
    print("BASELINE ACCURACY:", baseline_accuracy)

    result = permutation_importance(
        model,
        X_test,
        y_test,
        scoring="accuracy",
        n_repeats=20,
        random_state=42,
        n_jobs=-1,
    )

    importance_df = pd.DataFrame(
        {
            "feature": feature_columns,
            "importance_mean": result.importances_mean,
            "importance_std": result.importances_std,
        }
    ).sort_values(
        "importance_mean",
        ascending=False,
    )

    print("\nTOP 20 PERMUTATION FEATURES:")
    print(
        importance_df.head(20).to_string(index=False)
    )


if __name__ == "__main__":
    main()