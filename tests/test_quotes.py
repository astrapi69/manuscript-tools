"""Tests for manuscript_tools.quotes."""

from pathlib import Path

from manuscript_tools.quotes import (
    convert_file,
    convert_text,
    has_non_german_quotes,
)

# ---------------------------------------------------------------------------
# convert_text - straight double quotes
# ---------------------------------------------------------------------------


def test_straight_double_to_german() -> None:
    text = 'Er sagte "Hallo Welt" und ging.\n'
    result, stats = convert_text(text)
    assert "\u201e" in result  # „
    assert "\u201c" in result  # "
    assert '"' not in result
    assert stats.straight_double >= 1


def test_straight_double_multiple_pairs() -> None:
    text = 'Er sagte "Hallo" und sie sagte "Tschüss".\n'
    result, stats = convert_text(text)
    assert result.count("\u201e") == 2
    assert result.count("\u201c") == 2
    assert stats.straight_double >= 2


def test_straight_double_asymmetric_warns() -> None:
    text = 'Ein "unvollständiges Zitat.\n'
    result, stats = convert_text(text)
    assert stats.warnings == 1
    assert len(stats.warning_messages) == 1


# ---------------------------------------------------------------------------
# convert_text - English typographic double quotes
# ---------------------------------------------------------------------------


def test_english_double_to_german() -> None:
    text = "Er sagte \u201cHallo\u201d und ging.\n"
    result, stats = convert_text(text)
    assert "\u201e" in result  # „ (opening)
    assert "\u201c" in result  # " (closing, same as DE close)
    assert "\u201d" not in result
    assert stats.english_double >= 1


# ---------------------------------------------------------------------------
# convert_text - English typographic single quotes
# ---------------------------------------------------------------------------


def test_english_single_to_german() -> None:
    text = "Er sagte \u2018Hallo\u2019 und ging.\n"
    result, stats = convert_text(text)
    assert "\u201a" in result  # ‚ (German open single)
    assert "\u2018" in result  # ' (German close single)
    assert "\u2019" not in result
    assert stats.english_single >= 1


# ---------------------------------------------------------------------------
# convert_text - protected regions
# ---------------------------------------------------------------------------


def test_code_span_untouched() -> None:
    text = 'Nutze `echo "hello"` im Terminal.\n'
    result, stats = convert_text(text)
    assert '`echo "hello"`' in result
    assert stats.total_replacements == 0


def test_code_block_untouched() -> None:
    text = '```\necho "hello"\n```\n'
    result, stats = convert_text(text)
    assert result == text
    assert stats.total_replacements == 0


def test_frontmatter_untouched() -> None:
    text = '---\ntitle: "Mein Buch"\n---\nText hier.\n'
    result, stats = convert_text(text)
    assert 'title: "Mein Buch"' in result
    assert stats.total_replacements == 0


def test_html_attribute_untouched() -> None:
    text = '<img alt="Bild" src="test.png"> und "Text" hier.\n'
    result, stats = convert_text(text)
    assert 'alt="Bild"' in result
    assert 'src="test.png"' in result
    # Only "Text" should be converted
    assert "\u201e" in result


# ---------------------------------------------------------------------------
# convert_text - already correct
# ---------------------------------------------------------------------------


def test_already_german_unchanged() -> None:
    text = "Er sagte \u201eHallo\u201c und ging.\n"
    result, stats = convert_text(text)
    assert result == text
    assert stats.total_replacements == 0


# ---------------------------------------------------------------------------
# convert_text - mixed
# ---------------------------------------------------------------------------


def test_mixed_german_open_with_straight_close() -> None:
    text = '\u201eHallo" Welt.\n'
    result, stats = convert_text(text)
    assert "\u201e" in result
    assert "\u201c" in result
    assert '"' not in result


# ---------------------------------------------------------------------------
# has_non_german_quotes
# ---------------------------------------------------------------------------


def test_has_non_german_straight() -> None:
    assert has_non_german_quotes('Er sagte "Hallo".')


def test_has_non_german_english_close() -> None:
    assert has_non_german_quotes("Text mit \u201d hier.")


def test_has_no_non_german() -> None:
    assert not has_non_german_quotes("Er sagte \u201eHallo\u201c.")


def test_has_non_german_ignores_code() -> None:
    assert not has_non_german_quotes('Nutze `echo "hello"` hier.')


# ---------------------------------------------------------------------------
# convert_file
# ---------------------------------------------------------------------------


def test_convert_file_changes(tmp_path: Path) -> None:
    f = tmp_path / "test.md"
    f.write_text('Er sagte "Hallo" und ging.\n', encoding="utf-8")
    result = convert_file(f)
    assert result.changed
    assert result.error is None
    content = f.read_text(encoding="utf-8")
    assert "\u201e" in content
    assert f.with_suffix(".md.bak").exists()


def test_convert_file_dry_run(tmp_path: Path) -> None:
    f = tmp_path / "test.md"
    original = 'Er sagte "Hallo" und ging.\n'
    f.write_text(original, encoding="utf-8")
    result = convert_file(f, dry_run=True)
    assert result.changed
    assert f.read_text(encoding="utf-8") == original


def test_convert_file_no_change(tmp_path: Path) -> None:
    f = tmp_path / "test.md"
    f.write_text("Er sagte \u201eHallo\u201c und ging.\n", encoding="utf-8")
    result = convert_file(f)
    assert not result.changed


def test_convert_file_missing(tmp_path: Path) -> None:
    f = tmp_path / "nope.md"
    result = convert_file(f)
    assert result.error is not None
