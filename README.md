# manuscript-tools

A QA toolkit for German Markdown manuscripts. Validates style, sanitizes encoding, converts quotation marks, and measures readability.

**[Deutsche Version](README.de.md)** | **[Wiki](https://github.com/astrapi69/manuscript-tools/wiki)**

## Installation

```bash
pip install manuscript-tools
```

Or as project dependency:

```bash
poetry add manuscript-tools
```

## Commands

| Command | Description |
|---|---|
| `ms-check` | Style checks (5 core rules, `--strict` adds 3 prose rules) |
| `ms-sanitize` | Fix encoding, strip invisible chars, normalize Unicode |
| `ms-quotes` | Convert quotation marks to German typographic style „ " ‚ ' |
| `ms-metrics` | Word counts, sentence analysis, Flesch-DE readability score |
| `ms-validate` | Full QA pipeline (sanitize + quotes + check + readability) |

## Quick start

```bash
# Full QA pipeline
ms-validate manuscript/

# Style check only (core rules)
ms-check manuscript/

# Style check with prose analysis (filler words, passive voice, sentence length)
ms-check manuscript/ --strict

# Readability report
ms-metrics manuscript/

# Fix quotation marks (dry-run)
ms-quotes manuscript/ --dry-run
```

## Rules

**Core** (always active):

`no-dashes`, `no-invisible-chars`, `no-repeated-words`, `no-double-spaces`, `non-german-quotes`

**Prose** (with `--strict` or `ms-validate`):

`max-sentence-length`, `filler-words-de`, `passive-voice-de`

Custom rules are simple callables with the signature `(text: str, path: Path) -> list[StyleViolation]`. See the [Wiki](https://github.com/astrapi69/manuscript-tools/wiki/03-Eigene-Regeln) for a step-by-step tutorial.

## Configuration

Configure via `[tool.manuscript-tools]` in your `pyproject.toml`:

```toml
[tool.manuscript-tools]
rules = ["max-sentence-length"]          # merge with defaults
disable = ["passive-voice-de"]           # remove from active set
max-sentence-words = 30                  # default: 40
flesch-target = [65, 80]                 # warn if outside range
filler-words-extra = ["definitiv", "absolut"]  # extend filler list
```

No config = all defaults. `rules` merges with defaults (union). `disable` removes from the active set and takes precedence over `rules`. See the [Wiki](https://github.com/astrapi69/manuscript-tools/wiki/09-Konfiguration) for details.

## Readability

`ms-metrics` computes the Flesch-DE reading ease score (Amstad, 1978) with German-optimized syllable counting. Score interpretation:

| Score | Level | Typical use |
|---|---|---|
| 80-100 | Very easy | Children's books |
| 60-80 | Easy to medium | Fiction, non-fiction |
| 30-60 | Difficult | Journalism, academic |
| 0-30 | Very difficult | Legal, scientific |

## Development

```bash
git clone https://github.com/astrapi69/manuscript-tools.git
cd manuscript-tools
make install-dev
make ci          # lint + format check + 112 tests
```

## Documentation

Full documentation is available in the [Wiki](https://github.com/astrapi69/manuscript-tools/wiki):

- [Installation and Setup](https://github.com/astrapi69/manuscript-tools/wiki/01-Installation-und-Setup)
- [Usage](https://github.com/astrapi69/manuscript-tools/wiki/02-Verwendung)
- [Writing Custom Rules](https://github.com/astrapi69/manuscript-tools/wiki/03-Eigene-Regeln)
- [Integration into Projects](https://github.com/astrapi69/manuscript-tools/wiki/04-Integration)
- [Publishing to PyPI](https://github.com/astrapi69/manuscript-tools/wiki/05-Publishing)
- [Development and CI](https://github.com/astrapi69/manuscript-tools/wiki/06-Entwicklung-und-CI)
- [FAQ](https://github.com/astrapi69/manuscript-tools/wiki/07-FAQ)
- [Quick Start for Book Projects](https://github.com/astrapi69/manuscript-tools/wiki/08-Quick-Start)
- [Configuration](https://github.com/astrapi69/manuscript-tools/wiki/09-Konfiguration)

## License

BSD 3-Clause. See [LICENSE](LICENSE).
