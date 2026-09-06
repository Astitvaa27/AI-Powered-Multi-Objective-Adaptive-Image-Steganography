from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user_id
from backend.app.database import engine, get_db
from backend.app.models import image
from datetime import datetime, timezone
import json
from backend.app.models.suspicious_region import SuspiciousRegion
from backend.app.models.analysis_report import AnalysisReport
from backend.app.models.analysis_session import AnalysisSession
from backend.app.models.image import Image
from backend.app.models.model_prediction import ModelPrediction
from backend.app.models.model_version import ModelVersion
from backend.app.services.steganalysis_service import (
    analyze_image_with_ml,
)


router = APIRouter(
    prefix="/steganalysis",
    tags=["Steganalysis"],
)


@router.post("/analyze")
def analyze_steganography(
    image_path: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    user_id = UUID(current_user_id)
    print("DEBUG DB URL:", engine.url)
    print("DEBUG IMAGE TABLE COUNT:", db.query(Image).count())
    debug_sipi_images = db.query(Image).filter(
        Image.storage_path.ilike("%sipi%")
    ).all()

    print("DEBUG SIPI COUNT:", len(debug_sipi_images))

    for debug_image in debug_sipi_images:
        print(
            "DEBUG SIPI IMAGE:",
            debug_image.id,
            repr(debug_image.storage_path),
            debug_image.owner_id,
        )

    path = Path(image_path)

    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file not found.",
        )

    # Find the image registered in the database
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

    # Find the active steganalysis model
    model_version = (
        db.query(ModelVersion)
        .filter(
            ModelVersion.name == "Steganalysis Random Forest",
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

    # Create analysis session
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
        session.processing_time_ms = int(
            round(result["processing_time_ms"])
        )
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
            suspicious_region = SuspiciousRegion(
                analysis_session_id=session.id,
                x=region["x"],
                y=region["y"],
                width=region["width"],
                height=region["height"],
                suspicion_score=region["suspicion_score"],
                region_type=region["region_type"],
                metadata_json=region["metadata"],
            )
            db.add(suspicious_region)

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
                "detection_method": "Random Forest classification + LSB candidate-region ranking",
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