# MySQL

## Required environment variables

```bash
MYSQL_SOME_STRING="json encoded database data"
```

!!! note
    *Any variable that starts with "MYSQL".* There can be multiple MySQL databases definition for one backuper instance, for example `MYSQL_FOO_MY_DB1` and `MYSQL_BAR_MY_DB2`. Supported versions are: 15, 14, 13, 12, 11.

## MySQL environment variables values

Value of variables must be valid JSON encoded strings with following keys:

- **"password": "mysql password"**, *required parameter* (string)
- **"cron_rule": "\* \* \* \* \*"**, cron expression for backups, *required parameter* see https://crontab.guru/ for help (string)
- **"user": "mysql username"**, defaults to "root" (string)
- **"host": "mysql hostname"**, defaults to "localhost" (string)
- **"port": 3306**, port defaults to 3306 (integer)
- **"db": "database name"**, port defaults to "mysql" (string)
- **"max_backups": 7**, max number of backups, if this number is exceeded, oldest one is removed, defaults to environment variable `BACKUP_MAX_NUMBER` (integer)

## Examples

1. Local MySQL with backup every single minute

    **MYSQL_FIRST_DB='{"host": "localhost", "port": 3306, "password": "secret", "cron_rule": "\* \* \* \* \*"}'**

2. MySQL in local network with backup on every night (UTC) at 05:00

    **MYSQL_SECOND_DB='{"host": "10.0.0.1", "port": 3306, "user": "foo", "password": "change_me!", "db": "bar", "cron_rule": "0 5 \* \* \*"}'**

3. MySQL in local network with backup on every 6 hours at '15 with max number of backups of 20

    **MYSQL_THIRD_DB='{"host": "192.168.1.5", "port": 3306, "user": "root", "password": "change_me_please!", "db": "project", "cron_rule": "15 \*/3 \* \* \*", "max_backups": 20}'**

<br>
<br>
