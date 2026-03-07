#!/usr/bin/env python3
"""Bump version in pyproject.toml and sync to __init__.py.

Usage:
    python scripts/bump_version.py patch   # 0.2.0 -> 0.2.1
    python scripts/bump_version.py minor   # 0.2.0 -> 0.3.0
    python scripts/bump_version.py major   # 0.2.0 -> 1.0.0
    python scripts/bump_version.py 1.2.3   # set explicit version
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INIT_FILE = ROOT / "src" / "manuscript_tools" / "__init__.py"
VERSION_RE = re.compile(r'__version__\s*=\s*"([^"]+)"')


def read_init_version() -> str:
    text = INIT_FILE.read_text(encoding="utf-8")
    m = VERSION_RE.search(text)
    if not m:
        print("FEHLER: __version__ nicht in __init__.py gefunden.", file=sys.stderr)
        sys.exit(1)
    return m.group(1)


def write_init_version(version: str) -> None:
    text = INIT_FILE.read_text(encoding="utf-8")
    new_text = VERSION_RE.sub(f'__version__ = "{version}"', text)
    INIT_FILE.write_text(new_text, encoding="utf-8")


def bump_poetry(part: str) -> str:
    """Run poetry version and return the new version string."""
    result = subprocess.run(
        ["poetry", "version", part],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if result.returncode != 0:
        print(f"FEHLER: poetry version failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Extract version from output like "manuscript-tools 0.3.0"
    output = result.stdout.strip()
    version = output.split()[-1]
    return version


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: bump_version.py <patch|minor|major|X.Y.Z>")
        sys.exit(1)

    part = sys.argv[1]
    old_version = read_init_version()

    # Explicit version or semantic bump
    if re.match(r"^\d+\.\d+\.\d+$", part):
        new_version = bump_poetry(part)
    elif part in ("patch", "minor", "major"):
        new_version = bump_poetry(part)
    else:
        print(f"FEHLER: Unbekannter Bump-Typ: {part}")
        sys.exit(1)

    write_init_version(new_version)

    print(f"{old_version} -> {new_version}")
    print(f"  pyproject.toml: aktualisiert")
    print(f"  __init__.py:    aktualisiert")
    print()
    print("Naechste Schritte:")
    print(f'  git add -A && git commit -m "chore: bump version to {new_version}"')
    print(f'  git tag -a "v{new_version}" -m "v{new_version}"')


if __name__ == "__main__":
    main()
