# Single file

## Required environment variables

```bash
SINGLEFILE_SOME_STRING="json encoded data"
```

!!! note
    *Any variable that starts with "SINGLEFILE".* There can be multiple files paths definition for one backuper instance, for example `SINGLEFILE_FOO` and `SINGLEFILE_BAR`.

## Single file environment variables values

Value of variables must be valid JSON encoded strings with following keys:

- **"abs_path": "/path/to/file.extension"**, *required parameter* (string)
- **"cron_rule": "\* \* \* \* \*"**, cron expression for backups, *required parameter* see https://crontab.guru/ for help (string)
- **"max_backups": 7**, max number of backups, if this number is exceeded, oldest one is removed, defaults to environment variable `BACKUP_MAX_NUMBER` (integer)

## Examples

1. File with backup every single minute

    **SINGLEFILE_FIRST='{"abs_path": "/home/user/file.txt", "cron_rule": "\* \* \* \* \*"}'**

2. File with backup on every night (UTC) at 05:00

    **SINGLEFILE_SECOND='{"abs_path": "/home/user/file.txt", "cron_rule": "0 5 \* \* \*"}'**

3. File with backup on every 6 hours at '15 with max number of backups of 20

    **SINGLEFILE_THIRD='{"abs_path": "/home/user/file.txt", "cron_rule": "15 \*/3 \* \* \*", "max_backups": 20}'**

<br>
<br>
