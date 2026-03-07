"""Tests for manuscript_tools.metrics."""

from pathlib import Path

from manuscript_tools.metrics import count_words, file_metrics


def test_count_words_simple() -> None:
    assert count_words("Hallo Welt") == 2


def test_count_words_ignores_markdown_syntax() -> None:
    text = "## Kapitel 1\n\n> Ein Zitat mit **fetten** Woertern.\n"
    # Should count: Kapitel, 1, Ein, Zitat, mit, fetten, Woertern = 7
    assert count_words(text) == 7


def test_count_words_empty() -> None:
    assert count_words("") == 0


def test_count_words_only_symbols() -> None:
    assert count_words("--- ***") == 0


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
