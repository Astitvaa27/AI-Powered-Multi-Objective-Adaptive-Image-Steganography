"""add missing check constraints

Revision ID: 023857cbdabc
Revises: 9330f2826313
Create Date: 2026-08-30 15:59:51.166126

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '023857cbdabc'
down_revision: Union[str, Sequence[str], None] = '9330f2826313'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_optimization_max_iterations_positive",
        "optimization_runs",
        "max_iterations IS NULL OR max_iterations > 0",
    )

    op.create_check_constraint(
        "ck_optimization_processing_time_nonnegative",
        "optimization_runs",
        "processing_time_ms IS NULL OR processing_time_ms >= 0",
    )

    op.create_check_constraint(
        "ck_optimization_iteration_number_positive",
        "optimization_iterations",
        "iteration_number > 0",
    )

    op.create_check_constraint(
        "ck_candidate_number_positive",
        "candidate_configurations",
        "candidate_number IS NULL OR candidate_number > 0",
    )

    op.create_check_constraint(
        "ck_experiment_run_number_positive",
        "experiment_runs",
        "run_number > 0",
    )

    op.create_check_constraint(
        "ck_training_processing_time_nonnegative",
        "training_runs",
        "processing_time_ms IS NULL OR processing_time_ms >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_training_processing_time_nonnegative",
        "training_runs",
        type_="check",
    )

    op.drop_constraint(
        "ck_experiment_run_number_positive",
        "experiment_runs",
        type_="check",
    )

    op.drop_constraint(
        "ck_candidate_number_positive",
        "candidate_configurations",
        type_="check",
    )

    op.drop_constraint(
        "ck_optimization_iteration_number_positive",
        "optimization_iterations",
        type_="check",
    )

    op.drop_constraint(
        "ck_optimization_processing_time_nonnegative",
        "optimization_runs",
        type_="check",
    )

    op.drop_constraint(
        "ck_optimization_max_iterations_positive",
        "optimization_runs",
        type_="check",
    )