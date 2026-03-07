"""File discovery and I/O helpers."""

from __future__ import annotations

from pathlib import Path


def resolve_files(
        root: Path,
        include: str = "**/*.md",
        exclude: list[str] | None = None,
) -> list[Path]:
    """Collect files matching *include* under *root*, minus any *exclude* globs.

    If *root* is a file, returns it directly (no glob applied).
    """
    if root.is_file():
        return [root]

    if not root.is_dir():
        return []

    files = sorted(root.glob(include))

    if exclude:
        excluded: set[Path] = set()
        for pattern in exclude:
            excluded.update(root.glob(pattern))
        files = [f for f in files if f not in excluded]

    return [f for f in files if f.is_file()]


def read_text(path: Path) -> str:
    """Read a file as UTF-8, raising on decode errors."""
    return path.read_text(encoding="utf-8", errors="strict")
