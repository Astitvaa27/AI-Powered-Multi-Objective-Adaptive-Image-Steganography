"""create otp codes table and seed default user role

Revision ID: 45ebc4420b7b
Revises: 99cb65980aee
Create Date: 2026-09-07 00:00:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '45ebc4420b7b'
down_revision: Union[str, Sequence[str], None] = '99cb65980aee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'otp_codes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('purpose', sa.String(length=30), nullable=False),
        sa.Column('code_hash', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='otp_codes_user_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_otp_codes_user_id_purpose',
        'otp_codes',
        ['user_id', 'purpose'],
    )

    # Seed the default self-registration role if it doesn't already exist,
    # so /auth/signup always has a role to assign new users to.
    op.execute(
        sa.text(
            "INSERT INTO roles (id, name, description) "
            "VALUES (:id, :name, :description) "
            "ON CONFLICT (name) DO NOTHING"
        ).bindparams(
            id=uuid.uuid4(),
            name='user',
            description='Standard self-registered user',
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_otp_codes_user_id_purpose', table_name='otp_codes')
    op.drop_table('otp_codes')
    op.execute(sa.text("DELETE FROM roles WHERE name = 'user'"))
