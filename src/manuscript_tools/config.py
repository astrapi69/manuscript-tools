"""Project configuration via pyproject.toml.

Reads [tool.manuscript-tools] from the closest pyproject.toml and resolves
the active rule set based on defaults, user additions, and disables.

Resolution logic:
  1. Start with default rules (CORE or ALL depending on strict mode)
  2. If `rules` is set: validate names, merge with defaults (union)
  3. If `disable` is set: remove from active set
  4. If overlap between `rules` and `disable`: warn
  5. Return final ordered list

Example configuration:

    [tool.manuscript-tools]
    rules = ["max-sentence-length"]
    disable = ["passive-voice-de"]
    max-sentence-words = 30
    flesch-target = [60, 80]
    filler-words-extra = ["definitiv", "absolut", "total"]
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from manuscript_tools.checker import (
    ALL_RULE_NAMES,
    CORE_RULE_NAMES,
    RULE_REGISTRY,
    StyleRule,
    make_rule_filler_words_de,
    make_rule_max_sentence_length,
    resolve_rules,
)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ManuscriptConfig:
    """Resolved configuration for a manuscript-tools run."""

    active_rules: list[StyleRule] = field(default_factory=list)
    active_rule_names: list[str] = field(default_factory=list)
    max_sentence_words: int = 40
    flesch_target: tuple[float, float] = (0.0, 100.0)
    filler_words_extra: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Config file discovery
# ---------------------------------------------------------------------------


def find_pyproject(start: Path | None = None) -> Path | None:
    """Walk up from *start* to find the closest pyproject.toml."""
    current = (start or Path.cwd()).resolve()

    for directory in [current, *current.parents]:
        candidate = directory / "pyproject.toml"
        if candidate.is_file():
            return candidate
    return None


def read_tool_config(pyproject_path: Path | None = None) -> dict:
    """Read [tool.manuscript-tools] from pyproject.toml.

    Returns an empty dict if the file or section doesn't exist.
    """
    if pyproject_path is None:
        pyproject_path = find_pyproject()

    if pyproject_path is None or not pyproject_path.is_file():
        return {}

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    return data.get("tool", {}).get("manuscript-tools", {})


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_rule_names(names: list[str], field_name: str) -> list[str]:
    """Validate rule names against the registry, return warnings for unknown names."""
    warnings: list[str] = []
    for name in names:
        if name not in RULE_REGISTRY:
            warnings.append(
                f"Unbekannte Regel in '{field_name}': '{name}'. "
                f"Verfügbar: {', '.join(sorted(RULE_REGISTRY.keys()))}"
            )
    return warnings


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


def resolve_config(
    *,
    strict: bool = False,
    config_path: Path | None = None,
    raw_config: dict | None = None,
) -> ManuscriptConfig:
    """Resolve the active rule set from defaults + pyproject.toml config.

    Args:
        strict: If True, start with ALL rules (core + prose) instead of core only.
        config_path: Explicit path to pyproject.toml (optional).
        raw_config: Pre-loaded config dict (for testing, skips file I/O).

    Returns:
        ManuscriptConfig with resolved rules, thresholds, and warnings.
    """
    config = ManuscriptConfig()

    # Load raw config
    raw = raw_config if raw_config is not None else read_tool_config(config_path)

    # --- Step 1: Start with defaults ---
    active_names = list(ALL_RULE_NAMES) if strict else list(CORE_RULE_NAMES)

    # --- Step 2: Merge user rules ---
    user_rules: list[str] = raw.get("rules", [])
    if user_rules:
        config.warnings.extend(_validate_rule_names(user_rules, "rules"))
        # Filter to valid names only
        valid_user_rules = [n for n in user_rules if n in RULE_REGISTRY]
        # Merge: add new ones that aren't already in the active set
        for name in valid_user_rules:
            if name not in active_names:
                active_names.append(name)

    # --- Step 3: Apply disable ---
    disable: list[str] = raw.get("disable", [])
    if disable:
        config.warnings.extend(_validate_rule_names(disable, "disable"))

    # --- Step 4: Warn on overlap ---
    if user_rules and disable:
        overlap = set(user_rules) & set(disable)
        if overlap:
            for name in sorted(overlap):
                config.warnings.append(
                    f"Regel '{name}' ist in 'rules' und 'disable' gleichzeitig "
                    f"definiert. 'disable' hat Vorrang, Regel wird deaktiviert."
                )

    # Remove disabled rules
    valid_disable = {n for n in disable if n in RULE_REGISTRY}
    active_names = [n for n in active_names if n not in valid_disable]

    # --- Step 5: Resolve to callables ---
    config.active_rule_names = active_names
    config.active_rules = resolve_rules(active_names)

    # --- Thresholds and extras ---
    if "max-sentence-words" in raw:
        val = raw["max-sentence-words"]
        if isinstance(val, int) and val > 0:
            config.max_sentence_words = val
        else:
            config.warnings.append(
                f"'max-sentence-words' muss eine positive Ganzzahl sein, "
                f"erhalten: {val!r}. Verwende Default ({config.max_sentence_words})."
            )

    if "flesch-target" in raw:
        val = raw["flesch-target"]
        if (
            isinstance(val, list)
            and len(val) == 2
            and all(isinstance(v, int | float) for v in val)
            and val[0] <= val[1]
        ):
            config.flesch_target = (float(val[0]), float(val[1]))
        else:
            config.warnings.append(
                f"'flesch-target' muss eine Liste [min, max] sein, "
                f"erhalten: {val!r}. Verwende Default."
            )

    if "filler-words-extra" in raw:
        val = raw["filler-words-extra"]
        if isinstance(val, list) and all(isinstance(v, str) for v in val):
            config.filler_words_extra = [w.lower() for w in val]
        else:
            config.warnings.append(
                f"'filler-words-extra' muss eine Liste von Strings sein, "
                f"erhalten: {val!r}. Ignoriert."
            )

    # --- Step 6: Override rules with configured variants ---
    if config.max_sentence_words != 40 and "max-sentence-length" in active_names:
        custom_rule = make_rule_max_sentence_length(config.max_sentence_words)
        idx = active_names.index("max-sentence-length")
        config.active_rules[idx] = custom_rule

    if config.filler_words_extra and "filler-words-de" in active_names:
        custom_rule = make_rule_filler_words_de(config.filler_words_extra)
        idx = active_names.index("filler-words-de")
        config.active_rules[idx] = custom_rule

    return config
