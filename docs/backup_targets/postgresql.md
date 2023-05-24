# PostgreSQL

## Environment variable



```bash
POSTGRESQL_SOME_STRING="host=... password=... cron_rule=..."
```

!!! note
    *Any variable that starts with "POSTGRESQL".* There can be multiple PostgreSQL databases definition for one backuper instance, for example `POSTGRESQL_MY_FOO_POSTGRES_DB1` and `POSTGRESQL_MY_BAR_POSTGRES_DB2`. Supported versions are: 15, 14, 13, 12, 11.


## Postgres environment variables values

Value of variables must be in format (note **one space** between each block of `key=value`):
<h3> 
[key1]=[value1] [key2]=[value2] [key3]=[value3] (...)
</h3>

### Params

- **password=postgres password**, *required parameter* (string)
- **cron_rule=\* \* \* \* \***, cron expression for backups, *required parameter* see [https://crontab.guru/](https://crontab.guru/) for help (string)
- OPTIONAL **user=postgres username**, defaults to "postgres" (string)
- OPTIONAL **host=postgres hostname**, defaults to "localhost" (string)
- OPTIONAL **port=5432**, port defaults to 5432 (integer)
- OPTIONAL **db=database name**, defaults to "postgres" (string)
- OPTIONAL **max_backups=7**, max number of backups, if this number is exceeded, oldest one is removed, defaults to environment variable `BACKUP_MAX_NUMBER` (integer)



## Examples

1. Local postgres with backup every single minute

    **POSTGRESQL_FIRST_DB=host=localhost port=5432 password=secret cron_rule=\* \* \* \* \***

2. Postgres in local network with backup on every night (UTC) at 05:00

    **POSTGRESQL_SECOND_DB=host=10.0.0.1 port=5432 user=foo password=change_me! db=bar cron_rule=0 5 \* \* \***

3. Postgres in local network with backup on every 6 hours at '15 with max number of backups of 20

    **POSTGRESQL_THIRD_DB=host=192.168.1.5 port=5432 user=postgres password=change_me_please! db=project cron_rule=15 \*/3 \* \* \* max_backups=20**

<br>
<br>