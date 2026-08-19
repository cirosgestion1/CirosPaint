from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import html
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.services.tutorial_query_service import TutorialQueryService

SEARCH_ENDPOINT = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_ENDPOINT = "https://www.googleapis.com/youtube/v3/videos"
SUPPORTED_LANGUAGE_FILTERS = {"es", "en"}

SPANISH_LANGUAGE_MARKERS = {
    "como", "para", "con", "una", "uno", "del", "los", "las", "que", "pintar", "pintura",
    "miniatura", "miniaturas", "hacer", "guia", "paso", "facil", "espanol", "modelismo",
    "peana", "peanas", "barro", "oxido", "aerografo", "imprimacion", "barniz", "terreno",
}
ENGLISH_LANGUAGE_MARKERS = {
    "how", "to", "for", "with", "the", "and", "paint", "painting", "miniature", "miniatures",
    "make", "guide", "step", "easy", "english", "model", "models", "basing", "weathering",
    "airbrush", "primer", "varnish", "terrain", "scenery", "diorama",
}


class YouTubeApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class TutorialVideo:
    video_id: str
    title: str
    channel_title: str
    description: str
    thumbnail_url: str
    video_url: str
    duration_text: str
    published_at: str
    view_count: int
    like_count: int
    embeddable: bool = True
    relevance_score: int = 0
    youtube_position: int = 0
    language_code: str = ""

    @property
    def published_year(self) -> str:
        return self.published_at[:4] if self.published_at else ""

    @property
    def language_tag(self) -> str:
        return {"es": "ES", "en": "EN"}.get(self.language_code, "?")

    @property
    def language_name(self) -> str:
        return {"es": "Español", "en": "Inglés"}.get(self.language_code, "Idioma no identificado")


def _request_json(url: str, timeout: int = 15) -> dict:
    request = Request(url, headers={"User-Agent": "CirosPaint/0.9.4"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = ""
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            detail = payload.get("error", {}).get("message", "")
        except Exception:
            pass
        if exc.code in (400, 401, 403):
            raise YouTubeApiError(detail or "La clave de YouTube no es válida o la cuota de la API no está disponible.") from exc
        raise YouTubeApiError(detail or f"YouTube devolvió un error HTTP {exc.code}.") from exc
    except (URLError, TimeoutError) as exc:
        raise YouTubeApiError("No se ha podido conectar con YouTube. Comprueba tu conexión a Internet.") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise YouTubeApiError("No se ha podido interpretar la respuesta de YouTube.") from exc


def _parse_duration(value: str) -> str:
    match = re.fullmatch(r"P(?:\d+D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    if not match:
        return ""
    hours, minutes, seconds = (int(part or 0) for part in match.groups())
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def _published_sort_value(value: str) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def tutorial_sort_key(video: TutorialVideo) -> tuple[int, int, int, float]:
    return (
        int(video.relevance_score),
        max(0, int(video.view_count or 0)),
        max(0, int(video.like_count or 0)),
        _published_sort_value(video.published_at),
    )


def _base_language(value: str) -> str:
    value = (value or "").strip().lower().replace("_", "-")
    return value.split("-", 1)[0] if value else ""


def detect_video_language(title: str, description: str, default_audio_language: str = "", default_language: str = "") -> str:
    """Detect Spanish/English, preferring YouTube's own video metadata.

    defaultAudioLanguage describes the default audio track when the uploader
    supplied it. defaultLanguage describes title/description metadata. Text is
    only a fallback because many older videos omit both fields.
    """
    for value in (default_audio_language, default_language):
        base = _base_language(value)
        if base in SUPPORTED_LANGUAGE_FILTERS:
            return base

    text = f"{title or ''} {description or ''}".lower()
    words = re.findall(r"[a-záéíóúüñ]+", text)
    if not words:
        return ""
    spanish = sum(1 for word in words if word in SPANISH_LANGUAGE_MARKERS)
    english = sum(1 for word in words if word in ENGLISH_LANGUAGE_MARKERS)
    if spanish >= 2 and spanish > english:
        return "es"
    if english >= 2 and english > spanish:
        return "en"
    return ""


def build_language_search_plan(original_query: str, language_code: str) -> list[tuple[str, str]]:
    """Return API discovery queries as (query, relevanceLanguage).

    "Todos" uses two discovery requests, one per supported language. This is
    intentional: YouTube's relevanceLanguage is a preference rather than a
    strict language filter, and one bilingual query stayed biased toward the
    language used by the user.
    """
    return TutorialQueryService.language_search_plan(original_query, _base_language(language_code))


class YouTubeService:
    def __init__(self, api_key: str):
        self.api_key = (api_key or "").strip()

    def _search_ids(self, query: str, relevance_language: str, max_results: int) -> list[str]:
        search_params = {
            "part": "snippet",
            "type": "video",
            "maxResults": max(5, min(50, int(max_results))),
            "q": query,
            "order": "relevance",
            "safeSearch": "moderate",
            "videoEmbeddable": "true",
            "relevanceLanguage": relevance_language,
            "key": self.api_key,
        }
        payload = _request_json(f"{SEARCH_ENDPOINT}?{urlencode(search_params)}")
        ids: list[str] = []
        for item in payload.get("items") or []:
            video_id = (item.get("id") or {}).get("videoId")
            if video_id and video_id not in ids:
                ids.append(video_id)
        return ids

    def search_tutorials(
        self,
        original_query: str,
        search_query: str,
        candidate_count: int = 35,
        limit: int = 20,
        language_code: str = "",
    ) -> list[TutorialVideo]:
        if not self.api_key:
            raise YouTubeApiError("Configura primero una clave de YouTube Data API en Ajustes.")

        selected_language = _base_language(language_code)
        if selected_language not in SUPPORTED_LANGUAGE_FILTERS:
            selected_language = ""

        plan = build_language_search_plan(original_query or search_query, selected_language)
        per_search = max(10, min(25, int(candidate_count))) if len(plan) > 1 else max(5, min(50, int(candidate_count)))

        ids: list[str] = []
        positions: dict[str, int] = {}
        for query, relevance_language in plan:
            discovered = self._search_ids(query, relevance_language, per_search)
            for position, video_id in enumerate(discovered):
                if video_id not in positions:
                    ids.append(video_id)
                    positions[video_id] = position
                else:
                    positions[video_id] = min(positions[video_id], position)

        # videos.list accepts at most 50 IDs in one request.
        ids = ids[:50]
        if not ids:
            return []

        video_params = {
            "part": "snippet,statistics,contentDetails,status",
            "id": ",".join(ids),
            "maxResults": 50,
            "key": self.api_key,
        }
        details = _request_json(f"{VIDEOS_ENDPOINT}?{urlencode(video_params)}")
        results: list[TutorialVideo] = []
        for item in details.get("items") or []:
            video_id = item.get("id", "")
            snippet = item.get("snippet") or {}
            stats = item.get("statistics") or {}
            status = item.get("status") or {}
            content = item.get("contentDetails") or {}
            if not video_id or status.get("embeddable") is False:
                continue

            title = html.unescape(str(snippet.get("title", "")))
            description = html.unescape(str(snippet.get("description", "")))
            if not TutorialQueryService.result_is_hobby_related(original_query, title, description):
                continue

            detected_language = detect_video_language(
                title,
                description,
                str(snippet.get("defaultAudioLanguage", "")),
                str(snippet.get("defaultLanguage", "")),
            )

            # Español/Inglés are strict after discovery. relevanceLanguage alone
            # cannot provide that guarantee because YouTube documents it as a
            # relevance preference, not a hard language constraint.
            if selected_language and detected_language != selected_language:
                continue

            thumbs = snippet.get("thumbnails") or {}
            thumbnail = ""
            for key in ("maxres", "standard", "high", "medium", "default"):
                if isinstance(thumbs.get(key), dict) and thumbs[key].get("url"):
                    thumbnail = thumbs[key]["url"]
                    break

            position = positions.get(video_id, 99)
            relevance = TutorialQueryService.relevance_score(original_query, title, description, position)
            results.append(
                TutorialVideo(
                    video_id=video_id,
                    title=title,
                    channel_title=html.unescape(str(snippet.get("channelTitle", ""))),
                    description=description,
                    thumbnail_url=thumbnail,
                    video_url=f"https://www.youtube.com/watch?v={video_id}",
                    duration_text=_parse_duration(str(content.get("duration", ""))),
                    published_at=str(snippet.get("publishedAt", "")),
                    view_count=int(stats.get("viewCount") or 0),
                    like_count=int(stats.get("likeCount") or 0),
                    embeddable=True,
                    relevance_score=relevance,
                    youtube_position=position,
                    language_code=detected_language,
                )
            )

        results.sort(key=tutorial_sort_key, reverse=True)
        return results[: max(1, int(limit))]
