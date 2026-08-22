from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable


# Domain aliases that cannot be derived safely from the canonical catalog name.
FACTION_ALIASES: dict[str, tuple[str, ...]] = {
    "Imperio Galáctico": ("imperio", "imperial", "imperiales"),
    "Alianza Rebelde": ("rebeldes", "rebelde"),
    "República Galáctica": ("republica", "republicanos", "republicanas"),
    "Alianza Separatista": ("separatistas", "separatista"),
}


@dataclass(frozen=True)
class FactionMatch:
    faction_id: str
    faction_name: str


class MiniatureFactionResolver:
    """Strict, centralized faction aliases; deliberately no weak fuzzy matching."""

    def resolve(self, query: str, factions: Iterable[tuple[str, str]]) -> FactionMatch | None:
        needle = normalize_faction(query)
        matches = []
        for faction_id, faction_name in factions:
            if needle in faction_forms(faction_name):
                matches.append(FactionMatch(faction_id, faction_name))
        return matches[0] if len(matches) == 1 else None


def faction_forms(canonical_name: str) -> set[str]:
    canonical = normalize_faction(canonical_name)
    forms = {canonical}
    tokens = canonical.split()
    if len(tokens) > 1 and tokens[-1] in {"galactico", "galactica"}:
        forms.add(" ".join(tokens[:-1]))
    for value in (canonical_name, *FACTION_ALIASES.get(canonical_name, ())):
        normalized = normalize_faction(value)
        forms.add(normalized)
        if normalized.endswith("es") and len(normalized) > 4:
            forms.add(normalized[:-2])
        if normalized.endswith("s") and len(normalized) > 3:
            forms.add(normalized[:-1])
    return {value for value in forms if value}


def normalize_faction(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char)).casefold()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())
