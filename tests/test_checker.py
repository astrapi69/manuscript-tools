"""Tests for manuscript_tools.checker."""

from pathlib import Path

from manuscript_tools.checker import check_file, rule_no_invisible_chars


def test_rule_no_dashes_clean(tmp_path: Path) -> None:
    f = tmp_path / "clean.md"
    f.write_text("Ein sauberer Text - mit Bindestrich.\n", encoding="utf-8")
    report = check_file(f)
    assert report.ok
    assert report.words > 0


def test_rule_no_dashes_em_dash(tmp_path: Path) -> None:
    f = tmp_path / "dirty.md"
    f.write_text("Text mit \u2014 Em-Dash.\n", encoding="utf-8")
    report = check_file(f)
    assert not report.ok
    assert any(v.rule == "no-dashes" for v in report.violations)


def test_rule_no_dashes_en_dash(tmp_path: Path) -> None:
    f = tmp_path / "dirty2.md"
    f.write_text("Seiten 10\u201320\n", encoding="utf-8")
    report = check_file(f)
    assert not report.ok
    assert report.violations[0].line == 1


def test_rule_no_invisible_chars_zwsp(tmp_path: Path) -> None:
    f = tmp_path / "zwsp.md"
    f.write_text("Zero\u200bWidth\n", encoding="utf-8")
    violations = rule_no_invisible_chars(f.read_text(encoding="utf-8"), f)
    assert len(violations) == 1
    assert violations[0].rule == "no-invisible-chars"


def test_custom_rules(tmp_path: Path) -> None:
    """check_file accepts custom rule lists."""
    f = tmp_path / "test.md"
    f.write_text("Hallo Welt\n", encoding="utf-8")
    report = check_file(f, rules=[])
    assert report.ok  # no rules, no violations


def test_missing_file(tmp_path: Path) -> None:
    f = tmp_path / "nope.md"
    report = check_file(f)
    assert report.error is not None
