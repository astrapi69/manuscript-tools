"""German quotation mark conversion for Markdown files.

Converts straight and English typographic quotation marks to German style:
  Double: „ " (U+201E / U+201C)
  Single: ‚ ' (U+201A / U+2018)

Respects frontmatter, fenced code blocks, inline code spans and HTML attributes.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from manuscript_tools.io import read_text

# ---------------------------------------------------------------------------
# Character constants
# ---------------------------------------------------------------------------

# German target
DE_OPEN_DOUBLE = "\u201e"  # „
DE_CLOSE_DOUBLE = "\u201c"  # "
DE_OPEN_SINGLE = "\u201a"  # ‚
DE_CLOSE_SINGLE = "\u2018"  # '

# English typographic
EN_OPEN_DOUBLE = "\u201c"  # " (identical to DE_CLOSE_DOUBLE)
EN_CLOSE_DOUBLE = "\u201d"  # \u201d
EN_OPEN_SINGLE = "\u2018"  # ' (identical to DE_CLOSE_SINGLE)
EN_CLOSE_SINGLE = "\u2019"  # '

# Straight ASCII
STRAIGHT_DOUBLE = '"'
STRAIGHT_SINGLE = "'"

# All non-German quote characters (for detection)
NON_GERMAN_QUOTES = frozenset(
    {
        STRAIGHT_DOUBLE,
        EN_CLOSE_DOUBLE,  # U+201D
        EN_CLOSE_SINGLE,  # U+2019
    }
)

# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


@dataclass
class QuoteStats:
    """Statistics for a quote conversion run."""

    straight_double: int = 0
    english_double: int = 0
    english_single: int = 0
    lines_changed: int = 0
    warnings: int = 0
    warning_messages: list[str] = field(default_factory=list)

    @property
    def total_replacements(self) -> int:
        return self.straight_double + self.english_double + self.english_single

    @property
    def has_changes(self) -> bool:
        return self.total_replacements > 0


# ---------------------------------------------------------------------------
# Protected regions (inline code, HTML attributes)
# ---------------------------------------------------------------------------

_INLINE_CODE_RE = re.compile(r"`[^`]+`")
_HTML_ATTR_DOUBLE_RE = re.compile(r'(?:[\w-]+)\s*=\s*"[^"]*"')
_HTML_ATTR_SINGLE_RE = re.compile(r"(?:[\w-]+)\s*=\s*'[^']*'")


def _mask_protected_regions(line: str) -> list[tuple[int, int]]:
    """Return (start, end) ranges that must not be modified."""
    protected: list[tuple[int, int]] = []
    for pattern in (_INLINE_CODE_RE, _HTML_ATTR_DOUBLE_RE, _HTML_ATTR_SINGLE_RE):
        for m in pattern.finditer(line):
            protected.append((m.start(), m.end()))
    return protected


def _is_protected(pos: int, protected: list[tuple[int, int]]) -> bool:
    return any(start <= pos < end for start, end in protected)


def _find_unprotected(line: str, char: str, protected: list[tuple[int, int]]) -> list[int]:
    """Find all unprotected positions of *char* in *line*."""
    return [i for i, ch in enumerate(line) if ch == char and not _is_protected(i, protected)]


# ---------------------------------------------------------------------------
# Replacement functions (pure, no I/O)
# ---------------------------------------------------------------------------


def _replace_straight_double(
    line: str,
    protected: list[tuple[int, int]],
    stats: QuoteStats,
    line_num: int,
) -> str:
    """Replace straight double quotes pairwise with German „ "."""
    chars = list(line)
    straight_positions = _find_unprotected(line, STRAIGHT_DOUBLE, protected)

    if not straight_positions:
        return line

    # Phase 1: Match existing „ (U+201E) with a following straight " as closer
    orphan_openers = [
        i for i, ch in enumerate(chars) if ch == DE_OPEN_DOUBLE and not _is_protected(i, protected)
    ]

    consumed: set[int] = set()
    for opener_pos in orphan_openers:
        for sp in straight_positions:
            if sp > opener_pos and sp not in consumed:
                chars[sp] = DE_CLOSE_DOUBLE
                consumed.add(sp)
                stats.straight_double += 1
                break

    # Phase 2: Remaining straight " pairwise
    remaining = [p for p in straight_positions if p not in consumed]

    if len(remaining) % 2 != 0:
        msg = (
            f'Zeile {line_num}: Asymmetrisches gerades Anführungszeichen (") '
            f"- {len(remaining)} ungepaart"
        )
        stats.warning_messages.append(msg)
        stats.warnings += 1
        return "".join(chars)

    for i in range(0, len(remaining), 2):
        chars[remaining[i]] = DE_OPEN_DOUBLE
        chars[remaining[i + 1]] = DE_CLOSE_DOUBLE
        stats.straight_double += 1

    return "".join(chars)


def _replace_english_double(
    line: str,
    protected: list[tuple[int, int]],
    stats: QuoteStats,
) -> str:
    """Replace English typographic double quotes "\u201c \u201d with German „ "."""
    chars = list(line)

    close_positions = [
        i for i, ch in enumerate(chars) if ch == EN_CLOSE_DOUBLE and not _is_protected(i, protected)
    ]

    if not close_positions:
        return line

    open_positions = [
        i for i, ch in enumerate(chars) if ch == EN_OPEN_DOUBLE and not _is_protected(i, protected)
    ]

    changed = False
    used_close: set[int] = set()

    # Match pairs: U+201C ... U+201D -> U+201E ... U+201C
    for op in open_positions:
        for ci, cp in enumerate(close_positions):
            if cp > op and ci not in used_close:
                chars[op] = DE_OPEN_DOUBLE
                chars[cp] = DE_CLOSE_DOUBLE
                used_close.add(ci)
                changed = True
                break

    # Remaining standalone U+201D -> U+201C
    for ci, cp in enumerate(close_positions):
        if ci not in used_close:
            chars[cp] = DE_CLOSE_DOUBLE
            changed = True

    if changed:
        stats.english_double += 1

    return "".join(chars)


def _replace_english_single(
    line: str,
    protected: list[tuple[int, int]],
    stats: QuoteStats,
) -> str:
    """Replace English typographic single quotes ' ' with German ‚ '."""
    chars = list(line)

    open_positions = [
        i for i, ch in enumerate(chars) if ch == EN_OPEN_SINGLE and not _is_protected(i, protected)
    ]
    close_positions = [
        i for i, ch in enumerate(chars) if ch == EN_CLOSE_SINGLE and not _is_protected(i, protected)
    ]

    if not open_positions and not close_positions:
        return line

    changed = False
    used_close: set[int] = set()

    for op in open_positions:
        for ci, cp in enumerate(close_positions):
            if cp > op and ci not in used_close:
                chars[op] = DE_OPEN_SINGLE
                chars[cp] = DE_CLOSE_SINGLE
                used_close.add(ci)
                changed = True
                break

    if changed:
        stats.english_single += 1

    return "".join(chars)


# ---------------------------------------------------------------------------
# Line and file processing (pure, no I/O)
# ---------------------------------------------------------------------------


def convert_line(line: str, line_num: int, stats: QuoteStats) -> str:
    """Convert all quotation marks in a single line to German style."""
    protected = _mask_protected_regions(line)
    line = _replace_straight_double(line, protected, stats, line_num)

    protected = _mask_protected_regions(line)
    line = _replace_english_double(line, protected, stats)

    protected = _mask_protected_regions(line)
    line = _replace_english_single(line, protected, stats)

    return line


def convert_text(text: str) -> tuple[str, QuoteStats]:
    """Convert all quotation marks in *text* to German style.

    Pure function: string in, string + stats out.
    Respects YAML frontmatter and fenced code blocks.
    """
    stats = QuoteStats()
    lines = text.split("\n")
    result_lines: list[str] = []

    in_code_block = False
    in_frontmatter = False

    for line_num_0, line in enumerate(lines):
        line_num = line_num_0 + 1
        stripped = line.rstrip()

        # Frontmatter
        if line_num_0 == 0 and stripped == "---":
            in_frontmatter = True
            result_lines.append(line)
            continue

        if in_frontmatter and stripped == "---":
            in_frontmatter = False
            result_lines.append(line)
            continue

        if in_frontmatter:
            result_lines.append(line)
            continue

        # Fenced code blocks
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            result_lines.append(line)
            continue

        if in_code_block:
            result_lines.append(line)
            continue

        # Normal line
        new_line = convert_line(line, line_num, stats)
        if new_line != line:
            stats.lines_changed += 1
        result_lines.append(new_line)

    return "\n".join(result_lines), stats


# ---------------------------------------------------------------------------
# Detection (for checker rule)
# ---------------------------------------------------------------------------

_NON_GERMAN_QUOTE_RE = re.compile(r'["\u201d\u2019]')


def has_non_german_quotes(line: str) -> bool:
    """Check if a line contains non-German quotation marks outside protected regions."""
    protected = _mask_protected_regions(line)
    return any(not _is_protected(m.start(), protected) for m in _NON_GERMAN_QUOTE_RE.finditer(line))


# ---------------------------------------------------------------------------
# File-level operations (I/O)
# ---------------------------------------------------------------------------


@dataclass
class QuoteFileResult:
    """Result of converting quotes in a single file."""

    path: Path
    stats: QuoteStats = field(default_factory=QuoteStats)
    changed: bool = False
    error: str | None = None


def convert_file(
    path: Path,
    *,
    dry_run: bool = False,
    backup: bool = True,
) -> QuoteFileResult:
    """Convert quotation marks in a single file to German style."""
    result = QuoteFileResult(path=path)

    try:
        original = read_text(path)
    except Exception as exc:
        result.error = str(exc)
        return result

    converted, stats = convert_text(original)
    result.stats = stats

    if converted != original:
        result.changed = True
        if backup and not dry_run:
            shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
        if not dry_run:
            path.write_text(converted, encoding="utf-8")

    return result
