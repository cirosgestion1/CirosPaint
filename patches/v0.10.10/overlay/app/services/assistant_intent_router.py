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
    COUNT_OWNED_PAINTS = "count_owned_paints"
    LIST_FUTURE_PURCHASES = "list_future_purchases"
    ADD_FUTURE_PURCHASE = "add_future_purchase"
    COMPLETE_PURCHASE = "complete_purchase"
    GET_MINIATURE_COUNTS = "get_miniature_counts"
    COUNT_OWNED_MINIATURES = "count_owned_miniatures"
    QUERY_OWNED_ENTITY = "query_owned_entity"
    ADD_MINIATURE = "add_miniature"
    CHANGE_MINIATURE_STATUS = "change_miniature_status"
    SHOW_PAINT_CONTEXT = "show_paint_context"
    ADD_ACTIVE_PAINT_UNIT = "add_active_paint_unit"
    REMOVE_ACTIVE_PAINT_UNIT = "remove_active_paint_unit"
    SET_ACTIVE_PAINT_QUANTITY = "set_active_paint_quantity"
    ADD_ACTIVE_PAINT_FUTURE = "add_active_paint_future"


@dataclass(frozen=True)
class IntentMatch:
    intent: LocalIntent
    parameters: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


class LocalIntentHandler(Protocol):
    def search_paints(self, query: str): ...
    def find_paint(self, query: str): ...
    def query_owned_paints(self, query: str): ...
    def paints_by_color(self, color: str): ...
    def count_owned_paints(self, query: str = ""): ...
    def depleted_paints(self): ...
    def list_future_paints(self): ...
    def add_future_paint(self, query: str, quantity: int = 1): ...
    def mark_paint_purchased(self, query: str, quantity: int = 1): ...
    def miniature_counts(self, query: str): ...
    def count_owned_miniatures(self): ...
    def query_owned_entity(self, query: str): ...
    def change_miniature_status(self, query: str, target_status: str, quantity: int): ...
    def guided_add_miniature(self): ...
    def show_paint_context(self): ...
    def change_active_paint_quantity(self, mode: str, quantity: int = 1): ...
    def add_active_paint_to_future(self): ...


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
            LocalIntent.SEARCH_PAINT: lambda: getattr(
                self.handler, "search_paint_term", self.handler.search_paints
            )(args["query"]),
            LocalIntent.GET_PAINT_STOCK: lambda: getattr(
                self.handler, "query_owned_paints", self.handler.find_paint
            )(args["query"]),
            LocalIntent.LIST_DEPLETED_PAINTS: self.handler.depleted_paints,
            LocalIntent.LIST_PAINTS_BY_COLOR: lambda: self.handler.paints_by_color(args["color"]),
            LocalIntent.COUNT_OWNED_PAINTS: lambda: self.handler.count_owned_paints(args.get("query", "")),
            LocalIntent.LIST_FUTURE_PURCHASES: self.handler.list_future_paints,
            LocalIntent.ADD_FUTURE_PURCHASE: lambda: self.handler.add_future_paint(args["query"], args["quantity"]),
            LocalIntent.COMPLETE_PURCHASE: lambda: self.handler.mark_paint_purchased(args["query"], args["quantity"]),
            LocalIntent.GET_MINIATURE_COUNTS: lambda: self.handler.miniature_counts(args["query"]),
            LocalIntent.COUNT_OWNED_MINIATURES: lambda: self.handler.count_owned_miniatures(),
            LocalIntent.QUERY_OWNED_ENTITY: lambda: self.handler.query_owned_entity(args["query"]),
            LocalIntent.ADD_MINIATURE: self.handler.guided_add_miniature,
            LocalIntent.CHANGE_MINIATURE_STATUS: lambda: self.handler.change_miniature_status(
                args["query"], args["target_status"], args["quantity"]
            ),
            LocalIntent.SHOW_PAINT_CONTEXT: lambda: self.handler.show_paint_context(),
            LocalIntent.ADD_ACTIVE_PAINT_UNIT: lambda: self.handler.change_active_paint_quantity("add", 1),
            LocalIntent.REMOVE_ACTIVE_PAINT_UNIT: lambda: self.handler.change_active_paint_quantity("remove", 1),
            LocalIntent.SET_ACTIVE_PAINT_QUANTITY: lambda: self.handler.change_active_paint_quantity("set", args["quantity"]),
            LocalIntent.ADD_ACTIVE_PAINT_FUTURE: lambda: self.handler.add_active_paint_to_future(),
        }
        return handlers[match.intent]()

    def classify(self, text: str) -> IntentMatch | None:
        clean = " ".join(str(text or "").strip().split())
        normalized = _normalize(clean)
        if not clean:
            return None

        if normalized in {"muestra", "muestralas", "muestralos", "mostrar"}:
            return IntentMatch(LocalIntent.SHOW_PAINT_CONTEXT)
        if normalized in {"anadir otra", "anade otra", "anade una", "suma una"}:
            return IntentMatch(LocalIntent.ADD_ACTIVE_PAINT_UNIT)
        if normalized in {"quita una", "resta una"}:
            return IntentMatch(LocalIntent.REMOVE_ACTIVE_PAINT_UNIT)
        contextual_quantity = re.match(r"^pon(?:la)?(?:\s+a)?\s+(\d+)$", normalized)
        if contextual_quantity:
            return IntentMatch(LocalIntent.SET_ACTIVE_PAINT_QUANTITY, {"quantity": int(contextual_quantity.group(1))})
        if normalized in {"anadela a futuras compras", "agregala a futuras compras", "ponla en futuras compras"}:
            return IntentMatch(LocalIntent.ADD_ACTIVE_PAINT_FUTURE)

        colon_search = re.match(r"^(?:buscar|busca)\s+(?:pinturas?|paint)\s*:\s*(.+)$", clean, re.IGNORECASE)
        if colon_search:
            return IntentMatch(LocalIntent.SEARCH_PAINT, {"query": _entity(colon_search.group(1))})

        explicit_search = re.match(r"^(?:buscar|busca|mostrar|muestra|muestrame)\s+(?:(?:las?\s+)?pinturas?|paint)?\s*:?[ ]*(.+)$", normalized)
        if explicit_search:
            return IntentMatch(LocalIntent.SEARCH_PAINT, {"query": _entity(explicit_search.group(1))})

        if "agotad" in normalized and "pintur" in normalized:
            return IntentMatch(LocalIntent.LIST_DEPLETED_PAINTS)

        paint_count = re.match(
            r"^(?:cuantas|cantidad\s+de)\s+pinturas?(?:\s+(.+?))?\s+tengo$", normalized
        )
        if paint_count:
            return IntentMatch(LocalIntent.COUNT_OWNED_PAINTS, {"query": _entity(paint_count.group(1) or "")})

        if re.match(r"^(?:cuantas|cantidad\s+de)\s+miniaturas?\s+tengo$", normalized):
            return IntentMatch(LocalIntent.COUNT_OWNED_MINIATURES)

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

        explicit_color = re.match(r"^que\s+pinturas\s+tengo\s+de\s+color\s+(.+)$", normalized)
        if explicit_color:
            return IntentMatch(LocalIntent.LIST_PAINTS_BY_COLOR, {"color": _entity(explicit_color.group(1))})

        owned_paints = re.match(
            r"^(?:que\s+)?pinturas?\s+(.+?)\s+tengo$|^tengo\s+(?:(?:las?|unas?)\s+)?pinturas?\s+(.+)$",
            normalized,
        )
        if owned_paints and not re.match(r"^(?:cuantos|cuantas|cantidad)\b", normalized):
            term = _entity(owned_paints.group(1) or owned_paints.group(2))
            return IntentMatch(LocalIntent.GET_PAINT_STOCK, {"query": term})

        if re.search(r"\b(?:anade|agrega)\b.*\bminiaturas?\b", normalized):
            return IntentMatch(LocalIntent.ADD_MINIATURE)

        state_patterns = (
            (r"^(?:hoy\s+)?(?:he\s+)?(?:terminado|termine)\s+(?:(\d+|un|una|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\s+)?(.+)$", "Terminado"),
            (r"^(?:hoy\s+)?(?:he\s+)?(?:pintado|pinte)\s+(?:(\d+|un|una|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\s+)?(.+)$", "Pintado"),
            (r"^(?:hoy\s+)?(?:he\s+)?(?:montado|monte)\s+(?:(\d+|un|una|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\s+)?(.+)$", "Montado"),
        )
        for pattern, status in state_patterns:
            state = re.search(pattern, normalized)
            if state:
                return IntentMatch(
                    LocalIntent.CHANGE_MINIATURE_STATUS,
                    {"query": _strip_determiner(_entity(state.group(2))), "target_status": status, "quantity": _quantity(state.group(1))},
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

        owned_entity = re.match(r"^(.+?)\s+tengo$", normalized)
        if owned_entity:
            return IntentMatch(LocalIntent.QUERY_OWNED_ENTITY, {"query": _entity(owned_entity.group(1))})

        paint_have = re.search(r"(?:tengo|tienes|hay).*?(?:la\s+pintura\s+)?(.+)$", normalized)
        if paint_have and any(word in normalized for word in ("pintura", "tengo", "tienes")):
            query = re.sub(r"^de\s+", "", _entity(paint_have.group(1)), flags=re.IGNORECASE)
            return IntentMatch(LocalIntent.GET_PAINT_STOCK, {"query": query})

        if 1 <= len(normalized.split()) <= 4 and not set(normalized.split()) & {
            "como", "cuando", "donde", "porque", "quiero", "puedes", "hola", "ayuda"
        }:
            return IntentMatch(LocalIntent.SEARCH_PAINT, {"query": clean})

        return None


def _entity(value: str) -> str:
    return str(value or "").strip(" ?.!:;,\t\r\n")


def _strip_determiner(value: str) -> str:
    return re.sub(r"^(?:un|una|unos|unas)\s+", "", value, flags=re.IGNORECASE)


def _quantity(value: str | None) -> int:
    words = {"un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4,
             "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10}
    return int(value) if value and value.isdigit() else words.get(value or "", 1)


def _normalize(value: str) -> str:
    raw = unicodedata.normalize("NFKD", str(value or ""))
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch)).casefold()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", raw).split())
