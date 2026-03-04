from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any


@dataclass(slots=True)
class AuditEntry:
    timestamp: datetime
    actor: str
    action: str
    permitted: bool
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


class PermissionManager:
    def __init__(self) -> None:
        self._audit_log: list[AuditEntry] = []

    def can_execute(self, actor: str, permission: str, context: dict[str, Any]) -> bool:
        allowed_permissions = set(context.get("permissions", []))
        # Wildcard "*" grants all permissions
        if "*" in allowed_permissions:
            return True
        return permission in allowed_permissions

    def validate_or_raise(self, actor: str, permission: str, context: dict[str, Any]) -> None:
        permitted = self.can_execute(actor=actor, permission=permission, context=context)
        reason = "permission_granted" if permitted else "permission_denied"
        self._audit_log.append(
            AuditEntry(
                timestamp=datetime.now(UTC),
                actor=actor,
                action=permission,
                permitted=permitted,
                reason=reason,
                metadata={"session_id": context.get("session_id")},
            )
        )
        if not permitted:
            raise PermissionError(f"Actor '{actor}' lacks permission '{permission}'")

    @property
    def audit_log(self) -> list[AuditEntry]:
        return list(self._audit_log)
