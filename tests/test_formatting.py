"""Tests for manuscript_tools.formatting."""

from pathlib import Path

from manuscript_tools.formatting import (
    fix_broken_formatting,
    fix_formatting_file,
    has_broken_formatting,
)

# ---------------------------------------------------------------------------
# has_broken_formatting - detection
# ---------------------------------------------------------------------------


def test_detect_orphan_bold_at_end() -> None:
    lines = ["text with **", "bold content** here"]
    problems = has_broken_formatting(lines, 0)
    assert len(problems) == 1
    assert "**" in problems[0]


def test_detect_orphan_italic_at_end() -> None:
    lines = ["text with *", "italic content* here"]
    problems = has_broken_formatting(lines, 0)
    assert len(problems) == 1
    assert "*" in problems[0]


def test_detect_orphan_close_at_start() -> None:
    lines = ["text with **bold", "** continues here"]
    problems = has_broken_formatting(lines, 1)
    assert len(problems) >= 1


def test_clean_line_no_problems() -> None:
    lines = ["text with **bold** content"]
    problems = has_broken_formatting(lines, 0)
    assert len(problems) == 0


def test_ignores_list_markers() -> None:
    lines = ["* list item", "more text"]
    problems = has_broken_formatting(lines, 0)
    assert len(problems) == 0


def test_ignores_horizontal_rule() -> None:
    lines = ["***", "text after"]
    problems = has_broken_formatting(lines, 0)
    assert len(problems) == 0


def test_ignores_headings() -> None:
    lines = ["# heading with *", "text"]
    problems = has_broken_formatting(lines, 0)
    assert len(problems) == 0


def test_no_false_positive_last_line() -> None:
    """No problem if there's no next line."""
    lines = ["some text"]
    problems = has_broken_formatting(lines, 0)
    assert len(problems) == 0


# ---------------------------------------------------------------------------
# fix_broken_formatting - pure function
# ---------------------------------------------------------------------------


def test_fix_orphan_bold_at_end() -> None:
    text = "text with **\nbold content** here.\n"
    result, stats = fix_broken_formatting(text)
    assert "**" not in result.split("\n")[0].rstrip() or "**bold content**" in result
    assert stats.broken_bold >= 1
    assert stats.lines_fixed >= 1


def test_fix_orphan_italic_at_end() -> None:
    text = "text with *\nitalic content* here.\n"
    result, stats = fix_broken_formatting(text)
    assert stats.broken_italic >= 1


def test_fix_orphan_close_bold_at_start() -> None:
    text = "text **bold content\n** continues here.\n"
    result, stats = fix_broken_formatting(text)
    assert stats.broken_bold >= 1


def test_fix_preserves_clean_text() -> None:
    text = "text with **bold** content.\n\nAnother paragraph.\n"
    result, stats = fix_broken_formatting(text)
    assert result == text
    assert stats.total_fixes == 0


def test_fix_skips_code_blocks() -> None:
    text = "```\ntext with **\nbroken** here\n```\n"
    result, stats = fix_broken_formatting(text)
    assert result == text
    assert stats.total_fixes == 0


def test_fix_skips_frontmatter() -> None:
    text = "---\ntitle: text **\nbroken**\n---\nContent here.\n"
    result, stats = fix_broken_formatting(text)
    assert result == text
    assert stats.total_fixes == 0


def test_fix_multiple_breaks() -> None:
    text = "first **\nbold** text.\n\nsecond **\nalso bold** text.\n"
    result, stats = fix_broken_formatting(text)
    assert stats.broken_bold >= 2


def test_fix_preserves_list_items() -> None:
    text = "* first item\n* second item\n"
    result, stats = fix_broken_formatting(text)
    assert result == text
    assert stats.total_fixes == 0


# ---------------------------------------------------------------------------
# Paired markers at a line boundary are not breaks (issue #15)
# ---------------------------------------------------------------------------
#
# Pattern 2 used to report every line that starts with ** or *, and pattern 1
# every line that ends with a span, as long as the neighbour was non-empty.
# A marker is only orphaned when it has no partner on its own line.


def test_paired_bold_at_line_start_is_clean() -> None:
    """``**Titel:** Text`` closes on the same line; it is not a continuation."""
    lines = ["Vorheriger Absatz.", "**Titel:** Die Formbare Ewigkeit", "Ein Satz danach."]
    assert has_broken_formatting(lines, 1) == []


def test_paired_bold_name_at_line_start_is_clean() -> None:
    lines = ["Ueber den Autor", "**Asterios Raptis** ist Softwareentwickler.", "Mehr Text."]
    assert has_broken_formatting(lines, 1) == []


def test_paired_bold_at_line_end_is_clean() -> None:
    """A span that opens and closes on the line ends with ``**`` legitimately."""
    lines = ["Das ist **wichtig**", "und hier geht es weiter."]
    assert has_broken_formatting(lines, 0) == []


def test_paired_italic_at_line_boundaries_is_clean() -> None:
    lines = ["Absatz.", "*Kursiv* am Anfang", "Das ist *wichtig*", "weiter im Text."]
    assert has_broken_formatting(lines, 1) == []
    assert has_broken_formatting(lines, 2) == []


def test_marker_inside_inline_code_does_not_count() -> None:
    """Asterisks in a code span are literal, not formatting."""
    lines = ["Das Muster `**` steht fuer **fett**", "und so weiter."]
    assert has_broken_formatting(lines, 0) == []


def test_unpaired_bold_at_line_end_is_still_reported() -> None:
    lines = ["Das ist wirklich **", "wichtig** hier"]
    problems = has_broken_formatting(lines, 0)
    assert len(problems) == 1
    assert "**" in problems[0]


def test_fix_keeps_paired_bold_at_line_start() -> None:
    """ms-format must not merge ``**Titel:** ...`` into the previous line."""
    text = "Vorheriger Absatz.\n**Titel:** Die Formbare Ewigkeit\nEin Satz danach.\n"
    result, stats = fix_broken_formatting(text)
    assert result == text
    assert stats.total_fixes == 0


def test_fix_keeps_paired_bold_at_line_end() -> None:
    text = "Das ist **wichtig**\nund hier geht es weiter.\n"
    result, stats = fix_broken_formatting(text)
    assert result == text
    assert stats.total_fixes == 0


def test_fix_still_merges_a_genuine_bold_break() -> None:
    text = "Das ist wirklich **\nwichtig** hier.\n"
    result, stats = fix_broken_formatting(text)
    assert result == "Das ist wirklich **wichtig** hier.\n"
    assert stats.broken_bold == 1
    assert stats.lines_fixed == 1


# ---------------------------------------------------------------------------
# fix_formatting_file - I/O
# ---------------------------------------------------------------------------


def test_file_fixes_content(tmp_path: Path) -> None:
    f = tmp_path / "test.md"
    f.write_text("text with **\nbold** here.\n", encoding="utf-8")
    result = fix_formatting_file(f)
    assert result.changed
    assert result.error is None
    assert f.with_suffix(".md.bak").exists()


def test_file_dry_run(tmp_path: Path) -> None:
    f = tmp_path / "test.md"
    original = "text with **\nbold** here.\n"
    f.write_text(original, encoding="utf-8")
    result = fix_formatting_file(f, dry_run=True)
    assert result.changed
    assert f.read_text(encoding="utf-8") == original


def test_file_no_change(tmp_path: Path) -> None:
    f = tmp_path / "test.md"
    f.write_text("text with **bold** here.\n", encoding="utf-8")
    result = fix_formatting_file(f)
    assert not result.changed


def test_file_missing(tmp_path: Path) -> None:
    f = tmp_path / "nope.md"
    result = fix_formatting_file(f)
    assert result.error is not None
