from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


STOPWORDS = {
    "a", "al", "como", "con", "de", "del", "el", "en", "hacer", "la", "las", "lo",
    "los", "para", "por", "que", "un", "una", "unos", "unas", "tutorial", "tutoriales",
    "how", "to", "the", "a", "an", "for", "of", "and",
}

# Strong result signals: these are specific enough to identify miniature/model-making
# content on their own. Generic words such as "paint", "model", "tree" or "wood"
# are deliberately NOT in this set because they caused unrelated results to pass.
STRONG_HOBBY_TERMS = {
    "miniatura", "miniaturas", "miniature", "miniatures", "modelismo", "maqueta", "maquetas",
    "diorama", "dioramas", "escenografia", "scenery", "peana", "peanas", "basing",
    "terrain", "wargame", "wargaming", "tabletop", "weathering", "envejecido",
    "pigmento", "pigmentos", "kitbash", "kitbashing", "scratchbuild", "scratchbuilding",
    "tuft", "matojo", "matojos", "calca", "calcas", "decal", "decals",
    "warhammer", "sigmar", "legion", "stormtrooper", "stormtroopers", "seraphon", "skaven",
    "nighthaunt", "stormcast", "citadel", "vallejo",
}

STRONG_HOBBY_PHRASES = (
    "army painter", "scale model", "scale models", "model kit", "model kits", "plastic model",
    "plastic models", "model railroad", "model railway", "miniature painting", "model painting",
    "figure painting", "scale figure", "scale figures", "resin kit", "garage kit",
    "tabletop terrain", "tabletop scenery", "terrain building", "diorama building",
    "model tree", "model trees", "model scenery",
)

TECHNIQUE_TERMS = {
    "pintar", "pintura", "paint", "painting", "aerografo", "aerografia", "airbrush",
    "primer", "imprimacion", "wash", "shade", "contrast", "barniz", "varnish",
    "modelar", "esculpir", "sculpt", "texturizar", "textura", "mezclar", "mezcla",
    "aplicar", "desconchones", "chipping", "oxido", "rust", "barro", "mud",
    "nieve", "snow", "agua", "water", "madera", "wood", "piedra", "stone",
    "arbol", "arboles", "tree", "trees", "ruinas", "ruins", "hierba", "grass",
    "musgo", "moss", "suelo", "ground", "arena", "sand", "roca", "rocas", "rock", "rocks",
    "cuero", "leather", "metal", "resina", "resin", "construir", "build", "building",
}

# Terms accepted to decide that a USER QUERY belongs to the hobby. This may be
# broader than result filtering because ambiguous requests are intentionally
# contextualized before they reach YouTube.
HOBBY_TERMS = STRONG_HOBBY_TERMS | TECHNIQUE_TERMS | {
    "scale", "model", "painter", "army",
}

CRAFT_ACTION_TERMS = TECHNIQUE_TERMS

BLOCKED_TOPIC_PATTERNS = (
    r"\breal madrid\b", r"\bfc barcelona\b", r"\bfutbol\b", r"\bfootball\b", r"\bgoles?\b",
    r"\breceta\b.*\b(cocina|comida|tortilla|postre)\b", r"\bpython\b", r"\bjavascript\b",
    r"\bprogramacion\b", r"\bprogramming\b", r"\bbitcoin\b", r"\bcriptomonedas?\b",
    r"\bbolsa\b", r"\bstocks?\b", r"\bnoticias?\b", r"\bnetflix\b", r"\bpeliculas?\b",
    r"\bseries?\b.*\b(tv|television)\b", r"\bmusica\b", r"\bguitarra\b",
)

RESULT_BLOCK_PATTERNS = (
    r"\b(gardening|garden|planting|orchard|bonsai|horticulture|jardineria|plantar|huerto)\b",
    r"\b(binary tree|data structure|python|javascript|programming|programacion)\b",
    r"\b(real madrid|fc barcelona|football|futbol|goles?)\b",
    r"\b(recipe|receta|cooking|cocina)\b",
    r"\b(makeup|maquillaje|nail art|unas acrilicas)\b",
    r"\b(furniture|mueble|carpentry|carpinteria)\b",
)

CONTEXT_SUFFIX = "miniatura modelismo pintura diorama escenografia miniature painting tutorial"

COMMON_TRANSLATIONS = {
    "arbol": "tree", "arboles": "trees", "barro": "mud", "nieve": "snow", "agua": "water",
    "oxido": "rust", "madera": "wood", "piedra": "stone", "roca": "rock", "rocas": "rocks",
    "cuero": "leather", "ruinas": "ruins", "hierba": "grass", "musgo": "moss",
}


@dataclass(frozen=True)
class QueryDecision:
    valid: bool
    original_query: str
    search_query: str
    reason: str = ""


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text or "")
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", re.sub(r"[^a-zA-Z0-9+\- ]+", " ", without_marks).lower()).strip()


def meaningful_tokens(text: str) -> list[str]:
    tokens = [token for token in normalize(text).split() if len(token) > 1 and token not in STOPWORDS]
    return list(dict.fromkeys(tokens))


def expanded_query_tokens(text: str) -> list[str]:
    tokens = meaningful_tokens(text)
    expanded = list(tokens)
    for token in tokens:
        translated = COMMON_TRANSLATIONS.get(token)
        if translated and translated not in expanded:
            expanded.append(translated)
    return expanded


def has_strong_hobby_signal(text: str) -> bool:
    normalized = normalize(text)
    tokens = set(normalized.split())
    return bool(tokens & STRONG_HOBBY_TERMS) or any(phrase in normalized for phrase in STRONG_HOBBY_PHRASES)


class TutorialQueryService:
    @classmethod
    def contextualize(cls, query: str) -> QueryDecision:
        original = " ".join((query or "").split()).strip()
        if len(original) < 2:
            return QueryDecision(False, original, "", "Escribe una búsqueda un poco más concreta.")

        normalized = normalize(original)
        tokens = set(normalized.split())
        has_hobby_signal = bool(tokens & HOBBY_TERMS) or any(phrase in normalized for phrase in STRONG_HOBBY_PHRASES)
        explicitly_blocked = any(re.search(pattern, normalized) for pattern in BLOCKED_TOPIC_PATTERNS)
        if explicitly_blocked and not has_hobby_signal:
            return QueryDecision(
                False,
                original,
                "",
                "Esta búsqueda está fuera del ámbito de modelismo y pintura de Ciros Paint.",
            )

        translations = " ".join(COMMON_TRANSLATIONS[token] for token in tokens if token in COMMON_TRANSLATIONS)
        if any(term in tokens for term in STRONG_HOBBY_TERMS):
            search_query = f"{original} {translations} miniature painting tutorial modelismo".strip()
        else:
            search_query = f"{original} {translations} {CONTEXT_SUFFIX}".strip()
        return QueryDecision(True, original, search_query)

    @classmethod
    def relevance_score(cls, original_query: str, title: str, description: str, youtube_position: int = 0) -> int:
        query_norm = normalize(original_query)
        title_norm = normalize(title)
        desc_norm = normalize(description)
        tokens = expanded_query_tokens(original_query)

        score = max(0, 20 - max(0, int(youtube_position)))
        if query_norm and query_norm in title_norm:
            score += 60
        if tokens and all(token in title_norm for token in tokens if token not in COMMON_TRANSLATIONS.values()):
            score += 40
        for token in tokens:
            if token in title_norm:
                score += 14
            elif token in desc_norm:
                score += 4
        if has_strong_hobby_signal(title_norm):
            score += 24
        title_tokens = set(title_norm.split())
        if title_tokens & TECHNIQUE_TERMS:
            score += 8
        if any(word in title_norm for word in ("tutorial", "guide", "how to", "paso a paso", "step by step")):
            score += 7
        return score

    @classmethod
    def result_is_hobby_related(cls, original_query: str, title: str, description: str) -> bool:
        combined = normalize(f"{title} {description}")
        tokens = set(combined.split())

        # Strong hobby evidence always wins over generic blocked words that may
        # appear incidentally in a legitimate modelling description.
        strong_signal = has_strong_hobby_signal(combined)
        if any(re.search(pattern, combined) for pattern in RESULT_BLOCK_PATTERNS) and not strong_signal:
            return False
        if strong_signal:
            return True

        # Generic craft words are not enough. Require the user's actual subject
        # (including common ES->EN translations) plus additional modelling context.
        query_tokens = expanded_query_tokens(original_query)
        matched_query = {token for token in query_tokens if token in tokens}
        technique_hits = tokens & TECHNIQUE_TERMS
        model_context_hits = tokens & {"model", "models", "scale", "figure", "figures", "kit", "kits"}

        if not matched_query:
            return False
        if model_context_hits and technique_hits:
            return True
        if len(technique_hits) >= 2 and len(matched_query) >= 2:
            return True
        return False
