from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ObjectiveScoreCreate(BaseModel):
    objective_name: str = Field(min_length=1, max_length=100)
    score: float
    metric_values: dict = Field(default_factory=dict)
    ranking: int | None = Field(default=None, gt=0)


class ObjectiveScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    candidate_configuration_id: UUID
    objective_name: str
    score: float
    metric_values: dict
    ranking: int | None
    created_at: datetime