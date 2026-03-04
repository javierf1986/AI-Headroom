from __future__ import annotations

from pydantic import BaseModel, Field

from backend.tools.base import Tool, ToolSpec


class EchoInput(BaseModel):
    message: str = Field(description="The message to echo back")


class EchoOutput(BaseModel):
    echo: str = Field(description="The echoed message")


class EchoTool(Tool):
    spec = ToolSpec(
        id="echo",
        description="Returns the provided message.",
        required_permissions=["tool.echo"],
        input_schema=EchoInput,
        output_schema=EchoOutput,
    )

    def run(self, input_data: dict, context: dict) -> dict:
        return {"echo": input_data.get("message", "")}
