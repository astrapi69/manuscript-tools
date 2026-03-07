# manuscript-tools

A Python toolkit for validating, sanitizing and measuring Markdown manuscripts. Built for authors who automate their
publishing workflow.

**[Deutsche Version](README.de.md)**

## What it does

**ms-check** scans your manuscript for style violations. Ships with two built-in rules (typographic dashes, invisible
Unicode characters) and supports custom rules as simple Python callables.

**ms-sanitize** fixes encoding issues, normalizes Unicode (NFKC), strips invisible control characters, replaces
problematic whitespace and ensures consistent line endings. Supports dry-run and backup modes.

**ms-metrics** reports word counts, line counts and character counts per file and in total. Uses regex-based word
boundary matching instead of naive whitespace splitting, so Markdown syntax characters are not counted as words.

## Requirements

- Python 3.11+
- Poetry

## Installation

```bash
git clone <your-repo-url> manuscript-tools
cd manuscript-tools
make install
```

Or manually:

```bash
poetry install
```

## Usage

All commands accept a path (file or directory, default: `manuscript/`), `--include` and `--exclude` glob patterns.

### Style checks

```bash
make check
# or with custom path
make check MANUSCRIPT=chapters/
# or directly
poetry run ms-check manuscript/ --exclude 'drafts/*'
```

Output per file: rule name, violation message and line number. Exit code 1 if any violations are found.

### Sanitization

```bash
# Preview changes without writing
make sanitize-dry

# Apply changes with backup
make sanitize-backup

# Apply changes in-place (no backup)
make sanitize
```

### Text metrics

```bash
make metrics
```

Output:

```
chapter-01.md                     3,412 words   187 lines
chapter-02.md                     2,891 words   154 lines
----------------------------------------
Total                             6,303 words   341 lines    38,219 chars
```

### Combined validation

```bash
# Runs sanitize dry-run followed by style check
make validate
```

## Writing custom rules

A rule is any callable with the signature `(text: str, path: Path) -> list[StyleViolation]`.

```python
from pathlib import Path
from manuscript_tools.checker import check_file
from manuscript_tools.models import StyleViolation


def rule_no_todos(text: str, path: Path) -> list[StyleViolation]:
    return [
        StyleViolation(file=path, rule="no-todos", message="TODO found", line=i)
        for i, line in enumerate(text.splitlines(), start=1)
        if "TODO" in line
    ]


report = check_file(Path("chapter.md"), rules=[rule_no_todos])
```

## Development

```bash
# Install with dev dependencies
make install-dev

# Run tests
make test

# Run tests verbose
make test-v

# Lint
make lint

# Auto-fix lint issues
make lint-fix

# Format code
make format

# Full CI pipeline (lint + format check + tests)
make ci
```

## Project structure

```
src/manuscript_tools/
    __init__.py
    models.py       # Data classes (StyleViolation, FileReport, SanitizeResult, ...)
    io.py           # File discovery and reading
    checker.py      # Style validation with pluggable rules
    sanitizer.py    # Text sanitization (pure logic + file-level operation)
    metrics.py      # Word counting and text statistics
    cli.py          # CLI entry points (ms-check, ms-sanitize, ms-metrics)
tests/
    test_checker.py
    test_sanitizer.py
    test_metrics.py
Makefile            # All tasks in one place
pyproject.toml      # Poetry config, dependencies, tool settings
```

## Makefile targets

Run `make` or `make help` for a complete list:

| Target            | Description                                         |
|-------------------|-----------------------------------------------------|
| `install`         | Install project with all dependencies               |
| `install-dev`     | Install with dev dependencies                       |
| `check`           | Run style checks on manuscript                      |
| `sanitize`        | Sanitize manuscript files in-place                  |
| `sanitize-dry`    | Sanitize dry-run (preview only)                     |
| `sanitize-backup` | Sanitize with .bak backup files                     |
| `metrics`         | Show word counts and text metrics                   |
| `validate`        | Full validation pipeline (sanitize dry-run + check) |
| `test`            | Run all tests                                       |
| `ci`              | Full CI pipeline (lint + format check + tests)      |
| `clean`           | Remove build artifacts and caches                   |
| `build`           | Build distribution package                          |

All manuscript targets accept `MANUSCRIPT=path`, `INCLUDE=pattern` and `EXCLUDE=pattern` variables.

## License

MIT
