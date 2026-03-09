# manuscript-tools

QA-Toolkit für deutschsprachige Markdown-Manuskripte. Validiert Style, bereinigt Encoding, konvertiert Anführungszeichen und misst Lesbarkeit.

**[English version](README.md)** | **[Wiki](https://github.com/astrapi69/manuscript-tools/wiki)**

## Installation

```bash
pip install manuscript-tools
```

Oder als Projekt-Dependency:

```bash
poetry add manuscript-tools
```

## Kommandos

| Kommando | Beschreibung |
|---|---|
| `ms-check` | Style-Checks (5 Core-Regeln, `--strict` fügt 3 Prosa-Regeln hinzu) |
| `ms-sanitize` | Encoding reparieren, unsichtbare Zeichen entfernen, Unicode normalisieren |
| `ms-quotes` | Anführungszeichen in deutsche Typografie konvertieren „ " ‚ ' |
| `ms-metrics` | Wortzahl, Satzanalyse, Flesch-DE Lesbarkeitsindex |
| `ms-validate` | Volle QA-Pipeline (Sanitize + Quotes + Check + Lesbarkeit) |

## Schnellstart

```bash
# Volle QA-Pipeline
ms-validate manuscript/

# Nur Style-Check (Core-Regeln)
ms-check manuscript/

# Style-Check mit Prosa-Analyse (Füllwörter, Passiv, Satzlänge)
ms-check manuscript/ --strict

# Lesbarkeitsreport
ms-metrics manuscript/

# Anführungszeichen korrigieren (Vorschau)
ms-quotes manuscript/ --dry-run
```

## Regeln

**Core** (immer aktiv):

`no-dashes`, `no-invisible-chars`, `no-repeated-words`, `no-double-spaces`, `non-german-quotes`

**Prosa** (mit `--strict` oder `ms-validate`):

`max-sentence-length`, `filler-words-de`, `passive-voice-de`

Eigene Regeln sind einfache Callables mit der Signatur `(text: str, path: Path) -> list[StyleViolation]`. Das [Wiki](https://github.com/astrapi69/manuscript-tools/wiki/03-Eigene-Regeln) enthält ein Schritt-für-Schritt-Tutorial.

## Konfiguration

Konfigurierbar über `[tool.manuscript-tools]` in der `pyproject.toml`:

```toml
[tool.manuscript-tools]
rules = ["max-sentence-length"]          # mit Defaults zusammenführen
disable = ["passive-voice-de"]           # aus aktivem Set entfernen
max-sentence-words = 30                  # Default: 40
flesch-target = [65, 80]                 # warnen wenn ausserhalb
filler-words-extra = ["definitiv", "absolut"]  # Füllwortliste erweitern
```

Keine Konfiguration = alle Defaults. `rules` wird mit Defaults zusammengeführt (Union). `disable` entfernt aus dem aktiven Set und hat Vorrang vor `rules`. Details im [Wiki](https://github.com/astrapi69/manuscript-tools/wiki/09-Konfiguration).

## Lesbarkeit

`ms-metrics` berechnet den Flesch-DE Lesbarkeitsindex (Amstad, 1978) mit deutscher Silbenzählung. Bewertung:

| Score | Bewertung | Typische Verwendung |
|---|---|---|
| 80-100 | Sehr leicht | Kinderbuch |
| 60-80 | Leicht bis mittel | Belletristik, Sachbuch |
| 30-60 | Schwer | Journalismus, Fachtext |
| 0-30 | Sehr schwer | Juristisch, wissenschaftlich |

## Entwicklung

```bash
git clone https://github.com/astrapi69/manuscript-tools.git
cd manuscript-tools
make install-dev
make ci          # Lint + Format-Check + 112 Tests
```

## Dokumentation

Die vollständige Dokumentation liegt im [Wiki](https://github.com/astrapi69/manuscript-tools/wiki):

- [Installation und Setup](https://github.com/astrapi69/manuscript-tools/wiki/01-Installation-und-Setup)
- [Verwendung](https://github.com/astrapi69/manuscript-tools/wiki/02-Verwendung)
- [Eigene Regeln schreiben](https://github.com/astrapi69/manuscript-tools/wiki/03-Eigene-Regeln)
- [Integration in andere Projekte](https://github.com/astrapi69/manuscript-tools/wiki/04-Integration)
- [Publishing auf PyPI](https://github.com/astrapi69/manuscript-tools/wiki/05-Publishing)
- [Entwicklung und CI](https://github.com/astrapi69/manuscript-tools/wiki/06-Entwicklung-und-CI)
- [FAQ](https://github.com/astrapi69/manuscript-tools/wiki/07-FAQ)
- [Quick Start für Buchprojekte](https://github.com/astrapi69/manuscript-tools/wiki/08-Quick-Start)
- [Konfiguration](https://github.com/astrapi69/manuscript-tools/wiki/09-Konfiguration)

## Lizenz

BSD 3-Clause. Siehe [LICENSE](LICENSE).
