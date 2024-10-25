# Disaster recovery using ogion image

For it to work, you must have list and read access to your cloud provider (eg GCS, S3, etc.) in service account on credentials that are using inside ogion container.

The container has following commands available:

```
usage: main.py [-h] [-s] [-n] [--debug-download DEBUG_DOWNLOAD] [--target TARGET]
               [--restore-latest] [-r RESTORE] [-l]

Ogion program

options:
  -h, --help            show this help message and exit
  -s, --single          Only single backup then exit
  -n, --debug-notifications
                        Check if notifications setup is working
  --debug-download DEBUG_DOWNLOAD
                        Download given backup file locally and print path
  --target TARGET       Backup target
  --restore-latest      Restore given target to latest database
  -r, --restore RESTORE
                        Restore given target to backup file
  -l, --list            List all backups for given target
```

To eg. restore to the latest point for example backup target `postgresql_my-instance` you can use:

- k8s: `kubectl exec --it ogion-9c8b8b77d-z5xsc -n ogion -- python -m ogion.main --target postgresql_my-instance --restore-latest`
- docker: `docker compose run --rm ogion python -m ogion.main --target postgresql_my-instance --restore-latest`

PS. In the process, prgram will ask for age secret key in input.
