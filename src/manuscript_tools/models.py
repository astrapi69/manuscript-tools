"""Shared data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class StyleViolation:
    """A single style rule violation."""

    file: Path
    rule: str
    message: str
    line: int | None = None


@dataclass
class FileReport:
    """Result of processing a single file."""

    path: Path
    words: int = 0
    violations: list[StyleViolation] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and len(self.violations) == 0


@dataclass
class SanitizeResult:
    """Result of sanitizing a single file."""

    path: Path
    changed: bool = False
    error: str | None = None


@dataclass
class ReadabilityStats:
    """Readability metrics for a text or file."""

    sentences: int = 0
    words: int = 0
    syllables: int = 0
    chars: int = 0
    lines: int = 0
    avg_sentence_length: float = 0.0
    avg_word_length: float = 0.0
    avg_syllables_per_word: float = 0.0
    flesch_de: float = 0.0
    longest_sentence_words: int = 0
    longest_sentence_line: int = 0


@dataclass
class FileMetricsReport:
    """Full metrics report for a single file."""

    path: Path
    readability: ReadabilityStats = field(default_factory=ReadabilityStats)
    error: str | None = None


@dataclass
class RunStats:
    """Aggregated statistics for a batch run."""

    files_seen: int = 0
    files_ok: int = 0
    files_failed: int = 0
    total_words: int = 0
    total_violations: int = 0
    errors: int = 0
