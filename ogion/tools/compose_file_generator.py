# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import json
import logging
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import requests
import yaml

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

try:
    import ogion  # noqa
except ImportError:
    from compose_db_models import ComposeDatabase
    from endoflife_api import (
        EOL_DATA_DIR,
        EOLApiProduct,
        EOLApiProductCycle,
        update_eol_files,
    )
else:
    from ogion.tools.compose_db_models import ComposeDatabase
    from ogion.tools.endoflife_api import (
        EOL_DATA_DIR,
        EOLApiProduct,
        EOLApiProductCycle,
        update_eol_files,
    )

DB_PWD = "password-_-12!@#%^&*()/;><.,]}{["
DB_NAME = "database-_-12!@#%^&*()/;><.,]}{["
DB_USERNAME = "user-_-12!@#%^&*()/;><.,]}{["
DEFAULT_NETWORK = "ogion"
HTTP_OK = 200


def check_docker_image_exists(image_name: str) -> bool:
    """Check if a Docker image exists on Docker Hub."""
    try:
        # Parse image name to get repository and tag
        if ":" in image_name:
            repository, tag = image_name.split(":", 1)
        else:
            repository, tag = image_name, "latest"

        # Docker Hub API endpoint for checking if a tag exists
        url = f"https://registry.hub.docker.com/v2/repositories/library/{repository}/tags/{tag}/"
        log.info(f"Checking {url} for existence of image {image_name}")
        response = requests.get(url, timeout=10)

        response.raise_for_status()
        return response.status_code == HTTP_OK

    except Exception:
        # If there's any error (network, parsing, etc.), assume image doesn't exist
        return False


def get_mariadb_image_tag(cycle_version: str) -> str:
    regular_tag = f"mariadb:{cycle_version}"
    if "pytest" in sys.modules:
        # During tests, skip actual network calls
        return regular_tag

    if check_docker_image_exists(regular_tag):
        log.info(f"Using regular tag: {regular_tag}")
        return regular_tag

    rc_tag = f"mariadb:{cycle_version}-rc"
    if check_docker_image_exists(rc_tag):
        log.info(f"Using RC tag: {rc_tag}")
        return rc_tag

    return regular_tag


def mariadb_db_generator(cycle: EOLApiProductCycle) -> ComposeDatabase:
    host_port = 11000 + int(cycle.cycle.replace(".", ""))
    name = f"ogion_mariadb_{cycle.cycle.replace('.', '_')}"
    image_tag = get_mariadb_image_tag(cycle.cycle)
    compose_db = ComposeDatabase(
        name=name,
        restart="no",
        networks=[DEFAULT_NETWORK],
        version=cycle.cycle,
        image=image_tag,
        ports=[f"{host_port}:3306"],
        environment=[
            f"MARIADB_ROOT_PASSWORD=root-{DB_PWD}",
            f"MARIADB_DATABASE={DB_NAME}",
            f"MARIADB_USER={DB_USERNAME}",
            f"MARIADB_PASSWORD={DB_PWD}",
        ],
    )

    return compose_db


def mysql_db_generator(cycle: EOLApiProductCycle) -> ComposeDatabase:
    host_port = 9000 + int(cycle.cycle.replace(".", ""))
    name = f"ogion_mysql_{cycle.cycle.replace('.', '_')}"
    compose_db = ComposeDatabase(
        name=name,
        restart="no",
        networks=[DEFAULT_NETWORK],
        version=cycle.cycle,
        image=f"mysql:{cycle.cycle}",
        ports=[f"{host_port}:3306"],
        environment=[
            f"MYSQL_ROOT_PASSWORD=root-{DB_PWD}",
            f"MYSQL_DATABASE={DB_NAME}",
            f"MYSQL_USER={DB_USERNAME}",
            f"MYSQL_PASSWORD={DB_PWD}",
        ],
    )

    return compose_db


def postgres_db_generator(cycle: EOLApiProductCycle) -> ComposeDatabase:
    host_port = 10000 + int(cycle.cycle.replace(".", ""))
    name = f"ogion_postgres_{cycle.cycle.replace('.', '_')}"
    compose_db = ComposeDatabase(
        name=name,
        restart="no",
        networks=[DEFAULT_NETWORK],
        version=cycle.cycle,
        image=f"postgres:{cycle.cycle}-bookworm",
        ports=[f"{host_port}:5432"],
        environment=[
            f"POSTGRES_PASSWORD={DB_PWD}",
            f"POSTGRES_DB={DB_NAME}",
            f"POSTGRES_USER={DB_USERNAME}",
        ],
    )

    return compose_db


def handle_file(
    filename: Path,
    cycle_func: Callable[[EOLApiProductCycle], ComposeDatabase],
    omit_cycles: list[str] | None = None,
) -> list[ComposeDatabase]:
    with open(filename) as f:
        product = EOLApiProduct(cycles=json.load(f))

    before_eol_cycles = [cycle for cycle in product.cycles if cycle.before_eol]
    if omit_cycles is not None:
        before_eol_cycles = [
            cycle for cycle in before_eol_cycles if cycle.cycle not in omit_cycles
        ]

    return [cycle_func(cycle) for cycle in before_eol_cycles]


def db_compose_mariadb_data() -> list[ComposeDatabase]:
    return handle_file(EOL_DATA_DIR / "mariadb.json", mariadb_db_generator)


def db_compose_postgresql_data() -> list[ComposeDatabase]:
    return handle_file(EOL_DATA_DIR / "postgresql.json", postgres_db_generator)


def db_compose_mysql_data() -> list[ComposeDatabase]:
    return handle_file(EOL_DATA_DIR / "mysql.json", mysql_db_generator)


if __name__ == "__main__":
    log.info("Generating compose file data...")
    update_eol_files()
    data: dict[str, Any] = {
        "name": "ogion_dbs",
        "services": {},
        "networks": {"ogion": {}},
    }

    compose_data: list[ComposeDatabase] = []
    compose_data += db_compose_mariadb_data()
    compose_data += db_compose_postgresql_data()
    compose_data += db_compose_mysql_data()
    for compose_db_data in compose_data:
        data["services"][compose_db_data.name] = compose_db_data.model_dump(
            exclude={"name", "version"}
        )
    yml_data = yaml.safe_dump(data, indent=2)
    sys.stdout.write(yml_data)
