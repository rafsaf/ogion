# MariaDB

## Environment variable

```bash
MARIADB_SOME_STRING="host=... password=... cron_rule=..."
```

!!! note
    *Any variable that starts with "MARIADB".* There can be multiple MariaDB databases definition for one backuper instance, for example `MARIADB_FOO_MY_DB1` and `MARIADB_BAR_MY_DB2`. Supported versions are: 10.11, 10.6, 10.5, 10.4.

## Environment variables values

Value of variables must be in format (note **one space** between each block of `key=value`):
<h3> 
[key1]=[value1] [key2]=[value2] [key3]=[value3] (...)
</h3>

## Params

- **password=mariadb password**, *required parameter* (string)
- **cron_rule=\* \* \* \* \***, cron expression for backups, *required parameter* see [https://crontab.guru/](https://crontab.guru/) for help (string)
- OPTIONAL **user=mariadb username**, defaults to "root" (string)
- OPTIONAL **host=mariadb hostname**, defaults to "localhost" (string)
- OPTIONAL **port=3306**, port defaults to 3306 (integer)
- OPTIONAL **db=database name**, defaults to "mariadb" (string)
- OPTIONAL **max_backups=7**, max number of backups, if this number is exceeded, oldest one is removed, defaults to environment variable `BACKUP_MAX_NUMBER` (integer)

## Examples

1. Local MariaDB with backup every single minute

    **MARIADB_FIRST_DB=host=localhost port=3306 password=secret cron_rule=\* \* \* \* \***

2. MariaDB in local network with backup on every night (UTC) at 05:00

    **MARIADB_SECOND_DB=host=10.0.0.1 port=3306 user=foo password=change_me! db=bar cron_rule=0 5 \* \* \***

3. MariaDB in local network with backup on every 6 hours at '15 with max number of backups of 20

    **MARIADB_THIRD_DB=host=192.168.1.5 port=3306 user=root password=change_me_please! db=project cron_rule=15 \*/3 \* \* \* max_backups=20**

<br>
<br>
