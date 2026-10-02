from typing import List, Optional

from sqlalchemy import and_, desc, select

from src.infrastructure.context.sql_db.sqlite_dbcontext import SqliteDbContext
from src.infrastructure.di.inject import inject
from src.infrastructure.models.job import Job
from src.infrastructure.repositories.base.base_repository import BaseRepository


@inject
class JobRepository(BaseRepository[Job]):

    def __init__(self, db_context: SqliteDbContext):
        super().__init__(db_context=db_context, model=Job)

    async def get_by_linkedin_id_async(self, linkedin_job_id: str) -> Optional[Job]:
        async with self._db_context.session() as session:
            result = await session.execute(
                select(Job).where(Job.linkedin_job_id == linkedin_job_id)
            )
            return result.scalar_one_or_none()

    async def list_filtered_async(
        self,
        *,
        workplace_type: Optional[str] = None,
        sponsorship: Optional[str] = None,
        relocation: Optional[str] = None,
        has_salary: Optional[bool] = None,
        query: Optional[str] = None,
        applied: Optional[bool] = None,
        outcome: Optional[str] = None,
    ) -> List[Job]:
        async with self._db_context.session() as session:
            stmt = select(Job)
            conditions = []
            if workplace_type:
                conditions.append(Job.workplace_type == workplace_type)
            if sponsorship:
                conditions.append(Job.sponsorship == sponsorship)
            if relocation:
                conditions.append(Job.relocation == relocation)
            if applied is True:
                conditions.append(Job.applied.is_(True))
            elif applied is False:
                conditions.append(Job.applied.is_(False))
            if outcome:
                conditions.append(Job.outcome == outcome)
            if has_salary is True:
                conditions.append(Job.salary_text.is_not(None))
            if query:
                like = f"%{query.strip()}%"
                conditions.append(
                    Job.title.ilike(like)
                    | Job.company.ilike(like)
                    | Job.location.ilike(like)
                )
            if conditions:
                stmt = stmt.where(and_(*conditions))
            stmt = stmt.order_by(desc(Job.creation_datetime))
            result = await session.execute(stmt)
            return list(result.scalars().all())
