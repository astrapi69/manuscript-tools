"""Tests for manuscript_tools.checker."""

from pathlib import Path

from manuscript_tools.checker import (
    ALL_RULES_DE,
    CORE_RULES,
    check_file,
    rule_faked_dashes,
    rule_filler_words_de,
    rule_max_sentence_length,
    rule_no_double_spaces,
    rule_no_invisible_chars,
    rule_no_repeated_words,
    rule_non_german_quotes,
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


def test_no_invisible_chars_matches_what_the_sanitizer_removes(tmp_path: Path) -> None:
    """The checker must not be narrower than the sanitizer.

    ms-check is the report-only entry point: a user runs it, sees a clean
    result and concludes the file is fine. If ms-sanitize would still change
    the file, that conclusion was wrong. Every character the sanitizer strips
    therefore has to be reported here.
    """
    for char in ("\u00ad", "\u202e", "\u0007", "\u2028", "\u007f"):
        f = tmp_path / "probe.md"
        f.write_text(f"Wort{char}Wort\n", encoding="utf-8")
        violations = rule_no_invisible_chars(f.read_text(encoding="utf-8"), f)
        assert violations, f"{char!r} (U+{ord(char):04X}) not reported"


def test_no_invisible_chars_covers_the_cf_format_block(tmp_path: Path) -> None:
    """U+2060-206F is invisible in full and was missing entirely.

    The block holds the word joiner, the invisible math operators a formula
    editor pastes, the bidi isolates modern editors emit in place of the
    older embeddings, and the deprecated format characters. All are Unicode
    general category Cf, all render as nothing, and all arrive by copying
    from the web.
    """
    for codepoint in (0x2060, 0x2061, 0x2064, 0x2066, 0x2069, 0x206F):
        f = tmp_path / "cf.md"
        f.write_text(f"A{chr(codepoint)}B\n", encoding="utf-8")
        violations = rule_no_invisible_chars(f.read_text(encoding="utf-8"), f)
        assert violations, f"U+{codepoint:04X} not reported"


def test_no_invisible_chars_names_the_codepoint(tmp_path: Path) -> None:
    """ "Unsichtbare Zeichen gefunden" is not actionable on its own.

    The character cannot be seen in an editor, so the message has to say
    which one it is and where it sits.
    """
    f = tmp_path / "zwsp.md"
    f.write_text("Zero\u200bWidth\n", encoding="utf-8")
    violations = rule_no_invisible_chars(f.read_text(encoding="utf-8"), f)
    assert "U+200B" in violations[0].message


def test_no_invisible_chars_keeps_tab_newline_and_cr(tmp_path: Path) -> None:
    """Ordinary whitespace is text, not a finding."""
    f = tmp_path / "clean.md"
    f.write_text("Zeile eins\nSpalte\teins\r\nEnde\n", encoding="utf-8")
    assert rule_no_invisible_chars(f.read_text(encoding="utf-8"), f) == []


def test_no_invisible_chars_keeps_no_break_spaces(tmp_path: Path) -> None:
    """A no-break space is visible whitespace and legitimate typography.

    French sets one before "?" and "!". The sanitizer normalises it to a
    plain space, which is a different concern from invisibility; reporting it
    here would make the rule fire on correctly typeset prose.
    """
    f = tmp_path / "french.md"
    f.write_text("Comment \u00e7a va\u00a0?\n1\u202f000 W\u00f6rter\n", encoding="utf-8")
    assert rule_no_invisible_chars(f.read_text(encoding="utf-8"), f) == []


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
# rule_non_german_quotes
# ---------------------------------------------------------------------------


def test_non_german_quotes_straight() -> None:
    text = 'Er sagte "Hallo" und ging.\n'
    violations = rule_non_german_quotes(text, Path("test.md"))
    assert len(violations) == 1
    assert violations[0].rule == "non-german-quotes"


def test_non_german_quotes_english_close() -> None:
    text = "Text mit \u201d hier.\n"
    violations = rule_non_german_quotes(text, Path("test.md"))
    assert len(violations) == 1


def test_non_german_quotes_correct() -> None:
    text = "Er sagte \u201eHallo\u201c und ging.\n"
    violations = rule_non_german_quotes(text, Path("test.md"))
    assert len(violations) == 0


def test_non_german_quotes_ignores_code() -> None:
    text = '```\necho "hello"\n```\n'
    violations = rule_non_german_quotes(text, Path("test.md"))
    assert len(violations) == 0


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
    assert len(CORE_RULES) == 6


def test_all_rules_de_count() -> None:
    assert len(ALL_RULES_DE) == 9


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


# ---------------------------------------------------------------------------
# rule_faked_dashes
# ---------------------------------------------------------------------------
#
# The inverse of rule_no_dashes, deliberately. no-dashes forbids the dash
# outright, which is the right policy for a manuscript that wants none. This
# rule assumes the opposite: a dash is fine, it just has to be spelled as a
# real U+2014 rather than faked with "--" or a spaced hyphen.
#
# The two therefore contradict each other by construction and must never both
# be active, which is why this one stays out of CORE_RULES.
#
# False positives are the real risk here. German prose is full of hyphens
# that must not be touched: compounds, list bullets, front matter, table
# separators, CLI flags. Every one of those gets a test.


def _dash_hits(text: str) -> list[str]:
    return [v.message for v in rule_faked_dashes(text, Path("t.md"))]


def test_faked_dashes_flags_double_hyphen_between_words() -> None:
    assert _dash_hits("Der Hund lief -- und bellte.\n")


def test_faked_dashes_flags_double_hyphen_without_spaces() -> None:
    assert _dash_hits("Der Hund--er war jung--lief los.\n")


def test_faked_dashes_flags_spaced_hyphen_as_a_pause() -> None:
    assert _dash_hits("Der Hund lief - und bellte dabei.\n")


def test_faked_dashes_ignores_a_real_em_dash() -> None:
    """A correctly set dash is the TARGET state, never a finding."""
    assert _dash_hits("Der Hund lief \u2014 und bellte.\n") == []


def test_faked_dashes_ignores_a_real_en_dash() -> None:
    assert _dash_hits("Seiten 10\u201320 sind gemeint.\n") == []


def test_faked_dashes_ignores_compound_hyphens() -> None:
    """The single most common hyphen in German, and never a dash."""
    assert _dash_hits("Ein framework-agnostisches Kosten-Nutzen-Verhältnis.\n") == []


def test_faked_dashes_ignores_list_bullets() -> None:
    assert _dash_hits("- erster Punkt\n- zweiter Punkt\n  - eingerückt\n") == []


def test_faked_dashes_finds_a_faked_dash_inside_a_list_item() -> None:
    """Only the bullet marker is exempt, not the prose after it.

    Phase 1 against real text caught this: skipping the whole line missed
    three of seven known cases, all of them inside bullets.
    """
    assert _dash_hits("- Der Hund lief - und bellte dabei.\\n")


def test_faked_dashes_still_ignores_the_bullet_marker_itself() -> None:
    assert _dash_hits("- erster Punkt\\n- zweiter Punkt\\n") == []


def test_faked_dashes_ignores_horizontal_rules_and_front_matter() -> None:
    assert _dash_hits("---\ntitle: Test\n---\n\nText.\n\n---\n") == []


def test_faked_dashes_ignores_a_shields_badge_url() -> None:
    """Escaped hyphens in a badge slug are URL syntax, not a faked dash.

    The only false positive in 74 findings of the adaptive-learner sweep
    (issue #4).
    """
    line = (
        "[![License: CC BY-SA 4.0]"
        "(https://img.shields.io/badge/license-CC--BY--SA--4.0-blue)](LICENSE)\n"
    )
    assert _dash_hits(line) == []


def test_faked_dashes_ignores_a_bare_url() -> None:
    assert _dash_hits("Siehe https://example.com/a--b fuer Details.\n") == []


def test_faked_dashes_ignores_an_autolink() -> None:
    assert _dash_hits("Siehe <https://example.com/a--b> fuer Details.\n") == []


def test_faked_dashes_still_flags_prose_next_to_a_url() -> None:
    """Masking the URL must not hide a faked dash elsewhere on the line."""
    line = "Das Badge [x](https://img.shields.io/badge/a--b) fehlt -- leider.\n"
    assert _dash_hits(line)


def test_faked_dashes_ignores_table_separators() -> None:
    assert _dash_hits("| a | b |\n|---|---|\n| 1 | 2 |\n") == []


def test_faked_dashes_ignores_cli_flags() -> None:
    assert _dash_hits("Nutze ms-sanitize --dry-run vor dem Schreiben.\n") == []


def test_faked_dashes_ignores_code_fences() -> None:
    """Code is not prose; a -- inside it is an operator or a flag."""
    text = "Text.\n\n```shell\ngrep -- muster datei\nx = a--b\n```\n\nText.\n"
    assert _dash_hits(text) == []


def test_faked_dashes_ignores_inline_code() -> None:
    assert _dash_hits("Der Schalter `--dry-run` zeigt die Änderungen.\n") == []


def test_faked_dashes_ignores_german_suffix_hyphen_next_to_inline_code() -> None:
    """Removing inline code must not CREATE a gap that looks like a dash.

    "`matching`- und `free_text`-Strukturen" is correct German suffix
    hyphenation. Deleting the code spans outright turned it into
    "dieselben - und -Strukturen", which the spaced-hyphen pattern then
    matched. Phase 1 against the real articles caught this.
    """
    text = "Es sind dieselben `matching`- und `free_text`-Strukturen.\\n"
    assert _dash_hits(text) == []


def test_faked_dashes_ignores_numeric_ranges() -> None:
    """Deliberately excluded: a spaced hyphen between numbers reads as a
    range, and flagging it would cost more in false positives than it gains."""
    assert _dash_hits("Die Version 1.7 - 1.8 ist gemeint.\n") == []


def test_faked_dashes_message_names_the_faked_form() -> None:
    """The author has to see WHICH form was found to fix it."""
    hits = _dash_hits("Der Hund lief -- und bellte.\n")
    assert "--" in hits[0]


def test_faked_dashes_is_not_a_core_rule() -> None:
    """It contradicts no-dashes, so it must never run by default."""
    from manuscript_tools.checker import CORE_RULE_NAMES, RULE_REGISTRY

    assert "faked-dashes" in RULE_REGISTRY
    assert "faked-dashes" not in CORE_RULE_NAMES
