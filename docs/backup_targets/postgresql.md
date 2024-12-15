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
    _Any environment variable that starts with **"POSTGRESQL\_"** will be handled as PostgreSQL._ There can be multiple files paths definition for one ogion instance, for example `POSTGRESQL_FOO_MY_DB1` and `POSTGRESQL_BAR_MY_DB2`. [All currently supported versions are also supported by ogion](https://endoflife.date/postgresql). Changes in versions are automatically tracke . Params must be included in value, splited by single space for example `"value1=1 value2=foo"`.

## Params

| Name               | Type                 | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Default                   |
| :----------------- | :------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :------------------------ |
| password           | string[**requried**] | PostgreSQL database password.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | -                         |
| cron_rule          | string[**requried**] | Cron expression for backups, see [https://crontab.guru/](https://crontab.guru/) for help.                                                                                                                                                                                                                                                                                                                                                                                                                                                   | -                         |
| user               | string               | PostgreSQL database username.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | postgres                  |
| host               | string               | PostgreSQL database hostname.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | localhost                 |
| port               | int                  | PostgreSQL database port.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | 5432                      |
| db                 | string               | PostgreSQL database name.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | postgres                  |
| max_backups        | int                  | Soft limit how many backups can live at once for backup target. Defaults to `7`. This must makes sense with cron expression you use. For example if you want to have `7` day retention, and make backups at 5:00, `max_backups=7` is fine, but if you make `4` backups per day, you would need `max_backups=28`. Limit is soft and can be exceeded if no backup is older than value specified in min_retention_days. Min `1` and max `998`. Defaults to enviornment variable BACKUP_MAX_NUMBER, see [Configuration](./../configuration.md). | BACKUP_MAX_NUMBER         |
| min_retention_days | int                  | Hard minimum backups lifetime in days. Ogion won't ever delete files before, regardles of other options. Min `0` and max `36600`. Defaults to enviornment variable BACKUP_MIN_RETENTION_DAYS, see [Configuration](./../configuration.md).                                                                                                                                                                                                                                                                                                   | BACKUP_MIN_RETENTION_DAYS |

## Additional connection params

Extra variables that starts with `conn_` will be passed AS IS to psql command underthehood as url-encoded connection params:

For example you can use it for SSL setup:

- `conn_sslmode=verify-ca`
- `conn_sslrootcert=path-to-mounted-server-ca-file`
- `conn_sslcert=path-to-mounted-client-ca-file`
- `conn_sslkey=path-to-mounted-client-key-file`

## Examples

```bash
# 1. Local PostgreSQL with backup every single minute
POSTGRESQL_FIRST_DB='host=localhost port=5432 password=secret cron_rule=* * * * *'

# 2. PostgreSQL in local network with backup on every night (UTC) at 05:00
POSTGRESQL_SECOND_DB='host=10.0.0.1 port=5432 user=foo password=change_me! db=bar cron_rule=0 5 * * *'

# 3. PostgreSQL in local network with backup on every 6 hours at '15 with max number of backups of 20
POSTGRESQL_THIRD_DB='host=192.168.1.5 port=5432 user=root password=change_me_please! db=project cron_rule=15 */3 * * * max_backups=20'

# 4. PostgreSQL connected using sslmode require
POSTGRESQL_4_DB_SSL='host=localhost port=5432 password=secret cron_rule=* * * * * conn_sslmode=require'
```

<br>
<br>
