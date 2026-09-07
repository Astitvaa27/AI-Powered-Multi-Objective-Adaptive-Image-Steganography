import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user_id
from backend.app.database import get_db
from backend.app.models.analysis_report import AnalysisReport
from backend.app.models.analysis_session import AnalysisSession
from backend.app.models.image import Image
from backend.app.models.model_prediction import ModelPrediction
from backend.app.models.model_version import ModelVersion
from backend.app.models.suspicious_region import SuspiciousRegion
from backend.app.services.steganalysis_service import analyze_image_with_ml

router = APIRouter(
    prefix="/steganalysis",
    tags=["Steganalysis"],
)

ACTIVE_MODEL_NAME = "Steganalysis Random Forest"


def _get_active_model(db: Session) -> ModelVersion:
    model_version = (
        db.query(ModelVersion)
        .filter(
            ModelVersion.name == ACTIVE_MODEL_NAME,
            ModelVersion.status == "ACTIVE",
        )
        .order_by(ModelVersion.created_at.desc())
        .first()
    )

    if not model_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active steganalysis model not found.",
        )

    return model_version


def _execute_analysis(
    db: Session,
    image: Image,
    user_id: UUID,
) -> dict:
    """
    Run the ML steganalysis pipeline for a registered image and persist
    the session, prediction, candidate regions and report.
    """

    path = Path(image.storage_path)

    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file not found.",
        )

    model_version = _get_active_model(db)

    session = AnalysisSession(
        user_id=user_id,
        image_id=image.id,
        status="PROCESSING",
        analysis_type="STEGANALYSIS",
        started_at=datetime.now(timezone.utc),
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    try:
        result = analyze_image_with_ml(str(path))

        session.status = "COMPLETED"
        session.processing_time_ms = int(round(result["processing_time_ms"]))
        session.completed_at = datetime.now(timezone.utc)

        prediction = ModelPrediction(
            analysis_session_id=session.id,
            model_version_id=model_version.id,
            predicted_class=result["predicted_class"],
            confidence=result["confidence"],
            score=result["confidence"],
            probabilities=result["probabilities"],
            metadata_json={
                "feature_count": len(result["features"]),
            },
        )

        db.add(prediction)

        for region in result["suspicious_regions"]:
            db.add(
                SuspiciousRegion(
                    analysis_session_id=session.id,
                    x=region["x"],
                    y=region["y"],
                    width=region["width"],
                    height=region["height"],
                    suspicion_score=region["suspicion_score"],
                    region_type=region["region_type"],
                    metadata_json=region["metadata"],
                )
            )

        reports_dir = Path("storage/reports")
        reports_dir.mkdir(parents=True, exist_ok=True)

        report_path = reports_dir / f"{session.id}.json"

        report_content = {
            "analysis_session_id": str(session.id),
            "image_id": str(image.id),
            "predicted_class": result["predicted_class"],
            "confidence": result["confidence"],
            "probabilities": result["probabilities"],
            "feature_count": len(result["features"]),
            "features": result["features"],
            "processing_time_ms": session.processing_time_ms,
            "suspicious_regions": result["suspicious_regions"],
            "detection_summary": {
                "classification": result["predicted_class"],
                "confidence": result["confidence"],
                "candidate_region_count": len(result["suspicious_regions"]),
                "detection_method": (
                    "Random Forest classification + LSB candidate-region ranking"
                ),
            },
        }

        with open(report_path, "w", encoding="utf-8") as file:
            json.dump(report_content, file, indent=4)

        report = AnalysisReport(
            analysis_session_id=session.id,
            report_type="STEGANALYSIS",
            title="Steganalysis Analysis Report",
            summary=(
                f"Image classified as {prediction.predicted_class} "
                f"with confidence {prediction.confidence:.2f}. "
                f"{len(result['suspicious_regions'])} candidate regions were ranked."
            ),
            report_data={
                "predicted_class": prediction.predicted_class,
                "confidence": prediction.confidence,
                "probabilities": prediction.probabilities,
                "feature_count": len(result["features"]),
                "processing_time_ms": session.processing_time_ms,
                "candidate_region_count": len(result["suspicious_regions"]),
                "features": result["features"],
            },
            report_path=str(report_path),
            status="GENERATED",
        )

        db.add(report)
        db.commit()
        db.refresh(session)
        db.refresh(prediction)

        return {
            "status": session.status,
            "analysis_session_id": session.id,
            "model_prediction_id": prediction.id,
            "image_id": image.id,
            "predicted_class": prediction.predicted_class,
            "confidence": prediction.confidence,
            "probabilities": prediction.probabilities,
            "processing_time_ms": session.processing_time_ms,
            "feature_count": len(result["features"]),
            "features": result["features"],
            "suspicious_regions": result["suspicious_regions"],
            "model": {
                "id": model_version.id,
                "name": model_version.name,
                "version": model_version.version,
                "framework": model_version.framework,
                "architecture": model_version.architecture,
            },
            "analysis_report": {
                "id": report.id,
                "report_type": report.report_type,
                "title": report.title,
                "summary": report.summary,
                "report_data": report.report_data,
                "status": report.status,
            },
        }

    except Exception as exc:
        session.status = "FAILED"
        session.error_message = str(exc)

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Steganalysis failed: {exc}",
        )


@router.post("/analyze")
def analyze_steganography(
    image_path: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Analyse a registered image identified by its storage path."""

    user_id = UUID(current_user_id)

    if not Path(image_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file not found.",
        )

    image = (
        db.query(Image)
        .filter(
            Image.storage_path == image_path,
            Image.owner_id == user_id,
        )
        .first()
    )

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found for the current user.",
        )

    return _execute_analysis(db, image, user_id)


@router.post("/analyze/{image_id}")
def analyze_registered_image(
    image_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Analyse a registered image identified by its database id."""

    user_id = UUID(current_user_id)

    image = (
        db.query(Image)
        .filter(Image.id == image_id, Image.owner_id == user_id)
        .first()
    )

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found for the current user.",
        )

    return _execute_analysis(db, image, user_id)


@router.get("/model")
def get_active_model(
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Describe the currently active steganalysis model."""

    model_version = _get_active_model(db)

    return {
        "id": model_version.id,
        "name": model_version.name,
        "version": model_version.version,
        "framework": model_version.framework,
        "architecture": model_version.architecture,
        "task_type": model_version.task_type,
        "artifact_path": model_version.artifact_path,
        "artifact_available": Path(model_version.artifact_path).is_file(),
        "configuration": model_version.configuration,
        "description": model_version.description,
        "status": model_version.status,
        "created_at": model_version.created_at,
    }


@router.get("/stats")
def get_steganalysis_stats(
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Aggregate counters used by the dashboard."""

    user_id = UUID(current_user_id)

    base = db.query(AnalysisSession).filter(AnalysisSession.user_id == user_id)

    total_analyses = base.count()
    completed = base.filter(AnalysisSession.status == "COMPLETED").count()
    failed = base.filter(AnalysisSession.status == "FAILED").count()

    class_counts = dict(
        db.query(
            ModelPrediction.predicted_class,
            func.count(ModelPrediction.id),
        )
        .join(
            AnalysisSession,
            AnalysisSession.id == ModelPrediction.analysis_session_id,
        )
        .filter(AnalysisSession.user_id == user_id)
        .group_by(ModelPrediction.predicted_class)
        .all()
    )

    average_processing_time = (
        db.query(func.avg(AnalysisSession.processing_time_ms))
        .filter(
            AnalysisSession.user_id == user_id,
            AnalysisSession.status == "COMPLETED",
        )
        .scalar()
    )

    average_confidence = (
        db.query(func.avg(ModelPrediction.confidence))
        .join(
            AnalysisSession,
            AnalysisSession.id == ModelPrediction.analysis_session_id,
        )
        .filter(AnalysisSession.user_id == user_id)
        .scalar()
    )

    total_images = (
        db.query(func.count(Image.id))
        .filter(Image.owner_id == user_id, Image.status == "ACTIVE")
        .scalar()
    )

    total_regions = (
        db.query(func.count(SuspiciousRegion.id))
        .join(
            AnalysisSession,
            AnalysisSession.id == SuspiciousRegion.analysis_session_id,
        )
        .filter(AnalysisSession.user_id == user_id)
        .scalar()
    )

    return {
        "total_analyses": total_analyses,
        "completed_analyses": completed,
        "failed_analyses": failed,
        "clean_count": int(class_counts.get("CLEAN", 0)),
        "stego_count": int(class_counts.get("STEGO", 0)),
        "total_images": int(total_images or 0),
        "total_candidate_regions": int(total_regions or 0),
        "average_processing_time_ms": (
            float(average_processing_time) if average_processing_time else None
        ),
        "average_confidence": (
            float(average_confidence) if average_confidence else None
        ),
    }


@router.get("/sessions")
def list_analysis_sessions(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    predicted_class: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Paginated steganalysis history for the current user."""

    user_id = UUID(current_user_id)

    query = (
        db.query(AnalysisSession, ModelPrediction, Image)
        .outerjoin(
            ModelPrediction,
            ModelPrediction.analysis_session_id == AnalysisSession.id,
        )
        .outerjoin(Image, Image.id == AnalysisSession.image_id)
        .filter(AnalysisSession.user_id == user_id)
    )

    if predicted_class:
        query = query.filter(
            ModelPrediction.predicted_class == predicted_class.upper()
        )

    total = query.count()

    rows = (
        query
        .order_by(AnalysisSession.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "analysis_session_id": session.id,
                "image_id": session.image_id,
                "image_filename": getattr(image, "original_filename", None),
                "analysis_type": session.analysis_type,
                "status": session.status,
                "predicted_class": getattr(prediction, "predicted_class", None),
                "confidence": getattr(prediction, "confidence", None),
                "probabilities": getattr(prediction, "probabilities", None),
                "processing_time_ms": session.processing_time_ms,
                "error_message": session.error_message,
                "created_at": session.created_at,
                "completed_at": session.completed_at,
            }
            for session, prediction, image in rows
        ],
    }


@router.get("/sessions/{analysis_session_id}")
def get_analysis_session(
    analysis_session_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Full detail for a single steganalysis session."""

    user_id = UUID(current_user_id)

    session = (
        db.query(AnalysisSession)
        .filter(
            AnalysisSession.id == analysis_session_id,
            AnalysisSession.user_id == user_id,
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis session not found.",
        )

    prediction = (
        db.query(ModelPrediction)
        .filter(ModelPrediction.analysis_session_id == session.id)
        .first()
    )

    report = (
        db.query(AnalysisReport)
        .filter(AnalysisReport.analysis_session_id == session.id)
        .first()
    )

    regions = (
        db.query(SuspiciousRegion)
        .filter(SuspiciousRegion.analysis_session_id == session.id)
        .order_by(SuspiciousRegion.suspicion_score.desc())
        .all()
    )

    image = db.query(Image).filter(Image.id == session.image_id).first()

    model_version = None

    if prediction:
        model_version = (
            db.query(ModelVersion)
            .filter(ModelVersion.id == prediction.model_version_id)
            .first()
        )

    features = None

    if report and isinstance(report.report_data, dict):
        features = report.report_data.get("features")

    # Older sessions stored the feature vector only in the JSON report.
    if features is None and report and report.report_path:
        stored = Path(report.report_path)

        if stored.is_file():
            try:
                with open(stored, "r", encoding="utf-8") as file:
                    features = json.load(file).get("features")
            except (OSError, json.JSONDecodeError):
                features = None

    return {
        "analysis_session_id": session.id,
        "status": session.status,
        "analysis_type": session.analysis_type,
        "processing_time_ms": session.processing_time_ms,
        "error_message": session.error_message,
        "created_at": session.created_at,
        "started_at": session.started_at,
        "completed_at": session.completed_at,
        "image": (
            {
                "id": image.id,
                "original_filename": image.original_filename,
                "storage_path": image.storage_path,
                "width": image.width,
                "height": image.height,
                "channels": image.channels,
                "file_size_bytes": image.file_size_bytes,
                "mime_type": image.mime_type,
                "file_extension": image.file_extension,
                "metadata": image.metadata_json or {},
            }
            if image
            else None
        ),
        "prediction": (
            {
                "id": prediction.id,
                "predicted_class": prediction.predicted_class,
                "confidence": prediction.confidence,
                "probabilities": prediction.probabilities,
                "metadata": prediction.metadata_json or {},
            }
            if prediction
            else None
        ),
        "model": (
            {
                "id": model_version.id,
                "name": model_version.name,
                "version": model_version.version,
                "framework": model_version.framework,
                "architecture": model_version.architecture,
            }
            if model_version
            else None
        ),
        "features": features,
        "feature_count": len(features) if isinstance(features, dict) else None,
        "suspicious_regions": [
            {
                "id": region.id,
                "x": region.x,
                "y": region.y,
                "width": region.width,
                "height": region.height,
                "suspicion_score": region.suspicion_score,
                "region_type": region.region_type,
                "metadata": region.metadata_json or {},
            }
            for region in regions
        ],
        "report": (
            {
                "id": report.id,
                "report_type": report.report_type,
                "title": report.title,
                "summary": report.summary,
                "report_data": report.report_data,
                "report_path": report.report_path,
                "status": report.status,
                "created_at": report.created_at,
            }
            if report
            else None
        ),
    }


@router.get("/reports/{analysis_session_id}")
def get_analysis_report(
    analysis_session_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    user_id = UUID(current_user_id)

    report = (
        db.query(AnalysisReport)
        .join(
            AnalysisSession,
            AnalysisReport.analysis_session_id == AnalysisSession.id,
        )
        .filter(
            AnalysisReport.analysis_session_id == analysis_session_id,
            AnalysisSession.user_id == user_id,
        )
        .first()
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Analysis report not found.",
        )

    return {
        "id": report.id,
        "analysis_session_id": report.analysis_session_id,
        "report_type": report.report_type,
        "title": report.title,
        "summary": report.summary,
        "report_data": report.report_data,
        "report_path": report.report_path,
        "status": report.status,
        "created_at": report.created_at,
    }
