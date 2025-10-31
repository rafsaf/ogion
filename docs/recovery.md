# Manual Recovery

Preferred method is using ogion itself - see [CLI Reference](./cli.md).

If you need to restore manually without ogion, follow the steps below.

## Recovery Process

### 1. Download Backup

Download the backup file from your cloud provider (GCS, S3, Azure).

### 2. Decrypt with age

You need the age private key that matches the public key used during backup.

```bash
age -d -i /path/to/key.txt -o backup.sql.lz backup.sql.lz.age
```

### 3. Decompress with lzip

```bash
lzip -d backup.sql.lz
```

This produces the final backup file (e.g., `backup.sql`).

### 4. Restore Based on Type

#### PostgreSQL

Restore using `psql`:

```bash
psql -h localhost -p 5432 -U postgres -d database_name < backup.sql
```

#### MariaDB

Restore using `mariadb`:

```bash
mariadb -h localhost -P 3306 -u root -p database_name < backup.sql
```

#### File

Copy the file back:

```bash
cp backup_file /destination/path
```

#### Directory

Extract the tar archive:

```bash
tar xf backup.tar -C /destination/path --strip-components=1
```
