from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ChatRequest:
    session_id: str
    actor: str
    text: str
    language: str = "en"
    permissions: list[str] = field(default_factory=list)
    client_id: str | None = None
    preferred_voice_id: str | None = None
    preferred_sprite: str | None = None


@dataclass(slots=True)
class ToolCall:
    tool_id: str
    input_data: dict[str, Any]


@dataclass(slots=True)
class ChatResponse:
    session_id: str
    text: str
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    audio: dict[str, Any] | None = None
    avatar: dict[str, Any] | None = None
