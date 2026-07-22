"""Canonical definition of the characters that cannot be seen.

Both entry points need this list, and they need the SAME one. ``ms-check`` is
report-only, so a user runs it, sees a clean result and concludes the file is
fine; if ``ms-sanitize`` would still change that file, the conclusion was
wrong. Keeping the sets here, rather than one copy per module, is what stops
the checker from silently drifting narrower than the sanitizer again.

The distinction the module draws:

- Stripped or rewritten characters are invisible. A reader cannot see them, so
  the checker reports them.
- Normalised whitespace (the no-break spaces) is *visible* as a space and is
  legitimate typography, notably in French, which sets one before "?" and "!".
  The sanitizer still normalises it, but that is a formatting preference
  rather than a hidden character, so the checker stays quiet about it.

Every codepoint is spelled as a NUMBER below, never as the character itself.
Writing the characters literally makes the source unreadable in the one file
where taking a comment on trust is least acceptable, and a stray U+0000 makes
the module unimportable.
"""

from __future__ import annotations

import re
import unicodedata

#: C0 controls and DELETE, as (first, last) inclusive ranges. Tab (0x09),
#: newline (0x0A) and carriage return (0x0D) are ordinary text and absent.
CONTROL_RANGES: tuple[tuple[int, int], ...] = (
    (0x00, 0x08),
    (0x0B, 0x0C),
    (0x0E, 0x1F),
    (0x7F, 0x7F),
)

#: Zero-width and bidirectional formatting characters.
FORMAT_CODEPOINTS: tuple[int, ...] = (
    0x200B,  # ZERO WIDTH SPACE
    0x200C,  # ZERO WIDTH NON-JOINER
    0x200D,  # ZERO WIDTH JOINER
    0x200E,  # LEFT-TO-RIGHT MARK
    0x200F,  # RIGHT-TO-LEFT MARK
    0x202A,  # LEFT-TO-RIGHT EMBEDDING
    0x202B,  # RIGHT-TO-LEFT EMBEDDING
    0x202C,  # POP DIRECTIONAL FORMATTING
    0x202D,  # LEFT-TO-RIGHT OVERRIDE
    0x202E,  # RIGHT-TO-LEFT OVERRIDE
    0xFEFF,  # ZERO WIDTH NO-BREAK SPACE / BOM
)

#: Invisible characters the sanitizer rewrites rather than drops.
REWRITTEN_CODEPOINTS: dict[int, str] = {
    0x00AD: "",  # SOFT HYPHEN
    0x2028: "\n",  # LINE SEPARATOR
    0x2029: "\n",  # PARAGRAPH SEPARATOR
}

#: Visible whitespace the sanitizer normalises. NOT reported by the checker:
#: flagging these would fire on correctly typeset French prose.
NORMALISED_WHITESPACE: dict[int, str] = {
    0x00A0: " ",  # NO-BREAK SPACE
    0x202F: " ",  # NARROW NO-BREAK SPACE
}

CONTROL_CHARS_RE = re.compile(
    "[" + "".join(f"\\u{lo:04x}-\\u{hi:04x}" for lo, hi in CONTROL_RANGES) + "]"
)

FORMAT_CHARS: frozenset[str] = frozenset(chr(cp) for cp in FORMAT_CODEPOINTS)

#: The sanitizer's replacement table, keyed by character.
REPLACE_MAP: dict[str, str] = {
    **{chr(cp): value for cp, value in REWRITTEN_CODEPOINTS.items()},
    **{chr(cp): value for cp, value in NORMALISED_WHITESPACE.items()},
}

#: Everything a reader cannot see.
INVISIBLE_CHARS: frozenset[str] = frozenset(
    FORMAT_CHARS | {chr(cp) for cp in REWRITTEN_CODEPOINTS}
)

INVISIBLE_RE = re.compile(
    "["
    + "".join(f"\\u{ord(char):04x}" for char in sorted(INVISIBLE_CHARS))
    + "".join(f"\\u{lo:04x}-\\u{hi:04x}" for lo, hi in CONTROL_RANGES)
    + "]"
)


def describe(char: str) -> str:
    """``U+200B ZERO WIDTH SPACE``-style label for one character.

    Control characters carry no Unicode name, so they fall back to a generic
    label instead of an empty one.
    """
    codepoint = f"U+{ord(char):04X}"
    name = unicodedata.name(char, "")
    return f"{codepoint} {name}" if name else f"{codepoint} CONTROL CHARACTER"
