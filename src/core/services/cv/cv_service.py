from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from src.core.services.cv.cv_parser_service import CvParserService
from src.infrastructure.di.inject import inject
from src.infrastructure.models.candidate import Candidate
from src.infrastructure.repositories.candidate.candidate_repository import CandidateRepository
from src.infrastructure.utils.config_reader import ConfigReader


@inject
class CvService:

    def __init__(
        self,
        candidate_repository: CandidateRepository,
        cv_parser_service: CvParserService,
        config_reader: ConfigReader,
    ):
        self._repository = candidate_repository
        self._parser = cv_parser_service
        self._config = config_reader

    async def upload_async(self, filename: str, content: bytes) -> Candidate:
        if not filename.lower().endswith(".pdf"):
            raise ValueError("Only PDF CVs are supported.")

        max_mb = int(self._config.get("uploads.max_mb", 10))
        if len(content) > max_mb * 1024 * 1024:
            raise ValueError(f"CV is larger than {max_mb} MB.")

        raw_text = self._parser.extract_text(content)
        if len(raw_text.strip()) < 40:
            raise ValueError(
                "Could not read enough text from this PDF. "
                "Use a text-based CV rather than a scanned image."
            )

        parsed = self._parser.parse(raw_text)
        stored_path = self._store_file(filename, content)

        candidate = Candidate(
            original_filename=filename,
            stored_path=str(stored_path),
            raw_text=raw_text,
            full_name=parsed.get("full_name"),
            headline=parsed.get("headline"),
            email=parsed.get("email"),
            phone=parsed.get("phone"),
            location=parsed.get("location"),
            years_experience=parsed.get("years_experience"),
            skills_json=json.dumps(parsed.get("skills") or []),
            titles_json=json.dumps(parsed.get("titles") or []),
            education_json=json.dumps(parsed.get("education") or []),
        )
        return await self._repository.insert_async(candidate)

    async def get_latest_async(self) -> Optional[Candidate]:
        return await self._repository.get_latest_async()

    async def get_by_id_async(self, candidate_id: str) -> Optional[Candidate]:
        return await self._repository.get_by_id_async(candidate_id)

    async def list_async(self) -> List[Candidate]:
        return await self._repository.get_all_async()

    def _parsed_from_candidate(self, candidate: Candidate) -> dict:
        return {
            "titles": json.loads(candidate.titles_json or "[]"),
            "skills": json.loads(candidate.skills_json or "[]"),
            "headline": candidate.headline,
        }

    def suggested_keywords(self, candidate: Candidate) -> str:
        return self._parser.suggested_keywords(self._parsed_from_candidate(candidate))

    def suggested_tags(self, candidate: Candidate) -> List[str]:
        return self._parser.suggested_tags(self._parsed_from_candidate(candidate))

    def _store_file(self, filename: str, content: bytes) -> Path:
        upload_dir = Path(self._config.get("uploads.dir", "./data/uploads"))
        if not upload_dir.is_absolute():
            upload_dir = self._config.get_project_root() / upload_dir
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(filename).name.replace(" ", "_")
        path = upload_dir / f"{uuid4().hex}_{safe_name}"
        path.write_bytes(content)
        return path
