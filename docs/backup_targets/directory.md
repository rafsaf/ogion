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
    _Any environment variable that starts with "**DIRECTORY_**" will be handled as Directory._ There can be multiple files paths definition for one backuper instance, for example `DIRECTORY_FOO` and `DIRECTORY_BAR`. Params must be included in value, splited by single space for example `"value1=1 value2=foo"`.

## Params

| Name        | Type                 | Description                                                                                                                                                                                 | Default           |
| :---------- | :------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :---------------- |
| abs_path    | string[**requried**] | Absolute path to folder for backup.                                                                                                                                                         | -                 |
| cron_rule   | string[**requried**] | Cron expression for backups, see [https://crontab.guru/](https://crontab.guru/) for help.                                                                                                   | -                 |
| max_backups | int                  | Max number of backups stored in upload provider, if this number is exceeded, oldest one is removed, by default enviornment variable BACKUP_MAX_NUMBER, see [Configuration](/configuration). | BACKUP_MAX_NUMBER |


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
