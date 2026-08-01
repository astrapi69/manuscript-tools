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
| `ms-check` | Style-Checks (6 Core-Regeln, `--strict` fügt 3 Prosa-Regeln hinzu) |
| `ms-sanitize` | Encoding reparieren, unsichtbare Zeichen entfernen, Unicode normalisieren |
| `ms-quotes` | Anführungszeichen in deutsche Typografie konvertieren „ " ‚ ' |
| `ms-dashes` | Gefakte Gedankenstriche (`--`, gespationierter Bindestrich) durch echte ersetzen (`--to em\|en`) |
| `ms-umlauts` | ASCII-Umlaute (`fuer` zu `für`) per kuratierter Wortliste ersetzen |
| `ms-format` | Gebrochenes Bold/Italic von zeilenumbrechenden Formatierern reparieren |
| `ms-metrics` | Wortzahl, Satzanalyse, Flesch-DE Lesbarkeitsindex |
| `ms-validate` | Volle QA-Pipeline (Sanitize + Quotes + Formatierung + Check + Lesbarkeit) |

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

# Gebrochenes Bold/Italic reparieren (Vorschau)
ms-format manuscript/ --dry-run

# -- und gespationierte Bindestriche zu Halbgeviertstrichen (Vorschau)
ms-dashes manuscript/ --to en --dry-run

# ASCII-Umlaute wie "fuer" und "Uebung" ersetzen (Vorschau)
ms-umlauts manuscript/ --dry-run
```

## Dateiauswahl

Nicht auf Markdown beschränkt. Verzeichnisse werden per Default mit dem Glob `**/*.md` durchsucht; eine einzelne Datei als Argument wird unabhängig von der Endung direkt verarbeitet:

```bash
# Einzeldatei: kein Glob-Filter
ms-check brief.txt

# Verzeichnis mit anderen Endungen: Glob überschreiben
ms-sanitize docs/ --include '**/*.txt'
ms-check kapitel/ --include '**/*.tex' --exclude '**/build/**'
```

Dateien müssen UTF-8-Text sein (txt, tex, rst, html, ...) — Binärformate wie docx oder pdf werden nicht unterstützt. Die Regel `broken-formatting` prüft Markdown-Marker (`**`/`*`); bei Nicht-Markdown-Dateien ist sie harmlos oder lässt sich per `disable = ["broken-formatting"]` in der [Konfiguration](#konfiguration) abschalten.

## Beispiel

Ein Manuskript mit typischen Artefakten aus AI-Tools, Copy-Paste oder Code-Formatierern — Zeile 1 enthält ein unsichtbares Zero-Width Space (U+200B) nach „Test":

```markdown
Das ist ein Test mit unsichtbarem Zeichen.

Er sagte: "Hallo Welt" und ging.

Dies ist ein **
wichtiger Satz** im Text.
```

`ms-check` meldet jedes Problem mit Datei, Zeile und Regel — unsichtbare Zeichen werden mit Codepoint benannt:

```console
$ ms-check kapitel-01.md
FAIL: kapitel-01.md:1 [no-invisible-chars] Unsichtbare Unicode-Zeichen gefunden: U+200B ZERO WIDTH SPACE
FAIL: kapitel-01.md:3 [non-german-quotes] Nicht-deutsche Anführungszeichen gefunden
FAIL: kapitel-01.md:5 [broken-formatting] Oeffnendes ** am Zeilenende (Formatierung gebrochen)
------------------------------------------------------------
Dateien: 1, Woerter: 21
Status: FEHLER (1 Dateien, 3 Verstoss(e))
```

Schritt für Schritt beheben — jeder Fixer unterstützt `--dry-run` (Vorschau) und legt `.bak`-Backups an:

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

Ergebnis:

```markdown
Das ist ein Test mit unsichtbarem Zeichen.

Er sagte: „Hallo Welt“ und ging.

Dies ist ein **wichtiger Satz** im Text.
```

Oder alles in einem Durchlauf: `ms-validate kapitel-01.md --fix`.

## Regeln

**Core** (immer aktiv):

`no-dashes`, `no-invisible-chars`, `no-repeated-words`, `no-double-spaces`, `non-german-quotes`, `broken-formatting`

**Prosa** (mit `--strict` oder `ms-validate`):

`max-sentence-length`, `filler-words-de`, `passive-voice-de`

**Opt-in** (über `rules = [...]` in der Konfiguration):

`faked-dashes` — findet `--` und gespationierte Bindestriche, die einen echten Gedankenstrich ersetzen sollen. Widerspricht bewusst `no-dashes` (eine Regel verbietet Gedankenstriche, die andere verlangt korrekt gesetzte) — eine aktivieren, die andere deaktivieren. `ms-dashes --to em|en` schreibt die Funde um:

```text
Er kam -- wie immer -- viel zu spaet.      # vorher
Er kam – wie immer – viel zu spaet.        # nachher ms-dashes --to en
Seiten 12 - 15 behandeln das Thema.        # Zahlenbereiche bleiben unangetastet
[x](https://img.shields.io/badge/a--b)     # URLs und Badge-Slugs bleiben unangetastet
```

`ascii-umlauts` — findet ASCII-Umlaut-Schreibweisen (`fuer`, `Uebung`) aus kuratierter Wortliste; `ms-umlauts` schreibt sie um. Bewusst kein Pattern: Deutsch ist voller legitimer ae/oe/ue-Folgen („Frauen", „Goethe", „Aerobic"), darum werden nur geprüfte ganze Wörter angefasst — null False Positives per Konstruktion. Projektspezifisch erweiterbar über `umlaut-words-extra = ["oekologie"]`. `ss` zu `ß` bleibt außen vor (kontextabhängig, Schweiz-Konflikt).

```text
Das waere natuerlich schoen fuer alle.     # vorher
Das wäre natürlich schön für alle.         # nachher ms-umlauts
Goethe traf die Frauen beim Feuer.         # Namen und Diphthonge bleiben unangetastet
```

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
umlaut-words-extra = ["oekologie"]       # ascii-umlauts-Wortliste erweitern
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
make ci          # Lint + Format-Check + 208 Tests
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
