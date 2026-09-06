import hashlib
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.database import engine
from backend.app.models.model_version import ModelVersion


MODEL_PATH = Path(
    "storage/models/steganalysis_random_forest.joblib"
)


def calculate_sha256(path: Path) -> str:
    sha256 = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


artifact_hash = calculate_sha256(MODEL_PATH)

with Session(engine) as db:
    model = ModelVersion(
        name="Steganalysis Random Forest",
        version="1.0",
        framework="scikit-learn",
        architecture="RandomForestClassifier",
        task_type="BINARY_CLASSIFICATION",
        artifact_path=str(MODEL_PATH),
        artifact_hash=artifact_hash,
        configuration={
            "n_estimators": 200,
            "random_state": 42,
            "class_weight": "balanced",
            "features": 42,
            "classes": ["CLEAN", "STEGO"],
            "training_samples": 10,
            "test_samples": 10,
            "test_accuracy": 0.5,
        },
        description=(
            "Baseline Random Forest steganalysis model "
            "trained on 42 statistical image features "
            "for CLEAN versus STEGO classification."
        ),
        status="ACTIVE",
    )

    db.add(model)
    db.commit()

    print("MODEL REGISTERED:", model.id)
    print("NAME:", model.name)
    print("VERSION:", model.version)
    print("HASH:", model.artifact_hash)