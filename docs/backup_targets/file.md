# Single file

## Environment variable

```bash
SINGLEFILE_SOME_STRING="abs_path=... cron_rule=..."
```

!!! note
    *Any variable that starts with "SINGLEFILE".* There can be multiple files paths definition for one backuper instance, for example `SINGLEFILE_FOO` and `SINGLEFILE_BAR`.

## Single file environment variables values

Value of variables must be in format (note **one space** between each block of `key=value`):
<h3> 
[key1]=[value1] [key2]=[value2] [key3]=[value3] (...)
</h3>

### Params

- **abs_path=/path/to/file.extension**, *required parameter* (string)
- **cron_rule=\* \* \* \* \***, cron expression for backups, *required parameter* see [https://crontab.guru/](https://crontab.guru/) for help (string)
- OPTIONAL **max_backups=7**, max number of backups, if this number is exceeded, oldest one is removed, defaults to environment variable `BACKUP_MAX_NUMBER` (integer)

## Examples

1. File with backup every single minute

    **SINGLEFILE_FIRST=abs_path=/home/user/file.txt cron_rule=\* \* \* \* \***

2. File with backup on every night (UTC) at 05:00

    **SINGLEFILE_SECOND=abs_path=/home/user/file.txt cron_rule=0 5 \* \* \***

3. File with backup on every 6 hours at '15 with max number of backups of 20

    **SINGLEFILE_THIRD=abs_path=/home/user/file.txt cron_rule=15 \*/3 \* \* \* max_backups=20**

<br>
<br>
