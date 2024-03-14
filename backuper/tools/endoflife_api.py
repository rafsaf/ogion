# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import json
from datetime import UTC, datetime
from pathlib import Path

import requests
from pydantic import BaseModel, Field, computed_field

API_URL = "https://endoflife.date/api/"
SCRIPT_DIR = Path(__file__).resolve().parent.absolute()
EOL_DATA_DIR = SCRIPT_DIR / "eol_data"
STATUS_200 = 200


class EOLApiProductCycle(BaseModel):
    cycle: str
    release_date: str = Field(alias="releaseDate")
    eol: str | bool
    latest: str
    link: str | None = None
    support: str | bool | None = None
    discontinued: str | bool | None = None

    @computed_field  # type: ignore[misc]
    @property
    def before_eol(self) -> bool:
        now = datetime.now(UTC)
        if isinstance(self.eol, str):
            eol_date = datetime.strptime(self.eol, "%Y-%m-%d").replace(
                tzinfo=UTC, hour=23, minute=59, second=59
            )
            return now < eol_date
        if self.eol:
            return True
        if isinstance(self.support, str):
            support_end = datetime.strptime(self.support, "%Y-%m-%d").replace(
                tzinfo=UTC
            )
            return now < support_end
        if self.support:
            return True
        return False


class EOLApiProduct(BaseModel):
    cycles: list[EOLApiProductCycle]


def get_eol_data(product_name: str) -> None:
    res = requests.get(f"{API_URL}{product_name}.json")
    if res.status_code != STATUS_200:
        raise ValueError(f"unknown api response: {res.text}")

    api_product = EOLApiProduct(cycles=res.json())
    with open(EOL_DATA_DIR / f"{product_name}.json", "w") as f:
        json.dump(api_product.model_dump(by_alias=True)["cycles"], f, indent=4)


def update_eol_files() -> None:
    get_eol_data("mariadb")
    get_eol_data("postgresql")
    get_eol_data("mysql")


if __name__ == "__main__":
    update_eol_files()
