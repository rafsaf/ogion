# CLI Reference

```bash
usage: python3 -m ogion.main [-h] [-s] [-n]
                             [--debug-download DEBUG_DOWNLOAD]
                             [--target TARGET]
                             [--restore-latest]
                             [-r RESTORE] [-l]

Ogion - Automated database backup and secure cloud upload tool

options:
  -h, --help            show this help message and exit
  -s, --single          Run single backup then exit
                        (optionally for specific --target)
  -n, --debug-notifications
                        Check if notifications setup is
                        working
  --debug-download DEBUG_DOWNLOAD
                        Download given backup file locally
                        and print path
  --target TARGET       Backup target (required with
                        --list, --restore-latest,
                        --restore)
  --restore-latest      Restore given target to latest
                        backup
  -r, --restore RESTORE
                        Restore given target to specific
                        backup file
  -l, --list            List all backups for given target

Examples:
  ogion                                 Run in continuous backup mode
  ogion -s                              Run a single backup for all targets
  ogion --target mytarget -s            Run a single backup for specific target
  ogion --target mytarget --list
                                        List all backups for 'mytarget' target
  ogion --target mytarget --restore-latest
                                        Restore the latest backup for 'mytarget'
  ogion --target mytarget --restore backup_file.sql.lz.age
                                        Restore specific backup file for 'mytarget'
```

!!! note
    The `ogion` command is a bash script shortcut for `python -m ogion.main`. Both work and have autocompletion support.

## Disaster Recovery

Get a bash shell in the container, eg.:

**Kubernetes:**
```bash
kubectl exec -it ogion-9c8b8b77d-z5xsc -n ogion -- bash
```

**Docker:**
```bash
docker exec -it ogion bash
```

Then run restore commands:

```bash
# Restore to latest backup
ogion --target postgresql_my-instance --restore-latest

# Or first list available backups
ogion --target postgresql_my-instance --list

# And restore to specific backup
ogion --target postgresql_my-instance --restore backup_file.sql.lz.age
```

!!! note
    You'll be prompted for the age secret key during restore.
