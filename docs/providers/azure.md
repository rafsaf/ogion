---
hide:
  - toc
---

# Azure Blob Storage

## Environment variable

```bash
BACKUP_PROVIDER="name=azure container_name=my-ogion-instance connect_string=DefaultEndpointsProtocol=https;AccountName=accname;AccountKey=secret;EndpointSuffix=core.windows.net"
```

Uses Azure Blob Storage for storing backups.

!!! note
_There can be only one upload provider defined per app, using **BACKUP_PROVIDER** environemnt variable_. It's type is guessed by using `name`, in this case `name=azure`. Params must be included in value, splited by single space for example "value1=1 value2=foo".

## Params

| Name           | Type                 | Description                                                                                   | Default |
| :------------- | :------------------- | :-------------------------------------------------------------------------------------------- | :------ |
| name           | string[**requried**] | Must be set literaly to string `azure` to use Azure.                                          | -       |
| container_name | string[**requried**] | Storage account container name. It must be already created, ogion won't create new container. | -       |
| connect_string | string[**requried**] | Connection string copied from your storage account "Access keys" section.                     | -       |

## Examples

```bash
# 1. Storage account accname and container name my-ogion-instance
BACKUP_PROVIDER="name=azure container_name=my-ogion-instance connect_string=DefaultEndpointsProtocol=https;AccountName=accname;AccountKey=secret;EndpointSuffix=core.windows.net"

# 2. Storage account birds and container name birds
BACKUP_PROVIDER="name=azure container_name=birds connect_string=DefaultEndpointsProtocol=https;AccountName=birds;AccountKey=secret;EndpointSuffix=core.windows.net"
```

## Resources

#### Creating azure storage account

[https://learn.microsoft.com/en-us/azure/storage/common/storage-account-create?tabs=azure-portal](https://learn.microsoft.com/en-us/azure/storage/common/storage-account-create?tabs=azure-portal)

<br>
<br>
