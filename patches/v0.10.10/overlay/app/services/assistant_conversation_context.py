from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PaintConversationContext:
    """Small, in-memory paint context scoped to one assistant conversation."""

    active_paint_id: int | None = None
    candidate_paint_ids: list[int] = field(default_factory=list)
    candidate_paints: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ambiguous(self) -> bool:
        return len(self.candidate_paints) > 1

    def set_active(self, paint: dict[str, Any]) -> None:
        paint_id = paint.get("id")
        self.active_paint_id = int(paint_id) if paint_id is not None else None
        self.candidate_paint_ids = [self.active_paint_id] if self.active_paint_id is not None else []
        self.candidate_paints = [dict(paint)]

    def set_candidates(self, paints: list[dict[str, Any]]) -> None:
        self.active_paint_id = None
        self.candidate_paints = [dict(paint) for paint in paints]
        self.candidate_paint_ids = [int(paint["id"]) for paint in paints if paint.get("id") is not None]

    def clear(self) -> None:
        self.active_paint_id = None
        self.candidate_paint_ids.clear()
        self.candidate_paints.clear()
