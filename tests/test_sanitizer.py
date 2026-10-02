"""Tests for manuscript_tools.sanitizer."""

from pathlib import Path

from manuscript_tools.sanitizer import sanitize_file, sanitize_text


def test_sanitize_text_clean() -> None:
    result = sanitize_text("Hallo Welt\n")
    assert result == "Hallo Welt\n"


def test_sanitize_text_adds_trailing_newline() -> None:
    result = sanitize_text("Kein Newline am Ende")
    assert result.endswith("\n")


def test_sanitize_text_removes_bom() -> None:
    result = sanitize_text("\ufeffText mit BOM\n")
    assert "\ufeff" not in result
    assert result.startswith("Text")


def test_sanitize_text_replaces_nbsp() -> None:
    result = sanitize_text("Hallo\u00a0Welt\n")
    assert "\u00a0" not in result
    assert "Hallo Welt" in result


def test_sanitize_text_normalizes_crlf() -> None:
    result = sanitize_text("Zeile1\r\nZeile2\r\n")
    assert "\r" not in result
    assert result == "Zeile1\nZeile2\n"


def test_sanitize_text_strips_control_chars() -> None:
    result = sanitize_text("Text\x00mit\x07Muell\n")
    assert "\x00" not in result
    assert "\x07" not in result


def test_sanitize_text_keeps_german_quotation_marks() -> None:
    """German quotation marks and the curly apostrophe survive sanitizing.

    ftfy defaults to ``uncurl_quotes=True`` and turned „…“ (U+201E/U+201C),
    ‚…‘ (U+201A/U+2018) and ’ (U+2019) into ASCII " and '. A sanitizer
    that destroys the typography ms-quotes produces is a regression, not a fix
    (issue #12).
    """
    text = "Er sagte \u201eHallo \u201aWelt\u2018, hier\u201c und ging\u2019s.\n"
    assert sanitize_text(text) == text


def test_sanitize_file_no_change(tmp_path: Path) -> None:
    f = tmp_path / "clean.md"
    f.write_text("Sauberer Text.\n", encoding="utf-8")
    result = sanitize_file(f)
    assert not result.changed
    assert result.error is None


def test_sanitize_file_fixes_content(tmp_path: Path) -> None:
    f = tmp_path / "dirty.md"
    f.write_text("Text\u00a0mit\u00a0NBSP\n", encoding="utf-8")
    result = sanitize_file(f)
    assert result.changed
    cleaned = f.read_text(encoding="utf-8")
    assert "\u00a0" not in cleaned


def test_sanitize_file_dry_run(tmp_path: Path) -> None:
    f = tmp_path / "dirty.md"
    original = "Text\u00a0mit\u00a0NBSP\n"
    f.write_text(original, encoding="utf-8")
    result = sanitize_file(f, dry_run=True)
    assert result.changed
    # File should NOT have been modified
    assert f.read_text(encoding="utf-8") == original


def test_sanitize_file_backup(tmp_path: Path) -> None:
    f = tmp_path / "dirty.md"
    f.write_text("Text\u00a0mit\u00a0NBSP\n", encoding="utf-8")
    sanitize_file(f, backup=True)
    assert f.with_suffix(".md.bak").exists()
