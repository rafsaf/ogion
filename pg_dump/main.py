import logging
import sys

import config

log = logging.getLogger(__name__)
sys.path.insert(0, str(config.BASE_DIR))


if __name__ == "__main__":
    from pg_dump import core

    log.info("Initialize pg_dump...")
    PG_VERSION = core.get_postgres_major_version()
    core.recreate_pgpass_file()
    core.run_pg_dump()
