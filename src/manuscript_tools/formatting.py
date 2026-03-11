"""Detect and fix broken Markdown bold/italic formatting.

Finds cases where a code formatter (e.g. Eclipse) wrapped lines inside
bold (**) or italic (*) markers, causing the asterisks to render literally.

Common broken patterns:
    text with **         <- opening marker orphaned at end of line
    bold content**       <- closing marker on next line

    text with **bold     <- opening marker, text continues on next line
    content** here       <- closing marker on next line

    text *italic         <- same for single asterisks
    content* here

    text **bold content  <- closing marker orphaned at start of next line
    ** continues here
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from manuscript_tools.io import read_text

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

# Line ends with opening bold/italic marker (possibly with trailing space)
# Excludes list markers (line starting with * ), horizontal rules (***), and headings
_ORPHAN_OPEN_END = re.compile(r"(?<!\*)\*{1,2}\s*$")

# Line starts with closing bold/italic marker (possibly with leading space)
_ORPHAN_CLOSE_START = re.compile(r"^\s*\*{1,2}(?!\*)")

# Bold/italic that opens on one line and closes on the next:
# We detect this by finding unmatched opening markers on a line
_UNMATCHED_BOLD_OPEN = re.compile(r"\*\*(?!.*\*\*)")
_UNMATCHED_ITALIC_OPEN = re.compile(r"(?<!\*)\*(?!\*)(?!.*(?<!\*)\*(?!\*))")

# Closing marker at start of line (continuation from previous)
_CLOSE_BOLD_START = re.compile(r"^(.*?)\*\*")
_CLOSE_ITALIC_START = re.compile(r"^(.*?)(?<!\*)\*(?!\*)")


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


@dataclass
class FormatStats:
    """Statistics for a formatting fix run."""

    broken_bold: int = 0
    broken_italic: int = 0
    lines_fixed: int = 0
    warnings: int = 0
    warning_messages: list[str] = field(default_factory=list)

    @property
    def total_fixes(self) -> int:
        return self.broken_bold + self.broken_italic

    @property
    def has_changes(self) -> bool:
        return self.total_fixes > 0


# ---------------------------------------------------------------------------
# Detection (for checker rule)
# ---------------------------------------------------------------------------


def has_broken_formatting(lines: list[str], line_idx: int) -> list[str]:
    """Check if a line has broken bold/italic formatting.

    Returns a list of problem descriptions (empty if clean).
    Needs access to adjacent lines for context.
    """
    problems: list[str] = []
    line = lines[line_idx]
    stripped = line.rstrip()

    # Skip code blocks, headings, list markers, horizontal rules
    trimmed = stripped.lstrip()
    if trimmed.startswith("```") or trimmed.startswith("#") or trimmed in ("***", "---", "___"):
        return problems

    is_list_marker = bool(re.match(r"^\s*\*\s+\S", line))
    is_bare_asterisk = bool(re.match(r"^\s*\*\s*$", stripped))

    # Pattern 1: Line ends with orphaned ** or *
    has_next = line_idx + 1 < len(lines) and bool(lines[line_idx + 1].strip())
    if (
        _ORPHAN_OPEN_END.search(stripped)
        and not is_list_marker
        and not is_bare_asterisk
        and has_next
    ):
        is_bold = stripped.endswith("**")
        marker = "**" if is_bold else "*"
        problems.append(f"Oeffnendes {marker} am Zeilenende (Formatierung gebrochen)")

    # Pattern 2: Line starts with orphaned ** or * that closes from previous line
    if line_idx > 0 and _ORPHAN_CLOSE_START.match(trimmed) and not is_list_marker:
        match = _ORPHAN_CLOSE_START.match(trimmed)
        if match and match.group(0).strip() in ("*", "**"):
            marker = match.group(0).strip()
            problems.append(f"Schliessendes {marker} am Zeilenanfang (Formatierung gebrochen)")

    return problems


# ---------------------------------------------------------------------------
# Fix logic (pure, no I/O)
# ---------------------------------------------------------------------------


def fix_broken_formatting(text: str) -> tuple[str, FormatStats]:
    """Fix broken bold/italic formatting caused by line wrapping.

    Pure function: string in, string + stats out.
    Joins lines where bold/italic markers were split across line boundaries.
    """
    stats = FormatStats()
    lines = text.split("\n")
    result: list[str] = []

    in_code_block = False
    in_frontmatter = False
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip()
        trimmed = stripped.lstrip()

        # Frontmatter
        if i == 0 and trimmed == "---":
            in_frontmatter = True
            result.append(line)
            i += 1
            continue

        if in_frontmatter and trimmed == "---":
            in_frontmatter = False
            result.append(line)
            i += 1
            continue

        if in_frontmatter:
            result.append(line)
            i += 1
            continue

        # Code blocks
        if trimmed.startswith("```"):
            in_code_block = not in_code_block
            result.append(line)
            i += 1
            continue

        if in_code_block:
            result.append(line)
            i += 1
            continue

        # Skip horizontal rules and pure list markers
        if trimmed in ("***", "---", "___"):
            result.append(line)
            i += 1
            continue

        # Check for orphaned opening marker at end of line
        is_list = bool(re.match(r"^\s*\*\s+\S", line))
        is_bare = bool(re.match(r"^\s*\*\s*$", stripped))

        if i + 1 < len(lines) and _ORPHAN_OPEN_END.search(stripped) and not is_list and not is_bare:
            next_line = lines[i + 1].strip()
            skip_next = not next_line or next_line.startswith(("#", "```", "- ", "* ", "1."))

            if not skip_next:
                is_bold = stripped.endswith("**")
                close_pattern = _CLOSE_BOLD_START if is_bold else _CLOSE_ITALIC_START

                if close_pattern.search(next_line):
                    merged = stripped + next_line
                    result.append(merged)

                    if is_bold:
                        stats.broken_bold += 1
                    else:
                        stats.broken_italic += 1
                    stats.lines_fixed += 1

                    i += 2
                    continue

        # Check for orphaned closing marker at start of line
        if i > 0 and result and _ORPHAN_CLOSE_START.match(trimmed) and not is_list:
            match = _ORPHAN_CLOSE_START.match(trimmed)
            if match and match.group(0).strip() in ("*", "**"):
                marker = match.group(0).strip()
                is_bold = marker == "**"

                prev = result[-1].rstrip()
                merged = prev + trimmed
                result[-1] = merged

                if is_bold:
                    stats.broken_bold += 1
                else:
                    stats.broken_italic += 1
                stats.lines_fixed += 1

                i += 1
                continue

        result.append(line)
        i += 1

    return "\n".join(result), stats


# ---------------------------------------------------------------------------
# File-level operations (I/O)
# ---------------------------------------------------------------------------


@dataclass
class FormatFileResult:
    """Result of fixing formatting in a single file."""

    path: Path
    stats: FormatStats = field(default_factory=FormatStats)
    changed: bool = False
    error: str | None = None


def fix_formatting_file(
    path: Path,
    *,
    dry_run: bool = False,
    backup: bool = True,
) -> FormatFileResult:
    """Fix broken formatting in a single file."""
    result = FormatFileResult(path=path)

    try:
        original = read_text(path)
    except Exception as exc:
        result.error = str(exc)
        return result

    fixed, stats = fix_broken_formatting(original)
    result.stats = stats

    if fixed != original:
        result.changed = True
        if backup and not dry_run:
            shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
        if not dry_run:
            path.write_text(fixed, encoding="utf-8")

    return result
