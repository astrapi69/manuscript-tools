"""Tests for manuscript_tools.checker."""

from pathlib import Path

from manuscript_tools.checker import (
    ALL_RULES_DE,
    CORE_RULES,
    check_file,
    rule_filler_words_de,
    rule_max_sentence_length,
    rule_no_double_spaces,
    rule_no_invisible_chars,
    rule_no_repeated_words,
    rule_passive_voice_de,
)

# ---------------------------------------------------------------------------
# rule_no_dashes
# ---------------------------------------------------------------------------


def test_no_dashes_clean(tmp_path: Path) -> None:
    f = tmp_path / "clean.md"
    f.write_text("Ein sauberer Text - mit Bindestrich.\n", encoding="utf-8")
    report = check_file(f)
    assert report.ok
    assert report.words > 0


def test_no_dashes_em_dash(tmp_path: Path) -> None:
    f = tmp_path / "dirty.md"
    f.write_text("Text mit \u2014 Em-Dash.\n", encoding="utf-8")
    report = check_file(f)
    assert not report.ok
    assert any(v.rule == "no-dashes" for v in report.violations)


def test_no_dashes_en_dash(tmp_path: Path) -> None:
    f = tmp_path / "dirty2.md"
    f.write_text("Seiten 10\u201320\n", encoding="utf-8")
    report = check_file(f)
    assert not report.ok
    assert report.violations[0].line == 1


# ---------------------------------------------------------------------------
# rule_no_invisible_chars
# ---------------------------------------------------------------------------


def test_no_invisible_chars_zwsp(tmp_path: Path) -> None:
    f = tmp_path / "zwsp.md"
    f.write_text("Zero\u200bWidth\n", encoding="utf-8")
    violations = rule_no_invisible_chars(f.read_text(encoding="utf-8"), f)
    assert len(violations) == 1
    assert violations[0].rule == "no-invisible-chars"


# ---------------------------------------------------------------------------
# rule_no_repeated_words
# ---------------------------------------------------------------------------


def test_repeated_words_finds_dupes() -> None:
    text = "Der der Hund lief schnell.\n"
    violations = rule_no_repeated_words(text, Path("test.md"))
    assert len(violations) == 1
    assert "Der" in violations[0].message


def test_repeated_words_case_insensitive() -> None:
    text = "und Und das ist falsch.\n"
    violations = rule_no_repeated_words(text, Path("test.md"))
    assert len(violations) == 1


def test_repeated_words_clean() -> None:
    text = "Ein ganz normaler Satz ohne Fehler.\n"
    violations = rule_no_repeated_words(text, Path("test.md"))
    assert len(violations) == 0


def test_repeated_words_ignores_single_chars() -> None:
    """Single-char repetitions like 'a a' should be ignored (min 2 chars)."""
    text = "Punkt a a ist hier.\n"
    violations = rule_no_repeated_words(text, Path("test.md"))
    assert len(violations) == 0


# ---------------------------------------------------------------------------
# rule_no_double_spaces
# ---------------------------------------------------------------------------


def test_double_spaces_found() -> None:
    text = "Hier sind  zwei Leerzeichen.\n"
    violations = rule_no_double_spaces(text, Path("test.md"))
    assert len(violations) == 1
    assert violations[0].rule == "no-double-spaces"


def test_double_spaces_clean() -> None:
    text = "Hier ist alles korrekt.\n"
    violations = rule_no_double_spaces(text, Path("test.md"))
    assert len(violations) == 0


# ---------------------------------------------------------------------------
# rule_max_sentence_length
# ---------------------------------------------------------------------------


def test_sentence_length_short() -> None:
    text = "Kurzer Satz. Noch einer.\n"
    violations = rule_max_sentence_length(text, Path("test.md"))
    assert len(violations) == 0


def test_sentence_length_too_long() -> None:
    words = " ".join(["Wort"] * 45)
    text = f"{words}.\n"
    violations = rule_max_sentence_length(text, Path("test.md"))
    assert len(violations) == 1
    assert "45" in violations[0].message


def test_sentence_length_skips_headings() -> None:
    words = " ".join(["Wort"] * 45)
    text = f"# {words}\n"
    violations = rule_max_sentence_length(text, Path("test.md"))
    assert len(violations) == 0


# ---------------------------------------------------------------------------
# rule_filler_words_de
# ---------------------------------------------------------------------------


def test_filler_words_found() -> None:
    text = "Das ist eigentlich nicht so wichtig.\n"
    violations = rule_filler_words_de(text, Path("test.md"))
    assert len(violations) == 1
    assert "eigentlich" in violations[0].message


def test_filler_words_multiple() -> None:
    text = "Es ist halt irgendwie so, quasi normal.\n"
    violations = rule_filler_words_de(text, Path("test.md"))
    found = {v.message for v in violations}
    assert any("halt" in m for m in found)
    assert any("irgendwie" in m for m in found)
    assert any("quasi" in m for m in found)


def test_filler_words_clean() -> None:
    text = "Der Algorithmus berechnet das Ergebnis.\n"
    violations = rule_filler_words_de(text, Path("test.md"))
    assert len(violations) == 0


def test_filler_words_skips_headings() -> None:
    text = "# Eigentlich ein guter Titel\n"
    violations = rule_filler_words_de(text, Path("test.md"))
    assert len(violations) == 0


# ---------------------------------------------------------------------------
# rule_passive_voice_de
# ---------------------------------------------------------------------------


def test_passive_voice_werden() -> None:
    text = "Das Buch wird gelesen.\n"
    violations = rule_passive_voice_de(text, Path("test.md"))
    assert len(violations) >= 1
    assert violations[0].rule == "passive-voice-de"


def test_passive_voice_wurde() -> None:
    text = "Das Haus wurde gebaut.\n"
    violations = rule_passive_voice_de(text, Path("test.md"))
    assert len(violations) >= 1


def test_passive_voice_active_clean() -> None:
    text = "Sie schrieb das Buch.\n"
    violations = rule_passive_voice_de(text, Path("test.md"))
    assert len(violations) == 0


def test_passive_voice_worden() -> None:
    text = "Das Problem ist behoben worden.\n"
    violations = rule_passive_voice_de(text, Path("test.md"))
    assert len(violations) >= 1


# ---------------------------------------------------------------------------
# Rule sets and check_file
# ---------------------------------------------------------------------------


def test_custom_rules(tmp_path: Path) -> None:
    """check_file accepts custom rule lists."""
    f = tmp_path / "test.md"
    f.write_text("Hallo Welt\n", encoding="utf-8")
    report = check_file(f, rules=[])
    assert report.ok


def test_core_rules_count() -> None:
    assert len(CORE_RULES) == 4


def test_all_rules_de_count() -> None:
    assert len(ALL_RULES_DE) == 7


def test_missing_file(tmp_path: Path) -> None:
    f = tmp_path / "nope.md"
    report = check_file(f)
    assert report.error is not None


def test_strict_mode_file(tmp_path: Path) -> None:
    """ALL_RULES_DE catches filler words that DEFAULT_RULES would miss."""
    f = tmp_path / "filler.md"
    f.write_text("Das ist eigentlich nicht schlimm.\n", encoding="utf-8")
    report_default = check_file(f)
    report_strict = check_file(f, rules=ALL_RULES_DE)
    assert report_default.ok
    assert not report_strict.ok
