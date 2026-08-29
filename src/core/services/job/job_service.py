from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from src.core.services.cv.cv_service import CvService
from src.core.services.job.job_analyzer_service import JobAnalyzerService
from src.core.services.job.linkedin_job_client import (
    LinkedInJobClient,
    LinkedInListing,
    LinkedInUnavailableError,
)
from src.core.services.match.match_service import MatchService
from src.infrastructure.di.inject import inject
from src.infrastructure.models.candidate import Candidate
from src.infrastructure.models.job import Job
from src.infrastructure.models.job_match import JobMatch
from src.infrastructure.models.search_run import SearchRun
from src.infrastructure.repositories.job.job_repository import JobRepository
from src.infrastructure.repositories.job_match.job_match_repository import JobMatchRepository
from src.infrastructure.repositories.search_run.search_run_repository import SearchRunRepository


@inject
class JobService:

    def __init__(
        self,
        job_repository: JobRepository,
        job_match_repository: JobMatchRepository,
        search_run_repository: SearchRunRepository,
        cv_service: CvService,
        linkedin_job_client: LinkedInJobClient,
        job_analyzer_service: JobAnalyzerService,
        match_service: MatchService,
    ):
        self._jobs = job_repository
        self._matches = job_match_repository
        self._searches = search_run_repository
        self._cv_service = cv_service
        self._linkedin = linkedin_job_client
        self._analyzer = job_analyzer_service
        self._matcher = match_service

    async def search_async(
        self,
        *,
        keywords: Optional[List[str]] = None,
        country: Optional[str] = None,
        city: Optional[str] = None,
        remote_only: bool = False,
        sponsorship_only: bool = False,
        posted_within_days: int = 30,
        max_jobs: Optional[int] = None,
    ) -> Dict[str, Any]:
        candidate = await self._cv_service.get_latest_async()
        if candidate is None:
            raise ValueError("Upload a CV PDF first so we know what to search for.")

        tags = [item.strip() for item in (keywords or []) if item and item.strip()][:8]
        if not tags:
            tags = self._cv_service.suggested_tags(candidate)[:2]
        query = " OR ".join(tags)
        country_name = (country or "").strip() or None
        city_name = (city or "").strip() or None
        place = self._compose_location(country_name, city_name, candidate.location)

        run = SearchRun(
            candidate_id=candidate.id,
            keywords=query,
            location=place or None,
            remote_only=remote_only,
            sponsorship_only=sponsorship_only,
            jobs_found=0,
            status="running",
        )
        run = await self._searches.insert_async(run)

        try:
            listings = await self._linkedin.search(
                keywords=query,
                location=place,
                remote_only=remote_only,
                posted_within_days=posted_within_days,
                max_jobs=max_jobs,
                sponsorship_only=sponsorship_only,
            )
        except LinkedInUnavailableError as exc:
            run.status = "blocked"
            run.error_message = str(exc)
            await self._searches.update_async(run)
            raise

        saved: List[Dict[str, Any]] = []
        skipped_no_visa = 0
        for listing in listings:
            payload = await self._upsert_listing(listing, candidate)
            job = payload["job"]
            if sponsorship_only and not JobAnalyzerService.helps_immigration(
                job.sponsorship, job.relocation
            ):
                skipped_no_visa += 1
                continue
            saved.append(payload)

        hint = None
        if not listings:
            hint = (
                "LinkedIn returned no listings for those tags and place. "
                "Try fewer tags or leave city empty to search the whole country."
            )
        elif sponsorship_only and listings and not saved:
            hint = (
                f"Found {len(listings)} roles, but none clearly offer visa or work-permit "
                "sponsorship. A 'must relocate' line is not the same thing. "
                "Turn Visa sponsorship off to see every listing."
            )
        elif sponsorship_only and skipped_no_visa:
            hint = (
                f"Kept {len(saved)} visa-sponsorship roles and hid {skipped_no_visa} "
                "that do not mention a work visa or work permit."
            )

        run.status = "ok"
        run.jobs_found = len(saved)
        run.error_message = hint
        await self._searches.update_async(run)

        return {
            "search": run,
            "keywords": query,
            "country": country_name,
            "city": city_name,
            "location": place,
            "jobs": [self.to_card(item["job"], item["match"], candidate) for item in saved],
            "hint": hint,
        }

    @staticmethod
    def _compose_location(
        country: Optional[str],
        city: Optional[str],
        fallback: Optional[str] = None,
    ) -> Optional[str]:
        country_name = JobService._usable_location(country)
        city_name = JobService._usable_location(city)
        if city_name and country_name:
            return f"{city_name}, {country_name}"
        if country_name:
            return country_name
        if city_name:
            return city_name
        return JobService._usable_location(fallback)

    @staticmethod
    def _usable_location(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        place = " ".join(value.strip().split())
        if not place or "@" in place or len(place) > 80 or place.count(",") > 3:
            return None
        return place

    async def list_async(
        self,
        *,
        workplace_type: Optional[str] = None,
        sponsorship: Optional[str] = None,
        relocation: Optional[str] = None,
        has_salary: Optional[bool] = None,
        query: Optional[str] = None,
        min_success: Optional[float] = None,
        immigration_only: bool = False,
        applied: Optional[bool] = None,
        sort: str = "success",
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        cards = await self._sorted_cards(
            workplace_type=workplace_type,
            sponsorship=sponsorship,
            relocation=relocation,
            has_salary=has_salary,
            query=query,
            min_success=min_success,
            immigration_only=immigration_only,
            applied=applied,
            sort=sort,
        )
        total = len(cards)
        page_size = max(1, min(page_size, 50))
        pages = max(1, (total + page_size - 1) // page_size) if total else 1
        page = min(max(1, page), pages)
        start = (page - 1) * page_size
        return {
            "items": cards[start:start + page_size],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
        }

    async def _sorted_cards(
        self,
        *,
        workplace_type: Optional[str] = None,
        sponsorship: Optional[str] = None,
        relocation: Optional[str] = None,
        has_salary: Optional[bool] = None,
        query: Optional[str] = None,
        min_success: Optional[float] = None,
        immigration_only: bool = False,
        applied: Optional[bool] = None,
        sort: str = "success",
    ) -> List[Dict[str, Any]]:
        candidate = await self._cv_service.get_latest_async()
        jobs = await self._jobs.list_filtered_async(
            workplace_type=workplace_type,
            sponsorship="yes" if immigration_only else sponsorship,
            relocation=relocation,
            has_salary=has_salary,
            query=query,
            applied=applied,
        )
        match_map = {}
        if candidate:
            match_map = await self._matches.map_for_candidate_async(candidate.id)

        cards = [self.to_card(job, match_map.get(job.id), candidate) for job in jobs]
        if immigration_only:
            cards = [
                card for card in cards
                if JobAnalyzerService.helps_immigration(
                    card.get("sponsorship") or "unknown",
                    card.get("relocation") or "unknown",
                )
            ]
        if min_success is not None:
            cards = [
                card for card in cards
                if (card.get("interview_success_rate") or 0) >= min_success
            ]
        if sort == "salary":
            cards.sort(key=lambda c: c.get("salary_max") or c.get("salary_min") or 0, reverse=True)
        elif sort == "recent":
            cards.sort(key=lambda c: c.get("creation_datetime") or "", reverse=True)
        else:
            cards.sort(key=lambda c: c.get("interview_success_rate") or 0, reverse=True)
        return cards

    async def get_async(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = await self._jobs.get_by_id_async(job_id)
        if job is None:
            return None
        candidate = await self._cv_service.get_latest_async()
        match = None
        if candidate:
            match = await self._matches.get_by_job_and_candidate_async(job.id, candidate.id)
        return self.to_card(job, match, candidate, include_description=True)

    async def set_applied_async(self, job_id: str, applied: bool) -> Optional[Dict[str, Any]]:
        job = await self._jobs.get_by_id_async(job_id)
        if job is None:
            return None
        job.applied = applied
        job.modification_datetime = datetime.now(UTC)
        job = await self._jobs.update_async(job)
        candidate = await self._cv_service.get_latest_async()
        match = None
        if candidate:
            match = await self._matches.get_by_job_and_candidate_async(job.id, candidate.id)
        return self.to_card(job, match, candidate)

    async def delete_async(self, job_id: str) -> bool:
        await self._matches.delete_for_job_async(job_id)
        return await self._jobs.delete_async(job_id)

    async def stats_async(self, applied: Optional[bool] = None) -> Dict[str, Any]:
        cards = await self._sorted_cards(applied=applied)
        candidate = await self._cv_service.get_latest_async()
        rates = [c["interview_success_rate"] for c in cards if c.get("interview_success_rate") is not None]
        return {
            "jobs": len(cards),
            "remote": sum(1 for c in cards if c.get("workplace_type") == "remote"),
            "hybrid": sum(1 for c in cards if c.get("workplace_type") == "hybrid"),
            "sponsorship": sum(1 for c in cards if c.get("sponsorship") == "yes"),
            "with_salary": sum(1 for c in cards if c.get("salary_text")),
            "applied": sum(1 for c in cards if c.get("applied")),
            "avg_success": round(sum(rates) / len(rates), 1) if rates else 0,
            "has_cv": candidate is not None,
        }

    async def recent_searches_async(self) -> List[SearchRun]:
        return await self._searches.list_recent_async(8)

    async def _upsert_listing(
        self, listing: LinkedInListing, candidate: Candidate
    ) -> Dict[str, Any]:
        analysis = self._analyzer.analyze({
            "title": listing.title,
            "company": listing.company,
            "location": listing.location,
            "description": listing.description,
            "salary_hint": listing.salary_hint,
            "workplace_hint": listing.workplace_hint or listing.extra.get("criteria"),
        })
        existing = await self._jobs.get_by_linkedin_id_async(listing.linkedin_job_id)
        job = existing or Job(linkedin_job_id=listing.linkedin_job_id)
        job.title = listing.title
        job.company = listing.company
        job.location = listing.location
        job.description = listing.description or (existing.description if existing else "")
        job.url = listing.url
        job.salary_text = analysis["salary_text"]
        job.salary_min = analysis["salary_min"]
        job.salary_max = analysis["salary_max"]
        job.workplace_type = analysis["workplace_type"]
        job.sponsorship = analysis["sponsorship"]
        job.relocation = analysis["relocation"]
        job.employment_type = analysis["employment_type"]
        job.seniority = analysis["seniority"]
        job.posted_at = listing.posted_at
        job.is_easy_apply = listing.is_easy_apply
        job.source = "linkedin"
        job.modification_datetime = datetime.now(UTC)
        if existing is None:
            job.applied = False

        if existing:
            job = await self._jobs.update_async(job)
        else:
            job = await self._jobs.insert_async(job)

        score = self._matcher.score(
            candidate,
            job,
            required_skills=analysis["required_skills"],
            required_years=analysis["required_years"],
        )
        match = await self._matches.get_by_job_and_candidate_async(job.id, candidate.id)
        if match is None:
            match = JobMatch(job_id=job.id, candidate_id=candidate.id)
        match.interview_success_rate = score.interview_success_rate
        match.skill_match_rate = score.skill_match_rate
        match.title_match_rate = score.title_match_rate
        match.experience_match_rate = score.experience_match_rate
        match.matched_skills_json = json.dumps(score.matched_skills)
        match.missing_skills_json = json.dumps(score.missing_skills)
        match.summary = score.summary
        match.modification_datetime = datetime.now(UTC)
        if match.id:
            match = await self._matches.update_async(match)
        else:
            match = await self._matches.insert_async(match)

        return {"job": job, "match": match}

    def to_card(
        self,
        job: Job,
        match: Optional[JobMatch],
        candidate: Optional[Candidate],
        include_description: bool = False,
    ) -> Dict[str, Any]:
        card: Dict[str, Any] = {
            "id": job.id,
            "linkedin_job_id": job.linkedin_job_id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": job.url,
            "salary_text": job.salary_text,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "workplace_type": job.workplace_type,
            "sponsorship": job.sponsorship,
            "relocation": job.relocation,
            "employment_type": job.employment_type,
            "seniority": job.seniority,
            "posted_at": job.posted_at,
            "is_easy_apply": job.is_easy_apply,
            "applied": bool(job.applied),
            "source": job.source,
            "creation_datetime": job.creation_datetime.isoformat() if job.creation_datetime else None,
            "interview_success_rate": match.interview_success_rate if match else None,
            "skill_match_rate": match.skill_match_rate if match else None,
            "title_match_rate": match.title_match_rate if match else None,
            "experience_match_rate": match.experience_match_rate if match else None,
            "matched_skills": json.loads(match.matched_skills_json) if match else [],
            "missing_skills": json.loads(match.missing_skills_json) if match else [],
            "summary": match.summary if match else None,
            "candidate_id": candidate.id if candidate else None,
        }
        if include_description:
            card["description"] = job.description
        return card
