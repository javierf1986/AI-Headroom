from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Callable


@dataclass(slots=True)
class Event:
    name: str
    payload: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


Subscriber = Callable[[Event], None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Subscriber]] = defaultdict(list)
        self._history: list[Event] = []

    def subscribe(self, event_name: str, callback: Subscriber) -> None:
        self._subscribers[event_name].append(callback)

    def publish(self, event_name: str, payload: dict[str, Any]) -> Event:
        event = Event(name=event_name, payload=payload)
        self._history.append(event)
        for callback in self._subscribers.get(event_name, []):
            callback(event)
        return event

    @property
    def history(self) -> list[Event]:
        return list(self._history)
