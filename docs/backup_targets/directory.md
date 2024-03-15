---
hide:
  - toc
---

# Directory

## Environment variable

```bash
DIRECTORY_SOME_STRING="abs_path=... cron_rule=..."
```

!!! note
    _Any environment variable that starts with "\*\*DIRECTORY_\*\*" will be handled as Directory.\_ There can be multiple files paths definition for one ogion instance, for example `DIRECTORY_FOO` and `DIRECTORY_BAR`. Params must be included in value, splited by single space for example `"value1=1 value2=foo"`.

## Params

| Name               | Type                 | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Default                   |
| :----------------- | :------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :------------------------ |
| abs_path           | string[**requried**] | Absolute path to folder for backup.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | -                         |
| cron_rule          | string[**requried**] | Cron expression for backups, see [https://crontab.guru/](https://crontab.guru/) for help.                                                                                                                                                                                                                                                                                                                                                                                                                                                   | -                         |
| max_backups        | int                  | Soft limit how many backups can live at once for backup target. Defaults to `7`. This must makes sense with cron expression you use. For example if you want to have `7` day retention, and make backups at 5:00, `max_backups=7` is fine, but if you make `4` backups per day, you would need `max_backups=28`. Limit is soft and can be exceeded if no backup is older than value specified in min_retention_days. Min `1` and max `998`. Defaults to enviornment variable BACKUP_MAX_NUMBER, see [Configuration](./../configuration.md). | BACKUP_MAX_NUMBER         |
| min_retention_days | int                  | Hard minimum backups lifetime in days. Ogion won't ever delete files before, regardles of other options. Min `0` and max `36600`. Defaults to enviornment variable BACKUP_MIN_RETENTION_DAYS, see [Configuration](./../configuration.md).                                                                                                                                                                                                                                                                                                   | BACKUP_MIN_RETENTION_DAYS |

## Examples

```bash
# 1. Directory /home/user/folder with backup every single minute
DIRECTORY_FIRST='abs_path=/home/user/folder cron_rule=* * * * *'

# 2. Directory /etc with backup on every night (UTC) at 05:00
DIRECTORY_SECOND='abs_path=/etc cron_rule=0 5 * * *'

# 3. Mounted directory /mnt/homedir with backup on every 6 hours at '15 with max number of backups of 20
DIRECTORY_HOME_DIR='abs_path=/mnt/homedir cron_rule=15 */3 * * * max_backups=20'
```

<br>
<br>
