"""Markdown sanitization: fix encoding issues, normalize Unicode, strip control chars."""

from __future__ import annotations

import shutil
import unicodedata
from pathlib import Path

import ftfy

from manuscript_tools.invisible import (
    CONTROL_CHARS_RE,
    FORMAT_CHARS,
    REPLACE_MAP,
)
from manuscript_tools.io import read_text
from manuscript_tools.models import SanitizeResult

# ---------------------------------------------------------------------------
# Character maps
# ---------------------------------------------------------------------------

# The canonical sets live in ``invisible`` so the checker cannot drift
# narrower than the sanitizer again. Names kept for the code below.
_CONTROL_CHARS_RE = CONTROL_CHARS_RE
_FORMAT_CHARS = FORMAT_CHARS
_REPLACE_MAP = REPLACE_MAP


# ---------------------------------------------------------------------------
# Pure transformation (no I/O)
# ---------------------------------------------------------------------------


def sanitize_text(text: str) -> str:
    """Apply all sanitization steps to *text* and return the cleaned version."""
    # 1) Fix mojibake. ftfy's default ``uncurl_quotes=True`` would turn the
    #    German quotation marks „…“ and ‚…‘ (and the apostrophe ’)
    #    into ASCII " and ', which is exactly what ms-quotes then has to undo.
    text = ftfy.fix_text(text, uncurl_quotes=False)

    # 2) NFKC normalization
    text = unicodedata.normalize("NFKC", text)

    # 3) Replace known problematic chars
    for char, replacement in _REPLACE_MAP.items():
        text = text.replace(char, replacement)

    # 4) Strip format/bidi controls
    for char in _FORMAT_CHARS:
        text = text.replace(char, "")

    # 5) Remove remaining control chars
    text = _CONTROL_CHARS_RE.sub("", text)

    # 6) Normalize line endings, ensure trailing newline
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text and not text.endswith("\n"):
        text += "\n"

    return text


# ---------------------------------------------------------------------------
# File-level operation
# ---------------------------------------------------------------------------


def sanitize_file(
    path: Path,
    *,
    dry_run: bool = False,
    backup: bool = False,
) -> SanitizeResult:
    """Sanitize a single Markdown file in-place.

    Returns a result indicating whether the file was changed.
    """
    result = SanitizeResult(path=path)

    try:
        original = read_text(path)
    except Exception as exc:
        result.error = str(exc)
        return result

    cleaned = sanitize_text(original)

    if cleaned != original:
        result.changed = True
        if backup:
            shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
        if not dry_run:
            path.write_text(cleaned, encoding="utf-8")

    return result
