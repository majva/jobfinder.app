"""add applied flag to job

Revision ID: 002_job_applied
Revises: 001_init_jobfinder
Create Date: 2026-08-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_job_applied"
down_revision: Union[str, None] = "001_init_jobfinder"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("job") as batch:
        batch.add_column(
            sa.Column("applied", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    with op.batch_alter_table("job") as batch:
        batch.drop_column("applied")
