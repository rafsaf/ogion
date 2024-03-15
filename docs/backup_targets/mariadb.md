---
hide:
  - toc
---

# MariaDB

## Environment variable

```bash
MARIADB_SOME_STRING="host=... password=... cron_rule=..."
```

!!! note
    _Any environment variable that starts with "\*\*MARIADB_\*\*" will be handled as MariaDB.\_ There can be multiple files paths definition for one ogion instance, for example `MARIADB_FOO_MY_DB1` and `MARIADB_BAR_MY_DB2`. [All currently supported versions are also supported by ogion](https://endoflife.date/mariadb). Params must be included in value, splited by single space for example `"value1=1 value2=foo"`.

## Params

| Name               | Type                 | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Default                   |
| :----------------- | :------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :------------------------ |
| password           | string[**requried**] | Mariadb database password.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | -                         |
| cron_rule          | string[**requried**] | Cron expression for backups, see [https://crontab.guru/](https://crontab.guru/) for help.                                                                                                                                                                                                                                                                                                                                                                                                                                                   | -                         |
| user               | string               | Mariadb database username.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | root                      |
| host               | string               | Mariadb database hostname.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | localhost                 |
| port               | int                  | Mariadb database port.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | 3306                      |
| db                 | string               | Mariadb database name.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | mariadb                   |
| max_backups        | int                  | Soft limit how many backups can live at once for backup target. Defaults to `7`. This must makes sense with cron expression you use. For example if you want to have `7` day retention, and make backups at 5:00, `max_backups=7` is fine, but if you make `4` backups per day, you would need `max_backups=28`. Limit is soft and can be exceeded if no backup is older than value specified in min_retention_days. Min `1` and max `998`. Defaults to enviornment variable BACKUP_MAX_NUMBER, see [Configuration](./../configuration.md). | BACKUP_MAX_NUMBER         |
| min_retention_days | int                  | Hard minimum backups lifetime in days. Ogion won't ever delete files before, regardles of other options. Min `0` and max `36600`. Defaults to enviornment variable BACKUP_MIN_RETENTION_DAYS, see [Configuration](./../configuration.md).                                                                                                                                                                                                                                                                                                   | BACKUP_MIN_RETENTION_DAYS |

## Examples

```bash
# 1. Local MariaDB with backup every single minute
MARIADB_FIRST_DB='host=localhost port=3306 password=secret cron_rule=* * * * *'

# 2. MariaDB in local network with backup on every night (UTC) at 05:00
MARIADB_SECOND_DB='host=10.0.0.1 port=3306 user=foo password=change_me! db=bar cron_rule=0 5 * * *'

# 3. MariaDB in local network with backup on every 6 hours at '15 with max number of backups of 20
MARIADB_THIRD_DB='host=192.168.1.5 port=3306 user=root password=change_me_please! db=project cron_rule=15 */3 * * * max_backups=20'
```

<br>
<br>
