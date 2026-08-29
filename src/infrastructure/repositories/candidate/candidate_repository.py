from typing import Optional

from sqlalchemy import desc, select

from src.infrastructure.context.sql_db.sqlite_dbcontext import SqliteDbContext
from src.infrastructure.di.inject import inject
from src.infrastructure.models.candidate import Candidate
from src.infrastructure.repositories.base.base_repository import BaseRepository


@inject
class CandidateRepository(BaseRepository[Candidate]):

    def __init__(self, db_context: SqliteDbContext):
        super().__init__(db_context=db_context, model=Candidate)

    async def get_latest_async(self) -> Optional[Candidate]:
        async with self._db_context.session() as session:
            result = await session.execute(
                select(Candidate).order_by(desc(Candidate.creation_datetime)).limit(1)
            )
            return result.scalar_one_or_none()
