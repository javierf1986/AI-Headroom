from __future__ import annotations

from collections import defaultdict
from typing import Any


class SessionStore:
    def __init__(self) -> None:
        self._messages: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def append(self, session_id: str, role: str, content: str) -> None:
        self._messages[session_id].append({"role": role, "content": content})

    def get(self, session_id: str) -> list[dict[str, Any]]:
        return list(self._messages.get(session_id, []))
