"""Text metrics: word counts, sentence analysis, syllable counting, readability."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple

from manuscript_tools.io import read_text
from manuscript_tools.models import FileMetricsReport, ReadabilityStats

# ---------------------------------------------------------------------------
# Legacy NamedTuple (kept for backwards compatibility)
# ---------------------------------------------------------------------------


class FileMetrics(NamedTuple):
    """Basic metrics for a single file (legacy interface)."""

    path: Path
    words: int
    lines: int
    chars: int
    error: str | None = None


# ---------------------------------------------------------------------------
# Word counting
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)


def count_words(text: str) -> int:
    """Count words using word-boundary matching.

    More accurate than str.split() because it ignores Markdown syntax
    characters like #, *, >, etc.
    """
    return len(_WORD_RE.findall(text))


# ---------------------------------------------------------------------------
# Sentence splitting
# ---------------------------------------------------------------------------

# Markdown elements to strip before sentence analysis
_MD_HEADING = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_MD_BLOCKQUOTE = re.compile(r"^>\s*", re.MULTILINE)
_MD_LIST_MARKER = re.compile(r"^[\s]*[-*+]\s+", re.MULTILINE)
_MD_ORDERED_LIST = re.compile(r"^[\s]*\d+\.\s+", re.MULTILINE)
_MD_EMPHASIS = re.compile(r"(\*{1,3}|_{1,3})")
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MD_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]+\)")
_MD_CODE_BLOCK = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_MD_INLINE_CODE = re.compile(r"`[^`]+`")
_MD_HR = re.compile(r"^[-*_]{3,}\s*$", re.MULTILINE)

# Sentence boundary: period, exclamation, question mark followed by space or end
_SENTENCE_END = re.compile(r'[.!?]+(?:\s|"|\u201d|\u00bb|$)')


def _strip_markdown(text: str) -> str:
    """Remove Markdown formatting to get plain prose for analysis."""
    text = _MD_CODE_BLOCK.sub("", text)
    text = _MD_INLINE_CODE.sub("CODE", text)
    text = _MD_IMAGE.sub("", text)
    text = _MD_LINK.sub(r"\1", text)
    text = _MD_HR.sub("", text)
    text = _MD_HEADING.sub("", text)
    text = _MD_BLOCKQUOTE.sub("", text)
    text = _MD_LIST_MARKER.sub("", text)
    text = _MD_ORDERED_LIST.sub("", text)
    text = _MD_EMPHASIS.sub("", text)
    return text


def split_sentences(text: str) -> list[str]:
    """Split text into sentences.

    Strips Markdown syntax first, then splits on sentence-ending punctuation.
    Filters out empty results and very short fragments.
    """
    plain = _strip_markdown(text)
    # Split on sentence boundaries
    raw = _SENTENCE_END.split(plain)
    # Clean up and filter
    sentences = []
    for s in raw:
        cleaned = s.strip()
        # Must contain at least one word
        if cleaned and _WORD_RE.search(cleaned):
            sentences.append(cleaned)
    return sentences


# ---------------------------------------------------------------------------
# Syllable counting (German-optimized, works for English too)
# ---------------------------------------------------------------------------

_VOWEL_GROUPS = re.compile(r"[aeiouyVaeiouyaeou]+", re.IGNORECASE)

# German diphthongs and special vowel combinations that count as one syllable
_DE_DIPHTHONGS = re.compile(
    r"(ei|ai|au|eu|aeu|oe|ue|ie|aa|ee|oo)",
    re.IGNORECASE,
)


def count_syllables_word(word: str) -> int:
    """Estimate syllable count for a single word.

    Optimized for German but works reasonably for English.
    Uses vowel-group counting with adjustments for diphthongs
    and common suffixes.
    """
    word = word.lower().strip()
    if not word:
        return 0
    if len(word) <= 3:
        return 1

    # Replace diphthongs with single marker to avoid double-counting
    collapsed = _DE_DIPHTHONGS.sub("V", word)

    # Count remaining vowel groups
    groups = _VOWEL_GROUPS.findall(collapsed)
    count = len(groups)

    # German suffix adjustments
    if word.endswith("e") and not word.endswith("le"):
        # Final silent-ish 'e' in German is often still a syllable,
        # but already counted by vowel groups, so no adjustment needed
        pass

    # Common suffixes that add a syllable
    for suffix in ("tion", "sion", "ment", "heit", "keit", "ung", "lich"):
        if word.endswith(suffix):
            # These are typically already captured, but ensure minimum
            count = max(count, 2)
            break

    return max(count, 1)


def count_syllables(text: str) -> int:
    """Count total syllables in text."""
    words = _WORD_RE.findall(text)
    return sum(count_syllables_word(w) for w in words)


# ---------------------------------------------------------------------------
# Flesch Reading Ease (German adaptation)
# ---------------------------------------------------------------------------


def flesch_de(
    total_words: int,
    total_sentences: int,
    total_syllables: int,
) -> float:
    """Compute Flesch Reading Ease for German text.

    Formula (Amstad, 1978):
        180 - ASL - (58.5 * ASW)

    Where ASL = average sentence length (words/sentence)
    and ASW = average syllables per word.

    Score interpretation:
        0-30:  Sehr schwer (akademisch, juristisch)
        30-50: Schwer (Fachliteratur)
        50-60: Mittelschwer (Qualitaetsjournalismus)
        60-70: Mittel (Belletristik, Sachbuch)
        70-80: Leicht (Unterhaltungsliteratur)
        80-100: Sehr leicht (Kinderbuch, einfache Sprache)
    """
    if total_words == 0 or total_sentences == 0:
        return 0.0

    asl = total_words / total_sentences
    asw = total_syllables / total_words
    score = 180.0 - asl - (58.5 * asw)

    return round(max(0.0, min(score, 100.0)), 1)


def flesch_de_label(score: float) -> str:
    """Human-readable label for a Flesch-DE score."""
    if score >= 80:
        return "Sehr leicht"
    if score >= 70:
        return "Leicht"
    if score >= 60:
        return "Mittel"
    if score >= 50:
        return "Mittelschwer"
    if score >= 30:
        return "Schwer"
    return "Sehr schwer"


# ---------------------------------------------------------------------------
# Readability analysis (combines everything)
# ---------------------------------------------------------------------------


def analyze_readability(text: str) -> ReadabilityStats:
    """Full readability analysis of a text.

    Returns word count, sentence count, syllable count, averages,
    Flesch-DE score, and longest sentence info.
    """
    words = _WORD_RE.findall(text)
    word_count = len(words)
    syllable_count = sum(count_syllables_word(w) for w in words)
    sentences = split_sentences(text)
    sentence_count = len(sentences)
    char_count = len(text)
    line_count = text.count("\n")

    # Sentence length analysis
    longest_words = 0
    longest_line = 0
    if sentences:
        # Find sentence with most words and approximate its line
        lines = text.splitlines()
        for sent in sentences:
            sent_words = len(_WORD_RE.findall(sent))
            if sent_words > longest_words:
                longest_words = sent_words
                # Find approximate line number
                prefix = sent[:40]
                for i, line in enumerate(lines, start=1):
                    if prefix in line:
                        longest_line = i
                        break

    # Averages
    avg_sentence = word_count / sentence_count if sentence_count else 0.0
    avg_word_len = sum(len(w) for w in words) / word_count if word_count else 0.0
    avg_syllables = syllable_count / word_count if word_count else 0.0

    return ReadabilityStats(
        sentences=sentence_count,
        words=word_count,
        syllables=syllable_count,
        chars=char_count,
        lines=line_count,
        avg_sentence_length=round(avg_sentence, 1),
        avg_word_length=round(avg_word_len, 1),
        avg_syllables_per_word=round(avg_syllables, 2),
        flesch_de=flesch_de(word_count, sentence_count, syllable_count),
        longest_sentence_words=longest_words,
        longest_sentence_line=longest_line,
    )


# ---------------------------------------------------------------------------
# File-level API
# ---------------------------------------------------------------------------


def file_metrics(path: Path) -> FileMetrics:
    """Compute basic metrics for a single file (legacy interface)."""
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


def file_readability(path: Path) -> FileMetricsReport:
    """Compute full readability metrics for a single file."""
    try:
        text = read_text(path)
    except Exception as exc:
        return FileMetricsReport(path=path, error=str(exc))

    return FileMetricsReport(
        path=path,
        readability=analyze_readability(text),
    )


def batch_metrics(files: Sequence[Path]) -> list[FileMetrics]:
    """Compute basic metrics for multiple files."""
    return [file_metrics(f) for f in files]


def batch_readability(files: Sequence[Path]) -> list[FileMetricsReport]:
    """Compute full readability metrics for multiple files."""
    return [file_readability(f) for f in files]
