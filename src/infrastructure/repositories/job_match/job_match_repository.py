from typing import Dict, List, Optional

from sqlalchemy import desc, select

from src.infrastructure.context.sql_db.sqlite_dbcontext import SqliteDbContext
from src.infrastructure.di.inject import inject
from src.infrastructure.models.job_match import JobMatch
from src.infrastructure.repositories.base.base_repository import BaseRepository


@inject
class JobMatchRepository(BaseRepository[JobMatch]):

    def __init__(self, db_context: SqliteDbContext):
        super().__init__(db_context=db_context, model=JobMatch)

    async def get_by_job_and_candidate_async(
        self, job_id: str, candidate_id: str
    ) -> Optional[JobMatch]:
        async with self._db_context.session() as session:
            result = await session.execute(
                select(JobMatch).where(
                    JobMatch.job_id == job_id,
                    JobMatch.candidate_id == candidate_id,
                )
            )
            return result.scalar_one_or_none()

    async def map_for_candidate_async(self, candidate_id: str) -> Dict[str, JobMatch]:
        async with self._db_context.session() as session:
            result = await session.execute(
                select(JobMatch)
                .where(JobMatch.candidate_id == candidate_id)
                .order_by(desc(JobMatch.modification_datetime))
            )
            matches = list(result.scalars().all())
            mapped: Dict[str, JobMatch] = {}
            for match in matches:
                mapped.setdefault(match.job_id, match)
            return mapped

    async def list_for_candidate_async(self, candidate_id: str) -> List[JobMatch]:
        async with self._db_context.session() as session:
            result = await session.execute(
                select(JobMatch)
                .where(JobMatch.candidate_id == candidate_id)
                .order_by(desc(JobMatch.interview_success_rate))
            )
            return list(result.scalars().all())

    async def delete_for_job_async(self, job_id: str) -> None:
        async with self._db_context.session() as session:
            result = await session.execute(
                select(JobMatch).where(JobMatch.job_id == job_id)
            )
            for entity in result.scalars().all():
                await session.delete(entity)
            await session.commit()
