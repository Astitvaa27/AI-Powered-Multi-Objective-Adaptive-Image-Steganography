import pandas as pd
import joblib
from pathlib import Path

CSV_PATH = Path("storage/dataset/metadata/steganalysis_features.csv")
MODEL_PATH = Path("storage/models/steganalysis_random_forest.joblib")

df = pd.read_csv(CSV_PATH)

df["sample_group"] = df["file_name"].str.extract(r"(sipi_4\.1\.\d+)")

test_groups = ["sipi_4.1.06", "sipi_4.1.08"]

test_df = df[df["sample_group"].isin(test_groups)].copy()

artifact = joblib.load(MODEL_PATH)
model = artifact["model"]
feature_names = artifact["feature_names"]

X = test_df[feature_names]

predictions = model.predict(X)
probabilities = model.predict_proba(X)

print("INDIVIDUAL TEST PREDICTIONS")
print("=" * 70)

for i, (_, row) in enumerate(test_df.iterrows()):
    probability_map = {
        class_name: float(probability)
        for class_name, probability in zip(
            model.classes_,
            probabilities[i]
        )
    }

    predicted = predictions[i]
    confidence = max(probability_map.values())

    print(f"\nIMAGE: {row['file_name']}")
    print(f"ACTUAL: {row['label']}")
    print(f"PREDICTED: {predicted}")
    print(f"CLEAN PROBABILITY: {probability_map.get('CLEAN', 0):.4f}")
    print(f"STEGO PROBABILITY: {probability_map.get('STEGO', 0):.4f}")
    print(f"CONFIDENCE: {confidence:.4f}")
