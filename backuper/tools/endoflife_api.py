from pydantic import BaseModel, Field, computed_field
from datetime import datetime, timezone
import requests
import json
from pathlib import Path

API_URL = "https://endoflife.date/api/"
SCRIPT_DIR = Path(__file__).resolve().parent.absolute()
EOL_DATA_DIR = SCRIPT_DIR / "eol_data"


class EOLApiProductCycle(BaseModel):
    cycle: str
    release_date: str = Field(alias="releaseDate")
    eol: str | bool
    latest: str
    link: str | None = None
    support: str | bool | None = None
    discontinued: str | bool | None = None

    @computed_field
    @property
    def valid(self) -> bool:
        now = datetime.now(timezone.utc)
        if isinstance(self.eol, str):
            eol_date = datetime.strptime(self.eol, "%Y-%m-%d").replace(
                tzinfo=timezone.utc, hour=23, minute=59, second=59
            )
            return now < eol_date
        if self.eol:
            return True
        if isinstance(self.support, str):
            support_end = datetime.strptime(self.support, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            return now < support_end
        if self.support:
            return True
        return False


class EOLApiProduct(BaseModel):
    cycles: list[EOLApiProductCycle]


def get_eol_data(product_name: str) -> None:
    res = requests.get(f"{API_URL}{product_name}.json")
    if res.status_code != 200:
        raise ValueError(f"unknown api response: {res.text}")

    api_product = EOLApiProduct(cycles=res.json())
    with open(EOL_DATA_DIR / f"{product_name}.json", "w") as f:
        json.dump(api_product.model_dump(by_alias=True)["cycles"], f, indent=4)


if __name__ == "__main__":
    get_eol_data("mariadb")
    get_eol_data("postgresql")
    get_eol_data("mysql")
