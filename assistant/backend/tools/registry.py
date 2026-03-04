from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from backend.core.permissions import PermissionManager
from backend.tools.base import Tool

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self, permission_manager: PermissionManager) -> None:
        self._tools: dict[str, Tool] = {}
        self._permission_manager = permission_manager

    def register(self, tool: Tool) -> None:
        self._tools[tool.spec.id] = tool
        logger.info(f"Registered tool: {tool.spec.id}")

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "id": tool.spec.id,
                "description": tool.spec.description,
                "required_permissions": tool.spec.required_permissions,
                "schema": tool.get_schema_dict(),
            }
            for tool in self._tools.values()
        ]

    def validate_input(self, tool_id: str, input_data: dict[str, Any]) -> dict[str, Any]:
        """Validate and coerce input data against tool schema."""
        if tool_id not in self._tools:
            raise ValueError(f"Unknown tool '{tool_id}'")

        tool = self._tools[tool_id]
        if not tool.spec.input_schema:
            return input_data

        try:
            validated = tool.spec.input_schema(**input_data)
            return validated.model_dump()
        except ValidationError as e:
            logger.error(f"Input validation failed for {tool_id}: {e}")
            raise ValueError(f"Invalid input for tool '{tool_id}': {e}") from e

    def run(self, tool_id: str, input_data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        if tool_id not in self._tools:
            raise ValueError(f"Unknown tool '{tool_id}'")

        tool = self._tools[tool_id]
        actor = context.get("actor", "assistant")
        for permission in tool.spec.required_permissions:
            self._permission_manager.validate_or_raise(actor=actor, permission=permission, context=context)

        validated_input = self.validate_input(tool_id=tool_id, input_data=input_data)
        result = tool.run(input_data=validated_input, context=context)
        return result
