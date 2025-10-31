# GitHub Copilot Instructions for Ogion

## Project Overview

**Ogion** is a backup automation tool for PostgreSQL, MariaDB, MySQL databases, files, and directories. It uses age encryption with lzip compression and uploads to cloud storage (GCS, S3, Azure) or local debug storage.

See `README.md` for full project details. Check `docs/` folder for all documentation pages. Review `ogion/` folder for actual implementation.

## Testing Requirements - CRITICAL

1. **ALWAYS use `monkeypatch`** - NEVER use `@patch` decorator
2. **100% test coverage required** - No exceptions
3. **Follow existing test patterns** in `tests/` folder
4. **Use parametrize** for testing multiple database versions
5. **Use `freezegun`** for time-based tests: `@freeze_time("2022-12-11")`

### Test Example
```python
import pytest
from freezegun import freeze_time
from ogion import config

def test_something(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "SOME_CONFIG", "test_value")
    # test logic
    assert result == expected

@freeze_time("2022-12-11")
@pytest.mark.parametrize("target", ALL_POSTGRES_DBS_TARGETS)
def test_with_params(target: PostgreSQLTargetModel) -> None:
    # parametrize tests all database versions
    pass
```

## Running Tests & Linting

```bash
# Run tests (flags from pyproject.toml: -v, --cov, --cov-fail-under 100, -n auto)
uv run pytest

# Run linting (MUST pass before committing)
uv run pre-commit run -a
```

## Changelog - CRITICAL

**After every user-facing change, update `CHANGELOG.md`**

Follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format:

```markdown
## [Unreleased]

### Added
- New features

### Changed
- Changes in existing functionality
- **BREAKING**: Mark breaking changes like this

### Fixed
- Bug fixes
```

### When to Update Changelog
- CLI changes (commands, arguments, flags)
- Configuration changes
- Backup format or encryption changes
- Bug fixes users notice
- Documentation updates

### When NOT to Update
- Internal refactoring
- Test improvements (unless affecting users)
- Code style changes

## Code Quality Standards

- **Type hints required** - mypy strict mode enabled
- **Line length**: 88 characters
- **Import sorting**: Automatic via ruff
- **Python version**: 3.14
- **Coverage**: 100% required

## Documentation

After user-facing changes, verify:
- `docs/` folder is current
- `CHANGELOG.md` is updated
- `README.md` reflects changes (if applicable)

## Key Project Patterns

### Architecture
- `ogion/main.py` - CLI entry point, argcomplete
- `ogion/config.py` - Pydantic settings
- `ogion/core.py` - Backup/restore, subprocess, age encryption
- `ogion/backup_targets/` - PostgreSQL, MariaDB, MySQL, file, folder
- `ogion/upload_providers/` - GCS, S3, Azure, Debug
- `ogion/notifications/` - Discord, Slack, SMTP

### Patterns
- Pydantic models for all configuration
- Abstract base classes with `__init_subclass__` registration
- Context managers for notification wrapping
- Subprocess execution via `core.run_subprocess()`
- age encryption via `core.run_create_age_archive()` / `core.run_decrypt_age_archive()`

## Test Fixtures (conftest.py)

```python
CONST_UNSAFE_AGE_PUBLIC_KEY = "age1q5g88krfjgty48thtctz22h5ja85grufdm0jly3wll6pr9f30qsszmxzm2"
CONST_UNSAFE_AGE_SECRET_KEY = "AGE-SECRET-KEY-12L9ETSAZJXK2XLGQRU503VMJ59NGXASGXKAUH05KJ4TDC6UKTAJQGMSN3L"
CONST_TOKEN_URLSAFE = "mock"

# Fixtures
fixed_const_config_setup  # Sets up temp folders
fixed_secrets_token_urlsafe  # Mocks token for reproducible filenames
provider  # Parametrized: gcs, s3, azure, debug
ALL_POSTGRES_DBS_TARGETS  # All PostgreSQL versions
ALL_MARIADB_DBS_TARGETS  # All MariaDB versions
ALL_MYSQL_DBS_TARGETS  # All MySQL versions
```

## Quick Reference

### Must Follow
1. ✅ Use `monkeypatch`, never `@patch`
2. ✅ 100% coverage required
3. ✅ Update `CHANGELOG.md` for user-facing changes
4. ✅ Run `uv run pre-commit run -a` before committing
5. ✅ Type hints everywhere (mypy strict)
6. ✅ Check docs after changes

### Commands
```bash
uv sync                     # Install dependencies
uv run pytest              # Run tests with coverage
uv run pre-commit run -a   # Lint all files
uv run mypy .              # Type check
mkdocs serve               # Preview docs
```
