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


# ---------------------------------------------------------------------------
# Repeated words ("der der", "und und", "the the")
# ---------------------------------------------------------------------------

_REPEATED_WORD = re.compile(r"\b(\w{2,})\s+\1\b", re.IGNORECASE | re.UNICODE)


def rule_no_repeated_words(text: str, path: Path) -> list[StyleViolation]:
    """Flag immediately repeated words (e.g. 'der der', 'und und')."""
    violations: list[StyleViolation] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for m in _REPEATED_WORD.finditer(line):
            violations.append(
                StyleViolation(
                    file=path,
                    rule="no-repeated-words",
                    message=f"Wiederholtes Wort: '{m.group(1)}'",
                    line=lineno,
                )
            )
    return violations


# ---------------------------------------------------------------------------
# Sentence length
# ---------------------------------------------------------------------------

_SENTENCE_END = re.compile(r'[.!?]+(?:\s|"|\u201d|\u00bb|$)')
_WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)

# Threshold: sentences longer than this are flagged
MAX_SENTENCE_WORDS = 40


def rule_max_sentence_length(text: str, path: Path) -> list[StyleViolation]:
    """Flag sentences exceeding MAX_SENTENCE_WORDS words.

    Long sentences reduce readability. The default threshold of 40 words
    is generous; most style guides recommend 20-25 for prose.
    """
    violations: list[StyleViolation] = []
    lines = text.splitlines()

    for lineno, line in enumerate(lines, start=1):
        # Skip Markdown headings, code blocks, list markers
        stripped = line.strip()
        if (
            stripped.startswith("#")
            or stripped.startswith("```")
            or stripped.startswith(">")
            or stripped.startswith("- ")
            or stripped.startswith("* ")
            or re.match(r"^\d+\.\s", stripped)
        ):
            continue

        # Split line into sentence fragments at boundaries
        fragments = _SENTENCE_END.split(line)
        for fragment in fragments:
            words = _WORD_RE.findall(fragment)
            if len(words) > MAX_SENTENCE_WORDS:
                violations.append(
                    StyleViolation(
                        file=path,
                        rule="max-sentence-length",
                        message=f"Satz mit {len(words)} Woertern (max {MAX_SENTENCE_WORDS})",
                        line=lineno,
                    )
                )

    return violations


# ---------------------------------------------------------------------------
# Filler words (German)
# ---------------------------------------------------------------------------

# Common German filler words that weaken prose
_FILLER_WORDS_DE: frozenset[str] = frozenset(
    {
        "eigentlich",
        "irgendwie",
        "irgendwann",
        "irgendwo",
        "irgendwas",
        "sozusagen",
        "gewissermasen",
        "grundsaetzlich",
        "quasi",
        "halt",
        "eben",
        "wohl",
        "ziemlich",
        "durchaus",
        "letztendlich",
        "schlussendlich",
        "bekanntlich",
        "selbstverstaendlich",
        "natuerlich",
        "offensichtlich",
        "moeglicherweise",
        "eventuell",
        "gegebenenfalls",
        "im grunde",
        "an sich",
        "an und fuer sich",
        "so gesehen",
        "nichtsdestotrotz",
        "im prinzip",
    }
)

# Build regex from single-word fillers
_FILLER_SINGLE = frozenset(w for w in _FILLER_WORDS_DE if " " not in w)
_FILLER_MULTI = frozenset(w for w in _FILLER_WORDS_DE if " " in w)

_FILLER_SINGLE_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in sorted(_FILLER_SINGLE)) + r")\b",
    re.IGNORECASE,
)

_FILLER_MULTI_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in sorted(_FILLER_MULTI)) + r")\b",
    re.IGNORECASE,
)


def rule_filler_words_de(text: str, path: Path) -> list[StyleViolation]:
    """Flag German filler words that weaken prose.

    This is an advisory rule. Not every occurrence is wrong,
    but high density of filler words typically indicates weak writing.
    """
    violations: list[StyleViolation] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        # Skip headings and code
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("```"):
            continue

        for m in _FILLER_SINGLE_RE.finditer(line):
            violations.append(
                StyleViolation(
                    file=path,
                    rule="filler-words-de",
                    message=f"Fuellwort: '{m.group(1)}'",
                    line=lineno,
                )
            )
        for m in _FILLER_MULTI_RE.finditer(line):
            violations.append(
                StyleViolation(
                    file=path,
                    rule="filler-words-de",
                    message=f"Fuellwort: '{m.group(1)}'",
                    line=lineno,
                )
            )

    return violations


# ---------------------------------------------------------------------------
# Passive voice (German)
# ---------------------------------------------------------------------------

# German passive is formed with "werden/wurde/wird" + past participle
# Past participles: ge...t/ge...en OR inseparable prefix verbs (be-, ver-, er-, zer-, ent-, emp-)
_PARTICIPLE = r"(?:ge\w+(?:t|en|et)|(?:be|ver|er|zer|ent|emp|miss)\w+(?:t|en|et))"

_PASSIVE_PATTERN = re.compile(
    r"\b(wird|werde|werden|wurde|wurden|wirst|wuerde|wuerden)"
    r"\s+[\w\s]{0,30}?"
    r"\b(" + _PARTICIPLE + r")\b",
    re.IGNORECASE,
)

# "worden" as indicator of Perfekt-Passiv
_WORDEN_PATTERN = re.compile(
    r"\b(ist|sind|war|waren)\s+[\w\s]{0,30}?\b(" + _PARTICIPLE + r")\s+worden\b",
    re.IGNORECASE,
)


def rule_passive_voice_de(text: str, path: Path) -> list[StyleViolation]:
    """Flag potential passive voice constructions in German text.

    Passive voice is not always wrong, but high density often indicates
    weak, impersonal writing. This rule helps identify passages that
    could benefit from active reformulation.
    """
    violations: list[StyleViolation] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("```"):
            continue

        for m in _PASSIVE_PATTERN.finditer(line):
            violations.append(
                StyleViolation(
                    file=path,
                    rule="passive-voice-de",
                    message=(f"Passivkonstruktion: '{m.group(1)} ... {m.group(2)}'"),
                    line=lineno,
                )
            )
        for m in _WORDEN_PATTERN.finditer(line):
            violations.append(
                StyleViolation(
                    file=path,
                    rule="passive-voice-de",
                    message=(f"Perfekt-Passiv: '{m.group(1)} ... {m.group(2)} worden'"),
                    line=lineno,
                )
            )

    return violations


# ---------------------------------------------------------------------------
# Double spaces
# ---------------------------------------------------------------------------

_DOUBLE_SPACE = re.compile(r"(?<!\n) {2,}(?!\n)")


def rule_no_double_spaces(text: str, path: Path) -> list[StyleViolation]:
    """Flag double or multiple spaces within lines."""
    violations: list[StyleViolation] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            continue
        if _DOUBLE_SPACE.search(line):
            violations.append(
                StyleViolation(
                    file=path,
                    rule="no-double-spaces",
                    message="Doppelte Leerzeichen gefunden",
                    line=lineno,
                )
            )
    return violations


# ---------------------------------------------------------------------------
# Non-German quotation marks
# ---------------------------------------------------------------------------


def rule_non_german_quotes(text: str, path: Path) -> list[StyleViolation]:
    """Flag lines containing non-German quotation marks.

    Detects straight double quotes (\"), English closing double (\u201d)
    and English closing single (\u2019) outside of code spans and HTML attributes.
    Use ms-quotes to fix them automatically.
    """
    from manuscript_tools.quotes import has_non_german_quotes

    violations: list[StyleViolation] = []
    in_code_block = False

    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        if has_non_german_quotes(line):
            violations.append(
                StyleViolation(
                    file=path,
                    rule="non-german-quotes",
                    message="Nicht-deutsche Anführungszeichen gefunden",
                    line=lineno,
                )
            )
    return violations


# ---------------------------------------------------------------------------
# Rule sets
# ---------------------------------------------------------------------------

# Core rules: always relevant, low noise
CORE_RULES: list[StyleRule] = [
    rule_no_dashes,
    rule_no_invisible_chars,
    rule_no_repeated_words,
    rule_no_double_spaces,
    rule_non_german_quotes,
]

# German prose rules: advisory, may produce false positives
PROSE_RULES_DE: list[StyleRule] = [
    rule_max_sentence_length,
    rule_filler_words_de,
    rule_passive_voice_de,
]

# Default: core rules only (backwards compatible)
DEFAULT_RULES: list[StyleRule] = [*CORE_RULES]

# Full: core + prose (for thorough analysis)
ALL_RULES_DE: list[StyleRule] = [*CORE_RULES, *PROSE_RULES_DE]

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
