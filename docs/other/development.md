# Development

General knowledge of Git, Python and Docker is assumed.

## Requirements

- Python 3.11
- Poetry [https://python-poetry.org/](https://python-poetry.org/)
- Docker and docker compose plugin [https://docs.docker.com/get-docker/](https://docs.docker.com/get-docker/)
- Debian/Ubuntu

## Setup steps

1. Install python dependencies

    `poetry install`

2. Create `.env` file

    `cp .env.example .env`

3. To run database backups, you will need mariadb-client and postgresql-client installed and copied good version of 7zip (arm64 or amd64) from bin folder, there are dedicated scripts in folder `script` that does that.

4. Setup databases

    `docker compose up -d postgres_15 postgres_14 postgres_13 postgres_12 postgres_11 mysql_57 mysql_80 mariadb_1011 mariadb_1006 mariadb_1005 mariadb_1004`

5. You can run backup and pytest tests (--single to make all backups immediatly and then exit)

    `python -m backuper.main --single`

    `pytest`

## Docs

To play with documentation, after dependencies are in place installed with poetry:

`mkdocs serve` will start development server.

## Docs release

Mike is used for docs versioning: [https://github.com/jimporter/mike](https://github.com/jimporter/mike)

After new release is triggered, manual command needs to be run (eg. tag 0.1) and then generated commit pushed to origin:

```bash
mike deploy --push --update-aliases 0.1 latest
```

<br>
<br>
