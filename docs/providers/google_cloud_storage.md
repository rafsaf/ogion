---
hide:
  - toc
---

# Google Cloud Storage

## Environment variable

```bash
BACKUP_PROVIDER="name=gcs bucket_name=my_bucket_name bucket_upload_path=my_ogion_instance_1 service_account_base64=Z29vZ2xlX3NlcnZpY2VfYWNjb3VudAo="
```

Uses Google Cloud Storage bucket for storing backups.

!!! note
    _There can be only one upload provider defined per app, using **BACKUP_PROVIDER** environemnt variable_. It's type is guessed by using `name`, in this case `name=gcs`. Params must be included in value, splited by single space for example "value1=1 value2=foo".

## Params

| Name                   | Type                 | Description                                                                                                                                                                                                                                                                                            | Default |
| :--------------------- | :------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------ |
| name                   | string[**requried**] | Must be set literaly to string `gcs` to use Google Cloud Storage.                                                                                                                                                                                                                                      | -       |
| bucket_name            | string[**requried**] | Your globally unique bucket name.                                                                                                                                                                                                                                                                      | -       |
| bucket_upload_path     | string[**requried**] | Prefix that **every created backup** will have, for example if it is equal to `my_ogion_instance_1`, paths to backups will look like `my_ogion_instance_1/your_backup_target_eg_postgresql/file123.zip`. Usually this should be something unique for this ogion instance, for example `k8s_foo_ogion`. | -       |
| service_account_base64 | string[**requried**] | Base64 JSON service account file created in IAM, with write and read access permissions to bucket, see _Resources_ below.                                                                                                                                                                              | -       |
| chunk_size_mb          | int                  | The size of a chunk of data transfered to GCS, consider lower value only if for example your internet connection is slow or you know what you are doing, 100MB is google default.                                                                                                                      | 100     |
| chunk_timeout_secs     | int                  | The chunk of data transfered to GCS upload timeout, consider higher value only if for example your internet connection is slow or you know what you are doing, 60s is google default.                                                                                                                  | 60      |

## Examples

```bash
# 1. Bucket pets-bucket
BACKUP_PROVIDER='name=gcs bucket_name=pets-bucket bucket_upload_path=pets_ogion service_account_base64=Z29vZ2xlX3NlcnZpY2VfYWNjb3VudAo='

# 2. Bucket birds with smaller chunk size
BACKUP_PROVIDER='name=gcs bucket_name=birds bucket_upload_path=birds_ogion chunk_size_mb=25 chunk_timeout_secs=120 service_account_base64=Z29vZ2xlX3NlcnZpY2VfYWNjb3VudAo='
```

## Resources

#### Creating bucket

[https://cloud.google.com/storage/docs/creating-buckets](https://cloud.google.com/storage/docs/creating-buckets)

#### Creating service account

[https://cloud.google.com/iam/docs/service-accounts-create](https://cloud.google.com/iam/docs/service-accounts-create)

#### Giving it required roles to service account

1. Go "IAM and admin" -> "IAM"

2. Find your service account and update its roles

Give it following roles so it will have **read access for whole bucket "my_bucket_name"** and **admin access for only path prefix "my_ogion_instance_1" in bucket "my_bucket_name"**:

1. **Storage Object Admin** (with IAM condition: NAME starts with `projects/_/buckets/my_bucket_name/objects/my_ogion_instance_1`)
2. **Storage Object Viewer** (with IAM condition: NAME starts with `projects/_/buckets/my_bucket_name`)

After sucessfully creating service account, create new private key with JSON type and download it. File similar to `your_project_name-03189413be28.json` will appear in your Downloads.

To get base64 (without any new lines) from it, use command:

```bash
cat your_project_name-03189413be28.json | base64 -w 0
```

#### Terraform

If using terraform for managing cloud infra, Service Accounts definition can be following:

```bash
resource "google_service_account" "ogion-my_ogion_instance_1" {
  account_id   = "ogion-my_ogion_instance_1"
  display_name = "SA my_ogion_instance_1 for ogion bucket access"
}

resource "google_project_iam_member" "ogion-my_ogion_instance_1-iam-object-admin" {
  project = local.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.ogion-my_ogion_instance_1.email}"
  condition {
    title      = "object_admin_only_ogion_bucket_specific_path"
    expression = "resource.name.startsWith(\"projects/_/buckets/my_bucket_name/objects/my_ogion_instance_1\")"
  }
}
resource "google_project_iam_member" "ogion-my_ogion_instance_1-iam-object-viewer" {
  project = local.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.ogion-my_ogion_instance_1.email}"

  condition {
    title      = "object_viewer_only_ogion_bucket"
    expression = "resource.name.startsWith(\"projects/_/buckets/my_bucket_name\")"
  }
}

```

<br>
<br>
