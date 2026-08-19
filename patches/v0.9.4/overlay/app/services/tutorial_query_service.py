from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


STOPWORDS = {
    "a", "al", "como", "con", "de", "del", "el", "en", "hacer", "la", "las", "lo",
    "los", "para", "por", "que", "un", "una", "unos", "unas", "tutorial", "tutoriales",
    "how", "to", "the", "an", "for", "of", "and",
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

SPANISH_CONTEXT_SUFFIX = "miniaturas modelismo pintura diorama escenografia tutorial"
ENGLISH_CONTEXT_SUFFIX = "miniature painting model making diorama scenery tutorial"
CONTEXT_SUFFIX = f"{SPANISH_CONTEXT_SUFFIX} {ENGLISH_CONTEXT_SUFFIX}"

# Local hobby vocabulary used only to make the same user query useful in both
# Spanish and English. It is deliberately small and deterministic: this search
# path does not spend AI tokens.
SPANISH_TO_ENGLISH = {
    "arbol": "tree", "arboles": "trees", "barro": "mud", "nieve": "snow", "agua": "water",
    "oxido": "rust", "madera": "wood", "piedra": "stone", "roca": "rock", "rocas": "rocks",
    "cuero": "leather", "ruina": "ruin", "ruinas": "ruins", "hierba": "grass", "musgo": "moss",
    "pintar": "paint", "pintura": "painting", "miniatura": "miniature", "miniaturas": "miniatures",
    "modelismo": "modelmaking", "maqueta": "scale-model", "maquetas": "scale-models",
    "escenografia": "scenery", "terreno": "terrain", "peana": "base", "peanas": "bases",
    "aerografo": "airbrush", "aerografia": "airbrushing", "pigmento": "pigment", "pigmentos": "pigments",
    "barniz": "varnish", "imprimacion": "primer", "resina": "resin", "construir": "build",
    "modelar": "model", "esculpir": "sculpt", "texturizar": "texture", "textura": "texture",
    "mezclar": "mix", "mezcla": "mix", "aplicar": "apply", "aerografiar": "airbrush",
    "desconchones": "chipping", "suelo": "ground", "arena": "sand", "metal": "metal",
    "piel": "skin", "tanque": "tank", "herramienta": "tool", "herramientas": "tools",
    "envejecido": "weathering", "suciedad": "dirt", "lavado": "wash", "lavados": "washes",
}

ENGLISH_TO_SPANISH = {
    "tree": "arbol", "trees": "arboles", "mud": "barro", "snow": "nieve", "water": "agua",
    "rust": "oxido", "wood": "madera", "stone": "piedra", "rock": "roca", "rocks": "rocas",
    "leather": "cuero", "ruin": "ruina", "ruins": "ruinas", "grass": "hierba", "moss": "musgo",
    "paint": "pintar", "painting": "pintura", "miniature": "miniatura", "miniatures": "miniaturas",
    "modelmaking": "modelismo", "scenery": "escenografia", "terrain": "terreno", "base": "peana",
    "bases": "peanas", "airbrush": "aerografo", "airbrushing": "aerografia", "pigment": "pigmento",
    "pigments": "pigmentos", "varnish": "barniz", "primer": "imprimacion", "resin": "resina",
    "build": "construir", "sculpt": "esculpir", "texture": "textura", "mix": "mezclar",
    "apply": "aplicar", "chipping": "desconchones", "ground": "suelo", "sand": "arena",
    "skin": "piel", "tank": "tanque", "tool": "herramienta", "tools": "herramientas",
    "weathering": "envejecido", "dirt": "suciedad", "washes": "lavados",
}

COMMON_TRANSLATIONS = SPANISH_TO_ENGLISH
SPANISH_FUNCTION_WORDS = {"a", "al", "como", "con", "de", "del", "el", "en", "hacer", "la", "las", "lo", "los", "para", "por", "que", "un", "una", "unos", "unas"}
ENGLISH_FUNCTION_WORDS = {"a", "an", "and", "for", "how", "of", "the", "to", "with"}


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


def query_token_groups(text: str) -> list[tuple[str, ...]]:
    groups: list[tuple[str, ...]] = []
    for token in meaningful_tokens(text):
        variants = [token]
        translated = SPANISH_TO_ENGLISH.get(token) or ENGLISH_TO_SPANISH.get(token)
        if translated and translated not in variants:
            variants.append(translated)
        groups.append(tuple(variants))
    return groups


def _localized_terms(query: str, language_code: str) -> list[str]:
    tokens = normalize(query).split()
    output: list[str] = []
    if language_code == "en":
        for token in tokens:
            if token in SPANISH_TO_ENGLISH:
                value = SPANISH_TO_ENGLISH[token]
            elif token in SPANISH_FUNCTION_WORDS:
                continue
            else:
                value = token
            if value and value not in output:
                output.append(value)
    else:
        for token in tokens:
            if token in ENGLISH_TO_SPANISH:
                value = ENGLISH_TO_SPANISH[token]
            elif token in ENGLISH_FUNCTION_WORDS:
                continue
            else:
                value = token
            if value and value not in output:
                output.append(value)
    return output


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

        # Compatibility/default query: bilingual. The 0.9.4 YouTube service uses
        # localized_search_query() for the selected language before calling API.
        translations = " ".join(SPANISH_TO_ENGLISH[token] for token in tokens if token in SPANISH_TO_ENGLISH)
        search_query = f"{original} {translations} {CONTEXT_SUFFIX}".strip()
        return QueryDecision(True, original, re.sub(r"\s+", " ", search_query))

    @classmethod
    def localized_search_query(cls, query: str, language_code: str) -> str:
        language_code = (language_code or "").strip().lower()
        if language_code == "en":
            terms = _localized_terms(query, "en")
            return " ".join(terms + ENGLISH_CONTEXT_SUFFIX.split())
        terms = _localized_terms(query, "es")
        return " ".join(terms + SPANISH_CONTEXT_SUFFIX.split())

    @classmethod
    def language_search_plan(cls, query: str, language_code: str) -> list[tuple[str, str]]:
        language_code = (language_code or "").strip().lower()
        if language_code == "es":
            return [(cls.localized_search_query(query, "es"), "es")]
        if language_code == "en":
            return [(cls.localized_search_query(query, "en"), "en")]
        # "Todos" deliberately performs one Spanish and one English discovery
        # request. A single bilingual query remained strongly biased toward the
        # language in which the user typed the text.
        return [
            (cls.localized_search_query(query, "es"), "es"),
            (cls.localized_search_query(query, "en"), "en"),
        ]

    @classmethod
    def relevance_score(cls, original_query: str, title: str, description: str, youtube_position: int = 0) -> int:
        query_norm = normalize(original_query)
        title_norm = normalize(title)
        desc_norm = normalize(description)
        groups = query_token_groups(original_query)

        score = max(0, 20 - max(0, int(youtube_position)))
        if query_norm and query_norm in title_norm:
            score += 60
        if groups and all(any(variant in title_norm for variant in group) for group in groups):
            score += 40
        for group in groups:
            if any(variant in title_norm for variant in group):
                score += 14
            elif any(variant in desc_norm for variant in group):
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
        groups = query_token_groups(original_query)
        has_explicit_hobby_signal = bool(tokens & HOBBY_TERMS)
        if any(re.search(pattern, combined) for pattern in RESULT_BLOCK_PATTERNS) and not has_explicit_hobby_signal:
            return False
        if tokens & (HOBBY_TERMS | CRAFT_ACTION_TERMS):
            return True
        matched_groups = sum(1 for group in groups if any(variant in combined for variant in group))
        return bool(groups and matched_groups >= max(1, len(groups) // 2))
