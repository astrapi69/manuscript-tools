# manuscript-tools

Python-Toolkit zur Validierung, Bereinigung und Vermessung von Markdown-Manuskripten. Gebaut fuer Autoren, die ihren Publishing-Workflow automatisieren.

**[English version](README.md)**

## Was es macht

**ms-check** prueft das Manuskript auf Style-Verstoesse. Zwei eingebaute Regeln (typografische Gedankenstriche, unsichtbare Unicode-Zeichen) sind enthalten, eigene Regeln lassen sich als einfache Python-Callables registrieren.

**ms-sanitize** repariert Encoding-Probleme, normalisiert Unicode (NFKC), entfernt unsichtbare Steuerzeichen, ersetzt problematische Whitespace-Zeichen und stellt einheitliche Zeilenenden sicher. Unterstuetzt Dry-Run und Backup-Modus.

**ms-metrics** liefert Wortzahlen, Zeilenzahlen und Zeichenzahlen pro Datei und insgesamt. Nutzt Regex-basiertes Word-Boundary-Matching statt naivem Whitespace-Splitting, sodass Markdown-Syntax nicht als Woerter gezaehlt wird.

## Voraussetzungen

- Python 3.11+
- Poetry

## Installation

```bash
git clone <deine-repo-url> manuscript-tools
cd manuscript-tools
make install
```

Oder manuell:

```bash
poetry install
```

## Verwendung

Alle Kommandos akzeptieren einen Pfad (Datei oder Verzeichnis, Standard: `manuscript/`), `--include` und `--exclude` Glob-Patterns.

### Style-Checks

```bash
make check
# oder mit eigenem Pfad
make check MANUSCRIPT=kapitel/
# oder direkt
poetry run ms-check manuscript/ --exclude 'entwuerfe/*'
```

Ausgabe pro Datei: Regelname, Verstoessbeschreibung und Zeilennummer. Exit-Code 1 bei Verstoessen.

### Bereinigung

```bash
# Vorschau ohne Schreiben
make sanitize-dry

# Aenderungen mit Backup
make sanitize-backup

# Aenderungen direkt (ohne Backup)
make sanitize
```

### Textmetriken

```bash
make metrics
```

Ausgabe:

```
kapitel-01.md                     3.412 Woerter   187 Zeilen
kapitel-02.md                     2.891 Woerter   154 Zeilen
----------------------------------------
Gesamt                            6.303 Woerter   341 Zeilen    38.219 Zeichen
```

### Kombinierte Validierung

```bash
# Fuehrt Sanitize-Dry-Run gefolgt von Style-Check aus
make validate
```

## Eigene Regeln schreiben

Eine Regel ist jedes Callable mit der Signatur `(text: str, path: Path) -> list[StyleViolation]`.

```python
from pathlib import Path
from manuscript_tools.checker import check_file
from manuscript_tools.models import StyleViolation

def rule_no_todos(text: str, path: Path) -> list[StyleViolation]:
    return [
        StyleViolation(file=path, rule="no-todos", message="TODO gefunden", line=i)
        for i, line in enumerate(text.splitlines(), start=1)
        if "TODO" in line
    ]

report = check_file(Path("kapitel.md"), rules=[rule_no_todos])
```

## Entwicklung

```bash
# Mit Dev-Dependencies installieren
make install-dev

# Tests ausfuehren
make test

# Tests ausfuehrlich
make test-v

# Linter
make lint

# Lint-Probleme automatisch beheben
make lint-fix

# Code formatieren
make format

# Volle CI-Pipeline (Lint + Format-Check + Tests)
make ci
```

## Projektstruktur

```
src/manuscript_tools/
    __init__.py
    models.py       # Datenklassen (StyleViolation, FileReport, SanitizeResult, ...)
    io.py           # Datei-Discovery und Lesen
    checker.py      # Style-Validierung mit erweiterbaren Regeln
    sanitizer.py    # Textbereinigung (reine Logik + Datei-Operationen)
    metrics.py      # Wortzaehlung und Textstatistiken
    cli.py          # CLI-Einstiegspunkte (ms-check, ms-sanitize, ms-metrics)
tests/
    test_checker.py
    test_sanitizer.py
    test_metrics.py
Makefile            # Alle Tasks an einem Ort
pyproject.toml      # Poetry-Konfiguration, Dependencies, Tool-Einstellungen
```

## Makefile-Targets

`make` oder `make help` zeigt die vollstaendige Liste:

| Target | Beschreibung |
|---|---|
| `install` | Projekt mit allen Dependencies installieren |
| `install-dev` | Mit Dev-Dependencies installieren |
| `check` | Style-Checks auf Manuskript ausfuehren |
| `sanitize` | Manuskript-Dateien in-place bereinigen |
| `sanitize-dry` | Bereinigung als Dry-Run (nur Vorschau) |
| `sanitize-backup` | Bereinigung mit .bak-Backup-Dateien |
| `metrics` | Wortzahlen und Textmetriken anzeigen |
| `validate` | Volle Validierungs-Pipeline (Sanitize-Dry-Run + Check) |
| `test` | Alle Tests ausfuehren |
| `ci` | Volle CI-Pipeline (Lint + Format-Check + Tests) |
| `clean` | Build-Artefakte und Caches entfernen |
| `build` | Distributions-Paket bauen |

Alle Manuskript-Targets akzeptieren die Variablen `MANUSCRIPT=pfad`, `INCLUDE=pattern` und `EXCLUDE=pattern`.

## Lizenz

BSD 3-Clause. Siehe [LICENSE](LICENSE).
