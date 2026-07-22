"""Phase 2 of the faked-dash work: normalisation, once a target is chosen.

The rule in ``checker`` only reports. Rewriting needs a decision the tool
cannot make for the author, which is why ``target`` is required rather than
defaulted:

* A corpus that wants dashes may want the em-dash (U+2014) or, in German
  typography, the en-dash (U+2013) as the Halbgeviertstrich. Both are correct;
  they are different house styles.
* A corpus that forbids dashes outright, like the learn-content-engine blog,
  must NOT be normalised to a dash at all. The right fix there is a comma, a
  colon or a parenthesis, chosen per sentence. For that corpus this module is
  simply not the tool; ``ms-check`` reports and a human edits.

Silently picking one of those would make the fixer wrong for two of the three
cases, so there is no default.
"""

from pathlib import Path

import pytest
from manuscript_tools.dashes import DashTarget, normalize_dashes, normalize_file


def test_rewrites_a_spaced_hyphen_to_the_em_dash() -> None:
    assert normalize_dashes("Der Hund lief - und bellte.\n", DashTarget.EM) == (
        "Der Hund lief — und bellte.\n"
    )


def test_rewrites_a_spaced_hyphen_to_the_en_dash() -> None:
    """German typography sets the pause dash as a Halbgeviertstrich."""
    assert normalize_dashes("Der Hund lief - und bellte.\n", DashTarget.EN) == (
        "Der Hund lief – und bellte.\n"
    )


def test_rewrites_a_double_hyphen_between_words() -> None:
    assert normalize_dashes("Der Hund--er war jung--lief los.\n", DashTarget.EM) == (
        "Der Hund—er war jung—lief los.\n"
    )


def test_rewrites_a_spaced_double_hyphen() -> None:
    assert normalize_dashes("Der Hund lief -- und bellte.\n", DashTarget.EM) == (
        "Der Hund lief — und bellte.\n"
    )


def test_leaves_an_already_correct_dash_untouched() -> None:
    text = "Der Hund lief — und bellte.\n"
    assert normalize_dashes(text, DashTarget.EM) == text


def test_does_not_rewrite_an_en_dash_when_the_target_is_the_em_dash() -> None:
    """A real dash is already correct spelling; only FAKED forms are rewritten.

    Converting between the two real dashes is a house-style change, not the
    defect this tool addresses.
    """
    text = "Seiten 10–20 sind gemeint.\n"
    assert normalize_dashes(text, DashTarget.EM) == text


@pytest.mark.parametrize(
    "text",
    [
        "Ein framework-agnostisches Kosten-Nutzen-Verhältnis.\n",
        "- erster Punkt\n- zweiter Punkt\n",
        "---\ntitle: Test\n---\n\nText.\n",
        "| a | b |\n|---|---|\n",
        "Nutze ms-sanitize --dry-run vor dem Schreiben.\n",
        "```shell\ngrep -- muster datei\n```\n",
        "Der Schalter `--dry-run` zeigt die Änderungen.\n",
        "Es sind dieselben `matching`- und `free_text`-Strukturen.\n",
        "Die Version 1.7 - 1.8 ist gemeint.\n",
    ],
)
def test_leaves_every_non_dash_hyphen_untouched(text: str) -> None:
    """The detector's boundary cases must survive the rewriter unchanged.

    A fixer that edits these would damage correct text rather than merely
    report noise, so they are asserted against the rewriter too.
    """
    assert normalize_dashes(text, DashTarget.EM) == text


def test_rewrites_inside_a_list_item_but_keeps_the_bullet() -> None:
    assert normalize_dashes("- Der Hund lief - und bellte.\n", DashTarget.EM) == (
        "- Der Hund lief — und bellte.\n"
    )


def test_dry_run_reports_without_writing(tmp_path: Path) -> None:
    f = tmp_path / "a.md"
    original = "Der Hund lief - und bellte.\n"
    f.write_text(original, encoding="utf-8")
    result = normalize_file(f, DashTarget.EM, dry_run=True)
    assert result.changed
    assert f.read_text(encoding="utf-8") == original


def test_execute_writes_and_reports_the_count(tmp_path: Path) -> None:
    f = tmp_path / "a.md"
    f.write_text("Der Hund lief - und bellte -- sehr laut.\n", encoding="utf-8")
    result = normalize_file(f, DashTarget.EM, dry_run=False)
    assert result.changed
    assert result.replacements == 2
    assert "—" in f.read_text(encoding="utf-8")
    assert " - " not in f.read_text(encoding="utf-8")


def test_a_clean_file_is_not_rewritten(tmp_path: Path) -> None:
    f = tmp_path / "a.md"
    f.write_text("Ein framework-agnostischer Ansatz.\n", encoding="utf-8")
    result = normalize_file(f, DashTarget.EM, dry_run=False)
    assert not result.changed
    assert result.replacements == 0


def test_backup_is_written_next_to_the_file(tmp_path: Path) -> None:
    f = tmp_path / "a.md"
    f.write_text("Der Hund lief - und bellte.\n", encoding="utf-8")
    normalize_file(f, DashTarget.EM, dry_run=False, backup=True)
    assert (tmp_path / "a.md.bak").exists()
