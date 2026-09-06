from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OptimizationRunCreate(BaseModel):
    image_id: UUID
    payload_id: UUID | None = None
    optimization_algorithm: str = Field(min_length=1, max_length=50)
    objective_function: str = Field(min_length=1, max_length=100)
    max_iterations: int | None = Field(default=None, gt=0)
    configuration: dict = Field(default_factory=dict)


class OptimizationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    image_id: UUID
    payload_id: UUID | None
    selected_candidate_id: UUID | None
    optimization_algorithm: str
    objective_function: str
    max_iterations: int | None
    status: str
    best_score: float | None
    processing_time_ms: int | None
    configuration: dict