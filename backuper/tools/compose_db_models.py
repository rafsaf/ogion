from pydantic import BaseModel


class ComposeDatabase(BaseModel):
    name: str
    restart: str = "no"
    networks: list[str]
    version: str
    image: str
    environment: list[str]
    ports: list[str]
