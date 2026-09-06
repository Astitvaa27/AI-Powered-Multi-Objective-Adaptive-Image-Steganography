import joblib
import pandas as pd

from pathlib import Path


MODEL_PATH = Path(
    "storage/models/bossbase_steganalysis_random_forest.joblib"
)

CSV_PATH = Path(
    "storage/dataset/metadata/bossbase_steganalysis_features.csv"
)


def main():
    artifact = joblib.load(MODEL_PATH)

    model = artifact["model"]
    feature_names = artifact["feature_names"]

    importances = model.feature_importances_

    importance_df = pd.DataFrame(
        {
            "feature": feature_names,
            "importance": importances,
        }
    ).sort_values(
        "importance",
        ascending=False,
    )

    print("TOTAL FEATURES:", len(importance_df))
    print("\nTOP 20 FEATURES:")
    print(
        importance_df.head(20).to_string(index=False)
    )

    print(
        "\nIMPORTANCE SUM:",
        importance_df["importance"].sum(),
    )


if __name__ == "__main__":
    main()