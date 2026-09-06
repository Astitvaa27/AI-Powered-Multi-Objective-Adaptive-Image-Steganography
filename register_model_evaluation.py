from sqlalchemy.orm import Session

from backend.app.database import engine
from backend.app.models.model_evaluation import ModelEvaluation


MODEL_VERSION_ID = "d872a47e-d77f-48a8-ad27-6d968e40767f"
DATASET_ID = "1bfe6d14-4016-4599-9ddc-2199e0240506"


with Session(engine) as db:
    evaluation = ModelEvaluation(
        model_version_id=MODEL_VERSION_ID,
        dataset_id=DATASET_ID,
        evaluation_type="HOLDOUT_TEST",
        metrics={
            "accuracy": 0.50,
            "macro_f1": 0.45,
            "weighted_f1": 0.55,
            "classes": {
                "CLEAN": {
                    "precision": 0.20,
                    "recall": 0.50,
                    "f1": 0.29,
                    "support": 2,
                },
                "STEGO": {
                    "precision": 0.80,
                    "recall": 0.50,
                    "f1": 0.62,
                    "support": 8,
                },
            },
        },
        confusion_matrix={
            "labels": ["CLEAN", "STEGO"],
            "matrix": [[1, 1], [4, 4]],
        },
        evaluation_config={
            "split": "GROUP_AWARE_HOLDOUT",
            "train_samples": 10,
            "test_samples": 10,
            "features": 42,
            "random_state": 42,
            "source_groups": 4,
        },
    )

    db.add(evaluation)
    db.commit()

    print("EVALUATION REGISTERED:", evaluation.id)
    print("TYPE:", evaluation.evaluation_type)
    print("ACCURACY:", evaluation.metrics["accuracy"])