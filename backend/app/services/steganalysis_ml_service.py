from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier


MODEL_PATH = Path("storage/models/steganalysis_random_forest_18.joblib")

def train_random_forest(
    features: list[dict],
    labels: list[str],
    groups: list[str],
) -> dict:
    """
    Train a Random Forest steganalysis classifier.

    Each feature dictionary must contain the same numeric feature keys.
    Groups identify related images, such as CLEAN/STEGO pairs.
    """

    if not features:
        raise ValueError("No features supplied for training.")

    if len(features) != len(labels):
        raise ValueError("Features and labels must have the same length.")

    if len(features) != len(groups):
        raise ValueError("Features and groups must have the same length.")

    feature_names = list(features[0].keys())

    X = np.array(
        [[float(row[name]) for name in feature_names] for row in features],
        dtype=np.float64,
    )

    y = np.array(labels)

    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )

    model.fit(X, y)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(
        {
            "model": model,
            "feature_names": feature_names,
        },
        MODEL_PATH,
    )

    return {
        "model_path": str(MODEL_PATH),
        "samples": len(features),
        "features": len(feature_names),
        "classes": list(model.classes_),
    }


def load_random_forest():
    """Load the saved Random Forest model."""

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Steganalysis model not found: {MODEL_PATH}"
        )

    artifact = joblib.load(MODEL_PATH)

    return artifact["model"], artifact["feature_names"]


def predict_steganography(features: dict) -> dict:
    import pandas as pd

    model, feature_names = load_random_forest()

    X = pd.DataFrame(
        [[float(features[name]) for name in feature_names]],
        columns=feature_names,
    )

    predicted_class = model.predict(X)[0]

    probabilities = model.predict_proba(X)[0]

    probability_map = {
        class_name: float(probability)
        for class_name, probability in zip(
            model.classes_,
            probabilities,
        )
    }

    confidence = float(max(probabilities))

    return {
        "predicted_class": str(predicted_class),
        "confidence": confidence,
        "probabilities": probability_map,
    }