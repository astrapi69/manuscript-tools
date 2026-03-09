"""CLI entry points for manuscript-tools.

Registered as console_scripts via pyproject.toml:
  ms-check, ms-sanitize, ms-quotes, ms-metrics, ms-validate
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from manuscript_tools.checker import check_files
from manuscript_tools.config import resolve_config
from manuscript_tools.io import resolve_files
from manuscript_tools.metrics import batch_readability, flesch_de_label
from manuscript_tools.models import RunStats
from manuscript_tools.quotes import convert_file
from manuscript_tools.sanitizer import sanitize_file

# ---------------------------------------------------------------------------
# Shared argument helpers
# ---------------------------------------------------------------------------


def _base_parser(description: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    p.add_argument(
        "path",
        nargs="?",
        default="manuscript",
        help="File or directory to process",
    )
    p.add_argument(
        "--include",
        default="**/*.md",
        help="Glob pattern (default: **/*.md)",
    )
    p.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Glob patterns to exclude",
    )
    return p


def _resolve_or_exit(args: argparse.Namespace) -> list[Path]:
    root = Path(args.path)
    if not root.exists():
        print(f"Fehler: Pfad '{root}' nicht gefunden.", file=sys.stderr)
        sys.exit(1)

    files = resolve_files(root, include=args.include, exclude=args.exclude)
    if not files:
        print("Keine passenden Dateien gefunden.")
        sys.exit(0)

    return files


# ---------------------------------------------------------------------------
# ms-check
# ---------------------------------------------------------------------------


def check() -> None:
    """CLI: Run style checks on manuscript files."""
    parser = _base_parser("Check manuscript style rules.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable all rules including prose analysis (filler words, passive, sentence length)",
    )
    args = parser.parse_args()
    files = _resolve_or_exit(args)

    cfg = resolve_config(strict=args.strict)

    for w in cfg.warnings:
        print(f"CONFIG: {w}", file=sys.stderr)

    reports = check_files(files, rules=cfg.active_rules)
    stats = RunStats(files_seen=len(reports))

    for report in reports:
        if report.error:
            print(f"FEHLER: {report.path} - {report.error}", file=sys.stderr)
            stats.errors += 1
            continue

        if report.ok:
            print(f"OK: {report.path} ({report.words} Woerter)")
            stats.files_ok += 1
        else:
            for v in report.violations:
                loc = f":{v.line}" if v.line else ""
                print(f"FAIL: {report.path}{loc} [{v.rule}] {v.message}")
            stats.files_failed += 1
            stats.total_violations += len(report.violations)

        stats.total_words += report.words

    print("-" * 60)
    print(f"Dateien: {stats.files_seen}, Woerter: {stats.total_words}")

    if stats.files_failed > 0 or stats.errors > 0:
        print(
            f"Status: FEHLER ({stats.files_failed} Dateien, {stats.total_violations} Verstoss(e))"
        )
        sys.exit(1)
    else:
        print("Status: OK")


# ---------------------------------------------------------------------------
# ms-sanitize
# ---------------------------------------------------------------------------


def sanitize() -> None:
    """CLI: Sanitize manuscript Markdown files."""
    parser = _base_parser(
        "Sanitize Markdown files (fix encoding, normalize Unicode).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show changes without writing",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create .bak files before modifying",
    )
    args = parser.parse_args()
    files = _resolve_or_exit(args)

    stats = RunStats(files_seen=len(files))

    for path in files:
        result = sanitize_file(path, dry_run=args.dry_run, backup=args.backup)

        if result.error:
            print(f"FEHLER: {result.path} - {result.error}", file=sys.stderr)
            stats.errors += 1
        elif result.changed:
            verb = "WOULD CLEAN" if args.dry_run else "CLEANED"
            print(f"{verb}: {result.path}")
            stats.files_failed += 1  # reuse as "changed" counter
        else:
            print(f"OK: {result.path}")
            stats.files_ok += 1

    print("-" * 60)
    print(
        f"Gesehen: {stats.files_seen}, "
        f"Bereinigt: {stats.files_failed}, "
        f"Fehler: {stats.errors}"
        f"{' (dry-run)' if args.dry_run else ''}"
    )


# ---------------------------------------------------------------------------
# ms-quotes
# ---------------------------------------------------------------------------


def quotes() -> None:
    """CLI: Convert quotation marks to German typographic style."""
    parser = _base_parser(
        "Convert quotation marks to German style (\u201e \u201c \u201a \u2018).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show changes without writing",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create .bak files",
    )
    args = parser.parse_args()
    files = _resolve_or_exit(args)

    total_replacements = 0
    files_changed = 0

    for path in files:
        result = convert_file(
            path,
            dry_run=args.dry_run,
            backup=not args.no_backup,
        )

        if result.error:
            print(f"FEHLER: {result.path} - {result.error}", file=sys.stderr)
            continue

        if result.changed:
            verb = "WOULD FIX" if args.dry_run else "FIXED"
            s = result.stats
            print(f"{verb}: {result.path} ({s.total_replacements} Ersetzung(en))")
            files_changed += 1
            total_replacements += s.total_replacements
        else:
            print(f"OK: {result.path}")

        for w in result.stats.warning_messages:
            print(f"  WARNUNG: {w}", file=sys.stderr)

    print("-" * 60)
    print(
        f"Dateien: {len(files)}, "
        f"Korrigiert: {files_changed}, "
        f"Ersetzungen: {total_replacements}"
        f"{' (dry-run)' if args.dry_run else ''}"
    )


# ---------------------------------------------------------------------------
# ms-metrics
# ---------------------------------------------------------------------------


def metrics() -> None:
    """CLI: Show word counts, readability and text metrics."""
    parser = _base_parser("Show text metrics and readability for manuscript files.")
    args = parser.parse_args()
    files = _resolve_or_exit(args)

    reports = batch_readability(files)

    total_words = 0
    total_sentences = 0
    total_syllables = 0
    total_lines = 0
    total_chars = 0

    for r in reports:
        if r.error:
            print(f"FEHLER: {r.path} - {r.error}", file=sys.stderr)
            continue

        s = r.readability
        label = flesch_de_label(s.flesch_de)
        print(
            f"{r.path.name:30s}"
            f"  {s.words:>7,} Woerter"
            f"  {s.sentences:>5,} Saetze"
            f"  Flesch: {s.flesch_de:>5.1f} ({label})"
        )

        total_words += s.words
        total_sentences += s.sentences
        total_syllables += s.syllables
        total_lines += s.lines
        total_chars += s.chars

    print("-" * 60)
    print(
        f"{'Gesamt':30s}"
        f"  {total_words:>7,} Woerter"
        f"  {total_sentences:>5,} Saetze"
        f"  {total_lines:>6,} Zeilen"
    )

    if total_words > 0 and total_sentences > 0:
        from manuscript_tools.metrics import flesch_de as calc_flesch

        total_flesch = calc_flesch(total_words, total_sentences, total_syllables)
        total_label = flesch_de_label(total_flesch)
        avg_sent = total_words / total_sentences
        avg_syl = total_syllables / total_words
        print()
        print("Lesbarkeitsanalyse (gesamt):")
        print(f"  Flesch-DE:                 {total_flesch:>5.1f} ({total_label})")
        print(f"  Durchschn. Satzlaenge:     {avg_sent:>5.1f} Woerter")
        print(f"  Durchschn. Silben/Wort:    {avg_syl:>5.2f}")


# ---------------------------------------------------------------------------
# ms-validate
# ---------------------------------------------------------------------------


def validate() -> None:
    """CLI: Full validation pipeline (sanitize dry-run + strict check + metrics)."""
    parser = _base_parser(
        "Full validation pipeline: sanitize check, style check, readability report.",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Actually sanitize files (with backup) instead of dry-run",
    )
    args = parser.parse_args()
    files = _resolve_or_exit(args)

    cfg = resolve_config(strict=True)

    for w in cfg.warnings:
        print(f"CONFIG: {w}", file=sys.stderr)

    has_errors = False

    # --- Phase 1: Sanitize ---
    print("=" * 60)
    print("PHASE 1: Sanitize")
    print("=" * 60)

    sanitize_count = 0
    for path in files:
        dry_run = not args.fix
        result = sanitize_file(path, dry_run=dry_run, backup=args.fix)
        if result.error:
            print(f"FEHLER: {result.path} - {result.error}", file=sys.stderr)
            has_errors = True
        elif result.changed:
            verb = "BEREINIGT" if args.fix else "MUSS BEREINIGT WERDEN"
            print(f"  {verb}: {result.path}")
            sanitize_count += 1
            if not args.fix:
                has_errors = True

    if sanitize_count == 0:
        print("  Alle Dateien sauber.")
    elif not args.fix:
        print(f"  {sanitize_count} Datei(en) benötigen Bereinigung.")
        print("  Tipp: --fix zum automatischen Bereinigen verwenden.")

    # --- Phase 2: Quotes ---
    print()
    print("=" * 60)
    print("PHASE 2: Anführungszeichen")
    print("=" * 60)

    quotes_count = 0
    for path in files:
        dry_run = not args.fix
        result = convert_file(path, dry_run=dry_run, backup=args.fix)
        if result.error:
            print(f"FEHLER: {result.path} - {result.error}", file=sys.stderr)
            has_errors = True
        elif result.changed:
            verb = "KORRIGIERT" if args.fix else "MUSS KORRIGIERT WERDEN"
            print(f"  {verb}: {result.path} ({result.stats.total_replacements} Ersetzung(en))")
            quotes_count += 1
            if not args.fix:
                has_errors = True

        for w in result.stats.warning_messages:
            print(f"    WARNUNG: {w}", file=sys.stderr)

    if quotes_count == 0:
        print("  Alle Anführungszeichen korrekt.")
    elif not args.fix:
        print(f"  {quotes_count} Datei(en) mit nicht-deutschen Anführungszeichen.")
        print("  Tipp: --fix oder ms-quotes zum Korrigieren verwenden.")

    # --- Phase 3: Style Check ---
    print()
    print("=" * 60)
    print("PHASE 3: Style-Check (alle Regeln)")
    print("=" * 60)

    reports = check_files(files, rules=cfg.active_rules)
    total_violations = 0

    for report in reports:
        if report.error:
            print(f"FEHLER: {report.path} - {report.error}", file=sys.stderr)
            has_errors = True
            continue

        if report.ok:
            print(f"  OK: {report.path}")
        else:
            for v in report.violations:
                loc = f":{v.line}" if v.line else ""
                print(f"  FAIL: {report.path}{loc} [{v.rule}] {v.message}")
            total_violations += len(report.violations)

    if total_violations > 0:
        print(f"  {total_violations} Verstoss(e) gefunden.")
        has_errors = True
    else:
        print("  Keine Verstoesse.")

    # --- Phase 4: Readability ---
    print()
    print("=" * 60)
    print("PHASE 4: Lesbarkeit")
    print("=" * 60)

    readability_reports = batch_readability(files)
    total_words = 0
    total_sentences = 0
    total_syllables = 0

    for r in readability_reports:
        if r.error:
            continue
        s = r.readability
        label = flesch_de_label(s.flesch_de)
        print(
            f"  {r.path.name:28s}"
            f"  {s.words:>6,} W"
            f"  {s.sentences:>4,} S"
            f"  Flesch {s.flesch_de:>5.1f} ({label})"
        )
        if s.longest_sentence_words > 35:
            print(
                f"    Laengster Satz: {s.longest_sentence_words} Woerter"
                f" (Zeile {s.longest_sentence_line})"
            )
        total_words += s.words
        total_sentences += s.sentences
        total_syllables += s.syllables

    if total_words > 0 and total_sentences > 0:
        from manuscript_tools.metrics import flesch_de as calc_flesch

        total_flesch = calc_flesch(total_words, total_sentences, total_syllables)
        total_label = flesch_de_label(total_flesch)
        print()
        print(f"  Gesamt: {total_words:,} Woerter, Flesch-DE {total_flesch:.1f} ({total_label})")

        # Check against configured target range
        fmin, fmax = cfg.flesch_target
        if fmin > 0 or fmax < 100:
            if total_flesch < fmin or total_flesch > fmax:
                print(
                    f"  WARNUNG: Flesch-DE {total_flesch:.1f} liegt ausserhalb "
                    f"des Zielbereichs [{fmin:.0f}, {fmax:.0f}]"
                )
                has_errors = True
            else:
                print(f"  Flesch-DE liegt im Zielbereich [{fmin:.0f}, {fmax:.0f}]")

    # --- Summary ---
    print()
    print("=" * 60)
    if has_errors:
        print("ERGEBNIS: Probleme gefunden. Siehe Details oben.")
        sys.exit(1)
    else:
        print("ERGEBNIS: Alles OK.")
