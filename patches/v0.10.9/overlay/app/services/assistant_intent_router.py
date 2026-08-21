from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class LocalIntent(str, Enum):
    SEARCH_PAINT = "search_paint"
    GET_PAINT_STOCK = "get_paint_stock"
    LIST_DEPLETED_PAINTS = "list_depleted_paints"
    LIST_PAINTS_BY_COLOR = "list_paints_by_color"
    LIST_FUTURE_PURCHASES = "list_future_purchases"
    ADD_FUTURE_PURCHASE = "add_future_purchase"
    COMPLETE_PURCHASE = "complete_purchase"
    GET_MINIATURE_COUNTS = "get_miniature_counts"
    ADD_MINIATURE = "add_miniature"
    CHANGE_MINIATURE_STATUS = "change_miniature_status"


@dataclass(frozen=True)
class IntentMatch:
    intent: LocalIntent
    parameters: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


class LocalIntentHandler(Protocol):
    def search_paints(self, query: str): ...
    def find_paint(self, query: str): ...
    def paints_by_color(self, color: str): ...
    def depleted_paints(self): ...
    def list_future_paints(self): ...
    def add_future_paint(self, query: str, quantity: int = 1): ...
    def mark_paint_purchased(self, query: str, quantity: int = 1): ...
    def miniature_counts(self, query: str): ...
    def change_miniature_status(self, query: str, target_status: str, quantity: int): ...
    def guided_add_miniature(self): ...


class AssistantLocalIntentRouter:
    """Deterministic router for assistant operations already supported locally."""

    def __init__(self, handler: LocalIntentHandler):
        self.handler = handler

    def route(self, text: str):
        match = self.classify(text)
        if match is None:
            return None
        args = match.parameters
        handlers = {
            LocalIntent.SEARCH_PAINT: lambda: self.handler.search_paints(args["query"]),
            LocalIntent.GET_PAINT_STOCK: lambda: self.handler.find_paint(args["query"]),
            LocalIntent.LIST_DEPLETED_PAINTS: self.handler.depleted_paints,
            LocalIntent.LIST_PAINTS_BY_COLOR: lambda: self.handler.paints_by_color(args["color"]),
            LocalIntent.LIST_FUTURE_PURCHASES: self.handler.list_future_paints,
            LocalIntent.ADD_FUTURE_PURCHASE: lambda: self.handler.add_future_paint(args["query"], args["quantity"]),
            LocalIntent.COMPLETE_PURCHASE: lambda: self.handler.mark_paint_purchased(args["query"], args["quantity"]),
            LocalIntent.GET_MINIATURE_COUNTS: lambda: self.handler.miniature_counts(args["query"]),
            LocalIntent.ADD_MINIATURE: self.handler.guided_add_miniature,
            LocalIntent.CHANGE_MINIATURE_STATUS: lambda: self.handler.change_miniature_status(
                args["query"], args["target_status"], args["quantity"]
            ),
        }
        return handlers[match.intent]()

    def classify(self, text: str) -> IntentMatch | None:
        clean = " ".join(str(text or "").strip().split())
        normalized = _normalize(clean)
        if not clean:
            return None

        explicit_search = re.match(r"^(?:buscar|busca)\s+(?:pinturas?|paint)\s*:\s*(.+)$", clean, re.IGNORECASE)
        if explicit_search:
            return IntentMatch(LocalIntent.SEARCH_PAINT, {"query": _entity(explicit_search.group(1))})

        if "agotad" in normalized and "pintur" in normalized:
            return IntentMatch(LocalIntent.LIST_DEPLETED_PAINTS)

        if "futuras compras" in normalized or "compras futuras" in normalized:
            add_future = re.search(
                r"(?:anade|agrega|pon)\s+(?:(\d+)\s+)?(.+?)\s+(?:a|en)\s+(?:mis\s+)?(?:futuras compras|compras futuras)",
                normalized,
            )
            if add_future:
                return IntentMatch(
                    LocalIntent.ADD_FUTURE_PURCHASE,
                    {"query": _entity(add_future.group(2)), "quantity": int(add_future.group(1) or 1)},
                )
            return IntentMatch(LocalIntent.LIST_FUTURE_PURCHASES)

        purchased = re.search(
            r"^(?:he\s+)?comprad[oa]\s+(?:(\d+)\s+)?(?:unidades?\s+de\s+)?(.+)$",
            normalized,
        )
        if purchased:
            return IntentMatch(
                LocalIntent.COMPLETE_PURCHASE,
                {"query": _entity(purchased.group(2)), "quantity": int(purchased.group(1) or 1)},
            )

        color_match = re.search(r"(?:pinturas?|colores?).*?(?:color\s+)?([a-z]+)$", normalized)
        if color_match and any(token in normalized for token in ("que pinturas", "pinturas tengo")):
            return IntentMatch(LocalIntent.LIST_PAINTS_BY_COLOR, {"color": color_match.group(1)})

        if re.search(r"\b(?:anade|agrega)\b.*\bminiaturas?\b", normalized):
            return IntentMatch(LocalIntent.ADD_MINIATURE)

        state_patterns = (
            (r"^(?:he\s+)?(?:terminado|termine)\s+(\d+)\s+(.+)$", "Terminado"),
            (r"^(?:he\s+)?(?:pintado|pinte)\s+(\d+)\s+(.+)$", "Pintado"),
            (r"^(?:he\s+)?(?:montado|monte)\s+(\d+)\s+(.+)$", "Montado"),
        )
        for pattern, status in state_patterns:
            state = re.search(pattern, normalized)
            if state:
                return IntentMatch(
                    LocalIntent.CHANGE_MINIATURE_STATUS,
                    {"query": _entity(state.group(2)), "target_status": status, "quantity": int(state.group(1))},
                )

        stock = re.search(r"(?:cuantas?\s+unidades?\s+tengo\s+de|cuanto.*?tengo\s+de)\s+(.+)$", normalized)
        if stock:
            return IntentMatch(LocalIntent.GET_PAINT_STOCK, {"query": _entity(stock.group(1))})

        mini_patterns = (
            r"(?:cuantas?|cantidad).*?(?:miniaturas?|unidades?).*?(?:de\s+)?(.+)$",
            r"(?:cuantos?|cuantas?)\s+(.+?)\s+tengo(?:\s+en\s+total)?[?.!]*$",
        )
        for pattern in mini_patterns:
            miniature = re.search(pattern, normalized)
            if miniature:
                return IntentMatch(LocalIntent.GET_MINIATURE_COUNTS, {"query": _entity(miniature.group(1))})

        paint_have = re.search(r"(?:tengo|tienes|hay).*?(?:la\s+pintura\s+)?(.+)$", normalized)
        if paint_have and any(word in normalized for word in ("pintura", "tengo", "tienes")):
            query = re.sub(r"^de\s+", "", _entity(paint_have.group(1)), flags=re.IGNORECASE)
            return IntentMatch(LocalIntent.GET_PAINT_STOCK, {"query": query})

        return None


def _entity(value: str) -> str:
    return str(value or "").strip(" ?.!:;,\t\r\n")


def _normalize(value: str) -> str:
    raw = unicodedata.normalize("NFKD", str(value or ""))
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch)).casefold()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", raw).split())
