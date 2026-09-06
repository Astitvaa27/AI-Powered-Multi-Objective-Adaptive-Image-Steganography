from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.dataset import Dataset
from backend.app.schemas.dataset import DatasetCreate, DatasetResponse
from backend.app.core.security import require_permission


router = APIRouter(
    prefix="/datasets",
    tags=["Datasets"],
)


@router.post(
    "",
    response_model=DatasetResponse,
)
def create_dataset(
    dataset_data: DatasetCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("dataset.manage")),
):
    dataset = Dataset(
        name=dataset_data.name,
        version=dataset_data.version,
        description=dataset_data.description,
        source=dataset_data.source,
        license=dataset_data.license,
        dataset_hash=dataset_data.dataset_hash,
        metadata_json=dataset_data.metadata,
    )

    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return dataset


@router.get(
    "/{dataset_id}",
    response_model=DatasetResponse,
)
def get_dataset(
    dataset_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("dataset.manage")),
):
    dataset = (
        db.query(Dataset)
        .filter(Dataset.id == dataset_id)
        .first()
    )

    if not dataset:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found",
        )

    return dataset