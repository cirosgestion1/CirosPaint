from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import MetaData, Table, inspect, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.services.assistant_confidence_gateway import ConfidenceEscalationGateway, EscalationAction
from app.services.assistant_conversation_context import PaintConversationContext
from app.services.assistant_entity_resolver import EntityCandidate, LocalEntityResolver, normalize_entity_text
from app.services.assistant_intent_router import AssistantLocalIntentRouter
from app.services.assistant_paint_service import AssistantPaintService
from app.services.paint_catalog_service import PaintCatalogService
from app.services.miniature_faction_resolver import MiniatureFactionResolver, faction_forms, normalize_faction
from app.services.query_service import CentralizedQueryService, MiniatureCatalogUnit


CANONICAL_STATUSES = ("Sin montar", "Montado", "Pintado", "Terminado")
_STATUS_ALIASES = {
    "sin montar": "Sin montar",
    "unassembled": "Sin montar",
    "sin_montar": "Sin montar",
    "montado": "Montado",
    "montada": "Montado",
    "assembled": "Montado",
    "pintado": "Pintado",
    "pintada": "Pintado",
    "painted": "Pintado",
    "terminado": "Terminado",
    "terminada": "Terminado",
    "finished": "Terminado",
    "complete": "Terminado",
    "completed": "Terminado",
}


@dataclass
class LocalAssistantResult:
    status: str
    message: str
    kind: str = "text"
    data: dict[str, Any] = field(default_factory=dict)
    requires_ai_resolution: bool = False

    @property
    def ok(self) -> bool:
        return self.status == "ok"


MiniatureUnit = MiniatureCatalogUnit

class AssistantLocalService:
    """Zero-token assistant operations executed entirely by Ciros Paint."""

    def __init__(self, session: Session, context: PaintConversationContext | None = None):
        self.session = session
        self.paint_service = AssistantPaintService(session)
        self.catalog_service = self.paint_service.catalog_service
        self.query_service = CentralizedQueryService(
            session, paint_repository=self.paint_service.paint_repository,
            shopping_repository=self.paint_service.shopping_repository,
            paint_catalog_service=self.catalog_service,
        )
        self.paint_service.query_service = self.query_service
        self.entity_resolver = LocalEntityResolver()
        self.confidence_gateway = ConfidenceEscalationGateway()
        self.intent_router = AssistantLocalIntentRouter(self)
        self.faction_resolver = MiniatureFactionResolver()
        self.context = context or PaintConversationContext()
        self._miniatures = self.query_service.list_miniature_catalog_units()

    # ------------------------------------------------------------------
    # Paints
    # ------------------------------------------------------------------
    def paint_autocomplete(self) -> list[str]:
        values = []
        for paint in self.query_service.list_inventory_paints():
            brand = str(getattr(paint, "brand", "") or "").strip()
            name = str(getattr(paint, "name", "") or "").strip()
            if name:
                values.append(f"{brand} {name}".strip())
        return sorted(set(values), key=_normalize)

    def catalog_paint_autocomplete(self) -> list[str]:
        values = []
        for item in list(getattr(self.catalog_service, "_items", ())):
            brand = str(getattr(item, "brand", "") or "").strip()
            name = str(getattr(item, "name", "") or "").strip()
            if name:
                values.append(f"{brand} {name}".strip())
        return sorted(set(values), key=_normalize)

    def inventory_colors(self) -> list[str]:
        colors = {
            str(getattr(paint, "primary_color", "") or "").strip()
            for paint in self.query_service.list_inventory_paints()
        }
        return sorted((value for value in colors if value), key=_normalize)

    def search_paints(self, query: str) -> LocalAssistantResult:
        return self._from_tool_result(self.paint_service.search_paints(query=query))

    def search_paint_term(self, query: str) -> LocalAssistantResult | None:
        term_forms = _linguistic_forms(query)
        colors = self.query_service.list_inventory_colors()
        matching_colors = [color for color in colors if term_forms & _linguistic_forms(color)]
        if len(matching_colors) == 1:
            return self.paints_by_color(matching_colors[0])
        result = self.search_paints(query)
        return result if (result.data or {}).get("paints") else None

    def query_owned_paints(self, query: str) -> LocalAssistantResult:
        """Resolve an inventory query as a real catalog color or paint name."""
        term_forms = _linguistic_forms(query)
        colors = self.query_service.list_inventory_colors()
        matching_colors = [color for color in colors if term_forms & _linguistic_forms(color)]
        if len(matching_colors) == 1:
            return self.paints_by_color(matching_colors[0])
        return self.find_paint(query)

    def list_future_paints(self, scope: str = "all") -> LocalAssistantResult:
        rows = self.query_service.list_future_purchase_rows(include_restock=True)
        paint_rows = [row for row in rows if row["kind"] == "paint"]
        material_rows = [row for row in rows if row["kind"] == "material"]
        selected = paint_rows if scope == "paints" else material_rows if scope == "materials" else rows
        if scope == "paints":
            message = f"Tienes {len(paint_rows)} pintura{'s' if len(paint_rows) != 1 else ''} en Futuras compras."
        elif scope == "materials":
            message = f"Tienes {len(material_rows)} material{'es' if len(material_rows) != 1 else ''} en Futuras compras."
        else:
            message = (
                f"Tienes {len(rows)} productos en Futuras compras: "
                f"{len(paint_rows)} pintura{'s' if len(paint_rows) != 1 else ''} y "
                f"{len(material_rows)} material{'es' if len(material_rows) != 1 else ''}."
            )
        return LocalAssistantResult("ok", message, "future_purchases", {
            "items": [self._future_payload(row) for row in selected],
            "paint_count": len(paint_rows), "material_count": len(material_rows), "total": len(rows),
            "scope": scope,
        })

    def add_inventory_paint(self, query: str, quantity: int = 1) -> LocalAssistantResult:
        if not normalize_entity_text(query):
            return self.clarify_paint_operation()
        return self._from_tool_result(self.paint_service.add_paint_to_inventory(query=query, quantity=quantity))

    def clarify_paint_operation(self, query: str = "", reason: str = "missing_entity") -> LocalAssistantResult:
        if reason == "purchase_meaning":
            label = f" {query}" if query else " esa pintura"
            return LocalAssistantResult(
                "needs_input", f"¿Quieres añadir{label} a Futuras compras o marcarla como ya comprada?"
            )
        return LocalAssistantResult("needs_input", "¿Qué pintura quieres añadir?")

    def guided_add_miniature(self) -> LocalAssistantResult:
        return LocalAssistantResult(
            "ok",
            "Selecciona la miniatura que quieres añadir.",
            "text",
            {"actions": [{"label": "Añadir miniaturas", "action": "mini_add"}]},
        )

    def find_paint(self, query: str, *, allow_ai_fallback: bool = True) -> LocalAssistantResult:
        if not normalize_entity_text(query):
            return LocalAssistantResult("invalid", "Escribe el nombre de una pintura.")

        inventory_resolution = self.entity_resolver.resolve(query, self._inventory_paint_candidates())
        inventory_decision = self.confidence_gateway.evaluate(
            query, inventory_resolution, allow_gemini=allow_ai_fallback
        )
        if inventory_decision.accepts_local:
            paint = inventory_resolution.candidate.payload
            payload = self._paint_payload(paint)
            exact = inventory_decision.level.value in ("exact", "normalized")
            message = "Coincidencia exacta encontrada." if exact else f"He identificado la pintura como {payload['brand']} {payload['name']}."
            return LocalAssistantResult(
                "ok", message, "paints",
                {
                    "paints": [payload],
                    "exact": exact,
                    "resolver_confidence": round(inventory_decision.confidence, 3),
                    "confidence_level": inventory_decision.level.value,
                    "escalation_action": inventory_decision.action.value,
                    "active_paint_id": payload.get("id"),
                    "actions": self._paint_actions(payload.get("id")),
                },
            )

        if inventory_decision.action == EscalationAction.REQUEST_SELECTION and inventory_resolution.matches:
            labels = list(dict.fromkeys(item.label for item in inventory_resolution.matches))
            paint_matches = [self._paint_payload(item.payload) for item in inventory_resolution.matches]
            return LocalAssistantResult(
                "ambiguous", "Hay varias pinturas que podrían coincidir. Elige una para continuar.", "paint_matches",
                {
                    "entity_type": "paint", "candidates": labels, "raw_name": query,
                    "operation": "paint_find", "confidence_level": inventory_decision.level.value,
                    "escalation_action": inventory_decision.action.value, "paints": paint_matches,
                },
            )

        catalog_candidates = self._catalog_paint_candidates()
        catalog_resolution = self.entity_resolver.resolve(query, catalog_candidates)
        catalog_decision = self.confidence_gateway.evaluate(
            query, catalog_resolution, allow_gemini=allow_ai_fallback
        )
        if catalog_decision.accepts_local:
            catalog = catalog_resolution.candidate.payload
            label = f"{getattr(catalog, 'brand', '')} {getattr(catalog, 'name', '')}".strip()
            return LocalAssistantResult(
                "not_found", f"He identificado la pintura como {label}, pero no está en tu inventario.", "paints",
                {
                    "paints": [],
                    "resolved_catalog_name": label,
                    "resolver_confidence": round(catalog_decision.confidence, 3),
                    "confidence_level": catalog_decision.level.value,
                    "escalation_action": catalog_decision.action.value,
                },
            )

        ranked = self.entity_resolver.rank(query, catalog_candidates, limit=12)
        candidate_labels = list(dict.fromkeys(item.label for score, item in ranked if score >= 0.25))
        matches = inventory_resolution.matches or catalog_resolution.matches
        decision = inventory_decision if inventory_resolution.matches else catalog_decision
        if decision.action == EscalationAction.REQUEST_SELECTION and matches:
            labels = list(dict.fromkeys(item.label for item in matches))
            paint_matches = [self._paint_payload(item.payload) for item in matches if hasattr(item.payload, "available_units")]
            return LocalAssistantResult(
                "ambiguous", "Hay varias pinturas que podrían coincidir. Elige una para continuar.", "paint_matches",
                {
                    "entity_type": "paint", "candidates": labels, "raw_name": query,
                    "operation": "paint_find", "confidence_level": decision.level.value,
                    "escalation_action": decision.action.value, "paints": paint_matches,
                },
            )
        if allow_ai_fallback and candidate_labels:
            return LocalAssistantResult(
                "needs_resolution",
                "No puedo identificar con suficiente seguridad la pintura. Gemini puede interpretar únicamente el nombre entre opciones reales del catálogo.",
                "paint_matches",
                {
                    "entity_type": "paint", "candidates": candidate_labels, "raw_name": query,
                    "operation": "paint_find", "confidence_level": catalog_decision.level.value,
                    "escalation_action": EscalationAction.USE_GEMINI.value,
                },
                requires_ai_resolution=True,
            )
        return LocalAssistantResult(
            "not_found", "No he encontrado ninguna pintura del inventario que coincida.", "paints",
            {"paints": [], "candidates": candidate_labels, "confidence_level": "unresolved", "escalation_action": "reject"},
        )

    def paints_by_color(self, color: str) -> LocalAssistantResult:
        paints = [self._paint_payload(paint) for paint in self.query_service.filter_inventory_paints(color=color)]
        paints.sort(key=lambda item: (_normalize(item["brand"]), _normalize(item["name"])))
        if not paints:
            return LocalAssistantResult("not_found", f"No tienes pinturas cuyo color principal sea {color}.", "paints", {"paints": []})
        return LocalAssistantResult("ok", f"Tienes {len(paints)} pinturas cuyo color principal es {color}.", "paints", {"paints": paints})

    def count_owned_paints(self, query: str = "") -> LocalAssistantResult:
        if query:
            result = self.query_owned_paints(query)
            if result.kind == "paints":
                paints = list((result.data or {}).get("paints") or [])
                result.data["paint_count"] = len(paints)
                result.data["unit_count"] = sum(_safe_int(item.get("total_units")) for item in paints)
            return result
        paints = [self._paint_payload(paint) for paint in self.query_service.list_inventory_paints()]
        units = sum(_safe_int(item.get("total_units")) for item in paints)
        return LocalAssistantResult(
            "ok", f"Tienes {len(paints)} pinturas en el inventario, con {units} unidades en total.",
            "paints", {"paints": paints, "paint_count": len(paints), "unit_count": units},
        )

    def show_paint_context(self) -> LocalAssistantResult:
        paints = list(self.context.candidate_paints)
        if not paints:
            return LocalAssistantResult("invalid", "No hay una pintura ni candidatos activos que mostrar.")
        message = "Estas son las pinturas candidatas anteriores." if self.context.ambiguous else "Esta es la pintura activa."
        return LocalAssistantResult("ok", message, "paints", {"paints": paints})

    def change_active_paint_quantity(self, mode: str, quantity: int = 1) -> LocalAssistantResult:
        paint = self._active_inventory_paint()
        if paint is None:
            return LocalAssistantResult("ambiguous", "Selecciona primero una pintura inequívoca. No se ha modificado nada.")
        return self.change_paint_quantity_by_id(int(paint.id), mode, quantity)

    def change_paint_quantity_by_id(self, paint_id: int, mode: str, quantity: int = 1) -> LocalAssistantResult:
        """Apply a card action to its canonical paint, independent of global context."""
        paint = self.query_service.get_inventory_paint(int(paint_id))
        if paint is None:
            return LocalAssistantResult("not_found", "La pintura de esta tarjeta ya no existe en el inventario.")
        current = self.query_service.paint_units(paint)
        target = int(quantity) if mode == "set" else current + (1 if mode == "add" else -1)
        if target < 0:
            return LocalAssistantResult("invalid", "La cantidad no puede ser negativa. No se ha modificado nada.")
        result = self.paint_service.set_paint_quantity_by_id(int(paint.id), target)
        local = self._from_tool_result(result)
        self.update_paint_context(local)
        return local

    def add_active_paint_to_future(self) -> LocalAssistantResult:
        paint = self._active_inventory_paint()
        if paint is None:
            return LocalAssistantResult("ambiguous", "Selecciona primero una pintura inequívoca. No se ha modificado nada.")
        return self.add_paint_id_to_future(int(paint.id), 1)

    def add_paint_id_to_future(self, paint_id: int, quantity: int = 1) -> LocalAssistantResult:
        result = self.paint_service.add_paint_id_to_future_purchases(int(paint_id), quantity)
        local = self._from_tool_result(result)
        self.update_paint_context(local)
        return local

    def update_paint_context(self, result: LocalAssistantResult) -> None:
        if result.kind not in {"paints", "paint_matches"}:
            return
        paints = list((result.data or {}).get("paints") or [])
        if len(paints) == 1 and result.status == "ok":
            self.context.set_active(paints[0])
            result.data.setdefault("active_paint_id", paints[0].get("id"))
            result.data.setdefault("actions", self._paint_actions(paints[0].get("id")))
        elif len(paints) > 1:
            self.context.set_candidates(paints)
        elif result.status in {"not_found", "invalid"}:
            self.context.clear()

    def _active_inventory_paint(self):
        if self.context.active_paint_id is None or self.context.ambiguous:
            return None
        return self.query_service.get_inventory_paint(self.context.active_paint_id)

    @staticmethod
    def _paint_actions(paint_id: int | None) -> list[dict[str, Any]]:
        if paint_id is None:
            return []
        return [
            {"label": "+1 unidad", "action": "paint_active_add", "paint_id": int(paint_id)},
            {"label": "-1 unidad", "action": "paint_active_remove", "paint_id": int(paint_id)},
            {"label": "Cambiar cantidad", "action": "paint_active_set", "paint_id": int(paint_id)},
            {"label": "Añadir a futuras compras", "action": "paint_active_future", "paint_id": int(paint_id)},
        ]

    def depleted_paints(self) -> LocalAssistantResult:
        paints = []
        for paint in self.query_service.list_inventory_paints():
            payload = self._paint_payload(paint)
            # In Ciros Paint a pot in low_units is already the "casi agotado" portion.
            if payload["total_units"] == 0 or (payload["available_units"] == 0 and payload["low_units"] > 0):
                paints.append(payload)
        paints.sort(key=lambda item: (_normalize(item["brand"]), _normalize(item["name"])))
        if not paints:
            return LocalAssistantResult("ok", "No tienes pinturas agotadas ni casi agotadas.", "paints", {"paints": []})
        return LocalAssistantResult("ok", f"Hay {len(paints)} pinturas agotadas o casi agotadas.", "paints", {"paints": paints})

    def add_future_paint(self, query: str, quantity: int = 1) -> LocalAssistantResult:
        result = self.paint_service.add_paint_to_future_purchases(query=query, quantity=quantity)
        return self._from_tool_result(result)

    def mark_paint_purchased(self, query: str, quantity: int = 1) -> LocalAssistantResult:
        if not normalize_entity_text(query):
            paint = self._active_inventory_paint()
            if paint is None:
                return LocalAssistantResult("needs_input", "¿Qué pintura has comprado?")
            query = str(getattr(paint, "code", None) or f"{paint.brand} {paint.name}")
        return self._from_tool_result(self.paint_service.mark_paint_purchased(query=query, quantity=quantity))

    def mark_paint_id_purchased(self, paint_id: int, quantity: int = 1) -> LocalAssistantResult:
        return self._from_tool_result(self.paint_service.mark_paint_id_purchased(paint_id, quantity))

    # ------------------------------------------------------------------
    # Miniature catalog
    # ------------------------------------------------------------------
    def miniature_games(self, *, owned_only: bool = False) -> list[tuple[str, str]]:
        keys = self._owned_collection_keys() if owned_only else None
        return self.query_service.list_miniature_games(owned_only=owned_only, units=self._miniatures, owned_keys=keys)

    def miniature_factions(self, game_id: str, *, owned_only: bool = False) -> list[tuple[str, str]]:
        keys = self._owned_collection_keys() if owned_only else None
        return self.query_service.list_miniature_factions(
            game_id, owned_only=owned_only, units=self._miniatures, owned_keys=keys
        )

    def miniature_units(self, game_id: str = "", faction_id: str = "", *, owned_only: bool = False) -> list[MiniatureUnit]:
        keys = self._owned_collection_keys() if owned_only else None
        return self.query_service.list_miniature_catalog_units(
            game_id, faction_id, owned_only=owned_only, units=self._miniatures, owned_keys=keys
        )

    def owned_miniature_units(self) -> list[MiniatureUnit]:
        return self.miniature_units(owned_only=True)

    def _owned_collection_keys(self) -> set[str]:
        table = self._collection_table()
        unit_col = self._column(table, ("unit_id", "catalog_id", "unit_key", "miniature_id", "unit_name", "miniature_name", "name"))
        if unit_col is None:
            raise RuntimeError(f"La tabla {table.name} no contiene una columna identificable de unidad.")
        rows = [dict(row) for row in self.session.execute(select(table)).mappings().all()]
        qty_col = self._column(table, ("quantity", "count", "units", "amount", "cantidad"))
        wide = [
            self._column(table, names) for names in (
                ("unassembled", "unassembled_count", "sin_montar"),
                ("assembled", "assembled_count", "montado"),
                ("painted", "painted_count", "pintado"),
                ("finished", "finished_count", "terminado"),
            )
        ]
        keys: set[str] = set()
        for row in rows:
            if any(column is not None for column in wide):
                total = sum(_safe_int(row.get(column.name)) for column in wide if column is not None)
            else:
                total = _safe_int(row.get(qty_col.name)) if qty_col is not None else 1
            if total > 0:
                keys.add(_normalize(row.get(unit_col.name, "")))
        return keys

    def closest_miniature_names(self, raw_name: str, limit: int = 12, *, inventory_only: bool = False) -> list[str]:
        candidates = self._miniature_candidates(inventory_only=inventory_only)
        ranked = self.entity_resolver.rank(raw_name, candidates, limit=limit)
        return [candidate.label for _score, candidate in ranked]

    def resolve_miniature(
        self,
        query: str,
        *,
        allow_fuzzy: bool = True,
        inventory_only: bool = False,
    ) -> tuple[MiniatureUnit | None, list[MiniatureUnit]]:
        unit, matches, _decision = self.resolve_miniature_with_decision(
            query, allow_fuzzy=allow_fuzzy, inventory_only=inventory_only
        )
        return unit, matches

    def resolve_miniature_with_decision(
        self,
        query: str,
        *,
        allow_fuzzy: bool = True,
        inventory_only: bool = False,
    ):
        candidates = self._miniature_candidates(inventory_only=inventory_only)
        if not allow_fuzzy:
            needle = normalize_entity_text(query)
            exact = [candidate for candidate in candidates if needle in candidate.normalized_aliases()]
            resolution = self.entity_resolver.resolve(query, exact)
        else:
            relevant = self._relevant_miniature_candidates(query, candidates)
            resolution = self.entity_resolver.resolve(query, relevant)
        decision = self.confidence_gateway.evaluate(query, resolution, allow_gemini=True)
        if decision.accepts_local:
            unit = resolution.candidate.payload
            return unit, [unit], decision
        return None, [item.payload for item in resolution.matches], decision

    def _relevant_miniature_candidates(self, query: str, candidates: list[EntityCandidate]) -> list[EntityCandidate]:
        """Discard lexically unrelated miniatures before confidence evaluation."""
        needle = normalize_entity_text(query)
        if not needle:
            return []
        needle_tokens = {_singular_token(token) for token in needle.split()}
        ranked_scores = {
            candidate.key: score
            for score, candidate in self.entity_resolver.rank(query, candidates, limit=max(1, len(candidates)))
        }
        relevant = []
        for candidate in candidates:
            aliases = candidate.normalized_aliases()
            if needle in aliases:
                relevant.append(candidate)
                continue
            unit = candidate.payload
            if normalize_entity_text(getattr(unit, "game_name", "")) != "star wars legion":
                continue
            token_similarity = max(
                (SequenceMatcher(None, left, right).ratio()
                 for alias in aliases for left in needle_tokens
                 for right in (_singular_token(token) for token in alias.split())),
                default=0.0,
            )
            score = ranked_scores.get(candidate.key, 0.0)
            if token_similarity >= 0.72 and score >= 0.55:
                relevant.append(candidate)
        return relevant

    def count_owned_miniatures(self) -> LocalAssistantResult:
        entries = self.query_service.list_miniature_collection()
        counts = {
            status: sum(_safe_int(getattr(entry, column, 0)) for entry in entries)
            for status, column in (
                ("Sin montar", "unassembled_count"), ("Montado", "assembled_count"),
                ("Pintado", "painted_count"), ("Terminado", "finished_count"),
            )
        }
        total = sum(counts.values())
        return LocalAssistantResult(
            "ok", f"Tienes {total} miniaturas en tu colección.", "miniature_counts",
            {"counts": counts, "total": total},
        )

    def query_miniature_collection(self, query: str = "", unfinished: bool = False) -> LocalAssistantResult:
        entries = self.query_service.list_miniature_collection()
        if query:
            factions = sorted({(unit.faction_id, unit.faction_name) for unit in self._miniatures})
            faction = self.faction_resolver.resolve(query, factions)
            if faction is not None:
                accepted = faction_forms(faction.faction_name)
                entries = [entry for entry in entries if normalize_faction(getattr(entry, "faction", "")) in accepted]
                return self._miniature_collection_result(entries, unfinished, faction.faction_name)
            unit, matches, decision = self.resolve_miniature_with_decision(query, inventory_only=True)
            if unit is None:
                if matches:
                    return LocalAssistantResult(
                        "ambiguous", "Hay varias miniaturas que podrían coincidir.", "miniature_matches",
                        {"matches": [item.as_dict() for item in matches], "candidates": [item.unit_name for item in matches]},
                    )
                return LocalAssistantResult("not_found", "No encuentro esa miniatura o facción en tu colección.")
            entries = [entry for entry in entries if normalize_entity_text(getattr(entry, "unit_name", "")) in unit.normalized_aliases()] if hasattr(unit, "normalized_aliases") else [
                entry for entry in entries if normalize_entity_text(getattr(entry, "unit_name", "")) == normalize_entity_text(unit.unit_name)
            ]
            return self._miniature_collection_result(entries, unfinished, unit.unit_name)
        return self._miniature_collection_result(entries, unfinished, "")

    def _miniature_collection_result(self, entries: list[object], unfinished: bool, label: str) -> LocalAssistantResult:
        items = []
        totals = {status: 0 for status in CANONICAL_STATUSES}
        columns = {"Sin montar": "unassembled_count", "Montado": "assembled_count",
                   "Pintado": "painted_count", "Terminado": "finished_count"}
        for entry in entries:
            counts = {status: _safe_int(getattr(entry, column, 0)) for status, column in columns.items()}
            amount = sum(counts[status] for status in CANONICAL_STATUSES[:-1]) if unfinished else sum(counts.values())
            if amount <= 0:
                continue
            for status, value in counts.items():
                totals[status] += value
            items.append({"unit": {"unit_name": getattr(entry, "unit_name", "")}, "counts": counts, "amount": amount})
        total = sum(totals[status] for status in CANONICAL_STATUSES[:-1]) if unfinished else sum(totals.values())
        subject = f" de {label}" if label else ""
        message = f"Tienes {total} miniaturas{subject} por terminar." if unfinished else f"Tienes {total} miniaturas{subject} en tu colección."
        return LocalAssistantResult("ok", message, "miniature_list", {
            "items": items, "counts": totals, "total": total, "unfinished": unfinished, "label": label,
        })

    def query_owned_entity(self, query: str) -> LocalAssistantResult:
        """Resolve conversational '<entity> tengo' without guessing its domain."""
        unit, matches, decision = self.resolve_miniature_with_decision(query, inventory_only=True)
        if unit is not None:
            return self.miniature_counts(unit.unit_name)
        paint = self.query_owned_paints(query)
        if paint.status in {"ok", "ambiguous"}:
            return paint
        if matches:
            return LocalAssistantResult(
                "ambiguous" if decision.action == EscalationAction.REQUEST_SELECTION else "needs_resolution",
                "No puedo identificar con seguridad la miniatura.", "miniature_matches",
                {"entity_type": "miniature", "matches": [item.as_dict() for item in matches],
                 "candidates": [item.unit_name for item in matches], "raw_name": query,
                 "operation": "counts", "confidence_level": decision.level.value,
                 "escalation_action": decision.action.value},
                requires_ai_resolution=decision.should_escalate,
            )
        return paint

    def query_named_entity(self, query: str) -> LocalAssistantResult | None:
        """Resolve an isolated catalog name locally without treating general prose as an entity."""
        faction = self.query_miniature_collection(query)
        if faction.status == "ok":
            return faction
        unit, matches, decision = self.resolve_miniature_with_decision(query, inventory_only=True)
        if unit is not None:
            return self.miniature_counts(unit.unit_name)
        if matches and decision.action == EscalationAction.REQUEST_SELECTION:
            return LocalAssistantResult(
                "ambiguous", "Hay varias miniaturas que podrían coincidir.", "miniature_matches",
                {"matches": [item.as_dict() for item in matches],
                 "candidates": [item.unit_name for item in matches], "raw_name": query,
                 "operation": "counts", "confidence_level": decision.level.value,
                 "escalation_action": decision.action.value},
            )
        return self.search_paint_term(query)

    def miniature_counts(self, query: str) -> LocalAssistantResult:
        unit, matches, decision = self.resolve_miniature_with_decision(query, inventory_only=True)
        if unit is None:
            if matches and decision.action == EscalationAction.REQUEST_SELECTION:
                return LocalAssistantResult(
                    "ambiguous", "Hay varias miniaturas que podrían coincidir.", "miniature_matches",
                    {
                        "matches": [item.as_dict() for item in matches],
                        "candidates": [item.unit_name for item in matches],
                        "confidence_level": decision.level.value,
                        "escalation_action": decision.action.value,
                    },
                )
            if matches and decision.should_escalate:
                return LocalAssistantResult(
                    "needs_resolution",
                    "No puedo identificar con seguridad la miniatura. Gemini puede interpretar el nombre entre las unidades que ya tienes.",
                    "miniature_matches",
                    {
                        "entity_type": "miniature", "matches": [item.as_dict() for item in matches],
                        "candidates": [item.unit_name for item in matches], "raw_name": query,
                        "operation": "counts", "confidence_level": decision.level.value,
                        "escalation_action": decision.action.value,
                    },
                    requires_ai_resolution=True,
                )
            faction_result = self.query_miniature_collection(query)
            if faction_result.status == "ok":
                return faction_result
            return LocalAssistantResult("not_found", "No encuentro esa miniatura en tu colección de Ciros Paint.")
        try:
            counts = self._collection_counts(unit)
        except RuntimeError as exc:
            return LocalAssistantResult("error", str(exc))
        return LocalAssistantResult(
            "ok", f"Colección de {unit.unit_name}: {sum(counts.values())} miniaturas en total.",
            "miniature_counts",
            {
                "unit": unit.as_dict(), "counts": counts, "total": sum(counts.values()),
                "confidence_level": decision.level.value, "escalation_action": decision.action.value,
            },
        )

    def miniatures_by_completion(self, game_id: str, faction_id: str, finished: bool) -> LocalAssistantResult:
        rows = []
        for unit in self.miniature_units(game_id, faction_id, owned_only=True):
            counts = self._collection_counts(unit)
            amount = counts["Terminado"] if finished else sum(counts[name] for name in CANONICAL_STATUSES[:-1])
            if amount > 0:
                rows.append({"unit": unit.as_dict(), "counts": counts, "amount": amount})
        label = "terminadas" if finished else "no terminadas"
        if not rows:
            return LocalAssistantResult("ok", f"No hay miniaturas {label} para esa facción.", "miniature_list", {"items": []})
        return LocalAssistantResult("ok", f"Hay {len(rows)} unidades con miniaturas {label}.", "miniature_list", {"items": rows, "finished": finished})

    def available_miniature_transition_count(self, query: str, target_status: str) -> int:
        unit, _matches = self.resolve_miniature(query, inventory_only=True)
        if unit is None or target_status not in {"Montado", "Pintado", "Terminado"}:
            return 0
        counts = self._collection_counts(unit)
        sources = {
            "Montado": ("Sin montar",),
            "Pintado": ("Montado", "Sin montar"),
            "Terminado": ("Pintado", "Montado", "Sin montar"),
        }[target_status]
        return sum(_safe_int(counts.get(status)) for status in sources)

    def change_miniature_status(self, query: str, target_status: str, quantity: int) -> LocalAssistantResult:
        status = canonical_status(target_status)
        if status not in CANONICAL_STATUSES[1:]:
            return LocalAssistantResult("invalid", "El estado destino debe ser Montado, Pintado o Terminado.")
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return LocalAssistantResult("invalid", "La cantidad debe ser un número entero.")
        if quantity < 1:
            return LocalAssistantResult("invalid", "La cantidad debe ser al menos 1.")
        unit, matches, decision = self.resolve_miniature_with_decision(query, inventory_only=True)
        if unit is None:
            request_selection = bool(matches) and decision.action == EscalationAction.REQUEST_SELECTION
            return LocalAssistantResult(
                "ambiguous" if request_selection else ("needs_resolution" if matches else "not_found"),
                "No puedo identificar con seguridad la miniatura. Se puede pedir a Gemini que interprete el nombre entre las unidades que ya tienes.",
                "miniature_matches",
                {
                    "entity_type": "miniature",
                    "matches": [item.as_dict() for item in matches],
                    "candidates": [item.unit_name for item in matches],
                    "raw_name": query,
                    "target_status": status,
                    "quantity": quantity,
                    "operation": "status",
                    "confidence_level": decision.level.value,
                    "escalation_action": decision.action.value,
                },
                requires_ai_resolution=bool(matches) and decision.should_escalate,
            )
        try:
            self._move_status(unit, status, quantity)
            counts = self._collection_counts(unit)
        except RuntimeError as exc:
            return LocalAssistantResult("error", str(exc))
        verb = "Se ha cambiado" if quantity == 1 else "Se han cambiado"
        return LocalAssistantResult(
            "ok",
            f"{verb} {quantity} {unit.unit_name} al estado {status}.\n\n¿Quieres cambiar otra?",
            "miniature_counts",
            {
                "unit": unit.as_dict(),
                "counts": counts,
                "total": sum(counts.values()),
                "changed_quantity": quantity,
                "target_status": status,
                "actions": [{"label": "Cambiar otra miniatura", "action": "mini_status"}],
            },
        )

    def add_miniatures(self, unit: MiniatureUnit, quantity: int, status: str = "Sin montar") -> LocalAssistantResult:
        status = canonical_status(status)
        if status not in CANONICAL_STATUSES:
            return LocalAssistantResult("invalid", "Estado de miniatura no válido.")
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return LocalAssistantResult("invalid", "La cantidad debe ser un número entero.")
        if quantity < 1:
            return LocalAssistantResult("invalid", "La cantidad debe ser al menos 1.")
        try:
            self._add_collection_quantity(unit, status, quantity)
            counts = self._collection_counts(unit)
        except RuntimeError as exc:
            return LocalAssistantResult("error", str(exc))
        return LocalAssistantResult(
            "ok",
            f"Se han añadido {quantity} {unit.unit_name} a la colección como {status}.",
            "miniature_counts",
            {"unit": unit.as_dict(), "counts": counts, "total": sum(counts.values())},
        )

    # ------------------------------------------------------------------
    # Natural-language zero-token router
    # ------------------------------------------------------------------
    def try_handle_text(self, text: str) -> LocalAssistantResult | None:
        result = self.intent_router.route(text)
        if result is not None:
            self.update_paint_context(result)
        elif self.context.active_paint_id is not None or self.context.candidate_paints:
            self.context.clear()
        return result

    # ------------------------------------------------------------------
    # Miniature database adapter
    # ------------------------------------------------------------------
    def miniature_schema_debug(self) -> dict[str, Any]:
        inspector = inspect(self.session.get_bind())
        result = {}
        for table_name in inspector.get_table_names():
            if "mini" in table_name.casefold() or "collection" in table_name.casefold():
                result[table_name] = [column["name"] for column in inspector.get_columns(table_name)]
        return result

    def _collection_table(self) -> Table:
        bind = self.session.get_bind()
        inspector = inspect(bind)
        ranked = []
        for table_name in inspector.get_table_names():
            columns = {column["name"].casefold() for column in inspector.get_columns(table_name)}
            score = 0
            low_name = table_name.casefold()
            if "miniature" in low_name or "miniatura" in low_name:
                score += 6
            if "collection" in low_name or "coleccion" in low_name:
                score += 4
            if columns & {"status", "state", "estado"}:
                score += 5
            if columns & {"quantity", "count", "units", "amount", "cantidad"}:
                score += 3
            if columns & {"unit_id", "unit_name", "miniature_id", "miniature_name", "catalog_id", "name"}:
                score += 3
            if columns & {"unassembled", "assembled", "painted", "finished", "unassembled_count", "assembled_count", "painted_count", "finished_count", "sin_montar", "montado", "pintado", "terminado"}:
                score += 5
            ranked.append((score, table_name, columns))
        ranked.sort(reverse=True)
        if not ranked or ranked[0][0] < 7:
            detail = {name: sorted(cols) for _, name, cols in ranked[:6]}
            raise RuntimeError(f"No se ha podido localizar la tabla de colección de miniaturas. Esquema detectado: {detail}")
        return Table(ranked[0][1], MetaData(), autoload_with=bind)

    @staticmethod
    def _column(table: Table, names: Iterable[str]):
        lookup = {column.name.casefold(): column for column in table.columns}
        for name in names:
            if name.casefold() in lookup:
                return lookup[name.casefold()]
        return None

    def _matching_rows(self, table: Table, unit: MiniatureUnit) -> list[dict[str, Any]]:
        unit_col = self._column(table, ("unit_id", "catalog_id", "unit_key", "miniature_id", "unit_name", "miniature_name", "name"))
        if unit_col is None:
            raise RuntimeError(f"La tabla {table.name} no contiene una columna identificable de unidad.")
        rows = [dict(row) for row in self.session.execute(select(table)).mappings().all()]
        accepted = {_normalize(unit.unit_id), _normalize(unit.unit_name)}
        return [row for row in rows if _normalize(row.get(unit_col.name, "")) in accepted]

    def _collection_counts(self, unit: MiniatureUnit) -> dict[str, int]:
        table = self._collection_table()
        rows = self._matching_rows(table, unit)
        counts = {status: 0 for status in CANONICAL_STATUSES}
        status_col = self._column(table, ("status", "state", "estado"))
        qty_col = self._column(table, ("quantity", "count", "units", "amount", "cantidad"))
        wide = {
            "Sin montar": self._column(table, ("unassembled", "unassembled_count", "sin_montar")),
            "Montado": self._column(table, ("assembled", "assembled_count", "montado")),
            "Pintado": self._column(table, ("painted", "painted_count", "pintado")),
            "Terminado": self._column(table, ("finished", "finished_count", "terminado")),
        }
        if any(column is not None for column in wide.values()):
            for row in rows:
                for status, column in wide.items():
                    if column is not None:
                        counts[status] += _safe_int(row.get(column.name))
            return counts
        if status_col is None:
            raise RuntimeError(f"La tabla {table.name} no contiene estados de miniatura reconocibles.")
        for row in rows:
            status = canonical_status(row.get(status_col.name))
            if status in counts:
                counts[status] += _safe_int(row.get(qty_col.name)) if qty_col is not None else 1
        return counts

    def _move_status(self, unit: MiniatureUnit, target_status: str, quantity: int) -> None:
        table = self._collection_table()
        rows = self._matching_rows(table, unit)
        status_col = self._column(table, ("status", "state", "estado"))
        qty_col = self._column(table, ("quantity", "count", "units", "amount", "cantidad"))
        wide = {
            "Sin montar": self._column(table, ("unassembled", "unassembled_count", "sin_montar")),
            "Montado": self._column(table, ("assembled", "assembled_count", "montado")),
            "Pintado": self._column(table, ("painted", "painted_count", "pintado")),
            "Terminado": self._column(table, ("finished", "finished_count", "terminado")),
        }
        try:
            if any(column is not None for column in wide.values()):
                self._move_wide_status(table, rows, wide, target_status, quantity)
                self.session.commit()
                return
            if status_col is None:
                raise RuntimeError(f"La tabla {table.name} no contiene una columna de estado reconocible.")
            self._move_row_status(table, rows, status_col, qty_col, target_status, quantity)
            self.session.commit()
        except (SQLAlchemyError, RuntimeError) as exc:
            self.session.rollback()
            if isinstance(exc, RuntimeError):
                raise
            raise RuntimeError(f"No se ha podido actualizar el estado de la miniatura: {exc}") from exc

    def _move_wide_status(self, table, rows, wide, target_status, quantity):
        if not rows:
            raise RuntimeError("No hay miniaturas de esa unidad en la colección para cambiar de estado.")
        target_col = wide.get(target_status)
        if target_col is None:
            raise RuntimeError(f"La colección no tiene una columna para el estado {target_status}.")
        source_order = {
            "Montado": ("Sin montar",),
            "Pintado": ("Montado", "Sin montar"),
            "Terminado": ("Pintado", "Montado", "Sin montar"),
        }[target_status]
        row = rows[0]
        remaining = quantity
        changes = {target_col.name: _safe_int(row.get(target_col.name)) + quantity}
        for status in source_order:
            column = wide.get(status)
            if column is None or remaining <= 0:
                continue
            available = _safe_int(row.get(column.name))
            take = min(available, remaining)
            changes[column.name] = available - take
            remaining -= take
        if remaining:
            raise RuntimeError(f"Solo hay {quantity - remaining} miniaturas disponibles en estados anteriores para mover a {target_status}.")
        self.session.execute(update(table).where(self._row_identity(table, row)).values(**changes))

    def _move_row_status(self, table, rows, status_col, qty_col, target_status, quantity):
        source_order = {
            "Montado": ("Sin montar",),
            "Pintado": ("Montado", "Sin montar"),
            "Terminado": ("Pintado", "Montado", "Sin montar"),
        }[target_status]
        sources = [row for status in source_order for row in rows if canonical_status(row.get(status_col.name)) == status]
        available = sum(_safe_int(row.get(qty_col.name)) if qty_col is not None else 1 for row in sources)
        if available < quantity:
            raise RuntimeError(f"Solo hay {available} miniaturas disponibles en estados anteriores para mover a {target_status}.")
        target_rows = [row for row in rows if canonical_status(row.get(status_col.name)) == target_status]
        if qty_col is None:
            for row in sources[:quantity]:
                self.session.execute(update(table).where(self._row_identity(table, row)).values({status_col.name: target_status}))
            return
        remaining = quantity
        template = sources[0]
        for row in sources:
            if remaining <= 0:
                break
            amount = _safe_int(row.get(qty_col.name))
            take = min(amount, remaining)
            self.session.execute(update(table).where(self._row_identity(table, row)).values({qty_col.name: amount - take}))
            remaining -= take
        if target_rows:
            row = target_rows[0]
            current = _safe_int(row.get(qty_col.name))
            self.session.execute(update(table).where(self._row_identity(table, row)).values({qty_col.name: current + quantity}))
        else:
            values = self._clone_row_for_insert(table, template)
            values[status_col.name] = target_status
            values[qty_col.name] = quantity
            self.session.execute(table.insert().values(**values))

    def _add_collection_quantity(self, unit: MiniatureUnit, status: str, quantity: int) -> None:
        table = self._collection_table()
        rows = self._matching_rows(table, unit)
        status_col = self._column(table, ("status", "state", "estado"))
        qty_col = self._column(table, ("quantity", "count", "units", "amount", "cantidad"))
        wide = {
            "Sin montar": self._column(table, ("unassembled", "unassembled_count", "sin_montar")),
            "Montado": self._column(table, ("assembled", "assembled_count", "montado")),
            "Pintado": self._column(table, ("painted", "painted_count", "pintado")),
            "Terminado": self._column(table, ("finished", "finished_count", "terminado")),
        }
        try:
            if any(column is not None for column in wide.values()):
                if not rows:
                    values = self._new_unit_values(table, unit)
                    for key, column in wide.items():
                        if column is not None:
                            values[column.name] = quantity if key == status else 0
                    self.session.execute(table.insert().values(**values))
                else:
                    row = rows[0]
                    column = wide.get(status)
                    if column is None:
                        raise RuntimeError(f"No existe el estado {status} en la tabla de miniaturas.")
                    self.session.execute(update(table).where(self._row_identity(table, row)).values({column.name: _safe_int(row.get(column.name)) + quantity}))
                self.session.commit()
                return
            if status_col is None:
                raise RuntimeError(f"La tabla {table.name} no contiene una columna de estado reconocible.")
            same = [row for row in rows if canonical_status(row.get(status_col.name)) == status]
            if qty_col is not None and same:
                row = same[0]
                self.session.execute(update(table).where(self._row_identity(table, row)).values({qty_col.name: _safe_int(row.get(qty_col.name)) + quantity}))
            elif rows:
                values = self._clone_row_for_insert(table, rows[0])
                values[status_col.name] = status
                if qty_col is not None:
                    values[qty_col.name] = quantity
                self.session.execute(table.insert().values(**values))
            else:
                values = self._new_unit_values(table, unit)
                values[status_col.name] = status
                if qty_col is not None:
                    values[qty_col.name] = quantity
                    self.session.execute(table.insert().values(**values))
                else:
                    for _ in range(quantity):
                        self.session.execute(table.insert().values(**values))
            self.session.commit()
        except (SQLAlchemyError, RuntimeError) as exc:
            self.session.rollback()
            if isinstance(exc, RuntimeError):
                raise
            raise RuntimeError(f"No se han podido añadir las miniaturas a la colección: {exc}") from exc

    def _row_identity(self, table: Table, row: dict[str, Any]):
        pk = list(table.primary_key.columns)
        if not pk:
            raise RuntimeError(f"La tabla {table.name} no tiene clave primaria utilizable.")
        condition = None
        for column in pk:
            clause = column == row.get(column.name)
            condition = clause if condition is None else condition & clause
        return condition

    @staticmethod
    def _clone_row_for_insert(table: Table, row: dict[str, Any]) -> dict[str, Any]:
        pk_names = {column.name for column in table.primary_key.columns}
        return {
            column.name: row.get(column.name)
            for column in table.columns
            if column.name not in pk_names and not (column.autoincrement is True)
        }

    def _new_unit_values(self, table: Table, unit: MiniatureUnit) -> dict[str, Any]:
        values: dict[str, Any] = {}
        mapping = {
            "unit_id": unit.unit_id,
            "catalog_id": unit.unit_id,
            "unit_key": unit.unit_id,
            "miniature_id": unit.unit_id,
            "unit_name": unit.unit_name,
            "miniature_name": unit.unit_name,
            "name": unit.unit_name,
            "game_id": unit.game_id,
            "game": unit.game_name,
            "faction_id": unit.faction_id,
            "faction": unit.faction_name,
        }
        for column in table.columns:
            key = column.name.casefold()
            if key in mapping:
                values[column.name] = mapping[key]
        unit_col = self._column(table, ("unit_id", "catalog_id", "unit_key", "miniature_id", "unit_name", "miniature_name", "name"))
        if unit_col is None:
            raise RuntimeError(f"La tabla {table.name} no permite identificar la unidad que se quiere añadir.")
        return values

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _inventory_paint_candidates(self) -> list[EntityCandidate]:
        rows: list[EntityCandidate] = []
        for paint in self.query_service.list_inventory_paints():
            payload = self._paint_payload(paint)
            label = f"{payload['brand']} {payload['name']}".strip()
            aliases = tuple(str(value) for value in (payload['name'], payload.get('code'), payload.get('range_name')) if value)
            rows.append(EntityCandidate(str(payload.get('id') or label), label, aliases, paint))
        return rows

    def _catalog_paint_candidates(self) -> list[EntityCandidate]:
        rows: list[EntityCandidate] = []
        for index, item in enumerate(list(getattr(self.catalog_service, '_items', ()) )):
            brand = str(getattr(item, 'brand', '') or '').strip()
            name = str(getattr(item, 'name', '') or '').strip()
            label = f"{brand} {name}".strip()
            aliases = tuple(str(value) for value in (name, getattr(item, 'code', None), getattr(item, 'range_name', None), getattr(item, 'source_name', None)) if value)
            rows.append(EntityCandidate(f"catalog:{index}:{label}", label, aliases, item))
        return rows

    def _miniature_candidates(self, *, inventory_only: bool = False) -> list[EntityCandidate]:
        source = self.owned_miniature_units() if inventory_only else self._miniatures
        return [
            EntityCandidate(
                unit.unit_id,
                unit.unit_name,
                (unit.unit_id, f"{unit.faction_name} {unit.unit_name}", f"{unit.game_name} {unit.unit_name}"),
                unit,
            )
            for unit in source
        ]

    def _paint_payload(self, paint: object) -> dict[str, Any]:
        available = max(0, _safe_int(getattr(paint, "available_units", 0)))
        low = max(0, _safe_int(getattr(paint, "low_units", 0)))
        return {
            "id": getattr(paint, "id", None),
            "brand": str(getattr(paint, "brand", "") or ""),
            "name": str(getattr(paint, "name", "") or ""),
            "code": getattr(paint, "code", None),
            "range_name": getattr(paint, "range_name", None),
            "paint_type": str(getattr(paint, "paint_type", "") or ""),
            "primary_color": getattr(paint, "primary_color", None),
            "swatch_hex": getattr(paint, "swatch_hex", None),
            "available_units": available,
            "low_units": low,
            "total_units": available + low,
        }

    def _from_tool_result(self, result) -> LocalAssistantResult:
        data = dict(getattr(result, "data", {}) or {})
        kind = "paints" if data.get("paint") or data.get("paints") else "text"
        if data.get("paint") and not data.get("paints"):
            data["paints"] = [data["paint"]]
        if data.get("paints"):
            data["paints"] = [self._canonical_paint_payload(item) for item in data["paints"]]
            if data.get("paint"):
                data["paint"] = data["paints"][0]
        return LocalAssistantResult(str(getattr(result, "status", "error")), str(getattr(result, "message", "")), kind, data)

    def _canonical_paint_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        paint_id = payload.get("id")
        paint = self.query_service.get_inventory_paint(paint_id) if paint_id is not None else None
        return self._paint_payload(paint) if paint is not None else dict(payload)

    def _future_payload(self, row: dict[str, Any]) -> dict[str, Any]:
        entity = row[row["kind"]]
        payload = self._paint_payload(entity) if row["kind"] == "paint" else {
            "id": getattr(entity, "id", None), "brand": getattr(entity, "brand", None),
            "name": getattr(entity, "name", ""), "category": getattr(entity, "category", None),
        }
        return {"kind": row["kind"], "quantity": row["quantity"], "entity": payload}

    @staticmethod
    def _load_miniature_catalog() -> list[MiniatureUnit]:
        path = Path(__file__).resolve().parents[1] / "data" / "miniature_catalog.json"
        if not path.is_file():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
        rows: list[MiniatureUnit] = []
        for game_index, game in enumerate(payload.get("games") or []):
            game_name = _pick(game, "name", "title", "display_name") or f"Juego {game_index + 1}"
            game_id = str(_pick(game, "id", "key", "slug") or _slug(game_name))
            for faction_index, faction in enumerate(game.get("factions") or []):
                faction_name = _pick(faction, "name", "title", "display_name") or f"Facción {faction_index + 1}"
                faction_id = str(_pick(faction, "id", "key", "slug") or _slug(faction_name))
                for unit_index, unit in enumerate(faction.get("units") or []):
                    unit_name = _pick(unit, "name", "title", "display_name", "product_name")
                    if not unit_name:
                        continue
                    unit_id = str(_pick(unit, "id", "key", "slug", "unit_id", "catalog_id") or _slug(unit_name))
                    rows.append(MiniatureUnit(game_id, str(game_name), faction_id, str(faction_name), unit_id, str(unit_name)))
        return rows


def canonical_status(value: Any) -> str:
    normalized = _normalize(value).replace("_", " ")
    return _STATUS_ALIASES.get(normalized, str(value or "").strip())


def _pick(mapping: dict[str, Any], *keys: str):
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return None


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _normalize(value)).strip("-")


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.casefold().strip().split())


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _linguistic_forms(value: Any) -> set[str]:
    """Small generic Spanish singular/plural/gender normalization, data-driven by DB values."""
    normalized = normalize_entity_text(value)
    forms = {normalized}
    if normalized.endswith("es") and len(normalized) > 3:
        forms.add(normalized[:-2])
    if normalized.endswith("s") and len(normalized) > 2:
        forms.add(normalized[:-1])
    for form in tuple(forms):
        if form.endswith("a"):
            forms.add(form[:-1] + "o")
        elif form.endswith("o"):
            forms.add(form[:-1] + "a")
    return {form for form in forms if form}


def _singular_token(value: str) -> str:
    if value.endswith("es") and len(value) > 4:
        return value[:-2]
    if value.endswith("s") and len(value) > 3:
        return value[:-1]
    return value
