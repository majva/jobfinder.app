from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

JobOutcome = Literal["pending", "passed", "rejected"]


class SearchJobsDto(BaseModel):
    keywords: Optional[List[str]] = Field(default=None, max_length=12)
    country: Optional[str] = Field(default=None, max_length=100)
    city: Optional[str] = Field(default=None, max_length=100)
    remote_only: bool = False
    sponsorship_only: bool = False
    posted_within_days: int = Field(default=30, ge=1, le=90)
    max_jobs: Optional[int] = Field(default=None, ge=1, le=75)


class JobCardDto(BaseModel):
    id: str
    linkedin_job_id: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    url: str
    salary_text: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    workplace_type: str = "unknown"
    sponsorship: str = "unknown"
    relocation: str = "unknown"
    employment_type: Optional[str] = None
    seniority: Optional[str] = None
    posted_at: Optional[str] = None
    is_easy_apply: bool = False
    applied: bool = False
    outcome: JobOutcome = "pending"
    source: str = "linkedin"
    creation_datetime: Optional[str] = None
    interview_success_rate: Optional[float] = None
    skill_match_rate: Optional[float] = None
    title_match_rate: Optional[float] = None
    experience_match_rate: Optional[float] = None
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    candidate_id: Optional[str] = None
    description: Optional[str] = None


class SearchResultDto(BaseModel):
    keywords: str
    country: Optional[str] = None
    city: Optional[str] = None
    location: Optional[str] = None
    jobs_found: int
    jobs: List[JobCardDto]
    hint: Optional[str] = None


class AppliedDto(BaseModel):
    applied: bool = True


class OutcomeDto(BaseModel):
    outcome: JobOutcome = "pending"


class JobPageDto(BaseModel):
    items: List[JobCardDto]
    total: int
    page: int
    page_size: int
    pages: int


class JobStatsDto(BaseModel):
    jobs: int
    remote: int
    hybrid: int
    sponsorship: int
    with_salary: int
    applied: int = 0
    pending: int = 0
    passed: int = 0
    rejected: int = 0
    avg_success: float
    has_cv: bool


class SearchRunDto(BaseModel):
    id: str
    keywords: str
    location: Optional[str] = None
    remote_only: bool
    sponsorship_only: bool
    jobs_found: int
    status: str
    error_message: Optional[str] = None
    creation_datetime: datetime

    class Config:
        from_attributes = True
