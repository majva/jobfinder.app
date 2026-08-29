from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import List, Optional

from src.core.services.cv.skill_catalog import SKILL_CATALOG
from src.infrastructure.di.inject import inject
from src.infrastructure.models.candidate import Candidate
from src.infrastructure.models.job import Job


@dataclass
class MatchResult:
    interview_success_rate: float
    skill_match_rate: float
    title_match_rate: float
    experience_match_rate: float
    matched_skills: List[str]
    missing_skills: List[str]
    summary: str


@inject
class MatchService:

    def score(
        self,
        candidate: Candidate,
        job: Job,
        required_skills: Optional[List[str]] = None,
        required_years: Optional[int] = None,
    ) -> MatchResult:
        cv_skills = [s.lower() for s in json.loads(candidate.skills_json or "[]")]
        cv_titles = [t.lower() for t in json.loads(candidate.titles_json or "[]")]
        job_skills = [s.lower() for s in (required_skills or [])]
        if not job_skills:
            job_skills = self._skills_from_text(f"{job.title} {job.description}")

        matched = sorted({s for s in job_skills if s in cv_skills})
        missing = sorted({s for s in job_skills if s not in cv_skills})[:12]
        skill_rate = self._ratio(len(matched), max(len(job_skills), 1))
        if not job_skills:
            skill_rate = 35.0

        title_rate = self._title_rate(cv_titles, candidate.headline, job.title)
        exp_rate = self._experience_rate(candidate.years_experience, required_years)
        location_bonus = self._location_bonus(candidate.location, job)

        interview = (
            skill_rate * 0.45
            + title_rate * 0.25
            + exp_rate * 0.15
            + location_bonus * 0.15
        )
        interview = max(8.0, min(96.0, round(interview, 1)))

        summary = self._summary(interview, matched, missing, job)
        return MatchResult(
            interview_success_rate=interview,
            skill_match_rate=round(skill_rate, 1),
            title_match_rate=round(title_rate, 1),
            experience_match_rate=round(exp_rate, 1),
            matched_skills=matched[:16],
            missing_skills=missing,
            summary=summary,
        )

    def _title_rate(
        self, cv_titles: List[str], headline: Optional[str], job_title: str
    ) -> float:
        job_l = (job_title or "").lower()
        haystack = cv_titles + [((headline or "").lower())]
        if any(title and title in job_l or job_l in title for title in haystack if title):
            return 92.0
        tokens = {t for t in re.split(r"\W+", job_l) if len(t) > 3}
        cv_tokens = set()
        for item in haystack:
            cv_tokens.update(t for t in re.split(r"\W+", item) if len(t) > 3)
        if not tokens:
            return 40.0
        overlap = tokens & cv_tokens
        return min(90.0, 20.0 + 70.0 * (len(overlap) / max(len(tokens), 1)))

    def _experience_rate(self, years: Optional[int], required: Optional[int]) -> float:
        if years is None and required is None:
            return 55.0
        if required is None:
            return 70.0
        if years is None:
            return 40.0
        if years >= required:
            return 90.0
        gap = required - years
        return max(20.0, 90.0 - gap * 18.0)

    def _location_bonus(self, candidate_location: Optional[str], job: Job) -> float:
        if job.workplace_type == "remote":
            return 90.0
        if job.workplace_type == "hybrid":
            return 70.0
        cand = (candidate_location or "").lower()
        job_loc = (job.location or "").lower()
        if cand and job_loc and (cand in job_loc or job_loc in cand):
            return 85.0
        if job.relocation in {"offered", "required"}:
            return 60.0
        return 40.0

    def _summary(
        self,
        interview: float,
        matched: List[str],
        missing: List[str],
        job: Job,
    ) -> str:
        if interview >= 80:
            tone = "Strong interview outlook"
        elif interview >= 60:
            tone = "Solid chance — worth applying"
        elif interview >= 40:
            tone = "Stretch role — fill a few gaps first"
        else:
            tone = "Weak match on paper"
        bits = [tone]
        if matched:
            bits.append(f"overlapping skills: {', '.join(matched[:5])}")
        if missing:
            bits.append(f"likely gaps: {', '.join(missing[:4])}")
        if job.sponsorship == "yes":
            bits.append("mentions visa sponsorship")
        elif job.sponsorship == "no":
            bits.append("does not sponsor")
        return ". ".join(bits) + "."

    def _skills_from_text(self, text: str) -> List[str]:
        lowered = (text or "").lower()
        found = []
        for skill in SKILL_CATALOG:
            pattern = r"(?<![a-z0-9])" + re.escape(skill) + r"(?![a-z0-9])"
            if re.search(pattern, lowered):
                found.append(skill)
        return found[:30]

    @staticmethod
    def _ratio(num: int, den: int) -> float:
        if den <= 0:
            return 0.0
        return 100.0 * num / den
