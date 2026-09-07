import hashlib
import io
import uuid as uuid_module
from pathlib import Path
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import Response
from PIL import Image as PILImage
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.core.security import get_current_user_id
from backend.app.database import get_db
from backend.app.models.image import Image

router = APIRouter(
    prefix="/images",
    tags=["Images"],
)

settings = get_settings()

ALLOWED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tif",
    ".tiff",
    ".pgm",
    ".ppm",
    ".webp",
}

MAX_UPLOAD_BYTES = 25 * 1024 * 1024

# Formats a browser can render directly. Anything else is
# transcoded to PNG when served through the preview endpoint.
BROWSER_SAFE_MIME = {
    "image/png": "image/png",
    "image/jpeg": "image/jpeg",
    "image/webp": "image/webp",
    "image/bmp": "image/bmp",
}


def _serialize_image(image: Image) -> dict:
    return {
        "id": image.id,
        "original_filename": image.original_filename,
        "storage_path": image.storage_path,
        "mime_type": image.mime_type,
        "file_extension": image.file_extension,
        "file_size_bytes": image.file_size_bytes,
        "width": image.width,
        "height": image.height,
        "channels": image.channels,
        "bit_depth": image.bit_depth,
        "sha256_hash": image.sha256_hash,
        "metadata": image.metadata_json or {},
        "status": image.status,
        "created_at": image.created_at,
    }


def _inspect_image_file(path: Path) -> dict:
    """Read width/height/channel information from an image on disk."""

    try:
        with PILImage.open(path) as opened:
            width, height = opened.size
            channels = len(opened.getbands())
            image_format = (opened.format or "").upper()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported or corrupted image file: {exc}",
        )

    mime_by_format = {
        "PNG": "image/png",
        "JPEG": "image/jpeg",
        "BMP": "image/bmp",
        "TIFF": "image/tiff",
        "PPM": "image/x-portable-pixmap",
        "WEBP": "image/webp",
    }

    return {
        "width": width,
        "height": height,
        "channels": channels,
        "mime_type": mime_by_format.get(image_format, "application/octet-stream"),
    }


def _get_owned_image(
    image_id: UUID,
    user_id: UUID,
    db: Session,
) -> Image:
    image = (
        db.query(Image)
        .filter(
            Image.id == image_id,
            Image.owner_id == user_id,
        )
        .first()
    )

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found for the current user.",
        )

    return image


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
)
async def upload_image(
    file: UploadFile = File(...),
    image_type: str = Query(
        "COVER",
        description="Logical role of the image, e.g. COVER or SUSPECT.",
    ),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Upload an image and register it against the current user."""

    user_id = UUID(current_user_id)

    extension = Path(file.filename or "").suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unsupported image type. Allowed formats: "
                + ", ".join(sorted(ALLOWED_EXTENSIONS))
            ),
        )

    contents = await file.read()

    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image exceeds the 25 MB upload limit.",
        )

    sha256_hash = hashlib.sha256(contents).hexdigest()

    # Reuse an identical image already owned by this user.
    existing = (
        db.query(Image)
        .filter(
            Image.sha256_hash == sha256_hash,
            Image.owner_id == user_id,
            Image.status == "ACTIVE",
        )
        .first()
    )

    if existing and Path(existing.storage_path).exists():
        return _serialize_image(existing)

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    stored_path = upload_dir / f"{uuid_module.uuid4()}{extension}"
    stored_path.write_bytes(contents)

    try:
        info = _inspect_image_file(stored_path)
    except HTTPException:
        stored_path.unlink(missing_ok=True)
        raise

    image = Image(
        owner_id=user_id,
        original_filename=Path(file.filename or stored_path.name).name,
        storage_path=str(stored_path).replace("\\", "/"),
        mime_type=file.content_type or info["mime_type"],
        file_extension=extension,
        file_size_bytes=len(contents),
        width=info["width"],
        height=info["height"],
        channels=info["channels"],
        bit_depth=8,
        sha256_hash=sha256_hash,
        metadata_json={
            "image_type": image_type.upper(),
            "source": "USER_UPLOAD",
        },
        status="ACTIVE",
    )

    db.add(image)
    db.commit()
    db.refresh(image)

    return _serialize_image(image)


@router.post(
    "/register-path",
    status_code=status.HTTP_201_CREATED,
)
def register_existing_path(
    storage_path: str = Query(
        ...,
        description="Path of an existing image inside the storage directory.",
    ),
    image_type: str = Query("COVER"),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Register an image that already exists on disk (for example a
    BOSSBase dataset file) so it can be analysed through the UI.
    Restricted to paths inside the configured storage directory.
    """

    user_id = UUID(current_user_id)

    storage_root = Path(settings.STORAGE_DIR).resolve()
    path = Path(storage_path)

    try:
        resolved = path.resolve()
        resolved.relative_to(storage_root)
    except (ValueError, OSError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path must be located inside the storage directory.",
        )

    if not resolved.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No file exists at the supplied path.",
        )

    normalised = str(path).replace("\\", "/")

    existing = (
        db.query(Image)
        .filter(
            Image.storage_path == normalised,
            Image.owner_id == user_id,
        )
        .first()
    )

    if existing:
        return _serialize_image(existing)

    contents = resolved.read_bytes()
    info = _inspect_image_file(resolved)

    image = Image(
        owner_id=user_id,
        original_filename=resolved.name,
        storage_path=normalised,
        mime_type=info["mime_type"],
        file_extension=resolved.suffix.lower(),
        file_size_bytes=len(contents),
        width=info["width"],
        height=info["height"],
        channels=info["channels"],
        bit_depth=8,
        sha256_hash=hashlib.sha256(contents).hexdigest(),
        metadata_json={
            "image_type": image_type.upper(),
            "source": "REGISTERED_PATH",
        },
        status="ACTIVE",
    )

    db.add(image)
    db.commit()
    db.refresh(image)

    return _serialize_image(image)


@router.get("")
def list_images(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    image_type: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    user_id = UUID(current_user_id)

    query = (
        db.query(Image)
        .filter(
            Image.owner_id == user_id,
            Image.status == "ACTIVE",
        )
    )

    if image_type:
        query = query.filter(
            Image.metadata_json["image_type"].astext == image_type.upper()
        )

    total = query.count()

    images = (
        query
        .order_by(Image.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_serialize_image(image) for image in images],
    }


@router.get("/{image_id}")
def get_image(
    image_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    image = _get_owned_image(image_id, UUID(current_user_id), db)

    return _serialize_image(image)


@router.get("/{image_id}/file")
def get_image_file(
    image_id: UUID,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Serve image bytes for display. Formats a browser cannot render
    natively (PGM/PPM/TIFF) are transcoded to PNG on the fly, so the
    UI can preview BOSSBase dataset images.
    """

    image = _get_owned_image(image_id, UUID(current_user_id), db)

    path = Path(image.storage_path)

    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file is missing from storage.",
        )

    media_type = BROWSER_SAFE_MIME.get(image.mime_type)

    if media_type:
        return Response(
            content=path.read_bytes(),
            media_type=media_type,
            headers={"Cache-Control": "private, max-age=3600"},
        )

    try:
        with PILImage.open(path) as opened:
            buffer = io.BytesIO()
            opened.convert("RGB" if opened.mode not in ("L", "RGB") else opened.mode)
            opened.save(buffer, format="PNG")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to render image preview: {exc}",
        )

    return Response(
        content=buffer.getvalue(),
        media_type="image/png",
        headers={"Cache-Control": "private, max-age=3600"},
    )
