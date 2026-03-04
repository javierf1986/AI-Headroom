from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Type

from pydantic import BaseModel


@dataclass(slots=True)
class ToolSpec:
    id: str
    description: str
    required_permissions: list[str]
    input_schema: Type[BaseModel] | None = None
    output_schema: Type[BaseModel] | None = None


class Tool(ABC):
    spec: ToolSpec

    @abstractmethod
    def run(self, input_data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def get_schema_dict(self) -> dict[str, Any]:
        """Return OpenAI-compatible tool schema."""
        schema = {
            "type": "function",
            "function": {
                "name": self.spec.id,
                "description": self.spec.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }

        if self.spec.input_schema:
            try:
                schema["function"]["parameters"] = self.spec.input_schema.model_json_schema()
            except Exception:
                pass

        return schema
