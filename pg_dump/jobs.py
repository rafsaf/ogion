import logging
from datetime import datetime

from pg_dump import core

log = logging.getLogger(__name__)


class PgDumpJob:
    def __init__(self, start: datetime, db_version: str) -> None:
        self.start = start
        self.retries = 0
        self.db_version = db_version
        self.foldername = self.get_current_foldername()

    def get_current_foldername(self):
        return core.get_new_backup_foldername(
            now=datetime.utcnow(), db_version=self.db_version
        )
