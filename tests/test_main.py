import signal

from pg_dump.config import settings
from pg_dump.main import PgDumpDaemon


def test_pg_dump_daemon():
    daemon = PgDumpDaemon()
    pg_version = settings.PD_DATABASE_PORT[-2:]
    assert f"postgresql_{pg_version}." in settings.PRIV_PD_DB_VERSION
    daemon.run()
    assert daemon.healthcheck()
    daemon.exit(sig=signal.SIGTERM, frame=None)
    assert not daemon.healthcheck()
