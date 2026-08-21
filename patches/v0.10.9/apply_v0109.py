from __future__ import annotations

import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"Expected exactly one {label}; found {text.count(old)}")
    return text.replace(old, new, 1)


def replace_section(text: str, start: str, end: str, replacement: str, label: str) -> str:
    start_at = text.find(start)
    end_at = text.find(end, start_at)
    if start_at < 0 or end_at < 0:
        raise RuntimeError(f"Could not locate {label}")
    return text[:start_at] + replacement + text[end_at:]


def main(root: Path) -> None:
    config_path = root / "app/core/config.py"
    config = config_path.read_text(encoding="utf-8")
    config = replace_once(config, 'APP_VERSION = "0.10.8"', 'APP_VERSION = "0.10.9"', "0.10.8 version marker")
    config_path.write_text(config, encoding="utf-8")

    path = root / "app/services/assistant_local_service.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "from app.services.assistant_entity_resolver import EntityCandidate, LocalEntityResolver, normalize_entity_text\n",
        "from app.services.assistant_confidence_gateway import ConfidenceEscalationGateway, EscalationAction\n"
        "from app.services.assistant_entity_resolver import EntityCandidate, LocalEntityResolver, normalize_entity_text\n"
        "from app.services.assistant_intent_router import AssistantLocalIntentRouter\n",
        "assistant service imports",
    )
    text = replace_once(
        text,
        "        self.entity_resolver = LocalEntityResolver()\n        self._miniatures = self._load_miniature_catalog()\n",
        "        self.entity_resolver = LocalEntityResolver()\n"
        "        self.confidence_gateway = ConfidenceEscalationGateway()\n"
        "        self.intent_router = AssistantLocalIntentRouter(self)\n"
        "        self._miniatures = self._load_miniature_catalog()\n",
        "assistant service initialization",
    )

    paint_methods = '''    def search_paints(self, query: str) -> LocalAssistantResult:
        return self._from_tool_result(self.paint_service.search_paints(query=query))

    def list_future_paints(self) -> LocalAssistantResult:
        return self._from_tool_result(self.paint_service.list_future_paint_purchases())

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
            return LocalAssistantResult(
                "ambiguous", "Hay varias pinturas que podrían coincidir. Elige una para continuar.", "paint_matches",
                {
                    "entity_type": "paint", "candidates": labels, "raw_name": query,
                    "operation": "paint_find", "confidence_level": decision.level.value,
                    "escalation_action": decision.action.value,
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

'''
    text = replace_section(text, "    def find_paint(", "    def paints_by_color(", paint_methods, "paint resolution methods")

    miniature_resolution = '''    def resolve_miniature(
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
            resolution = self.entity_resolver.resolve(query, candidates)
        decision = self.confidence_gateway.evaluate(query, resolution, allow_gemini=True)
        if decision.accepts_local:
            unit = resolution.candidate.payload
            return unit, [unit], decision
        return None, [item.payload for item in resolution.matches], decision

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

'''
    text = replace_section(text, "    def resolve_miniature(", "    def miniatures_by_completion(", miniature_resolution, "miniature resolution methods")

    old_change_start = "    def change_miniature_status("
    change_end = "    def add_miniatures("
    old_change = text[text.find(old_change_start):text.find(change_end, text.find(old_change_start))]
    new_change = old_change.replace(
        "        unit, matches = self.resolve_miniature(query, inventory_only=True)\n        if unit is None:\n",
        "        unit, matches, decision = self.resolve_miniature_with_decision(query, inventory_only=True)\n"
        "        if unit is None:\n"
        "            request_selection = bool(matches) and decision.action == EscalationAction.REQUEST_SELECTION\n",
    ).replace(
        '                "needs_resolution" if matches else "not_found",',
        '                "ambiguous" if request_selection else ("needs_resolution" if matches else "not_found"),',
    ).replace(
        '                    "operation": "status",\n',
        '                    "operation": "status",\n                    "confidence_level": decision.level.value,\n                    "escalation_action": decision.action.value,\n',
    ).replace(
        "                requires_ai_resolution=bool(matches),",
        "                requires_ai_resolution=bool(matches) and decision.should_escalate,",
    )
    if new_change == old_change:
        raise RuntimeError("Miniature status method was not updated")
    text = text.replace(old_change, new_change, 1)

    router = '''    def try_handle_text(self, text: str) -> LocalAssistantResult | None:
        return self.intent_router.route(text)

'''
    text = replace_section(text, "    def try_handle_text(", "    # ------------------------------------------------------------------\n    # Miniature database adapter", router, "natural-language router")
    path.write_text(text, encoding="utf-8")

    required = (
        root / "app/services/assistant_intent_router.py",
        root / "app/services/assistant_confidence_gateway.py",
        root / "tests/test_assistant_intent_gateway_v0109.py",
    )
    missing = [str(item) for item in required if not item.is_file()]
    if missing:
        raise RuntimeError(f"Missing 0.10.9 overlay files: {missing}")
    print("Applied Ciros Paint 0.10.9 local intent router and confidence gateway")


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    main(target)
