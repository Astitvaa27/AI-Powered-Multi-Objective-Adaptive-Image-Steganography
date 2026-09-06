import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix

CSV_PATH = "storage/dataset/metadata/steganalysis_features.csv"

df = pd.read_csv(CSV_PATH)

df["sample_group"] = df["file_name"].str.extract(r"(sipi_4\.1\.\d+)")

df["split"] = df["sample_group"].map({
    "sipi_4.1.05": "TRAIN",
    "sipi_4.1.07": "TRAIN",
    "sipi_4.1.06": "TEST",
    "sipi_4.1.08": "TEST",
})

all_features = [
    c for c in df.columns
    if c not in {"file_name", "label", "sample_group", "split"}
]

new_features = [
    c for c in all_features
    if (
        "early_lsb" in c
        or "remaining_lsb" in c
        or "sequential_lsb" in c
    )
]

old_features = [
    c for c in all_features
    if c not in new_features
]

train_df = df[df["split"] == "TRAIN"]
test_df = df[df["split"] == "TEST"]

def run_test(name, features):
    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )

    model.fit(
        train_df[features],
        train_df["label"],
    )

    predictions = model.predict(test_df[features])

    accuracy = accuracy_score(
        test_df["label"],
        predictions,
    )

    cm = confusion_matrix(
        test_df["label"],
        predictions,
        labels=["CLEAN", "STEGO"],
    )

    print(f"\n{name}")
    print("-" * len(name))
    print("FEATURES:", len(features))
    print("ACCURACY:", accuracy)
    print("CONFUSION MATRIX:")
    print(cm)


print("TOTAL FEATURES:", len(all_features))
print("OLD FEATURES:", len(old_features))
print("NEW FEATURES:", len(new_features))

run_test("OLD 42 FEATURES", old_features)
run_test("NEW 9 FEATURES ONLY", new_features)
run_test("ALL 51 FEATURES", all_features)
