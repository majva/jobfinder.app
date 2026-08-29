import json
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from src.application.cv.dtos.cv_dto import CandidateResponseDto
from src.core.services.cv.cv_service import CvService
from src.infrastructure.di.inject import inject
from src.infrastructure.models.candidate import Candidate


@inject
class CvController:

    def __init__(self, cv_service: CvService):
        self._cv_service = cv_service

    def api(self):
        router = APIRouter(
            prefix="",
            tags=["CV"],
            responses={404: {"description": "Not found"}},
        )

        @router.post(
            "/upload",
            response_model=CandidateResponseDto,
            status_code=status.HTTP_201_CREATED,
            summary="Upload a CV PDF",
        )
        async def upload_cv(file: UploadFile = File(...)) -> CandidateResponseDto:
            raw = await file.read()
            try:
                candidate = await self._cv_service.upload_async(
                    filename=file.filename or "cv.pdf",
                    content=raw,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return self._to_dto(candidate)

        @router.get(
            "/latest",
            response_model=CandidateResponseDto,
            summary="Get the latest uploaded CV",
        )
        async def latest_cv() -> CandidateResponseDto:
            candidate = await self._cv_service.get_latest_async()
            if candidate is None:
                raise HTTPException(status_code=404, detail="No CV uploaded yet.")
            return self._to_dto(candidate)

        @router.get(
            "/",
            response_model=List[CandidateResponseDto],
            summary="List uploaded CVs",
        )
        async def list_cvs() -> List[CandidateResponseDto]:
            candidates = await self._cv_service.list_async()
            return [self._to_dto(item) for item in candidates]

        return router

    def _to_dto(self, candidate: Candidate) -> CandidateResponseDto:
        return CandidateResponseDto(
            id=candidate.id,
            original_filename=candidate.original_filename,
            full_name=candidate.full_name,
            headline=candidate.headline,
            email=candidate.email,
            phone=candidate.phone,
            location=candidate.location,
            years_experience=candidate.years_experience,
            skills=json.loads(candidate.skills_json or "[]"),
            titles=json.loads(candidate.titles_json or "[]"),
            education=json.loads(candidate.education_json or "[]"),
            suggested_keywords=self._cv_service.suggested_keywords(candidate),
            suggested_tags=self._cv_service.suggested_tags(candidate),
            creation_datetime=candidate.creation_datetime,
        )
