import pandas as pd
from pathlib import Path

from sklearn.metrics import accuracy_score, confusion_matrix

from backend.app.services.steganalysis_ml_service import predict_steganography


CSV_PATH = Path("storage/dataset/metadata/steganalysis_features.csv")

df = pd.read_csv(CSV_PATH)

feature_columns = [
    column
    for column in df.columns
    if column not in {"file_name", "label"}
]

predictions = []

for _, row in df.iterrows():

    features = {
        column: float(row[column])
        for column in feature_columns
    }

    result = predict_steganography(features)

    predictions.append(result["predicted_class"])

df["predicted"] = predictions

accuracy = accuracy_score(df["label"], df["predicted"])

cm = confusion_matrix(
    df["label"],
    df["predicted"],
    labels=["CLEAN", "STEGO"],
)

print("SAVED MODEL FULL DATASET EVALUATION")
print("-" * 50)

print("TOTAL SAMPLES:", len(df))
print("FEATURES:", len(feature_columns))

print("\nACTUAL LABELS:")
print(df["label"].value_counts())

print("\nPREDICTED LABELS:")
print(df["predicted"].value_counts())

print("\nACCURACY:", accuracy)

print("\nCONFUSION MATRIX:")
print(cm)

print("\nPREDICTIONS:")
print(
    df[
        [
            "file_name",
            "label",
            "predicted",
        ]
    ].to_string(index=False)
)