from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PayloadCreate(BaseModel):
    payload_type: str = Field(min_length=1, max_length=30)
    original_size_bytes: int = Field(ge=0)
    encoded_size_bytes: int | None = Field(default=None, ge=0)
    payload_hash: str | None = Field(default=None, max_length=64)
    encryption_enabled: bool = False
    encryption_algorithm: str | None = Field(default=None, max_length=50)
    encryption_metadata: dict = Field(default_factory=dict)
    storage_path: str | None = None


class PayloadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payload_type: str
    original_size_bytes: int
    encoded_size_bytes: int | None
    payload_hash: str | None
    encryption_enabled: bool
    encryption_algorithm: str | None
    encryption_metadata: dict
    storage_path: str | None