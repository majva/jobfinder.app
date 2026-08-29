"""
JobFinder entry point.
"""

import asyncio
from os import path as os_path
from sys import path as sys_path, exit as sys_exit

sys_path.append(os_path.dirname(os_path.dirname(os_path.dirname(os_path.abspath(__file__)))))

from src.application.web import WebService
from src.infrastructure.context.sql_db.sqlite_dbcontext import SqliteDbContext
from src.infrastructure.di.bootstrap import bootstrap_di
from src.infrastructure.di.inject import resolve


class App:

    def start_up(self):
        bootstrap_di()
        db = resolve(SqliteDbContext)
        asyncio.run(db.ensure_schema())
        resolve(WebService).start()


if __name__ == "__main__":
    try:
        App().start_up()
    except KeyboardInterrupt:
        print("[-] Somebody stop the service ...")
        sys_exit(0)
