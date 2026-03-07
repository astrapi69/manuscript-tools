"""Markdown sanitization: fix encoding issues, normalize Unicode, strip control chars."""

from __future__ import annotations

import re
import shutil
import unicodedata
from pathlib import Path

import ftfy

from manuscript_tools.io import read_text
from manuscript_tools.models import SanitizeResult

# ---------------------------------------------------------------------------
# Character maps
# ---------------------------------------------------------------------------

_CONTROL_CHARS_RE = re.compile(
    r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]"
)  # preserves \t (0009), \n (000A), \r (000D)

_FORMAT_CHARS: frozenset[str] = frozenset(
    {
        "\u200b",  # ZWSP
        "\u200c",  # ZWNJ
        "\u200d",  # ZWJ
        "\u200e",  # LRM
        "\u200f",  # RLM
        "\u202a",
        "\u202b",
        "\u202c",
        "\u202d",
        "\u202e",  # bidi overrides
        "\ufeff",  # BOM
    }
)

_REPLACE_MAP: dict[str, str] = {
    "\u00ad": "",  # soft hyphen
    "\u2028": "\n",  # line separator
    "\u2029": "\n",  # paragraph separator
    "\u202f": " ",  # narrow no-break space
    "\u00a0": " ",  # no-break space
}


# ---------------------------------------------------------------------------
# Pure transformation (no I/O)
# ---------------------------------------------------------------------------


def sanitize_text(text: str) -> str:
    """Apply all sanitization steps to *text* and return the cleaned version."""
    # 1) Fix mojibake
    text = ftfy.fix_text(text)

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
