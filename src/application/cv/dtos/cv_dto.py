from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CandidateResponseDto(BaseModel):
    id: str
    original_filename: str
    full_name: Optional[str] = None
    headline: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    years_experience: Optional[int] = None
    skills: List[str] = Field(default_factory=list)
    titles: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
    suggested_keywords: Optional[str] = None
    suggested_tags: List[str] = Field(default_factory=list)
    creation_datetime: datetime

    class Config:
        from_attributes = True
