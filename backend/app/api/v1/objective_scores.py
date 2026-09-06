from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user_id
from backend.app.database import get_db
from backend.app.models.candidate_configuration import CandidateConfiguration
from backend.app.models.objective_score import ObjectiveScore
from backend.app.models.optimization_iteration import OptimizationIteration
from backend.app.models.optimization_run import OptimizationRun
from backend.app.schemas.objective_score import (
    ObjectiveScoreCreate,
    ObjectiveScoreResponse,
)

router = APIRouter(
    prefix="/candidates/{candidate_id}/scores",
    tags=["Objective Scores"],
)


def get_user_candidate(
    candidate_id: UUID,
    current_user_id: str,
    db: Session,
):
    return (
        db.query(CandidateConfiguration)
        .join(
            OptimizationIteration,
            OptimizationIteration.id == CandidateConfiguration.iteration_id,
        )
        .join(
            OptimizationRun,
            OptimizationRun.id == OptimizationIteration.optimization_run_id,
        )
        .filter(
            CandidateConfiguration.id == candidate_id,
            OptimizationRun.user_id == UUID(current_user_id),
        )
        .first()
    )


@router.post(
    "",
    response_model=ObjectiveScoreResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_objective_score(
    candidate_id: UUID,
    score_data: ObjectiveScoreCreate,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    candidate = get_user_candidate(
        candidate_id,
        current_user_id,
        db,
    )

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate configuration not found",
        )

    score = ObjectiveScore(
        candidate_configuration_id=candidate_id,
        objective_name=score_data.objective_name,
        score=score_data.score,
        metric_values=score_data.metric_values,
        ranking=score_data.ranking,
    )

    db.add(score)

    try:
        db.commit()
        db.refresh(score)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Objective score already exists for this candidate",
        )

    return score


@router.get(
    "",
    response_model=list[ObjectiveScoreResponse],
)
def get_candidate_scores(
    candidate_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    candidate = get_user_candidate(
        candidate_id,
        current_user_id,
        db,
    )

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate configuration not found",
        )

    return (
        db.query(ObjectiveScore)
        .filter(
            ObjectiveScore.candidate_configuration_id == candidate_id
        )
        .order_by(ObjectiveScore.created_at)
        .all()
    )