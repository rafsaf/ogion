---
hide:
  - toc
---

# PostgreSQL

## Environment variable

```bash
POSTGRESQL_SOME_STRING="host=... password=... cron_rule=..."
```

!!! note
    _Any environment variable that starts with "**POSTGRESQL_**" will be handled as PostgreSQL._ There can be multiple files paths definition for one backuper instance, for example `POSTGRESQL_FOO_MY_DB1` and `POSTGRESQL_BAR_MY_DB2`. Supported versions are: 15, 14, 13, 12, 11. Params must be included in value, splited by single space for example `"value1=1 value2=foo"`.

## Params

| Name        | Type                 | Description                                                                                                                                                                                 | Default           |
| :---------- | :------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :---------------- |
| password    | string[**requried**] | PostgreSQL database password.                                                                                                                                                               | -                 |
| cron_rule   | string[**requried**] | Cron expression for backups, see [https://crontab.guru/](https://crontab.guru/) for help.                                                                                                   | -                 |
| user        | string               | PostgreSQL database username.                                                                                                                                                               | postgres          |
| host        | string               | PostgreSQL database hostname.                                                                                                                                                               | localhost         |
| port        | int                  | PostgreSQL database port.                                                                                                                                                                   | 5432              |
| db          | string               | PostgreSQL database name.                                                                                                                                                                   | postgres          |
| max_backups | int                  | Max number of backups stored in upload provider, if this number is exceeded, oldest one is removed, by default enviornment variable BACKUP_MAX_NUMBER, see [Configuration](/configuration). | BACKUP_MAX_NUMBER |


## Examples

```bash
# 1. Local PostgreSQL with backup every single minute
POSTGRESQL_FIRST_DB='host=localhost port=5432 password=secret cron_rule=* * * * *'

# 2. PostgreSQL in local network with backup on every night (UTC) at 05:00
POSTGRESQL_SECOND_DB='host=10.0.0.1 port=5432 user=foo password=change_me! db=bar cron_rule=0 5 * * *'

# 3. PostgreSQL in local network with backup on every 6 hours at '15 with max number of backups of 20
POSTGRESQL_THIRD_DB='host=192.168.1.5 port=5432 user=root password=change_me_please! db=project cron_rule=15 */3 * * * max_backups=20'
```

<br>
<br>
