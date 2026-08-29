from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from src.infrastructure.context.sql_db.sqlite_dbcontext import Base


class Candidate(Base):
    __tablename__ = "candidate"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid4()))
    original_filename = Column(String(255), nullable=False)
    stored_path = Column(String(500), nullable=False)
    raw_text = Column(Text, nullable=False, default="")
    full_name = Column(String(200), nullable=True)
    headline = Column(String(300), nullable=True)
    email = Column(String(200), nullable=True)
    phone = Column(String(80), nullable=True)
    location = Column(String(200), nullable=True)
    years_experience = Column(Integer, nullable=True)
    skills_json = Column(Text, nullable=False, default="[]")
    titles_json = Column(Text, nullable=False, default="[]")
    education_json = Column(Text, nullable=False, default="[]")

    creation_datetime = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
