"""Text metrics: word counts and basic statistics."""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple, Sequence

from manuscript_tools.io import read_text


class FileMetrics(NamedTuple):
    """Metrics for a single file."""

    path: Path
    words: int
    lines: int
    chars: int
    error: str | None = None


# Matches sequences of word characters (handles Unicode letters too)
_WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)


def count_words(text: str) -> int:
    """Count words in *text* using word-boundary matching.

    More accurate than str.split() because it ignores Markdown syntax
    characters like #, *, >, etc.
    """
    return len(_WORD_RE.findall(text))


def file_metrics(path: Path) -> FileMetrics:
    """Compute metrics for a single file."""
    try:
        text = read_text(path)
    except Exception as exc:
        return FileMetrics(path=path, words=0, lines=0, chars=0, error=str(exc))

    return FileMetrics(
        path=path,
        words=count_words(text),
        lines=text.count("\n"),
        chars=len(text),
    )


def batch_metrics(files: Sequence[Path]) -> list[FileMetrics]:
    """Compute metrics for multiple files."""
    return [file_metrics(f) for f in files]
