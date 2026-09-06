import pandas as pd
import joblib
from pathlib import Path

csv_path = Path("storage/dataset/metadata/steganalysis_features.csv")
model_path = Path("storage/models/steganalysis_random_forest.joblib")

df = pd.read_csv(csv_path)

artifact = joblib.load(model_path)
model = artifact["model"]
feature_names = artifact["feature_names"]

importance = pd.DataFrame({
    "feature": feature_names,
    "importance": model.feature_importances_,
})

importance = importance.sort_values(
    "importance",
    ascending=False,
)

print(importance.head(20).to_string(index=False))
