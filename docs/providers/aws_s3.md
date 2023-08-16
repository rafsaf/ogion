---
hide:
  - toc
---

# AWS S3

## Environment variable

```bash
BACKUP_PROVIDER="name=aws bucket_name=my_bucket_name bucket_upload_path=my_backuper_instance_1 key_id=AKIAU5JB5UQDL8C3K6UP key_secret=nFTXlO7nsPNNUj59tFE21Py9tOO8fwOtHNsr3YwN region=eu-central-1"
```

Uses AWS S3 bucket for storing backups.

!!! note
    _There can be only one upload provider defined per app, using **BACKUP_PROVIDER** environemnt variable_. It's type is guessed by using `name`, in this case `name=aws`. Params must be included in value, splited by single space for example "value1=1 value2=foo".
## Params

| Name               | Type                 | Description                                                                                                                                                                                                                                                                                                        | Default |
| :----------------- | :------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------ |
| name               | string[**requried**] | Must be set literaly to string `gcs` to use Google Cloud Storage.                                                                                                                                                                                                                                                  | -       |
| bucket_name        | string[**requried**] | Your globally unique bucket name.                                                                                                                                                                                                                                                                                  | -       |
| bucket_upload_path | string[**requried**] | Prefix that **every created backup** will have, for example if it is equal to `my_backuper_instance_1`, paths to backups will look like `my_backuper_instance_1/your_backup_target_eg_postgresql/file123.zip`. Usually this should be something unique for this backuper instance, for example `k8s_foo_backuper`. | -       |
| region             | string[**requried**] | Bucket region.                                                                                                                                                                                                                                                                                                     | -       |
| key_id             | string[**requried**] | IAM user access key id, see _Resources_ below.                                                                                                                                                                                                                                                                     | -       |
| key_secret         | string[**requried**] | IAM user access key secret, see _Resources_ below.                                                                                                                                                                                                                                                                 | -       |
| max_bandwidth      | int                  | Max bandwith of file upload that is passed to aws sdk transfer config, see their docs: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/customizations/s3.html#boto3.s3.transfer.TransferConfig.                                                                                                  | null    |

## Examples

```bash
# 1. Bucket pets-bucket
BACKUP_PROVIDER='name=aws bucket_name=pets-bucket bucket_upload_path=pets_backuper key_id=AKIAU5JB5UQDL8C3K6UP key_secret=nFTXlO7nsPNNUj59tFE21Py9tOO8fwOtHNsr3YwN region=eu-central-1'

# 2. Bucket birds with other region
BACKUP_PROVIDER='name=aws bucket_name=birds bucket_upload_path=birds_backuper key_id=AKIAU5JB5UQDL8C3K6UP key_secret=nFTXlO7nsPNNUj59tFE21Py9tOO8fwOtHNsr3YwN region=us-east-1'
```


## Resources

#### Bucket and IAM walkthrough

[https://docs.aws.amazon.com/AmazonS3/latest/userguide/walkthrough1.html](https://docs.aws.amazon.com/AmazonS3/latest/userguide/walkthrough1.html)

#### Giving IAM user required permissions

Assuming your bucket name is `my_bucket_name` and upload path `test-upload-path`, 4 permissions are needed for IAM user (s3:ListBucket, s3:PutObject, s3:GetObject, s3:DeleteObject):

```json
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "AllowList",
			"Effect": "Allow",
			"Action": "s3:ListBucket",
			"Resource": "arn:aws:s3:::my_bucket_name",
			"Condition": {
				"StringLike": {
					"s3:prefix": "test-upload-path/*"
				}
			}
		},
		{
			"Sid": "AllowPutGetDelete",
			"Effect": "Allow",
			"Action": [
				"s3:PutObject",
				"s3:GetObject",
				"s3:DeleteObject"
			],
			"Resource": "arn:aws:s3:::my_bucket_name/test-upload-path/*"
		}
	]
}
```


<br>
<br>
