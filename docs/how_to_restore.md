# How to restore

To restore backups you already have in cloud, for sure you will need `age` to extract the archive (and of course you age private key matching one of those in `AGE_RECIPIENTS` used for creating it in a first place). That step is ommited below.

For below databases restore, you can for sure use `ogion` image itself (as it already has required software installed, for restore also, and must have network access to database). Tricky part can be "how to deliver age backup file to ogion container". This is also true for transporting it anywhere. Usual way is to use `scp` and for containers for docker compose and kubernetes respectively `docker compose cp` and `kubectl cp`.

Other idea if you feel unhappy with passing your database backups around (even if password protected) would be to make the backup file public for a moment and available to download and use tools like `curl` to download it on destination place. If leaked, there is yet very strong cryptography to protect you. This should be sufficient for bunch of projects.

## Directory and single file

Just file or directory, copy them back where you want.

## PostgreSQL

Backup is made using `pg_dump` ([see def \_backup() params](https://github.com/rafsaf/ogion/blob/main/ogion/backup_targets/postgresql.py)). To restore database, you will need `psql` [https://www.postgresql.org/docs/current/app-psql.html](https://www.postgresql.org/docs/current/app-psql.html) and network access to database. If on debian/ubuntu, this is provided by apt package `postgresql-client`.

Follow docs (ogion creates typical SQL file backups, nothing special about them), but command will look something like that:

```bash
psql -h localhost -p 5432 -U postgres database_name -W < backup_file.sql
```

## MariaDB

Backup is made using `mariadb-dump` ([see def \_backup() params](https://github.com/rafsaf/ogion/blob/main/ogion/backup_targets/mariadb.py)). To restore database, you will need `mariadb` [https://mariadb.com/kb/en/mariadb-command-line-client/](https://mariadb.com/kb/en/mariadb-command-line-client/) and network access to database. If on debian/ubuntu, this is provided by apt package [https://mariadb.com/kb/en/mariadb-package-repository-setup-and-usage/](https://mariadb.com/kb/en/mariadb-package-repository-setup-and-usage/).

Follow docs (ogion creates typical SQL file backups, nothing special about them), but command will look something like that:

```bash
mariadb -h localhost -P 3306 -u root -p database_name < backup_file.sql
```

<br>
<br>
