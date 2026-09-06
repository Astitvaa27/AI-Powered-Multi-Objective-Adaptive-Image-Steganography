"""add business uniqueness constraints

Revision ID: 9330f2826313
Revises: 461e58df3a59
Create Date: 2026-08-30 15:54:58.323472

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9330f2826313'
down_revision: Union[str, Sequence[str], None] = '461e58df3a59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_experiment_runs_experiment_run_number",
        "experiment_runs",
        ["experiment_id", "run_number"],
    )

    op.create_unique_constraint(
        "uq_optimization_iterations_run_iteration_number",
        "optimization_iterations",
        ["optimization_run_id", "iteration_number"],
    )

    op.create_unique_constraint(
        "uq_candidate_configurations_iteration_candidate_number",
        "candidate_configurations",
        ["iteration_id", "candidate_number"],
    )

    op.create_unique_constraint(
        "uq_objective_scores_candidate_objective",
        "objective_scores",
        ["candidate_configuration_id", "objective_name"],
    )

    op.create_unique_constraint(
        "uq_model_evaluations_model_dataset_type",
        "model_evaluations",
        ["model_version_id", "dataset_id", "evaluation_type"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_model_evaluations_model_dataset_type",
        "model_evaluations",
        type_="unique",
    )

    op.drop_constraint(
        "uq_objective_scores_candidate_objective",
        "objective_scores",
        type_="unique",
    )

    op.drop_constraint(
        "uq_candidate_configurations_iteration_candidate_number",
        "candidate_configurations",
        type_="unique",
    )

    op.drop_constraint(
        "uq_optimization_iterations_run_iteration_number",
        "optimization_iterations",
        type_="unique",
    )

    op.drop_constraint(
        "uq_experiment_runs_experiment_run_number",
        "experiment_runs",
        type_="unique",
    )
