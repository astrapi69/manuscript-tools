"""Rewrite ASCII umlaut spellings ("fuer") to real umlauts ("für").

The rule in ``checker`` only reports; this module rewrites. Both work from
the identical curated word list (``checker.UMLAUT_WORDS`` plus
``umlaut-words-extra`` from the configuration), so detector and fixer can
never disagree about what is a finding.

Why a word list and not a pattern: German is full of legitimate ae/oe/ue
sequences — diphthong plus e ("Frauen", "Feuer", "neue"), names ("Goethe",
"Michael") and loanwords ("Aerobic", "Poesie"). Only whole tokens from the
vetted list are ever touched.

ss -> ß is deliberately out of scope: it needs context-dependent rules
(Masse vs. Maße), collides with Swiss orthography, and a wrong ß damages a
text worse than a missing one.
"""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from manuscript_tools.checker import (
    _BARE_URL,
    _FENCE,
    _INLINE_CODE,
    _LINK_TARGET,
    build_umlaut_pattern,
    umlautify,
)
from manuscript_tools.io import read_text


@dataclass
class UmlautResult:
    """Outcome of rewriting one file."""

    path: Path
    changed: bool
    replacements: int


def _protected_spans(line: str) -> list[tuple[int, int]]:
    """Ranges that must not be rewritten (inline code, URLs)."""
    spans = [(m.start(), m.end()) for m in _INLINE_CODE.finditer(line)]
    spans += [(m.start(), m.end()) for m in _LINK_TARGET.finditer(line)]
    spans += [(m.start(), m.end()) for m in _BARE_URL.finditer(line)]
    return spans


def _outside(spans: list[tuple[int, int]], start: int, end: int) -> bool:
    return all(end <= s or start >= e for s, e in spans)


def replace_ascii_umlauts(text: str, extra_words: Sequence[str] = ()) -> tuple[str, int]:
    """Rewrite every listed ASCII umlaut word, return (text, count).

    Skips code fences, inline code, link targets and URLs: an identifier
    or slug containing "fuer" must keep its ASCII spelling.
    """
    pattern = build_umlaut_pattern(extra_words)
    out: list[str] = []
    total = 0
    in_fence = False
    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\n\r")
        ending = line[len(stripped) :]
        if _FENCE.match(stripped):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        protected = _protected_spans(stripped)
        edits = [
            (m.start(), m.end(), umlautify(m.group(0)))
            for m in pattern.finditer(stripped)
            if _outside(protected, m.start(), m.end())
        ]
        # Right to left, so earlier offsets stay valid as the string changes.
        for start, end, replacement in sorted(edits, reverse=True):
            stripped = stripped[:start] + replacement + stripped[end:]
            total += 1
        out.append(stripped + ending)
    return "".join(out), total


def fix_file(
    path: Path,
    *,
    extra_words: Sequence[str] = (),
    dry_run: bool = False,
    backup: bool = True,
) -> UmlautResult:
    """Rewrite one file. With ``dry_run`` nothing is written."""
    original = read_text(path)
    rewritten, replacements = replace_ascii_umlauts(original, extra_words)
    if replacements == 0:
        return UmlautResult(path=path, changed=False, replacements=0)
    if not dry_run:
        if backup:
            shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
        path.write_text(rewritten, encoding="utf-8")
    return UmlautResult(path=path, changed=True, replacements=replacements)
