from __future__ import annotations

from datetime import datetime, UTC

from pydantic import BaseModel, Field

from backend.tools.base import Tool, ToolSpec


class DateTimeInput(BaseModel):
    pass


class DateTimeOutput(BaseModel):
    utc: str = Field(description="Current UTC timestamp in ISO format")


class DateTimeTool(Tool):
    spec = ToolSpec(
        id="datetime.now",
        description="Returns current UTC timestamp.",
        required_permissions=["tool.datetime.read"],
        input_schema=DateTimeInput,
        output_schema=DateTimeOutput,
    )

    def run(self, input_data: dict, context: dict) -> dict:
        return {"utc": datetime.now(UTC).isoformat()}
