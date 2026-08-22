from __future__ import annotations


# Catalog vocabulary belongs here instead of in description parsers.  Each
# qualifier narrows a human abbreviation to catalog metadata; it never creates
# a paint that is absent from the catalog.
RANGE_QUALIFIER_ALIASES: dict[str, tuple[str, str]] = {
    "vmc": ("vallejo", "model color"),
}

# Common commercial shortening used inside paint names.
PAINT_NAME_TOKEN_ALIASES: dict[str, str] = {
    "fluo": "fluorescent",
}

# These phrases describe hobby materials rather than bottled paints.  They are
# deliberately product categories, not exclusions for any particular brand or
# regression sample.
NON_PAINT_MATERIAL_PHRASES: tuple[str, ...] = (
    "basing paste",
    "matte varnish",
    "matt varnish",
    "fine turf",
    "battleground",
)

# When a manufacturer publishes the same named colour in several delivery
# formats, an unqualified author reference means the regular brush paint.  Air
# and spray products remain resolvable when their range is written explicitly.
SPECIAL_DELIVERY_RANGE_TOKENS: frozenset[str] = frozenset({"air", "spray"})
