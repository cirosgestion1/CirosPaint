from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.library import TutorialFavorite


class LibraryRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_favorites(self) -> list[TutorialFavorite]:
        stmt = select(TutorialFavorite).order_by(TutorialFavorite.added_at.desc(), TutorialFavorite.id.desc())
        return list(self.session.scalars(stmt).all())

    def is_favorite(self, video_id: str) -> bool:
        stmt = select(TutorialFavorite.id).where(TutorialFavorite.video_id == video_id)
        return self.session.scalar(stmt) is not None

    def get_by_video_id(self, video_id: str) -> TutorialFavorite | None:
        stmt = select(TutorialFavorite).where(TutorialFavorite.video_id == video_id)
        return self.session.scalar(stmt)

    def add_favorite(self, video, source_query: str = "") -> TutorialFavorite:
        existing = self.get_by_video_id(video.video_id)
        if existing:
            return existing
        item = TutorialFavorite(
            video_id=video.video_id,
            title=video.title,
            channel_title=video.channel_title,
            description=video.description,
            thumbnail_url=video.thumbnail_url,
            video_url=video.video_url,
            duration_text=video.duration_text,
            published_at=video.published_at,
            view_count=max(0, int(video.view_count or 0)),
            like_count=max(0, int(video.like_count or 0)),
            source_query=source_query.strip(),
        )
        self.session.add(item)
        self.session.commit()
        return item

    def remove_favorite(self, video_id: str) -> bool:
        item = self.get_by_video_id(video_id)
        if not item:
            return False
        self.session.delete(item)
        self.session.commit()
        return True
