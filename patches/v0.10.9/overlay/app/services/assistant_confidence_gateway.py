from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.services.assistant_entity_resolver import EntityResolution, normalize_entity_text


class ConfidenceLevel(str, Enum):
    EXACT = "exact"
    NORMALIZED = "normalized"
    FUZZY_HIGH = "fuzzy_high"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


class EscalationAction(str, Enum):
    ACCEPT_LOCAL = "accept_local"
    REQUEST_SELECTION = "request_selection"
    USE_GEMINI = "use_gemini"
    REJECT = "reject"


@dataclass(frozen=True)
class ConfidenceDecision:
    level: ConfidenceLevel
    action: EscalationAction
    confidence: float
    margin: float
    reason: str

    @property
    def accepts_local(self) -> bool:
        return self.action == EscalationAction.ACCEPT_LOCAL

    @property
    def should_escalate(self) -> bool:
        return self.action == EscalationAction.USE_GEMINI


class ConfidenceEscalationGateway:
    """Common policy between deterministic resolution and Gemini fallback."""

    def __init__(self, *, ambiguity_floor: float = 0.72):
        self.ambiguity_floor = float(ambiguity_floor)

    def evaluate(
        self,
        query: str,
        resolution: EntityResolution,
        *,
        allow_gemini: bool = True,
    ) -> ConfidenceDecision:
        confidence = float(resolution.confidence or 0.0)
        margin = float(resolution.margin or 0.0)

        if resolution.resolved and resolution.candidate is not None:
            raw_query = " ".join(str(query or "").strip().casefold().split())
            raw_aliases = {
                " ".join(str(value or "").strip().casefold().split())
                for value in (resolution.candidate.label, resolution.candidate.key, *resolution.candidate.aliases)
            }
            if raw_query in raw_aliases:
                level = ConfidenceLevel.EXACT
                reason = "exact local match"
            elif normalize_entity_text(query) in resolution.candidate.normalized_aliases():
                level = ConfidenceLevel.NORMALIZED
                reason = "normalized local match"
            else:
                level = ConfidenceLevel.FUZZY_HIGH
                reason = "high-confidence fuzzy local match"
            return ConfidenceDecision(level, EscalationAction.ACCEPT_LOCAL, confidence, margin, reason)

        if resolution.matches and confidence >= self.ambiguity_floor:
            return ConfidenceDecision(
                ConfidenceLevel.AMBIGUOUS,
                EscalationAction.REQUEST_SELECTION,
                confidence,
                margin,
                "several plausible local candidates",
            )

        if allow_gemini and resolution.matches:
            return ConfidenceDecision(
                ConfidenceLevel.UNRESOLVED,
                EscalationAction.USE_GEMINI,
                confidence,
                margin,
                "local confidence is insufficient",
            )

        return ConfidenceDecision(
            ConfidenceLevel.UNRESOLVED,
            EscalationAction.REJECT,
            confidence,
            margin,
            "no safe local resolution",
        )
