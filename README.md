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
| `ms-check` | Style checks (6 core rules, `--strict` adds 3 prose rules) |
| `ms-sanitize` | Fix encoding, strip invisible chars, normalize Unicode |
| `ms-quotes` | Convert quotation marks to German typographic style „ " ‚ ' |
| `ms-dashes` | Rewrite faked dashes (`--`, spaced hyphen) to a real dash (`--to em\|en`) |
| `ms-umlauts` | Rewrite ASCII umlauts (`fuer` to `für`) from a curated word list |
| `ms-format` | Fix broken bold/italic caused by line-wrapping formatters |
| `ms-metrics` | Word counts, sentence analysis, Flesch-DE readability score |
| `ms-validate` | Full QA pipeline (sanitize + quotes + formatting + check + readability) |

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

# Fix broken bold/italic formatting (dry-run)
ms-format manuscript/ --dry-run

# Rewrite -- and spaced hyphens to en-dashes (German typography, dry-run)
ms-dashes manuscript/ --to en --dry-run

# Rewrite ASCII umlauts like "fuer" and "Uebung" (dry-run)
ms-umlauts manuscript/ --dry-run
```

## File selection

Not limited to Markdown. Directories are scanned with the glob `**/*.md` by default; a single file passed as argument is processed as-is, regardless of extension:

```bash
# Single file: no glob filter applied
ms-check brief.txt

# Directory with other extensions: override the glob
ms-sanitize docs/ --include '**/*.txt'
ms-check kapitel/ --include '**/*.tex' --exclude '**/build/**'
```

Files must be UTF-8 text (txt, tex, rst, html, ...) — binary formats like docx or pdf are not supported. The `broken-formatting` rule checks Markdown `**`/`*` markers; for non-Markdown files it is harmless, or disable it via `disable = ["broken-formatting"]` in the [configuration](#configuration).

## Example

A manuscript with typical artifacts from AI tools, copy-paste, or code formatters — line 1 contains an invisible zero-width space (U+200B) after "Test":

```markdown
Das ist ein Test mit unsichtbarem Zeichen.

Er sagte: "Hallo Welt" und ging.

Dies ist ein **
wichtiger Satz** im Text.
```

`ms-check` reports every problem with file, line, and rule — invisible characters are named by codepoint:

```console
$ ms-check kapitel-01.md
FAIL: kapitel-01.md:1 [no-invisible-chars] Unsichtbare Unicode-Zeichen gefunden: U+200B ZERO WIDTH SPACE
FAIL: kapitel-01.md:3 [non-german-quotes] Nicht-deutsche Anführungszeichen gefunden
FAIL: kapitel-01.md:5 [broken-formatting] Oeffnendes ** am Zeilenende (Formatierung gebrochen)
------------------------------------------------------------
Dateien: 1, Woerter: 21
Status: FEHLER (1 Dateien, 3 Verstoss(e))
```

Fix step by step — every fixer supports `--dry-run` (preview) and writes `.bak` backups:

```console
$ ms-sanitize kapitel-01.md
CLEANED: kapitel-01.md
$ ms-quotes kapitel-01.md
FIXED: kapitel-01.md (1 Ersetzung(en))
$ ms-format kapitel-01.md
FIXED: kapitel-01.md (1 bold, 0 italic)
$ ms-check kapitel-01.md
OK: kapitel-01.md (20 Woerter)
Status: OK
```

Result:

```markdown
Das ist ein Test mit unsichtbarem Zeichen.

Er sagte: „Hallo Welt“ und ging.

Dies ist ein **wichtiger Satz** im Text.
```

Or run the whole pipeline in one go: `ms-validate kapitel-01.md --fix`.

## Rules

**Core** (always active):

`no-dashes`, `no-invisible-chars`, `no-repeated-words`, `no-double-spaces`, `non-german-quotes`, `broken-formatting`

`no-dashes` reports both the en dash (U+2013) and the em dash (U+2014) by default; `dashes-allow = ["en"]` in the configuration lets one kind pass — the en dash is what `ms-dashes --to en` writes. `no-repeated-words` skips the lowercase doubling of `der`, `die`, `das` and `sie` inside a sentence (relative pronoun followed by an article: „Leser, die die Natur lieben“); the same pair capitalised at a sentence start is still reported.

**Prose** (with `--strict` or `ms-validate`):

`max-sentence-length`, `filler-words-de`, `passive-voice-de`

**Opt-in** (via `rules = [...]` in the configuration):

`faked-dashes` — flags `--` and spaced hyphens standing in for a real dash. By design it contradicts `no-dashes` (one forbids dashes, the other demands correctly typed ones), so enable one and disable the other. `ms-dashes --to em|en` rewrites the findings:

```text
Er kam -- wie immer -- viel zu spaet.      # before
Er kam – wie immer – viel zu spaet.        # after ms-dashes --to en
Seiten 12 - 15 behandeln das Thema.        # numeric ranges stay untouched
[x](https://img.shields.io/badge/a--b)     # URLs and badge slugs stay untouched
```

`ascii-umlauts` — flags ASCII umlaut spellings (`fuer`, `Uebung`) from a curated word list; `ms-umlauts` rewrites them. Deliberately not a pattern: German is full of legitimate ae/oe/ue sequences ("Frauen", "Goethe", "Aerobic"), so only vetted whole words are touched — zero false positives by construction. Extend the list per project via `umlaut-words-extra = ["oekologie"]`. `ss` to `ß` is out of scope (context-dependent, Swiss orthography conflict).

```text
Das waere natuerlich schoen fuer alle.     # before
Das wäre natürlich schön für alle.         # after ms-umlauts
Goethe traf die Frauen beim Feuer.         # names and diphthongs stay untouched
```

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
umlaut-words-extra = ["oekologie"]       # extend the ascii-umlauts word list
dashes-allow = ["en"]                    # let the German en dash pass
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
make ci          # lint + format check + 255 tests
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
