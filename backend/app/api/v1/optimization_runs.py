from uuid import UUID
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user_id
from backend.app.database import get_db
from backend.app.models.image import Image
from backend.app.models.optimization_run import OptimizationRun
from backend.app.schemas.optimization_run import (
    OptimizationRunCreate,
    OptimizationRunResponse,
)
from datetime import datetime, timezone

from backend.app.models.candidate_configuration import CandidateConfiguration
from backend.app.models.embedding_method import EmbeddingMethod
from backend.app.models.objective_score import ObjectiveScore
from backend.app.models.optimization_iteration import OptimizationIteration
from backend.app.services.optimization_service import process_lsb_candidate

router = APIRouter(
    prefix="/optimization-runs",
    tags=["Optimization Runs"],
)


@router.post(
    "",
    response_model=OptimizationRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_optimization_run(
    run_data: OptimizationRunCreate,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    # Verify that the image exists
    image = (
        db.query(Image)
        .filter(Image.id == run_data.image_id)
        .first()
    )

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    run = OptimizationRun(
        user_id=UUID(current_user_id),
        image_id=run_data.image_id,
        payload_id=run_data.payload_id,
        optimization_algorithm=run_data.optimization_algorithm,
        objective_function=run_data.objective_function,
        max_iterations=run_data.max_iterations,
        configuration=run_data.configuration,
        status="CREATED",
    )

    db.add(run)
    db.commit()
    db.refresh(run)

    return run


@router.get(
    "/{run_id}",
    response_model=OptimizationRunResponse,
)
def get_optimization_run(
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
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

    return run

@router.post(
    "/{run_id}/execute",
)
def execute_optimization_run(
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
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

    if not run.max_iterations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="max_iterations must be set",
        )

    configuration = run.configuration or {}

    channel_modes = configuration.get(
        "channel_modes",
        ["RGB"],
    )

    lsb_bits_values = configuration.get(
        "lsb_bits",
        [1],
    )

    if not isinstance(channel_modes, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="channel_modes must be a list",
        )

    if not isinstance(lsb_bits_values, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lsb_bits must be a list",
        )

    # Get active embedding methods
    methods = (
        db.query(EmbeddingMethod)
        .filter(
            EmbeddingMethod.code.in_(["LSB", "DCT", "DWT"]),
            EmbeddingMethod.is_active.is_(True),
        )
        .all()
    )

    if not methods:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active embedding methods found",
        )

    methods_by_code = {method.code: method for method in methods}
    print("ACTIVE METHODS:", [method.code for method in methods])

    run.status = "PROCESSING"
    run.started_at = datetime.now(timezone.utc)
    run_start = perf_counter()
    db.commit()

    all_iteration_results = []

    try:
        for iteration_number in range(
            1,
            run.max_iterations + 1,
        ):
            # Create iteration
            iteration = OptimizationIteration(
                optimization_run_id=run.id,
                iteration_number=iteration_number,
                optimizer_state={
                    "algorithm": run.optimization_algorithm,
                    "iteration": iteration_number,
                },
                status="STARTED",
            )

            db.add(iteration)
            db.commit()
            db.refresh(iteration)

            # Generate candidates from the configured grid
            candidate_number = 1

            for method_code, method in methods_by_code.items():

                if method_code == "LSB":
                    for channel_mode in channel_modes:
                        for lsb_bits in lsb_bits_values:
                            candidate = CandidateConfiguration(
                                iteration_id=iteration.id,
                                method_id=method.id,
                                candidate_number=candidate_number,
                                parameters={
                                    "channel_mode": channel_mode,
                                    "lsb_bits": int(lsb_bits),
                                },
                                status="GENERATED",
                            )

                            db.add(candidate)
                            candidate_number += 1

                elif method_code == "DCT":
                    candidate = CandidateConfiguration(
                        iteration_id=iteration.id,
                        method_id=method.id,
                        candidate_number=candidate_number,
                        parameters={},
                        status="GENERATED",
                    )

                    db.add(candidate)
                    candidate_number += 1

                elif method_code == "DWT":
                    candidate = CandidateConfiguration(
                        iteration_id=iteration.id,
                        method_id=method.id,
                        candidate_number=candidate_number,
                        parameters={},
                        status="GENERATED",
                    )

                    db.add(candidate)
                    candidate_number += 1

            db.commit()

            # Get generated candidates
            candidates = (
                db.query(CandidateConfiguration)
                .filter(
                    CandidateConfiguration.iteration_id
                    == iteration.id
                )
                .order_by(
                    CandidateConfiguration.candidate_number
                )
                .all()
            )

            iteration_results = []

            # Process every candidate
            for candidate in candidates:
                score = process_lsb_candidate(
                    db=db,
                    run=run,
                    iteration=iteration,
                    candidate=candidate,
                )

                iteration_results.append(
                    {
                        "candidate_id": str(candidate.id),
                        "candidate_number": candidate.candidate_number,
                        "score": score.score,
                        "objective_name": score.objective_name,
                        "metric_values": score.metric_values,
                    }
                )

            # Get scores for ranking
            scored_candidates = (
                db.query(
                    CandidateConfiguration,
                    ObjectiveScore,
                )
                .join(
                    ObjectiveScore,
                    ObjectiveScore.candidate_configuration_id
                    == CandidateConfiguration.id,
                )
                .filter(
                    CandidateConfiguration.iteration_id
                    == iteration.id,
                    ObjectiveScore.objective_name
                    == run.objective_function,
                )
                .all()
            )

            if not scored_candidates:
                raise ValueError(
                    "No candidate scores found"
                )

            # Rank candidates
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

            for rank, (candidate, score) in enumerate(
                ranked_candidates,
                start=1,
            ):
                score.ranking = rank

            best_candidate, best_score = (
                ranked_candidates[0]
            )

            iteration.selected_candidate_id = (
                best_candidate.id
            )

            iteration.status = "COMPLETED"
            iteration.completed_at = (
                datetime.now(timezone.utc)
            )

            db.commit()

            all_iteration_results.append(
                {
                    "iteration_number": iteration_number,
                    "iteration_id": str(iteration.id),
                    "selected_candidate_id": str(
                        best_candidate.id
                    ),
                    "best_score": best_score.score,
                    "candidates_processed": len(
                        iteration_results
                    ),
                    "results": iteration_results,
                }
            )

        # Find the best candidate across ALL iterations
        all_scored_candidates = (
            db.query(
                CandidateConfiguration,
                ObjectiveScore,
                OptimizationIteration,
            )
            .join(
                ObjectiveScore,
                ObjectiveScore.candidate_configuration_id
                == CandidateConfiguration.id,
            )
            .join(
                OptimizationIteration,
                OptimizationIteration.id
                == CandidateConfiguration.iteration_id,
            )
            .filter(
                OptimizationIteration.optimization_run_id
                == run.id,
                ObjectiveScore.objective_name
                == run.objective_function,
            )
            .all()
        )

        if run.objective_function == "MINIMIZE_MSE":
            final_candidate, final_score, final_iteration = min(
                all_scored_candidates,
                key=lambda item: item[1].score,
            )
        else:
            final_candidate, final_score, final_iteration = max(
                all_scored_candidates,
                key=lambda item: item[1].score,
            )

        run.selected_candidate_id = final_candidate.id
        run.best_score = final_score.score
        run.status = "COMPLETED"
        run.processing_time_ms = (perf_counter() - run_start) * 1000
        run.completed_at = datetime.now(timezone.utc)

        db.commit()

        return {
            "run_id": str(run.id),
            "algorithm": run.optimization_algorithm,
            "objective_function": run.objective_function,
            "iterations_completed": run.max_iterations,
            "selected_candidate_id": str(
                final_candidate.id
            ),
            "selected_iteration_id": str(
                final_iteration.id
            ),
            "best_score": final_score.score,
            "iterations": all_iteration_results,
        }

    except Exception as exc:
        db.rollback()

        run.status = "FAILED"
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )