from __future__ import annotations

import unicodedata

from app.core.settings_store import SettingsStore


class FavoriteCategoryService:
    MINIATURES = "Miniaturas"
    GENERAL = "Modelismo general"
    CATEGORIES = (MINIATURES, GENERAL)

    _STRONG_MINIATURE_TERMS = (
        "miniatura",
        "miniaturas",
        "miniature",
        "miniatures",
        "warhammer",
        "age of sigmar",
        "star wars legion",
        "star wars: legion",
        "stormtrooper",
        "space marine",
        "kill team",
        "warhammer 40k",
        "40k",
        "figurine",
        "figure painting",
        "painting figures",
        "painting miniatures",
        "paint miniatures",
        "28mm",
        "32mm",
    )
    _MINIATURE_TERMS = (
        "peana",
        "peanas",
        "basing",
        "army painting",
        "tabletop miniature",
        "wargame miniature",
    )
    _GENERAL_TERMS = (
        "modelismo",
        "diorama",
        "dioramas",
        "escenografia",
        "scenery",
        "terrain",
        "maqueta",
        "maquetas",
        "scale model",
        "model kit",
        "weathering",
        "aerografo",
        "airbrush",
        "pigment",
        "pigments",
        "arbol",
        "tree",
        "barro",
        "mud",
        "nieve",
        "snow",
        "agua",
        "water effect",
        "resina",
        "resin",
        "foam",
        "espuma",
        "corcho",
        "cork",
        "vegetacion",
        "vegetation",
        "cesped",
        "grass",
    )

    @staticmethod
    def _normalize(value: str) -> str:
        value = unicodedata.normalize("NFKD", value or "")
        value = "".join(char for char in value if not unicodedata.combining(char))
        return " ".join(value.lower().split())

    @classmethod
    def classify_text(cls, *parts: str) -> str:
        text = cls._normalize(" ".join(part or "" for part in parts))
        strong_miniatures = sum(1 for term in cls._STRONG_MINIATURE_TERMS if term in text)
        if strong_miniatures:
            return cls.MINIATURES

        miniature_score = sum(2 for term in cls._MINIATURE_TERMS if term in text)
        general_score = sum(1 for term in cls._GENERAL_TERMS if term in text)
        if miniature_score > general_score and miniature_score > 0:
            return cls.MINIATURES
        return cls.GENERAL

    @classmethod
    def classify_video(cls, video, source_query: str = "") -> str:
        return cls.classify_text(
            getattr(video, "title", ""),
            getattr(video, "description", ""),
            source_query,
        )

    @classmethod
    def category_for_favorite(cls, favorite) -> str:
        stored, manual = SettingsStore.favorite_category(favorite.video_id)
        if manual and stored in cls.CATEGORIES:
            return stored
        category = cls.classify_text(
            favorite.title,
            favorite.description,
            favorite.source_query,
        )
        if stored != category or manual:
            SettingsStore.set_favorite_category(favorite.video_id, category, manual=False)
        return category

    @classmethod
    def save_auto_category(cls, video, source_query: str = "") -> str:
        category = cls.classify_video(video, source_query)
        SettingsStore.set_favorite_category(video.video_id, category, manual=False)
        return category

    @classmethod
    def set_manual_category(cls, video_id: str, category: str) -> None:
        if category not in cls.CATEGORIES:
            raise ValueError(f"Unsupported favorite category: {category}")
        SettingsStore.set_favorite_category(video_id, category, manual=True)

    @classmethod
    def clear_category(cls, video_id: str) -> None:
        SettingsStore.remove_favorite_category(video_id)
