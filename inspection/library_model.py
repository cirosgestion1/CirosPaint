from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TutorialFavorite(Base):
    __tablename__ = "tutorial_favorites"
    __table_args__ = (UniqueConstraint("video_id", name="uq_tutorial_favorite_video"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    channel_title: Mapped[str] = mapped_column(String(250), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    thumbnail_url: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    video_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    duration_text: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    published_at: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    view_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    like_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    source_query: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
