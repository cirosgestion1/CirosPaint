from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


STOPWORDS = {
    "a", "al", "como", "con", "de", "del", "el", "en", "hacer", "la", "las", "lo",
    "los", "para", "por", "que", "un", "una", "unos", "unas", "tutorial", "tutoriales",
    "how", "to", "the", "a", "an", "for", "of", "and",
}

HOBBY_TERMS = {
    "miniatura", "miniaturas", "modelismo", "maqueta", "maquetas", "diorama", "dioramas",
    "escenografia", "peana", "peanas", "terreno", "terrain", "wargame", "wargaming",
    "aerografo", "aerografia", "airbrush", "weathering", "envejecido", "pigmento", "pigmentos",
    "barniz", "imprimacion", "primer", "wash", "shade", "contrast", "resina", "resin",
    "kitbash", "kitbashing", "scratchbuild", "scratchbuilding", "tuft", "matojo", "matojos",
    "calca", "calcas", "decal", "decals", "miniature", "miniatures", "scale", "model",
    "warhammer", "sigmar", "legion", "stormtrooper", "stormtroopers", "seraphon", "skaven",
    "nighthaunt", "stormcast", "citadel", "vallejo", "ak", "army", "painter",
}

CRAFT_ACTION_TERMS = {
    "pintar", "pintura", "paint", "painting", "construir", "build", "building", "modelar",
    "esculpir", "sculpt", "texturizar", "textura", "mezclar", "mezcla", "aplicar", "aerografiar",
    "desconchones", "oxido", "barro", "nieve", "agua", "madera", "piedra", "arbol", "arboles",
    "ruinas", "ruina", "hierba", "musgo", "suelo", "arena", "roca", "rocas", "cuero", "metal",
}

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


class TutorialQueryService:
    @classmethod
    def contextualize(cls, query: str) -> QueryDecision:
        original = " ".join((query or "").split()).strip()
        if len(original) < 2:
            return QueryDecision(False, original, "", "Escribe una búsqueda un poco más concreta.")

        normalized = normalize(original)
        tokens = set(normalized.split())
        has_hobby_signal = bool(tokens & (HOBBY_TERMS | CRAFT_ACTION_TERMS))
        explicitly_blocked = any(re.search(pattern, normalized) for pattern in BLOCKED_TOPIC_PATTERNS)
        if explicitly_blocked and not has_hobby_signal:
            return QueryDecision(
                False,
                original,
                "",
                "Esta búsqueda está fuera del ámbito de modelismo y pintura de Ciros Paint.",
            )

        # Keep the user's wording, but bias YouTube toward the hobby. This is intentionally
        # local/deterministic: 0.9.0 does not spend AI tokens to understand a search.
        translations = " ".join(COMMON_TRANSLATIONS[token] for token in tokens if token in COMMON_TRANSLATIONS)
        if any(term in tokens for term in HOBBY_TERMS):
            search_query = f"{original} {translations} miniature painting tutorial modelismo".strip()
        else:
            search_query = f"{original} {translations} {CONTEXT_SUFFIX}".strip()
        return QueryDecision(True, original, search_query)

    @classmethod
    def relevance_score(cls, original_query: str, title: str, description: str, youtube_position: int = 0) -> int:
        query_norm = normalize(original_query)
        title_norm = normalize(title)
        desc_norm = normalize(description)
        tokens = meaningful_tokens(original_query)

        score = max(0, 20 - max(0, int(youtube_position)))
        if query_norm and query_norm in title_norm:
            score += 60
        if tokens and all(token in title_norm for token in tokens):
            score += 40
        for token in tokens:
            if token in title_norm:
                score += 14
            elif token in desc_norm:
                score += 4
        title_tokens = set(title_norm.split())
        if title_tokens & HOBBY_TERMS:
            score += 14
        if title_tokens & CRAFT_ACTION_TERMS:
            score += 8
        if any(word in title_norm for word in ("tutorial", "guide", "how to", "paso a paso", "step by step")):
            score += 7
        return score

    @classmethod
    def result_is_hobby_related(cls, original_query: str, title: str, description: str) -> bool:
        combined = normalize(f"{title} {description}")
        tokens = set(combined.split())
        query_tokens = meaningful_tokens(original_query)
        has_explicit_hobby_signal = bool(tokens & HOBBY_TERMS)
        if any(re.search(pattern, combined) for pattern in RESULT_BLOCK_PATTERNS) and not has_explicit_hobby_signal:
            return False
        if tokens & (HOBBY_TERMS | CRAFT_ACTION_TERMS):
            return True
        # A result can still be useful when its title closely matches the user's specific subject.
        return bool(query_tokens and sum(1 for token in query_tokens if token in combined) >= max(1, len(query_tokens) // 2))
