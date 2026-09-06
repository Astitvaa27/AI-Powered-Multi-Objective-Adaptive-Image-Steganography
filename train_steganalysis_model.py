import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
import joblib
from pathlib import Path


CSV_PATH = Path("storage/dataset/metadata/steganalysis_features.csv")
MODEL_PATH = Path("storage/models/steganalysis_random_forest.joblib")

df = pd.read_csv(CSV_PATH)

# Recreate the source groups
df["sample_group"] = df["file_name"].str.extract(
    r"(sipi_4\.1\.\d+)"
)

# Use the same group-aware split
df["split"] = df["sample_group"].map({
    "sipi_4.1.05": "TRAIN",
    "sipi_4.1.07": "TRAIN",
    "sipi_4.1.06": "TEST",
    "sipi_4.1.08": "TEST",
})

feature_columns = [
    column
    for column in df.columns
    if column not in {
        "file_name",
        "label",
        "sample_group",
        "split",
    }
]

train_df = df[df["split"] == "TRAIN"]
test_df = df[df["split"] == "TEST"]

X_train = train_df[feature_columns]
y_train = train_df["label"]

X_test = test_df[feature_columns]
y_test = test_df["label"]

print("TRAIN SAMPLES:", len(train_df))
print("TEST SAMPLES:", len(test_df))
print("FEATURES:", len(feature_columns))
print("TRAIN LABELS:")
print(y_train.value_counts())
print("TEST LABELS:")
print(y_test.value_counts())

model = RandomForestClassifier(
    n_estimators=200,
    random_state=42,
    class_weight="balanced",
    n_jobs=-1,
)

model.fit(X_train, y_train)

predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)
cm = confusion_matrix(
    y_test,
    predictions,
    labels=["CLEAN", "STEGO"],
)

print("\nTEST ACCURACY:", accuracy)

print("\nCONFUSION MATRIX:")
print(cm)

print("\nCLASSIFICATION REPORT:")
print(
    classification_report(
        y_test,
        predictions,
        labels=["CLEAN", "STEGO"],
        zero_division=0,
    )
)

MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

joblib.dump(
    {
        "model": model,
        "feature_names": feature_columns,
    },
    MODEL_PATH,
)

print("\nMODEL SAVED:", MODEL_PATH)