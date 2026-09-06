import hashlib
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.database import engine
from backend.app.models.image import Image
from backend.app.models.dataset_image import DatasetImage


DATASET_ID = uuid.UUID(
    "1bfe6d14-4016-4599-9ddc-2199e0240506"
)

STEGO_DIR = Path("storage/dataset/stego")


def calculate_sha256(path: Path) -> str:
    sha256 = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


files = sorted(
    STEGO_DIR.glob("*lsb3*medium.tiff")
)

print("FILES FOUND:", len(files))

with Session(engine) as db:

    for f in files:

        if "4.1.05" in f.name or "4.1.07" in f.name:
            split = "TRAIN"
        else:
            split = "TEST"

        image = Image(
            original_filename=f.name,
            storage_path=str(f),
            mime_type="image/tiff",
            file_extension=".tiff",
            file_size_bytes=f.stat().st_size,
            width=256,
            height=256,
            channels=3,
            bit_depth=8,
            sha256_hash=calculate_sha256(f),
            metadata_json={
                "embedding_method": "LSB",
                "channel_mode": "RGB",
                "lsb_bits": 3,
                "payload_size_bytes": 84,
            },
            status="ACTIVE",
        )

        db.add(image)
        db.flush()

        dataset_image = DatasetImage(
            dataset_id=DATASET_ID,
            image_id=image.id,
            split=split,
            label="STEGO",
            sample_group=f.stem.split("_stego_")[0],
            metadata_json={
                "embedding_method": "LSB",
                "channel_mode": "RGB",
                "lsb_bits": 3,
                "payload_size_bytes": 84,
            },
        )

        db.add(dataset_image)

        print(
            "REGISTERED:",
            f.name,
            "|",
            split,
            "|",
            image.id,
        )

    db.commit()

print("REGISTRATION COMPLETE:", len(files))