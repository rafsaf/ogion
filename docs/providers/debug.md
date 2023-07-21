# Debug

Uses only local files (folder inside container) for storing backup. This is meant only for debug purposes.

If you absolutely must not upload backups to outside world, consider adding some persistant volume for folder where buckups live in the container, that is `/var/lib/backuper/data`.

## Configuration


```bash
BACKUP_PROVIDER="name=debug"
```

## Environment variables values

Value of variables must be in format (note **one space** between each block of `key=value`):
<h3> 
[key1]=[value1] [key2]=[value2] [key3]=[value3] (...)
</h3>

## Params

- **name=debug**, *required parameter* (string)