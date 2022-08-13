import signal

from pg_dump import config
from pg_dump.main import PgDumpDaemon


def test_pg_dump_daemon():
    daemon = PgDumpDaemon(exit_on_fail=True)
    pg_version = config.settings.PGDUMP_DATABASE_PORT[-2:]
    assert f"postgresql_{pg_version}." in daemon.db_version
    daemon.run()
    assert daemon.healthcheck()
    daemon.exit(sig=signal.SIGTERM, frame=None)
    assert not daemon.healthcheck()
