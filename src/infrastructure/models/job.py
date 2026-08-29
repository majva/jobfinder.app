from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from src.infrastructure.context.sql_db.sqlite_dbcontext import Base


class Job(Base):
    __tablename__ = "job"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid4()))
    linkedin_job_id = Column(String(64), nullable=False, unique=True, index=True)
    title = Column(String(300), nullable=False)
    company = Column(String(200), nullable=True)
    location = Column(String(200), nullable=True)
    description = Column(Text, nullable=False, default="")
    url = Column(String(700), nullable=False)
    salary_text = Column(String(200), nullable=True)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    workplace_type = Column(String(40), nullable=False, default="unknown")
    sponsorship = Column(String(20), nullable=False, default="unknown")
    relocation = Column(String(20), nullable=False, default="unknown")
    employment_type = Column(String(40), nullable=True)
    seniority = Column(String(40), nullable=True)
    posted_at = Column(String(80), nullable=True)
    is_easy_apply = Column(Boolean, nullable=False, default=False)
    applied = Column(Boolean, nullable=False, default=False)
    source = Column(String(40), nullable=False, default="linkedin")

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
