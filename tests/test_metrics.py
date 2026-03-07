"""Tests for manuscript_tools.metrics."""

from pathlib import Path

from manuscript_tools.metrics import (
    analyze_readability,
    count_syllables,
    count_syllables_word,
    count_words,
    file_metrics,
    file_readability,
    flesch_de,
    flesch_de_label,
    split_sentences,
)

# ---------------------------------------------------------------------------
# count_words
# ---------------------------------------------------------------------------


def test_count_words_simple() -> None:
    assert count_words("Hallo Welt") == 2


def test_count_words_ignores_markdown_syntax() -> None:
    text = "## Kapitel 1\n\n> Ein Zitat mit **fetten** Woertern.\n"
    # Kapitel, 1, Ein, Zitat, mit, fetten, Woertern = 7
    assert count_words(text) == 7


def test_count_words_empty() -> None:
    assert count_words("") == 0


def test_count_words_only_symbols() -> None:
    assert count_words("--- ***") == 0


# ---------------------------------------------------------------------------
# count_syllables_word
# ---------------------------------------------------------------------------


def test_syllables_short_word() -> None:
    assert count_syllables_word("Hund") == 1


def test_syllables_two_syllables() -> None:
    assert count_syllables_word("Katze") >= 2


def test_syllables_diphthong_ei() -> None:
    # "Brei" has one syllable (ei is a diphthong)
    assert count_syllables_word("Brei") == 1


def test_syllables_diphthong_au() -> None:
    assert count_syllables_word("Haus") == 1


def test_syllables_multi() -> None:
    # "Freundlichkeit" should have 3+ syllables
    assert count_syllables_word("Freundlichkeit") >= 3


def test_syllables_empty() -> None:
    assert count_syllables_word("") == 0


def test_syllables_single_char() -> None:
    assert count_syllables_word("a") == 1


# ---------------------------------------------------------------------------
# count_syllables (text)
# ---------------------------------------------------------------------------


def test_syllables_text() -> None:
    text = "Der Hund lief schnell."
    result = count_syllables(text)
    assert result >= 4  # Der(1) Hund(1) lief(1) schnell(1)


# ---------------------------------------------------------------------------
# split_sentences
# ---------------------------------------------------------------------------


def test_split_sentences_simple() -> None:
    text = "Erster Satz. Zweiter Satz. Dritter Satz."
    sentences = split_sentences(text)
    assert len(sentences) == 3


def test_split_sentences_exclamation() -> None:
    text = "Halt! Wer da? Niemand."
    sentences = split_sentences(text)
    assert len(sentences) == 3


def test_split_sentences_strips_markdown() -> None:
    text = "## Kapitel\n\nErster Satz. **Zweiter** Satz.\n"
    sentences = split_sentences(text)
    # "Kapitel" is a heading word, "Erster Satz", "Zweiter Satz"
    assert len(sentences) >= 2


def test_split_sentences_empty() -> None:
    assert split_sentences("") == []


def test_split_sentences_no_punctuation() -> None:
    text = "Ein Text ohne Satzzeichen am Ende"
    sentences = split_sentences(text)
    assert len(sentences) >= 1


# ---------------------------------------------------------------------------
# flesch_de
# ---------------------------------------------------------------------------


def test_flesch_de_simple() -> None:
    # Short words, short sentences -> high score
    score = flesch_de(total_words=10, total_sentences=5, total_syllables=12)
    assert score > 60


def test_flesch_de_complex() -> None:
    # Long words, long sentences -> low score
    score = flesch_de(total_words=100, total_sentences=3, total_syllables=250)
    assert score < 40


def test_flesch_de_empty() -> None:
    assert flesch_de(0, 0, 0) == 0.0


def test_flesch_de_clamped() -> None:
    # Score should be clamped between 0 and 100
    score = flesch_de(total_words=1, total_sentences=1, total_syllables=1)
    assert 0.0 <= score <= 100.0


# ---------------------------------------------------------------------------
# flesch_de_label
# ---------------------------------------------------------------------------


def test_flesch_labels() -> None:
    assert flesch_de_label(85) == "Sehr leicht"
    assert flesch_de_label(75) == "Leicht"
    assert flesch_de_label(65) == "Mittel"
    assert flesch_de_label(55) == "Mittelschwer"
    assert flesch_de_label(40) == "Schwer"
    assert flesch_de_label(15) == "Sehr schwer"


# ---------------------------------------------------------------------------
# analyze_readability
# ---------------------------------------------------------------------------


def test_readability_basic() -> None:
    text = "Kurzer Satz. Noch ein Satz. Und ein dritter.\n"
    stats = analyze_readability(text)
    assert stats.words > 0
    assert stats.sentences == 3
    assert stats.syllables > 0
    assert stats.flesch_de > 0
    assert stats.avg_sentence_length > 0


def test_readability_empty() -> None:
    stats = analyze_readability("")
    assert stats.words == 0
    assert stats.sentences == 0
    assert stats.flesch_de == 0.0


def test_readability_single_sentence() -> None:
    text = "Ein einzelner kurzer Satz.\n"
    stats = analyze_readability(text)
    assert stats.sentences == 1
    assert stats.avg_sentence_length == stats.words


def test_readability_longest_sentence() -> None:
    text = "Kurz. Das hier ist ein deutlich laengerer Satz mit vielen Woertern.\n"
    stats = analyze_readability(text)
    assert stats.longest_sentence_words > 2


# ---------------------------------------------------------------------------
# file_metrics (legacy interface)
# ---------------------------------------------------------------------------


def test_file_metrics_valid(tmp_path: Path) -> None:
    f = tmp_path / "test.md"
    f.write_text("Erste Zeile\nZweite Zeile\n", encoding="utf-8")
    m = file_metrics(f)
    assert m.words == 4
    assert m.lines == 2
    assert m.error is None


def test_file_metrics_missing_file(tmp_path: Path) -> None:
    f = tmp_path / "nope.md"
    m = file_metrics(f)
    assert m.error is not None
    assert m.words == 0


# ---------------------------------------------------------------------------
# file_readability
# ---------------------------------------------------------------------------


def test_file_readability_valid(tmp_path: Path) -> None:
    f = tmp_path / "test.md"
    f.write_text(
        "Erster Satz ist kurz. Zweiter Satz auch. Dritter ebenso.\n",
        encoding="utf-8",
    )
    report = file_readability(f)
    assert report.error is None
    assert report.readability.words > 0
    assert report.readability.sentences == 3
    assert report.readability.flesch_de > 0


def test_file_readability_missing(tmp_path: Path) -> None:
    f = tmp_path / "nope.md"
    report = file_readability(f)
    assert report.error is not None
