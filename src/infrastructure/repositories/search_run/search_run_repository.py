from typing import List

from sqlalchemy import desc, select

from src.infrastructure.context.sql_db.sqlite_dbcontext import SqliteDbContext
from src.infrastructure.di.inject import inject
from src.infrastructure.models.search_run import SearchRun
from src.infrastructure.repositories.base.base_repository import BaseRepository


@inject
class SearchRunRepository(BaseRepository[SearchRun]):

    def __init__(self, db_context: SqliteDbContext):
        super().__init__(db_context=db_context, model=SearchRun)

    async def list_recent_async(self, limit: int = 10) -> List[SearchRun]:
        async with self._db_context.session() as session:
            result = await session.execute(
                select(SearchRun)
                .order_by(desc(SearchRun.creation_datetime))
                .limit(limit)
            )
            return list(result.scalars().all())
