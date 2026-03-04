from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class LLMReply:
    text: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


class LocalLLMClient:
    def generate(self, prompt: str, session_messages: list[dict[str, Any]]) -> LLMReply:
        lower = prompt.lower()
        if "time" in lower or "date" in lower:
            return LLMReply(
                text="I will check the current UTC time.",
                tool_calls=[{"tool_id": "datetime.now", "input_data": {}}],
            )
        if lower.startswith("echo "):
            return LLMReply(
                text="I will echo that.",
                tool_calls=[{"tool_id": "echo", "input_data": {"message": prompt[5:]}}],
            )
        return LLMReply(text=f"Local response: {prompt}")

    def finalize(self, original_prompt: str, tool_results: list[dict[str, Any]]) -> str:
        if not tool_results:
            return f"Local response: {original_prompt}"
        return f"Tool results: {tool_results}"
