from uuid import UUID
from datetime import datetime, timezone
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user_id
from backend.app.database import get_db
from backend.app.models.optimization_run import OptimizationRun
from backend.app.models.optimization_iteration import OptimizationIteration
from backend.app.models.objective_score import ObjectiveScore
from backend.app.models.candidate_configuration import CandidateConfiguration
from backend.app.services.optimization_service import process_lsb_candidate
from backend.app.schemas.optimization_iteration import (
    OptimizationIterationCreate,
    OptimizationIterationResponse,
)



router = APIRouter(
    prefix="/optimization-runs/{run_id}/iterations",
    tags=["Optimization Iterations"],
)


@router.post(
    "",
    response_model=OptimizationIterationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_optimization_iteration(
    run_id: UUID,
    iteration_data: OptimizationIterationCreate,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    # Verify that the optimization run exists
    run = (
        db.query(OptimizationRun)
        .filter(
            OptimizationRun.id == run_id,
            OptimizationRun.user_id == UUID(current_user_id),
        )
        .first()
    )

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Optimization run not found",
        )

    iteration = OptimizationIteration(
        optimization_run_id=run_id,
        iteration_number=iteration_data.iteration_number,
        optimizer_state=iteration_data.optimizer_state,
        status="STARTED",
    )
    
    db.add(iteration)

    try:
        db.commit()
        db.refresh(iteration)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Iteration number already exists for this optimization run",
        )

    return iteration


@router.get(
    "",
    response_model=list[OptimizationIterationResponse],
)
def get_optimization_iterations(
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    # Verify that the optimization run belongs to the current user
    run = (
        db.query(OptimizationRun)
        .filter(
            OptimizationRun.id == run_id,
            OptimizationRun.user_id == UUID(current_user_id),
        )
        .first()
    )

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Optimization run not found",
        )

    iterations = (
        db.query(OptimizationIteration)
        .filter(
            OptimizationIteration.optimization_run_id == run_id
        )
        .order_by(OptimizationIteration.iteration_number)
        .all()
    )

    return iterations


@router.get(
    "/{iteration_id}",
    response_model=OptimizationIterationResponse,
)
def get_optimization_iteration(
    run_id: UUID,
    iteration_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    iteration = (
        db.query(OptimizationIteration)
        .join(
            OptimizationRun,
            OptimizationRun.id == OptimizationIteration.optimization_run_id,
        )
        .filter(
            OptimizationIteration.id == iteration_id,
            OptimizationIteration.optimization_run_id == run_id,
            OptimizationRun.user_id == UUID(current_user_id),
        )
        .first()
    )

    if not iteration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Optimization iteration not found",
        )

    return iteration

@router.post(
    "/{iteration_id}/select-best",
    response_model=OptimizationIterationResponse,
)
def select_best_candidate(
    run_id: UUID,
    iteration_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    # Verify iteration belongs to the current user and run
    iteration = (
        db.query(OptimizationIteration)
        .join(
            OptimizationRun,
            OptimizationRun.id == OptimizationIteration.optimization_run_id,
        )
        .filter(
            OptimizationIteration.id == iteration_id,
            OptimizationIteration.optimization_run_id == run_id,
            OptimizationRun.user_id == UUID(current_user_id),
        )
        .first()
    )

    if not iteration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Optimization iteration not found",
        )

    # Get the optimization run
    run = (
        db.query(OptimizationRun)
        .filter(
            OptimizationRun.id == run_id,
            OptimizationRun.user_id == UUID(current_user_id),
        )
        .first()
    )

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Optimization run not found",
        )

    # Get candidates and their scores
    candidates = (
        db.query(CandidateConfiguration, ObjectiveScore)
        .join(
            ObjectiveScore,
            ObjectiveScore.candidate_configuration_id
            == CandidateConfiguration.id,
        )
        .filter(
            CandidateConfiguration.iteration_id == iteration_id,
            ObjectiveScore.objective_name == run.objective_function,
        )
        .all()
    )

    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No candidate scores found for this iteration",
        )

    # Select the candidate with the highest score
    if run.objective_function == "MINIMIZE_MSE":
        best_candidate, best_score = min(
            candidates,
            key=lambda item: item[1].score,
        )
    else:
        best_candidate, best_score = max(
            candidates,
            key=lambda item: item[1].score,
        )

    # Save the selected candidate
    iteration.selected_candidate_id = best_candidate.id
    iteration.status = "COMPLETED"
    iteration.completed_at = datetime.now(timezone.utc)

    run.selected_candidate_id = best_candidate.id
    run.best_score = best_score.score
    run.status = "COMPLETED"
    run.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(iteration)

    return iteration

@router.post(
    "/{iteration_id}/process",
)
def process_optimization_iteration(
    run_id: UUID,
    iteration_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    # Verify iteration belongs to the current user's run
    iteration = (
        db.query(OptimizationIteration)
        .join(
            OptimizationRun,
            OptimizationRun.id == OptimizationIteration.optimization_run_id,
        )
        .filter(
            OptimizationIteration.id == iteration_id,
            OptimizationIteration.optimization_run_id == run_id,
            OptimizationRun.user_id == UUID(current_user_id),
        )
        .first()
    )

    if not iteration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Optimization iteration not found",
        )

    run = (
        db.query(OptimizationRun)
        .filter(
            OptimizationRun.id == run_id,
            OptimizationRun.user_id == UUID(current_user_id),
        )
        .first()
    )

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Optimization run not found",
        )

    candidates = (
        db.query(CandidateConfiguration)
        .filter(
            CandidateConfiguration.iteration_id == iteration_id
        )
        .order_by(CandidateConfiguration.candidate_number)
        .all()
    )

    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No candidates found for this iteration",
        )

    results = []

    run.started_at = datetime.now(timezone.utc)
    run.status = "PROCESSING"
    run_start = perf_counter()

    try:
        for candidate in candidates:
            score = process_lsb_candidate(
                db=db,
                run=run,
                iteration=iteration,
                candidate=candidate,
            )

            results.append(
                {
                    "candidate_id": str(candidate.id),
                    "candidate_number": candidate.candidate_number,
                    "objective_name": score.objective_name,
                    "score": score.score,
                    "metric_values": score.metric_values,
                }
            )

    except Exception as exc:

        candidate.status = "FAILED"
        iteration.status = "FAILED"
        run.status = "FAILED"

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

        # Automatically select the best candidate
    scored_candidates = (
        db.query(CandidateConfiguration, ObjectiveScore)
        .join(
            ObjectiveScore,
            ObjectiveScore.candidate_configuration_id
            == CandidateConfiguration.id,
        )
        .filter(
            CandidateConfiguration.iteration_id == iteration_id,
            ObjectiveScore.objective_name == run.objective_function,
        )
        .all()
    )

    if not scored_candidates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No candidate scores found after processing",
        )

    if run.objective_function == "MINIMIZE_MSE":
        ranked_candidates = sorted(
            scored_candidates,
            key=lambda item: item[1].score,
        )
    else:
        ranked_candidates = sorted(
            scored_candidates,
            key=lambda item: item[1].score,
            reverse=True,
        )

    # Assign ranking to each candidate
    for rank, (candidate, score) in enumerate(
        ranked_candidates,
        start=1,
    ):
        score.ranking = rank

    best_candidate, best_score = ranked_candidates[0]

    iteration.selected_candidate_id = best_candidate.id
    iteration.status = "COMPLETED"
    iteration.completed_at = datetime.now(timezone.utc)

    run.selected_candidate_id = best_candidate.id
    run.best_score = best_score.score
    run.status = "COMPLETED"
    run.processing_time_ms = (perf_counter() - run_start) * 1000
    run.completed_at = datetime.now(timezone.utc)

    db.commit()

    return {
        "run_id": str(run.id),
        "iteration_id": str(iteration.id),
        "algorithm": run.optimization_algorithm,
        "objective_function": run.objective_function,
        "candidates_processed": len(results),
        "selected_candidate_id": str(best_candidate.id),
        "best_score": best_score.score,
        "results": results,
    }