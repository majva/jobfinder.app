from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.application.job.dtos.job_dto import (
    AppliedDto,
    JobCardDto,
    JobPageDto,
    JobStatsDto,
    SearchJobsDto,
    SearchResultDto,
    SearchRunDto,
)
from src.core.services.job.linkedin_job_client import LinkedInUnavailableError
from src.core.services.job.job_service import JobService
from src.infrastructure.di.inject import inject


@inject
class JobController:

    def __init__(self, job_service: JobService):
        self._job_service = job_service

    def api(self):
        router = APIRouter(
            prefix="",
            tags=["Jobs"],
            responses={404: {"description": "Not found"}},
        )

        @router.post(
            "/search",
            response_model=SearchResultDto,
            summary="Search LinkedIn using the latest CV",
        )
        async def search_jobs(payload: SearchJobsDto) -> SearchResultDto:
            try:
                result = await self._job_service.search_async(
                    keywords=payload.keywords,
                    country=payload.country,
                    city=payload.city,
                    remote_only=payload.remote_only,
                    sponsorship_only=payload.sponsorship_only,
                    posted_within_days=payload.posted_within_days,
                    max_jobs=payload.max_jobs,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            except LinkedInUnavailableError as exc:
                raise HTTPException(status_code=503, detail=str(exc)) from exc
            return SearchResultDto(
                keywords=result["keywords"],
                country=result.get("country"),
                city=result.get("city"),
                location=result["location"],
                jobs_found=len(result["jobs"]),
                jobs=[JobCardDto.model_validate(item) for item in result["jobs"]],
                hint=result.get("hint"),
            )

        @router.get(
            "/",
            response_model=JobPageDto,
            summary="List stored jobs",
        )
        async def list_jobs(
            workplace_type: Optional[str] = None,
            sponsorship: Optional[str] = None,
            relocation: Optional[str] = None,
            has_salary: Optional[bool] = None,
            query: Optional[str] = None,
            min_success: Optional[float] = Query(default=None, ge=0, le=100),
            immigration_only: bool = False,
            applied: Optional[bool] = None,
            sort: str = Query(default="success"),
            page: int = Query(default=1, ge=1),
            page_size: int = Query(default=10, ge=5, le=50),
        ) -> JobPageDto:
            result = await self._job_service.list_async(
                workplace_type=workplace_type,
                sponsorship=sponsorship,
                relocation=relocation,
                has_salary=has_salary,
                query=query,
                min_success=min_success,
                immigration_only=immigration_only,
                applied=applied,
                sort=sort,
                page=page,
                page_size=page_size,
            )
            return JobPageDto(
                items=[JobCardDto.model_validate(item) for item in result["items"]],
                total=result["total"],
                page=result["page"],
                page_size=result["page_size"],
                pages=result["pages"],
            )

        @router.get(
            "/stats",
            response_model=JobStatsDto,
            summary="Dashboard counters",
        )
        async def stats(applied: Optional[bool] = None) -> JobStatsDto:
            return JobStatsDto.model_validate(
                await self._job_service.stats_async(applied=applied)
            )

        @router.get(
            "/searches",
            response_model=List[SearchRunDto],
            summary="Recent searches",
        )
        async def searches() -> List[SearchRunDto]:
            runs = await self._job_service.recent_searches_async()
            return [SearchRunDto.model_validate(run) for run in runs]

        @router.post(
            "/{job_id}/applied",
            response_model=JobCardDto,
            summary="Mark a job as applied",
        )
        async def mark_applied(job_id: str, payload: AppliedDto) -> JobCardDto:
            card = await self._job_service.set_applied_async(job_id, payload.applied)
            if card is None:
                raise HTTPException(status_code=404, detail="Job not found.")
            return JobCardDto.model_validate(card)

        @router.get(
            "/{job_id}",
            response_model=JobCardDto,
            summary="Job detail",
        )
        async def get_job(job_id: str) -> JobCardDto:
            card = await self._job_service.get_async(job_id)
            if card is None:
                raise HTTPException(status_code=404, detail="Job not found.")
            return JobCardDto.model_validate(card)

        @router.delete(
            "/{job_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary="Remove a stored job",
        )
        async def delete_job(job_id: str) -> None:
            deleted = await self._job_service.delete_async(job_id)
            if not deleted:
                raise HTTPException(status_code=404, detail="Job not found.")

        return router
