from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CandidateConfigurationCreate(BaseModel):
    method_id: UUID
    candidate_number: int | None = Field(default=None, gt=0)
    parameters: dict = Field(default_factory=dict)


class CandidateConfigurationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    iteration_id: UUID
    method_id: UUID
    candidate_number: int | None
    parameters: dict
    status: str
    created_at: datetime