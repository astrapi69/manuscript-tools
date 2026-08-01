"""ASCII umlauts: curated word list, never a substring pattern.

The naive approach — replace every ae/oe/ue — destroyed 17 of 21 sample
words when trialled ("Frauen" -> "Fraün", "Goethe" -> "Göthe"). These
tests therefore guard the false positives as hard as the corrections:
every word class that broke the naive pattern gets an explicit test.
"""

from pathlib import Path

from manuscript_tools.checker import rule_ascii_umlauts, umlautify
from manuscript_tools.config import resolve_config
from manuscript_tools.umlauts import fix_file, replace_ascii_umlauts


def _hits(text: str) -> list[str]:
    return [v.message for v in rule_ascii_umlauts(text, Path("t.md"))]


def _fixed(text: str) -> str:
    rewritten, _ = replace_ascii_umlauts(text)
    return rewritten


# ---------------------------------------------------------------------------
# Corrections
# ---------------------------------------------------------------------------


def test_rewrites_fuer() -> None:
    assert _fixed("Das ist fuer dich.\n") == "Das ist für dich.\n"


def test_rewrites_a_sentence_with_several_words() -> None:
    assert _fixed("Ich moechte das natuerlich fuer dich pruefen.\n") == (
        "Ich möchte das natürlich für dich prüfen.\n"
    )


def test_rewrites_a_word_with_two_umlauts() -> None:
    assert _fixed("Das Fruehstueck war gut.\n") == "Das Frühstück war gut.\n"


def test_rule_reports_word_and_replacement() -> None:
    hits = _hits("Das ist fuer dich.\n")
    assert len(hits) == 1
    assert '"fuer"' in hits[0]
    assert '"für"' in hits[0]


# ---------------------------------------------------------------------------
# Case preservation
# ---------------------------------------------------------------------------


def test_case_lower() -> None:
    assert umlautify("fuer") == "für"


def test_case_title() -> None:
    assert umlautify("Ueber") == "Über"


def test_case_upper() -> None:
    assert umlautify("FUER") == "FÜR"


def test_titlecase_in_text() -> None:
    assert _fixed("Ueber den Bergen.\n") == "Über den Bergen.\n"


# ---------------------------------------------------------------------------
# False-positive guards: the word classes that broke the naive pattern
# ---------------------------------------------------------------------------


def test_leaves_diphthong_words_untouched() -> None:
    text = "Die Frauen bauen neue Feuer und zahlen Steuern.\n"
    assert _fixed(text) == text
    assert _hits(text) == []


def test_leaves_names_untouched() -> None:
    text = "Goethe traf Michael in Israel.\n"
    assert _fixed(text) == text
    assert _hits(text) == []


def test_leaves_loanwords_untouched() -> None:
    text = "Aerobic und Poesie sind aktuell ein Duell.\n"
    assert _fixed(text) == text
    assert _hits(text) == []


def test_leaves_unknown_ascii_words_untouched() -> None:
    """Not on the list means not touched, even if it looks like a hit."""
    text = "Der Fuehrerschein fehlt.\n"
    assert _fixed(text) == text
    assert _hits(text) == []


# ---------------------------------------------------------------------------
# Protected regions
# ---------------------------------------------------------------------------


def test_leaves_inline_code_untouched() -> None:
    text = "Der Parameter `fuer_alle` bleibt, fuer dich nicht.\n"
    assert _fixed(text) == "Der Parameter `fuer_alle` bleibt, für dich nicht.\n"


def test_leaves_code_fences_untouched() -> None:
    text = "```\nfuer = 1\n```\n"
    assert _fixed(text) == text
    assert _hits(text) == []


def test_leaves_link_targets_untouched() -> None:
    text = "Siehe [Doku](https://example.com/fuer/uebung) fuer Details.\n"
    assert _fixed(text) == "Siehe [Doku](https://example.com/fuer/uebung) für Details.\n"
    assert len(_hits(text)) == 1


def test_leaves_bare_urls_untouched() -> None:
    text = "Siehe https://example.com/fuer dazu.\n"
    assert _fixed(text) == text
    assert _hits(text) == []


# ---------------------------------------------------------------------------
# Idempotence and extension
# ---------------------------------------------------------------------------


def test_idempotent() -> None:
    once = _fixed("Das waere schoen fuer alle.\n")
    assert _fixed(once) == once


def test_extra_words_extend_the_list() -> None:
    rewritten, n = replace_ascii_umlauts(
        "Die Oekologie lehrt uns viel.\n", extra_words=["oekologie"]
    )
    assert rewritten == "Die Ökologie lehrt uns viel.\n"
    assert n == 1


def test_without_extra_words_the_same_word_stays() -> None:
    text = "Die Oekologie lehrt uns viel.\n"
    assert _fixed(text) == text


# ---------------------------------------------------------------------------
# Config resolution
# ---------------------------------------------------------------------------


def test_rule_is_opt_in() -> None:
    cfg = resolve_config(raw_config={})
    assert "ascii-umlauts" not in cfg.active_rule_names


def test_rule_activates_via_rules() -> None:
    cfg = resolve_config(raw_config={"rules": ["ascii-umlauts"]})
    assert "ascii-umlauts" in cfg.active_rule_names


def test_umlaut_words_extra_reaches_the_configured_rule() -> None:
    cfg = resolve_config(
        raw_config={
            "rules": ["ascii-umlauts"],
            "umlaut-words-extra": ["oekologie"],
        }
    )
    idx = cfg.active_rule_names.index("ascii-umlauts")
    rule = cfg.active_rules[idx]
    assert rule("Die Oekologie lehrt.\n", Path("t.md"))


def test_umlaut_words_extra_rejects_non_list() -> None:
    cfg = resolve_config(raw_config={"umlaut-words-extra": "oekologie"})
    assert cfg.umlaut_words_extra == []
    assert any("umlaut-words-extra" in w for w in cfg.warnings)


# ---------------------------------------------------------------------------
# File operations
# ---------------------------------------------------------------------------


def test_dry_run_reports_without_writing(tmp_path: Path) -> None:
    f = tmp_path / "t.md"
    f.write_text("Das ist fuer dich.\n", encoding="utf-8")
    result = fix_file(f, dry_run=True)
    assert result.changed
    assert result.replacements == 1
    assert f.read_text(encoding="utf-8") == "Das ist fuer dich.\n"


def test_execute_writes_with_backup(tmp_path: Path) -> None:
    f = tmp_path / "t.md"
    f.write_text("Das ist fuer dich.\n", encoding="utf-8")
    result = fix_file(f)
    assert result.changed
    assert f.read_text(encoding="utf-8") == "Das ist für dich.\n"
    backup = tmp_path / "t.md.bak"
    assert backup.read_text(encoding="utf-8") == "Das ist fuer dich.\n"


def test_a_clean_file_is_not_rewritten(tmp_path: Path) -> None:
    f = tmp_path / "t.md"
    f.write_text("Die Frauen bauen neue Feuer.\n", encoding="utf-8")
    result = fix_file(f)
    assert not result.changed
    assert not (tmp_path / "t.md.bak").exists()


# ---------------------------------------------------------------------------
# Documented limitations: high precision, deliberately incomplete recall.
# These tests turn would-be bug reports into known, guaranteed behaviour.
# ---------------------------------------------------------------------------


def test_unlisted_compounds_stay_by_design() -> None:
    """The whole-word pattern never fires inside a compound.

    "kaefig" is on the list, "Vogelkaefig" is not — and \\b keeps the
    listed word from matching inside it. Not a bug: the fix is to add
    the compound to umlaut-words-extra.
    """
    text = "Der Vogelkaefig steht im Nebengebaeude.\n"
    assert _fixed(text) == text
    assert _hits(text) == []


def test_ss_is_never_touched() -> None:
    """ss -> ß is out of scope: context-dependent (Masse vs. Maße) and
    wrong for Swiss orthography. No rule, no rewrite, ever."""
    text = "Die Strasse war gross und die Masse an Wasser floss.\n"
    assert _fixed(text) == text
    assert _hits(text) == []


def test_umlautify_leaves_ss_alone() -> None:
    """Why "aeusserst" is NOT on the list: umlautify would produce
    "äusserst", but Duden wants "äußerst" — half a fix is worse than
    none, so ss-words stay off the list entirely."""
    from manuscript_tools.checker import UMLAUT_WORDS

    assert umlautify("aeusserst") == "äusserst"
    assert "aeusserst" not in UMLAUT_WORDS


def test_hyphenated_word_across_lines_is_ignored() -> None:
    """A word split at a line break ("Ue-\\nbertragung") is invisible to
    the line-based scan. Known limitation; joining hyphenated words is
    a pre-processing concern, not an umlaut fixer's."""
    text = "Das ist eine Ue-\nbertragung.\n"
    assert _fixed(text) == text
    assert _hits(text) == []


def test_aeu_resolves_to_aeu_umlaut() -> None:
    """ "aeu" must become "äu": the ae half is replaced, the remaining
    eu is a diphthong and stays. Guards the substitution order in
    umlautify against future refactoring."""
    assert umlautify("haeufig") == "häufig"
    assert umlautify("Haeufig") == "Häufig"
    assert _fixed("Das passiert haeufig.\n") == "Das passiert häufig.\n"


def test_swiss_spelling_is_replaced_only_if_the_user_lists_it() -> None:
    """Swiss official spelling ("Mueller", "Zuerich") is legally valid.
    The core list contains no proper names for exactly that reason; a
    user who adds them via extra_words takes over that judgement."""
    rewritten, n = replace_ascii_umlauts(
        "Herr Mueller aus Zuerich.\n", extra_words=["mueller", "zuerich"]
    )
    assert rewritten == "Herr Müller aus Zürich.\n"
    assert n == 2
    text = "Herr Mueller aus Zuerich.\n"
    assert _fixed(text) == text


def test_compound_sentence_with_three_replacements() -> None:
    assert _fixed("Die Aenderung der Gruende war noetig.\n") == (
        "Die Änderung der Gründe war nötig.\n"
    )
