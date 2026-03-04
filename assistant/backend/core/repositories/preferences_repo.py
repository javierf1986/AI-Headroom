from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import select

from backend.core.db import init_db, session_scope
from backend.core.models import UserPreference


@dataclass(slots=True)
class PreferenceRecord:
    client_id: str
    default_avatar: str | None = None


class PreferencesRepository:
    def __init__(self) -> None:
        self._db_ready = init_db()
        self._memory: dict[str, PreferenceRecord] = {}

    def _memory_get(self, client_id: str) -> PreferenceRecord:
        if client_id not in self._memory:
            self._memory[client_id] = PreferenceRecord(client_id=client_id)
        return self._memory[client_id]

    def get(self, client_id: str) -> PreferenceRecord:
        if not self._db_ready:
            return self._memory_get(client_id)

        with session_scope() as session:
            model = session.scalar(select(UserPreference).where(UserPreference.client_id == client_id))
            if model is None:
                model = UserPreference(client_id=client_id)
                session.add(model)
                session.flush()

            return PreferenceRecord(
                client_id=model.client_id,
                default_avatar=model.default_avatar,
            )

    def update(self, client_id: str, updates: dict[str, str | None]) -> PreferenceRecord:
        allowed = {"default_avatar"}
        normalized_updates = {k: v for k, v in updates.items() if k in allowed}

        if not normalized_updates:
            return self.get(client_id)

        if not self._db_ready:
            current = self._memory_get(client_id)
            for key, value in normalized_updates.items():
                setattr(current, key, value)
            return current

        with session_scope() as session:
            model = session.scalar(select(UserPreference).where(UserPreference.client_id == client_id))
            if model is None:
                model = UserPreference(client_id=client_id)
                session.add(model)
                session.flush()

            for key, value in normalized_updates.items():
                setattr(model, key, value)

            session.flush()

            return PreferenceRecord(
                client_id=model.client_id,
                default_avatar=model.default_avatar,
            )

    @staticmethod
    def to_dict(record: PreferenceRecord) -> dict[str, str | None]:
        return asdict(record)
