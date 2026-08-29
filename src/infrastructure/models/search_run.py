from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from src.infrastructure.context.sql_db.sqlite_dbcontext import Base


class SearchRun(Base):
    __tablename__ = "search_run"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid4()))
    candidate_id = Column(String(36), nullable=True, index=True)
    keywords = Column(String(400), nullable=False, default="")
    location = Column(String(200), nullable=True)
    remote_only = Column(Boolean, nullable=False, default=False)
    sponsorship_only = Column(Boolean, nullable=False, default=False)
    jobs_found = Column(Integer, nullable=False, default=0)
    status = Column(String(40), nullable=False, default="ok")
    error_message = Column(Text, nullable=True)

    creation_datetime = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
