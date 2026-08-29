"""init jobfinder tables

Revision ID: 001_init_jobfinder
Revises:
Create Date: 2026-08-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_init_jobfinder"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "candidate",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.String(length=500), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=True),
        sa.Column("headline", sa.String(length=300), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("phone", sa.String(length=80), nullable=True),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("years_experience", sa.Integer(), nullable=True),
        sa.Column("skills_json", sa.Text(), nullable=False),
        sa.Column("titles_json", sa.Text(), nullable=False),
        sa.Column("education_json", sa.Text(), nullable=False),
        sa.Column("creation_datetime", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_candidate_id"), "candidate", ["id"], unique=False)

    op.create_table(
        "job",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("linkedin_job_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("company", sa.String(length=200), nullable=True),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("url", sa.String(length=700), nullable=False),
        sa.Column("salary_text", sa.String(length=200), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("workplace_type", sa.String(length=40), nullable=False),
        sa.Column("sponsorship", sa.String(length=20), nullable=False),
        sa.Column("relocation", sa.String(length=20), nullable=False),
        sa.Column("employment_type", sa.String(length=40), nullable=True),
        sa.Column("seniority", sa.String(length=40), nullable=True),
        sa.Column("posted_at", sa.String(length=80), nullable=True),
        sa.Column("is_easy_apply", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("creation_datetime", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("modification_datetime", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("linkedin_job_id"),
    )
    op.create_index(op.f("ix_job_id"), "job", ["id"], unique=False)
    op.create_index(op.f("ix_job_linkedin_job_id"), "job", ["linkedin_job_id"], unique=True)

    op.create_table(
        "job_match",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("interview_success_rate", sa.Float(), nullable=False),
        sa.Column("skill_match_rate", sa.Float(), nullable=False),
        sa.Column("title_match_rate", sa.Float(), nullable=False),
        sa.Column("experience_match_rate", sa.Float(), nullable=False),
        sa.Column("matched_skills_json", sa.Text(), nullable=False),
        sa.Column("missing_skills_json", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("creation_datetime", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("modification_datetime", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidate.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["job.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_job_match_candidate_id"), "job_match", ["candidate_id"], unique=False)
    op.create_index(op.f("ix_job_match_id"), "job_match", ["id"], unique=False)
    op.create_index(op.f("ix_job_match_job_id"), "job_match", ["job_id"], unique=False)

    op.create_table(
        "search_run",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=True),
        sa.Column("keywords", sa.String(length=400), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("remote_only", sa.Boolean(), nullable=False),
        sa.Column("sponsorship_only", sa.Boolean(), nullable=False),
        sa.Column("jobs_found", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("creation_datetime", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_search_run_candidate_id"), "search_run", ["candidate_id"], unique=False)
    op.create_index(op.f("ix_search_run_id"), "search_run", ["id"], unique=False)


def downgrade() -> None:
    op.drop_table("search_run")
    op.drop_table("job_match")
    op.drop_table("job")
    op.drop_table("candidate")
