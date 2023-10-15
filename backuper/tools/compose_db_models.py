from pydantic import BaseModel


class ComposeDatabaseDefinition(BaseModel):
    restart: str = "no"
    networks: list[str]
    image: str
    environment: list[str]
    ports: list[str]


class ComposeDatabase(BaseModel):
    name: ComposeDatabaseDefinition


class ComposeFile(BaseModel):
    services: list[ComposeDatabase]
