# Google Cloud Storage

Make use of Google Cloud Storage bucket.
## Configuration

```bash
BACKUP_PROVIDER="name=gcs bucket_name=my_bucket_name bucket_upload_path=my_backuper_instance_1 service_account_base64=Z29vZ2xlX3NlcnZpY2VfYWNjb3VudAo="
```

## Environment variables values

Value of variables must be in format (note **one space** between each block of `key=value`):
<h3> 
[key1]=[value1] [key2]=[value2] [key3]=[value3] (...)
</h3>

## Params

- **name=gcs**, *required parameter* (string)
- **bucket_name=some bucket name**, your globally unique bucket name (string)
- **service_account_base64=base64 service account**, base64 JSON service account file created in IAM.

    Give it following roles so it will have **read access for whole bucket "my_bucket_name"** and **admin access for only path prefix "my_backuper_instance_1" in bucket "my_bucket_name"**:

    1. **Storage Object Admin** (with IAM condition: NAME starts with `projects/_/buckets/my_bucket_name/objects/my_backuper_instance_1`)
    2. **Storage Object Viewer** (with IAM condition: NAME starts with `projects/_/buckets/my_bucket_name`)

    After sucessfully creating service account, create new private key with JSON type and download it. File similar to `your_project_name-03189413be28.json` will appear in your Downloads.

    To get base64 (without any new lines) from it, use command:

    ```bash
    cat your_project_name-03189413be28.json | base64 -w 0
    ```

- OPTIONAL **bucket_upload_path=backuper instance name**, prefix that **every created backup** will have, for example if it is equal to `my_backuper_instance_1`, paths to backups will look like `my_backuper_instance_1/your_backup_target_eg_postgresql/file123.zip`. Usually this should be something unique for this backuper instance, for example `k8s_foo_backuper` (string)

## Resources

#### Creating bucket

[https://cloud.google.com/storage/docs/creating-buckets](https://cloud.google.com/storage/docs/creating-buckets)


#### Creating service account

[https://cloud.google.com/iam/docs/service-accounts-create](https://cloud.google.com/iam/docs/service-accounts-create)

#### Giving it required roles

1. Go "IAM and admin" -> "IAM"

2. Find your service account and update its roles

#### Terraform

If using terraform for managing cloud infra, Service Accounts definition will be following:

```bash
resource "google_service_account" "backuper-my_backuper_instance_1" {
  account_id   = "backuper-my_backuper_instance_1"
  display_name = "SA my_backuper_instance_1 for backuper bucket access"
}

resource "google_project_iam_member" "backuper-my_backuper_instance_1-iam-object-admin" {
  project = local.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.backuper-my_backuper_instance_1.email}"
  condition {
    title      = "object_admin_only_backuper_bucket_specific_path"
    expression = "resource.name.startsWith(\"projects/_/buckets/my_bucket_name/objects/my_backuper_instance_1\")"
  }
}
resource "google_project_iam_member" "backuper-my_backuper_instance_1-iam-object-viewer" {
  project = local.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.backuper-my_backuper_instance_1.email}"

  condition {
    title      = "object_viewer_only_backuper_bucket"
    expression = "resource.name.startsWith(\"projects/_/buckets/my_bucket_name\")"
  }
}

```

<br>
<br>