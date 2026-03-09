"""Tests for manuscript_tools.config."""

from manuscript_tools.config import resolve_config

# ---------------------------------------------------------------------------
# Default behavior (no config)
# ---------------------------------------------------------------------------


def test_default_core_rules() -> None:
    cfg = resolve_config(raw_config={})
    assert len(cfg.active_rule_names) == 5
    assert "no-dashes" in cfg.active_rule_names
    assert "non-german-quotes" in cfg.active_rule_names
    assert "filler-words-de" not in cfg.active_rule_names
    assert len(cfg.warnings) == 0


def test_default_strict_rules() -> None:
    cfg = resolve_config(strict=True, raw_config={})
    assert len(cfg.active_rule_names) == 8
    assert "filler-words-de" in cfg.active_rule_names
    assert "passive-voice-de" in cfg.active_rule_names


# ---------------------------------------------------------------------------
# rules: merge with defaults
# ---------------------------------------------------------------------------


def test_rules_merge_with_defaults() -> None:
    cfg = resolve_config(raw_config={"rules": ["max-sentence-length"]})
    # Core (5) + 1 merged = 6
    assert len(cfg.active_rule_names) == 6
    assert "max-sentence-length" in cfg.active_rule_names
    assert "no-dashes" in cfg.active_rule_names


def test_rules_duplicate_with_default_no_double() -> None:
    cfg = resolve_config(raw_config={"rules": ["no-dashes"]})
    # Should not duplicate
    assert cfg.active_rule_names.count("no-dashes") == 1
    assert len(cfg.active_rule_names) == 5


def test_rules_unknown_warns() -> None:
    cfg = resolve_config(raw_config={"rules": ["nonexistent-rule"]})
    assert len(cfg.warnings) == 1
    assert "nonexistent-rule" in cfg.warnings[0]


# ---------------------------------------------------------------------------
# disable
# ---------------------------------------------------------------------------


def test_disable_removes_rule() -> None:
    cfg = resolve_config(raw_config={"disable": ["no-dashes"]})
    assert "no-dashes" not in cfg.active_rule_names
    assert len(cfg.active_rule_names) == 4


def test_disable_multiple() -> None:
    cfg = resolve_config(raw_config={"disable": ["no-dashes", "no-double-spaces"]})
    assert "no-dashes" not in cfg.active_rule_names
    assert "no-double-spaces" not in cfg.active_rule_names
    assert len(cfg.active_rule_names) == 3


def test_disable_unknown_warns() -> None:
    cfg = resolve_config(raw_config={"disable": ["fake-rule"]})
    assert len(cfg.warnings) == 1


def test_disable_strict_rule() -> None:
    cfg = resolve_config(
        strict=True,
        raw_config={"disable": ["passive-voice-de"]},
    )
    assert "passive-voice-de" not in cfg.active_rule_names
    assert len(cfg.active_rule_names) == 7


# ---------------------------------------------------------------------------
# rules + disable overlap
# ---------------------------------------------------------------------------


def test_overlap_warns_and_disable_wins() -> None:
    cfg = resolve_config(
        raw_config={
            "rules": ["max-sentence-length"],
            "disable": ["max-sentence-length"],
        },
    )
    assert "max-sentence-length" not in cfg.active_rule_names
    overlap_warnings = [w for w in cfg.warnings if "rules" in w and "disable" in w]
    assert len(overlap_warnings) == 1


def test_overlap_with_core_rule() -> None:
    cfg = resolve_config(
        raw_config={
            "rules": ["no-dashes"],
            "disable": ["no-dashes"],
        },
    )
    assert "no-dashes" not in cfg.active_rule_names
    overlap_warnings = [w for w in cfg.warnings if "rules" in w and "disable" in w]
    assert len(overlap_warnings) == 1


# ---------------------------------------------------------------------------
# max-sentence-words
# ---------------------------------------------------------------------------


def test_max_sentence_words_override() -> None:
    cfg = resolve_config(
        strict=True,
        raw_config={"max-sentence-words": 25},
    )
    assert cfg.max_sentence_words == 25


def test_max_sentence_words_invalid() -> None:
    cfg = resolve_config(raw_config={"max-sentence-words": -5})
    assert cfg.max_sentence_words == 40  # default
    assert len(cfg.warnings) == 1


def test_max_sentence_words_wrong_type() -> None:
    cfg = resolve_config(raw_config={"max-sentence-words": "thirty"})
    assert cfg.max_sentence_words == 40
    assert len(cfg.warnings) == 1


# ---------------------------------------------------------------------------
# flesch-target
# ---------------------------------------------------------------------------


def test_flesch_target_set() -> None:
    cfg = resolve_config(raw_config={"flesch-target": [60, 80]})
    assert cfg.flesch_target == (60.0, 80.0)


def test_flesch_target_invalid_order() -> None:
    cfg = resolve_config(raw_config={"flesch-target": [80, 60]})
    assert cfg.flesch_target == (0.0, 100.0)  # default
    assert len(cfg.warnings) == 1


def test_flesch_target_wrong_format() -> None:
    cfg = resolve_config(raw_config={"flesch-target": "high"})
    assert cfg.flesch_target == (0.0, 100.0)
    assert len(cfg.warnings) == 1


# ---------------------------------------------------------------------------
# filler-words-extra
# ---------------------------------------------------------------------------


def test_filler_words_extra() -> None:
    cfg = resolve_config(raw_config={"filler-words-extra": ["Definitiv", "ABSOLUT"]})
    assert "definitiv" in cfg.filler_words_extra
    assert "absolut" in cfg.filler_words_extra


def test_filler_words_extra_invalid() -> None:
    cfg = resolve_config(raw_config={"filler-words-extra": "not-a-list"})
    assert cfg.filler_words_extra == []
    assert len(cfg.warnings) == 1


# ---------------------------------------------------------------------------
# Rule override (factories)
# ---------------------------------------------------------------------------


def test_custom_sentence_length_creates_factory(tmp_path) -> None:
    """Configured max-sentence-words should create a rule with the custom threshold."""
    cfg = resolve_config(
        strict=True,
        raw_config={"max-sentence-words": 5},
    )
    # Find the sentence length rule and test it
    idx = cfg.active_rule_names.index("max-sentence-length")
    rule = cfg.active_rules[idx]

    from pathlib import Path

    # 7 words should trigger with max=5
    text = "Eins zwei drei vier fünf sechs sieben.\n"
    violations = rule(text, Path("test.md"))
    assert len(violations) >= 1
    assert "5" in violations[0].message


def test_custom_filler_words_creates_factory(tmp_path) -> None:
    """Configured filler-words-extra should extend the default filler list."""
    cfg = resolve_config(
        strict=True,
        raw_config={"filler-words-extra": ["krass"]},
    )
    idx = cfg.active_rule_names.index("filler-words-de")
    rule = cfg.active_rules[idx]

    from pathlib import Path

    text = "Das ist krass wichtig.\n"
    violations = rule(text, Path("test.md"))
    assert len(violations) >= 1
    assert "krass" in violations[0].message


# ---------------------------------------------------------------------------
# Empty / no config
# ---------------------------------------------------------------------------


def test_no_config_file() -> None:
    cfg = resolve_config(raw_config={})
    assert len(cfg.active_rules) == 5
    assert cfg.max_sentence_words == 40
    assert cfg.flesch_target == (0.0, 100.0)
    assert cfg.filler_words_extra == []
    assert cfg.warnings == []


def test_combined_config() -> None:
    cfg = resolve_config(
        strict=True,
        raw_config={
            "rules": ["max-sentence-length"],
            "disable": ["passive-voice-de", "no-double-spaces"],
            "max-sentence-words": 30,
            "flesch-target": [65, 80],
            "filler-words-extra": ["mega"],
        },
    )
    assert "passive-voice-de" not in cfg.active_rule_names
    assert "no-double-spaces" not in cfg.active_rule_names
    assert "max-sentence-length" in cfg.active_rule_names
    assert cfg.max_sentence_words == 30
    assert cfg.flesch_target == (65.0, 80.0)
    assert "mega" in cfg.filler_words_extra
    # 8 total - 2 disabled = 6
    assert len(cfg.active_rule_names) == 6
