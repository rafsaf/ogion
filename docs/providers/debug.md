---
hide:
  - toc
---

# Debug

## Environment variable

```bash
BACKUP_PROVIDER="name=debug"
```

Uses only local files (folder inside container) for storing backup. This is meant only for debug purposes.

If you absolutely must not upload backups to outside world, consider adding some persistant volume for folder where buckups live in the container, that is `/var/lib/ogion/data`.

!!! note
_There can be only one upload provider defined per app, using **BACKUP_PROVIDER** environemnt variable_. It's type is guessed by using `name`, in this case `name=debug`.

## Params

| Name | Type                 | Description                                          | Default |
| :--- | :------------------- | :--------------------------------------------------- | :------ |
| name | string[**requried**] | Must be set literaly to string `debug` to use Debug. | -       |

## Examples

```bash
# 1. Debug provider
BACKUP_PROVIDER='name=debug'

```

<br>
<br>
