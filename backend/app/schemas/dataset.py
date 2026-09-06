from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DatasetCreate(BaseModel):
    name: str
    version: str
    description: str | None = None
    source: str | None = None
    license: str | None = None
    dataset_hash: str | None = None
    metadata: dict = Field(default_factory=dict)


class DatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version: str
    description: str | None
    source: str | None
    license: str | None
    dataset_hash: str | None

    metadata: dict = Field(
        validation_alias="metadata_json",
        serialization_alias="metadata",
    )

    is_active: bool