"""Normalisation of faked dashes in Markdown files (phase 2).

The ``faked-dashes`` rule in :mod:`manuscript_tools.checker` reports ``--`` and
spaced hyphens standing in for a dash. This module rewrites them, once the
author has said WHICH dash they want.

``target`` is required rather than defaulted, deliberately. There is no single
correct answer:

* An em-dash (U+2014) is the English convention.
* German typography sets the pause dash as an en-dash (U+2013,
  Halbgeviertstrich), so a German manuscript may legitimately want that.
* A corpus that forbids the dash outright wants NEITHER. The correct fix there
  is a comma, a colon or a parenthesis, chosen per sentence. For such a corpus
  this module is the wrong tool: report with ``ms-check`` and edit by hand.

Picking one silently would make the fixer wrong for two of those three cases.

What is rewritten is only the FAKED spelling. An already correct dash is left
alone, including the other real dash: converting U+2013 to U+2014 or back is a
house-style change, not the defect this addresses.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from manuscript_tools.checker import (
    _BULLET,
    _DOUBLE_HYPHEN,
    _FENCE,
    _INLINE_CODE,
    _NUMERIC_RANGE,
    _SPACED_HYPHEN,
    _TABLE_OR_RULE,
)
from manuscript_tools.io import read_text


class DashTarget(Enum):
    """The dash a faked one is rewritten to."""

    EM = "—"
    EN = "–"


@dataclass
class DashResult:
    """Outcome of normalising one file."""

    path: Path
    changed: bool
    replacements: int


def _protected_spans(line: str) -> list[tuple[int, int]]:
    """Ranges of the line that must not be rewritten (inline code)."""
    return [(m.start(), m.end()) for m in _INLINE_CODE.finditer(line)]


def _outside(spans: list[tuple[int, int]], start: int, end: int) -> bool:
    return all(end <= s or start >= e for s, e in spans)


def _normalize_line(line: str, dash: str) -> tuple[str, int]:
    """Rewrite the faked dashes in one line, leaving everything else alone."""
    protected = _protected_spans(line)
    protected += [(m.start(), m.end()) for m in _NUMERIC_RANGE.finditer(line)]
    # The bullet marker is not prose and must survive verbatim.
    bullet = _BULLET.match(line)
    if bullet:
        protected.append((bullet.start(), bullet.end()))

    replacements = 0
    # Right to left, so earlier offsets stay valid as the string changes.
    edits: list[tuple[int, int, str]] = []
    for match in _DOUBLE_HYPHEN.finditer(line):
        if _outside(protected, match.start(), match.end()):
            edits.append((match.start(), match.end(), dash))
    for match in _SPACED_HYPHEN.finditer(line):
        if _outside(protected, match.start(), match.end()):
            edits.append((match.start(), match.end(), f" {dash} "))
    for start, end, replacement in sorted(edits, reverse=True):
        line = line[:start] + replacement + line[end:]
        replacements += 1
    return line, replacements


def normalize_dashes(text: str, target: DashTarget) -> str:
    """Rewrite every faked dash in ``text`` to ``target``.

    Skips exactly what the detector skips: code fences, inline code, bullet
    markers, table separators, horizontal rules, front matter and numeric
    ranges. A fixer that edited those would damage correct text rather than
    merely report noise.
    """
    out: list[str] = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\n\r")
        ending = line[len(stripped) :]
        if _FENCE.match(stripped):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence or _TABLE_OR_RULE.match(stripped):
            out.append(line)
            continue
        rewritten, _ = _normalize_line(stripped, target.value)
        out.append(rewritten + ending)
    return "".join(out)


def count_replacements(text: str, target: DashTarget) -> int:
    """How many faked dashes ``normalize_dashes`` would rewrite."""
    total = 0
    in_fence = False
    for line in text.splitlines():
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence or _TABLE_OR_RULE.match(line):
            continue
        _, n = _normalize_line(line, target.value)
        total += n
    return total


def normalize_file(
    path: Path,
    target: DashTarget,
    *,
    dry_run: bool = False,
    backup: bool = False,
) -> DashResult:
    """Normalise one file. With ``dry_run`` nothing is written."""
    original = read_text(path)
    replacements = count_replacements(original, target)
    if replacements == 0:
        return DashResult(path=path, changed=False, replacements=0)
    if not dry_run:
        if backup:
            shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
        path.write_text(normalize_dashes(original, target), encoding="utf-8")
    return DashResult(path=path, changed=True, replacements=replacements)
