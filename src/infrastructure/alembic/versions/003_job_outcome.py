"""add outcome status to job

Revision ID: 003_job_outcome
Revises: 002_job_applied
Create Date: 2026-10-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_job_outcome"
down_revision: Union[str, None] = "002_job_applied"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("job") as batch:
        batch.add_column(
            sa.Column("outcome", sa.String(length=20), nullable=False, server_default="pending")
        )


def downgrade() -> None:
    with op.batch_alter_table("job") as batch:
        batch.drop_column("outcome")
