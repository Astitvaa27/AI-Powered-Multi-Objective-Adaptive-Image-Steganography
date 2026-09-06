from pathlib import Path
import pandas as pd

from backend.app.services.steganalysis_ml_service import predict_steganography

CSV_PATH = Path("storage/dataset/metadata/steganalysis_features.csv")

df = pd.read_csv(CSV_PATH)

# Take one CLEAN sample and one STEGO sample
clean_row = df[df["label"] == "CLEAN"].iloc[0]
stego_row = df[df["label"] == "STEGO"].iloc[0]

feature_columns = [
    column
    for column in df.columns
    if column not in {"file_name", "label"}
]

clean_features = {
    column: float(clean_row[column])
    for column in feature_columns
}

stego_features = {
    column: float(stego_row[column])
    for column in feature_columns
}

print("MODEL TEST")
print("-" * 50)

print("\nCLEAN SAMPLE:")
print("File:", clean_row["file_name"])
print("Actual:", clean_row["label"])

clean_prediction = predict_steganography(clean_features)

print("Predicted:", clean_prediction["predicted_class"])
print("Confidence:", clean_prediction["confidence"])
print("Probabilities:", clean_prediction["probabilities"])

print("\nSTEGO SAMPLE:")
print("File:", stego_row["file_name"])
print("Actual:", stego_row["label"])

stego_prediction = predict_steganography(stego_features)

print("Predicted:", stego_prediction["predicted_class"])
print("Confidence:", stego_prediction["confidence"])
print("Probabilities:", stego_prediction["probabilities"])