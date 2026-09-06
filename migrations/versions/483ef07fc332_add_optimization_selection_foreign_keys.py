"""add optimization selection foreign keys

Revision ID: 483ef07fc332
Revises: 023857cbdabc
Create Date: 2026-08-30 16:01:26.992120

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '483ef07fc332'
down_revision: Union[str, Sequence[str], None] = '023857cbdabc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        "optimization_runs_selected_candidate_id_fkey",
        "optimization_runs",
        "candidate_configurations",
        ["selected_candidate_id"],
        ["id"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
    )

    op.create_foreign_key(
        "optimization_iterations_selected_candidate_id_fkey",
        "optimization_iterations",
        "candidate_configurations",
        ["selected_candidate_id"],
        ["id"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
    )


def downgrade() -> None:
    op.drop_constraint(
        "optimization_iterations_selected_candidate_id_fkey",
        "optimization_iterations",
        type_="foreignkey",
    )

    op.drop_constraint(
        "optimization_runs_selected_candidate_id_fkey",
        "optimization_runs",
        type_="foreignkey",
    )
