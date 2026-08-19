from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AssistantToolResult:
    """Provider-neutral result returned by a Ciros Assistant tool.

    The assistant model never receives ORM objects directly. Every tool result
    is reduced to JSON-compatible data so any future AI provider can consume
    the same contract.
    """

    status: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    requires_user_input: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "data": self.data,
            "requires_user_input": self.requires_user_input,
        }


@dataclass(frozen=True)
class AssistantToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    mutates_data: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "mutates_data": self.mutates_data,
        }
