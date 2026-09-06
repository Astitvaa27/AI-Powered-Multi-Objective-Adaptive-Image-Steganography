from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user_id
from backend.app.database import get_db
from backend.app.models.candidate_configuration import CandidateConfiguration
from backend.app.models.embedding_method import EmbeddingMethod
from backend.app.models.optimization_iteration import OptimizationIteration
from backend.app.models.optimization_run import OptimizationRun
from backend.app.schemas.candidate_configuration import (
    CandidateConfigurationCreate,
    CandidateConfigurationResponse,
)

router = APIRouter(
    prefix="/optimization-iterations/{iteration_id}/candidates",
    tags=["Candidate Configurations"],
)


def get_user_iteration(
    iteration_id: UUID,
    current_user_id: str,
    db: Session,
):
    return (
        db.query(OptimizationIteration)
        .join(
            OptimizationRun,
            OptimizationRun.id == OptimizationIteration.optimization_run_id,
        )
        .filter(
            OptimizationIteration.id == iteration_id,
            OptimizationRun.user_id == UUID(current_user_id),
        )
        .first()
    )


@router.post(
    "",
    response_model=CandidateConfigurationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_candidate_configuration(
    iteration_id: UUID,
    candidate_data: CandidateConfigurationCreate,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    # Verify that the iteration belongs to the current user
    iteration = get_user_iteration(
        iteration_id,
        current_user_id,
        db,
    )

    if not iteration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Optimization iteration not found",
        )

    # Verify that the embedding method exists and is active
    method = (
        db.query(EmbeddingMethod)
        .filter(
            EmbeddingMethod.id == candidate_data.method_id,
            EmbeddingMethod.is_active.is_(True),
        )
        .first()
    )

    if not method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Embedding method not found or inactive",
        )

    candidate = CandidateConfiguration(
        iteration_id=iteration_id,
        method_id=candidate_data.method_id,
        candidate_number=candidate_data.candidate_number,
        parameters=candidate_data.parameters,
        status="GENERATED",
    )

    db.add(candidate)

    try:
        db.commit()
        db.refresh(candidate)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Candidate number already exists for this iteration",
        )

    return candidate


@router.get(
    "",
    response_model=list[CandidateConfigurationResponse],
)
def get_candidate_configurations(
    iteration_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    iteration = get_user_iteration(
        iteration_id,
        current_user_id,
        db,
    )

    if not iteration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Optimization iteration not found",
        )

    candidates = (
        db.query(CandidateConfiguration)
        .filter(
            CandidateConfiguration.iteration_id == iteration_id
        )
        .order_by(CandidateConfiguration.candidate_number)
        .all()
    )

    return candidates


@router.get(
    "/{candidate_id}",
    response_model=CandidateConfigurationResponse,
)
def get_candidate_configuration(
    iteration_id: UUID,
    candidate_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    iteration = get_user_iteration(
        iteration_id,
        current_user_id,
        db,
    )

    if not iteration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Optimization iteration not found",
        )

    candidate = (
        db.query(CandidateConfiguration)
        .filter(
            CandidateConfiguration.id == candidate_id,
            CandidateConfiguration.iteration_id == iteration_id,
        )
        .first()
    )

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate configuration not found",
        )

    return candidate