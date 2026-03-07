"""CLI entry points for manuscript-tools.

Registered as console_scripts via pyproject.toml:
  ms-check, ms-sanitize, ms-metrics
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from manuscript_tools.checker import check_files
from manuscript_tools.io import resolve_files
from manuscript_tools.metrics import batch_metrics
from manuscript_tools.models import RunStats
from manuscript_tools.sanitizer import sanitize_file

# ---------------------------------------------------------------------------
# Shared argument helpers
# ---------------------------------------------------------------------------


def _base_parser(description: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("path", nargs="?", default="manuscript", help="File or directory to process")
    p.add_argument("--include", default="**/*.md", help="Glob pattern (default: **/*.md)")
    p.add_argument("--exclude", action="append", default=[], help="Glob patterns to exclude")
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
    args = parser.parse_args()
    files = _resolve_or_exit(args)

    reports = check_files(files)
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

    print("-" * 40)
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
    parser = _base_parser("Sanitize Markdown files (fix encoding, normalize Unicode).")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    parser.add_argument("--backup", action="store_true", help="Create .bak files before modifying")
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

    print("-" * 40)
    print(
        f"Gesehen: {stats.files_seen}, "
        f"Bereinigt: {stats.files_failed}, "
        f"Fehler: {stats.errors}"
        f"{' (dry-run)' if args.dry_run else ''}"
    )


# ---------------------------------------------------------------------------
# ms-metrics
# ---------------------------------------------------------------------------


def metrics() -> None:
    """CLI: Show word counts and text metrics."""
    parser = _base_parser("Show text metrics for manuscript files.")
    args = parser.parse_args()
    files = _resolve_or_exit(args)

    results = batch_metrics(files)

    total_words = 0
    total_lines = 0
    total_chars = 0

    for m in results:
        if m.error:
            print(f"FEHLER: {m.path} - {m.error}", file=sys.stderr)
            continue
        print(f"{m.path.name:30s}  {m.words:>7,} Woerter  {m.lines:>6,} Zeilen")
        total_words += m.words
        total_lines += m.lines
        total_chars += m.chars

    print("-" * 40)
    print(
        f"{'Gesamt':30s}  {total_words:>7,} Woerter"
        f"  {total_lines:>6,} Zeilen  {total_chars:>8,} Zeichen"
    )
