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

    @property
    def published_year(self) -> str:
        return self.published_at[:4] if self.published_at else ""


def _request_json(url: str, timeout: int = 15) -> dict:
    request = Request(url, headers={"User-Agent": "CirosPaint/0.9.0"})
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


class YouTubeService:
    def __init__(self, api_key: str):
        self.api_key = (api_key or "").strip()

    def search_tutorials(self, original_query: str, search_query: str, candidate_count: int = 35, limit: int = 20) -> list[TutorialVideo]:
        if not self.api_key:
            raise YouTubeApiError("Configura primero una clave de YouTube Data API en Ajustes.")

        search_params = {
            "part": "snippet",
            "type": "video",
            "maxResults": max(5, min(50, int(candidate_count))),
            "q": search_query,
            "order": "relevance",
            "safeSearch": "moderate",
            "relevanceLanguage": "es",
            "videoEmbeddable": "true",
            "key": self.api_key,
        }
        search_payload = _request_json(f"{SEARCH_ENDPOINT}?{urlencode(search_params)}")
        search_items = search_payload.get("items") or []
        ids: list[str] = []
        positions: dict[str, int] = {}
        for position, item in enumerate(search_items):
            video_id = (item.get("id") or {}).get("videoId")
            if video_id and video_id not in positions:
                ids.append(video_id)
                positions[video_id] = position
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
                )
            )

        # Product rule: relevance is absolute priority. For similarly relevant candidates,
        # more views wins, then likes, then recency.
        results.sort(key=tutorial_sort_key, reverse=True)
        return results[: max(1, int(limit))]
