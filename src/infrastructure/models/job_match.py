from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.sql import func

from src.infrastructure.context.sql_db.sqlite_dbcontext import Base


class JobMatch(Base):
    __tablename__ = "job_match"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid4()))
    job_id = Column(String(36), ForeignKey("job.id"), nullable=False, index=True)
    candidate_id = Column(String(36), ForeignKey("candidate.id"), nullable=False, index=True)
    interview_success_rate = Column(Float, nullable=False, default=0.0)
    skill_match_rate = Column(Float, nullable=False, default=0.0)
    title_match_rate = Column(Float, nullable=False, default=0.0)
    experience_match_rate = Column(Float, nullable=False, default=0.0)
    matched_skills_json = Column(Text, nullable=False, default="[]")
    missing_skills_json = Column(Text, nullable=False, default="[]")
    summary = Column(Text, nullable=True)

    creation_datetime = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    modification_datetime = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=True,
        onupdate=lambda: datetime.now(UTC),
    )
