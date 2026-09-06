from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OptimizationIterationCreate(BaseModel):
    iteration_number: int = Field(gt=0)
    optimizer_state: dict = Field(default_factory=dict)


class OptimizationIterationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    optimization_run_id: UUID
    iteration_number: int
    status: str
    selected_candidate_id: UUID | None
    optimizer_state: dict
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime