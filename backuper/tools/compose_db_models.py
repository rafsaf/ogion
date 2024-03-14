# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from pydantic import BaseModel


class ComposeDatabase(BaseModel):
    name: str
    restart: str = "no"
    networks: list[str]
    version: str
    image: str
    environment: list[str]
    ports: list[str]
