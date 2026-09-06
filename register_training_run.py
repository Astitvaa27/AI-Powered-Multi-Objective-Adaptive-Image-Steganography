from pathlib import Path
import hashlib
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.database import engine
from backend.app.models.training_run import TrainingRun


DATASET_ID = "1bfe6d14-4016-4599-9ddc-2199e0240506"
MODEL_VERSION_ID = "d872a47e-d77f-48a8-ad27-6d968e40767f"
MODEL_PATH = Path("storage/models/steganalysis_random_forest.joblib")


def calculate_sha256(path: Path) -> str:
    sha256 = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


started_at = datetime.now(timezone.utc)
artifact_hash = calculate_sha256(MODEL_PATH)

with Session(engine) as db:
    run = TrainingRun(
        dataset_id=DATASET_ID,
        model_version_id=MODEL_VERSION_ID,
        training_framework="scikit-learn",
        status="COMPLETED",
        hyperparameters={
            "algorithm": "RandomForestClassifier",
            "n_estimators": 200,
            "random_state": 42,
            "class_weight": "balanced",
            "features": 42,
        },
        metrics={
            "accuracy": 0.50,
            "macro_f1": 0.45,
            "weighted_f1": 0.55,
            "train_samples": 10,
            "test_samples": 10,
        },
        artifact_path=str(MODEL_PATH),
        artifact_hash=artifact_hash,
        processing_time_ms=0,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
    )

    db.add(run)
    db.commit()

    print("TRAINING RUN REGISTERED:", run.id)
    print("STATUS:", run.status)
    print("MODEL:", run.model_version_id)
    print("DATASET:", run.dataset_id)