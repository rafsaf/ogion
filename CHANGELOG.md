# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **GitHub Copilot instructions** - Added `.github/copilot-instructions.md` with project-specific guidelines for AI assistants, including testing requirements, code quality standards, and changelog maintenance rules
- **Shell autocomplete support** - Added bash autocomplete for all CLI commands and arguments using `argcomplete` library. Autocomplete works for target names, backup files, and all command options
- **New `ogion` command** - Added `ogion` bash script as a convenient shortcut for `python -m ogion.main`. Both commands work identically and support autocomplete
- **Improved `--single` flag** - Can now backup a specific target using `--single --target <name>` instead of running all backups
- Dynamic autocomplete for `--target` argument that suggests available backup targets from your configuration
- Dynamic autocomplete for `--restore` and `--debug-download` arguments that suggests available backup files

### Changed

- Migrated from Poetry to uv for dependency management
- Added this Changelog file
- Migrate to Python 3.14 and Debian Trixie
- **Enhanced CLI help text** - More descriptive help messages with practical examples for common use cases
- **Better argument validation** - CLI now validates argument combinations upfront and shows clear error messages (e.g., `--list` requires `--target`, `--restore-latest` and `--restore` are mutually exclusive)
- Container entrypoint changed to `ogion` command for consistency

### Fixed

- Edge case fixes for `--list` and `--restore-latest` commands when using many similar env names for azure and gcs (eg. POSTGRESQL_TEST, POSTGRESQL_TEST_HOURLY could lead to use of wrong backup file name in `--restore-latest` and wrong list in `--list`)

## [8.2] - 2025-10-05

### Added

- PostgreSQL client 18 support
- Use `getpass` for password prompts (improved security)

### Fixed

- Memory leak in croniter
- MariaDB RC images handling in compose file generator

## [8.1] - 2025-07-25

### Added

- Retry on network errors for upload providers

### Changed

- Frozen Ruff and mypy versions
- Don't use patch version of database images in file generator

## [8.0] - 2025-05-13

### Added

- **lzip compression before encryption** - all backups now use lzip compression before age encryption for better compression ratios and resistance to compression side-channel attacks
- Print available backup targets on startup

### Changed

- **BREAKING**: Backup format changed - now uses lzip compression layer before age encryption

## [7.3] - 2025-03-01

### Added

- Benchmark commands for testing
- Poetry v2 support

### Fixed

- Hyphen in extra options parsing bug

## [7.2] - 2024-12-15

### Added

- Optional parameters support for PostgreSQL backups
- Optional parameters support for MariaDB backups
- Lazy loading for upload providers (faster startup)

### Changed

- Improved documentation

## [7.1] - 2024-10-26

### Fixed

- Google Cloud credentials authentication problem

## [7.0] - 2024-10-25

### Added

- **age encryption replaces 7zip** - migration from GPG/7zip to modern age encryption
- Azure Blob Storage testing with Azurite
- Minio client for S3 testing
- Fake GCS server for testing
- Migrate to python 3.13
- Database restore commands (`restore` and `restore-latest`)
- `download` and `list` commands for backups
- `all_target_backups` functionality

### Changed

- **BREAKING**: Encryption format changed from 7zip to age
- **BREAKING**: Removed MySQL 8.0 duplicate of MariaDB
- **BREAKING**: Environment variable changes for backup targets
- Removed boto3, now using minio client for S3
- Improved test coverage to 100%
- Docker entrypoint script removed, no root mode by default
- Better SIGTERM handling

### Removed

- 7zip encryption support (replaced by age)
- Root mode in Docker by default

## [6.0] - 2024-03-15

### Added

- End-to-end tests for MySQL, MariaDB, and PostgreSQL dump/restore
- File and folder backup target tests
- Test coverage improvements
- Release automation workflow
- CONTRIBUTING.md and PR templates

### Changed

- **BREAKING**: Project renamed from "backuper" to "Ogion"
- **BREAKING**: Folder renamed from `backuper` to `ogion`
- **BREAKING**: Changed to GNU GPLv3 license
- Fully migrated to Ruff (removed flake8, black, isort)
- Pydantic models now used for initialization of backup targets and providers
- Python 3.12 minimum required version
- 88 character line length enforced

### Fixed

- Escape special characters in folder and file names during backup

## [5.1] - 2023-10-15

### Added

- Automatic docker-compose.dbs.yml updates workflow
- PostgreSQL 16 support
- MySQL 8.1 and MariaDB 11.1 support
- Python 3.12 support

### Changed

- Renamed MySQL references to MariaDB internally
- Refactored docker-compose structure

### Fixed

- Acceptance tests issues

## [5.0] - 2023-09-15

### Added

- Slack notifications support
- SMTP/Email notifications support

### Changed

- Improved notification system architecture

## [4.0] - 2023-08-27

### Added

- Azure Blob Storage upload provider
- Minimum retention days parameter for providers (with 0 days support)
- `--clean` flag for PostgreSQL backup options
- Pydantic-based environment variable validation
- pytest-xdist for faster test execution

### Changed

- AWS and GCP providers now use SecretStr for sensitive data
- Updated documentation for all providers

## [3.2] - 2023-08-16

### Added

- AWS S3 upload provider with boto3
- Tests for AWS provider

## [3.1] - 2023-08-12

### Added

- Documentation versioning with mike
- Docs published at versioned URLs

### Changed

- Updated configuration documentation links

## [3.0] - 2023-08-12

### Added

- Two additional options for GCS provider

### Changed

- **BREAKING**: Renamed upload provider names
- Improved GCS provider logic
- Fixed max_backups handling
- Better cleanup in run_backup
- Improved documentation for providers and targets

## [2.0] - 2023-08-08

### Added

- Thread name to logging output
- Better logging in backup runs

### Changed

- **BREAKING**: Refactored notifications system
- **BREAKING**: Renamed storage providers to just "providers"
- **BREAKING**: Config refactored with better class target model names
- **BREAKING**: Environment variable names changed
- Pydantic 2.0 migration
- Move to abstract config for backup target detection

### Removed

- Raw requirements.txt files (poetry only)

## [1.2] - 2023-07-11

### Added

- Mypy type checking with 100% coverage
- Bandit security checks
- Makefile with coverage requirements (100%)

### Changed

- Migrated to Pydantic 2.0
- Migrated 7-Zip to version 23.01
- Python base image to Bookworm
- Provider architecture now uses `__init_subclass__`

### Fixed

- GCS tests storage mock
- Test timeouts increased to 5s

## [1.1] - 2023-06-18

### Changed

- GCS chunk size lowered and timeout set to 120s for better network support

### Fixed

- GCS tests after chunk_size changes

## [1.0] - 2023-05-28

### Added

- Comprehensive documentation
- License update

## [0.16] - 2023-05-28

### Added

- Configuration documentation
- How to restore documentation
- Deployment documentation
- `env_name` added to backup file names

## [0.15] - 2023-05-25

### Added

- Added `.sql` postfix to backup files

### Changed

- **BREAKING**: PostgreSQL backups now use plain SQL format instead of `-Fc`

### Fixed

- Documentation updates for backup targets

## [0.14] - 2023-05-24

### Added

- Special characters support for MariaDB, MySQL, and PostgreSQL

### Changed

- **BREAKING**: Environment variable parsing changed from JSON to pgbouncer-like `key=value` syntax

## [0.13] - 2023-05-07

### Fixed

- Log files permissions in Docker container at `/var/log`

## [0.12] - 2023-05-07

### Changed

- Set `LOG_FOLDER_PATH` to `/var/log` in container

## [0.11] - 2023-05-07

### Fixed

- Typo in `_init_pgpass_file`

## [0.10] - 2023-05-06

### Changed

- PostgreSQL pgpass file initialization with different connection params

## [0.9] - 2023-05-06

### Fixed

- Valid venv path in Dockerfile

## [0.8] - 2023-05-06

### Fixed

- pgpass file permissions for `CONST_PGPASS_FILE_PATH`

## [0.7] - 2023-05-04

### Added

- ARM64 architecture support and tests
- Documentation pages
- Base backup tests
- Graceful shutdown with daemon threads and timeout
- `ZIP_ARCHIVE_LEVEL` environment variable
- Log rotation (max ~100KB per file)

## [0.6] - 2023-04-28

### Changed

- MySQL client installation commented out in install script

## [0.5] - 2023-04-28

### Added

- MariaDB backup target support
- MySQL backup target support
- Single file and directory backup targets
- Discord webhook notifications
- Google Cloud Storage provider
- MkDocs documentation
- Validation for environment variables and paths
- Password regex validation
- ZIP archive password support

### Changed

- Renamed project to "backuper"
- Provider architecture improvements

## [0.4.0] - 2022-12-11

### Added

- Tests for core module
- Runtime arguments
- 7zip precompiled binaries
- Retry logic for GCS provider
- Post-save and clean methods for providers

### Changed

- Dockerfile improvements with multi-stage builds

## [0.3.0] - 2022-08-20

### Changed

- Updated Pydantic
- Improved Docker image to prevent immediate exit
- Reduced CPU usage with better sleep intervals

## [0.2] - 2022-08-20

### Added

- Expressive README
- Docker environment variables

## [0.1] - 2022-08-15

### Added

- Initial release
- PostgreSQL backup support with pg_dump
- Basic Docker support
- GPG encryption support
- Multi-threaded backup architecture
- Cron-like scheduling with croniter
- Environment variable configuration
