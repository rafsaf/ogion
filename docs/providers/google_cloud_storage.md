# Google Cloud Storage

## Required environment variables

```bash
BACKUP_PROVIDER="gcs"
GOOGLE_BUCKET_NAME="my_bucket_name"
GOOGLE_BUCKET_UPLOAD_PATH="my_backuper_instance_1"
GOOGLE_SERVICE_ACCOUNT_BASE64="base64 service account"
```

## BACKUP_PROVIDER

`BACKUP_PROVIDER` is case sensitive const backup provider name, for Google Cloud Storage it must be equal to `gcs`.

## GOOGLE_BUCKET_NAME

`GOOGLE_BUCKET_NAME` is your globally unique bucket name.

## GOOGLE_BUCKET_UPLOAD_PATH

`GOOGLE_BUCKET_UPLOAD_PATH` is prefix that **every created backup** will have, for example if it is equal to `my_backuper_instance_1`, paths to backups will look like `my_backuper_instance_1/your_backup_target_eg_postgresql/file123.zip`. Usually this should be something unique for this backuper instance, for example `k8s_foo_backuper`.

## GOOGLE_SERVICE_ACCOUNT_BASE64

`GOOGLE_SERVICE_ACCOUNT_BASE64` is base64 JSON service account file created in IAM.

Give it following roles so it will have **read access for whole bucket "my_bucket_name"** and **admin access for only path prefix "my_backuper_instance_1" in bucket "my_bucket_name"**:

- **Storage Object Admin** (with IAM condition: NAME starts with `projects/_/buckets/my_bucket_name/objects/my_backuper_instance_1`)
- **Storage Object Viewer** (with IAM condition: NAME starts with `projects/_/buckets/my_bucket_name`)

After sucessfully creating service account, create new private key with JSON type and download it. File similar to `your_project_name-03189413be28.json` will appear in your Downloads.

To get base64 (without any new lines) from it, use command:

```bash
cat your_project_name-03189413be28.json | base64 -w 0
```


## Resources

#### Creating bucket

https://cloud.google.com/storage/docs/creating-buckets


#### Creating service account

https://cloud.google.com/iam/docs/service-accounts-create

#### Giving it required roles

1. Go "IAM and admin" -> "IAM"

2. Find your service account and update its roles

<br>
<br>
