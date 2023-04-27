# MariaDB

## Required environment variables

```bash
MARIADB_SOME_STRING="json encoded database data"
```

!!! note
    *Any variable that starts with "MARIADB".* There can be multiple MariaDB databases definition for one backuper instance, for example `MARIADB_FOO_MY_DB1` and `MARIADB_BAR_MY_DB2`. Supported versions are: 10.11, 10.6, 10.5, 10.4.

## MariaDB environment variables values

Value of variables must be valid JSON encoded strings with following keys:

- **"password": "mariadb password"**, *required parameter* (string)
- **"cron_rule": "\* \* \* \* \*"**, cron expression for backups, *required parameter* see https://crontab.guru/ for help (string)
- **"user": "mariadb username"**, defaults to "root" (string)
- **"host": "mariadb hostname"**, defaults to "localhost" (string)
- **"port": 3306**, port defaults to 3306 (integer)
- **"db": "database name"**, defaults to "mariadb" (string)
- **"max_backups": 7**, max number of backups, if this number is exceeded, oldest one is removed, defaults to environment variable `BACKUP_MAX_NUMBER` (integer)

## Examples

1. Local MariaDB with backup every single minute

    **MARIADB_FIRST_DB='{"host": "localhost", "port": 3306, "password": "secret", "cron_rule": "\* \* \* \* \*"}'**

2. MariaDB in local network with backup on every night (UTC) at 05:00

    **MARIADB_SECOND_DB='{"host": "10.0.0.1", "port": 3306, "user": "foo", "password": "change_me!", "db": "bar", "cron_rule": "0 5 \* \* \*"}'**

3. MariaDB in local network with backup on every 6 hours at '15 with max number of backups of 20

    **MARIADB_THIRD_DB='{"host": "192.168.1.5", "port": 3306, "user": "root", "password": "change_me_please!", "db": "project", "cron_rule": "15 \*/3 \* \* \*", "max_backups": 20}'**

<br>
<br>
