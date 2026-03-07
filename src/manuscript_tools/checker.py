"""Style checking with pluggable rules."""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from pathlib import Path

from manuscript_tools.io import read_text
from manuscript_tools.models import FileReport, StyleViolation

# ---------------------------------------------------------------------------
# Rule type: callable(text, path) -> list[StyleViolation]
# ---------------------------------------------------------------------------
StyleRule = Callable[[str, Path], list[StyleViolation]]

# ---------------------------------------------------------------------------
# Built-in rules
# ---------------------------------------------------------------------------

_DASH_PATTERN = re.compile(r"[\u2013\u2014]")


def rule_no_dashes(text: str, path: Path) -> list[StyleViolation]:
    """Flag en-dashes and em-dashes."""
    violations: list[StyleViolation] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _DASH_PATTERN.search(line):
            violations.append(
                StyleViolation(
                    file=path,
                    rule="no-dashes",
                    message="Gedankenstrich (en/em-dash) gefunden",
                    line=lineno,
                )
            )
    return violations


_ZWSP_PATTERN = re.compile(r"[\u200b\u200c\u200d\u200e\u200f\ufeff]")


def rule_no_invisible_chars(text: str, path: Path) -> list[StyleViolation]:
    """Flag zero-width and invisible Unicode characters."""
    violations: list[StyleViolation] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _ZWSP_PATTERN.search(line):
            violations.append(
                StyleViolation(
                    file=path,
                    rule="no-invisible-chars",
                    message="Unsichtbare Unicode-Zeichen gefunden",
                    line=lineno,
                )
            )
    return violations


# Default rule set
DEFAULT_RULES: list[StyleRule] = [rule_no_dashes, rule_no_invisible_chars]

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_file(
    path: Path,
    rules: Sequence[StyleRule] | None = None,
) -> FileReport:
    """Run all *rules* against a single file and return a report."""
    active_rules = rules if rules is not None else DEFAULT_RULES
    report = FileReport(path=path)

    try:
        text = read_text(path)
    except Exception as exc:
        report.error = str(exc)
        return report

    report.words = len(text.split())

    for rule in active_rules:
        report.violations.extend(rule(text, path))

    return report


def check_files(
    files: Sequence[Path],
    rules: Sequence[StyleRule] | None = None,
) -> list[FileReport]:
    """Run checks on multiple files."""
    return [check_file(f, rules=rules) for f in files]
