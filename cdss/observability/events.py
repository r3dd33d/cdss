from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from cdss.core.enums import AgentType, EventType

# Fields that must never appear in event payloads.
_PII_KEYS = {"raw_input", "patient_text", "message"}


def _redact(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove known PII keys from an event payload."""
    return {k: v for k, v in payload.items() if k not in _PII_KEYS}


class AgentEvent(BaseModel):
    event_type: EventType
    run_id: str
    parent_run_id: str | None = None
    agent_type: AgentType | None = None
    label: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def build(
        cls,
        event_type: EventType,
        run_id: str,
        *,
        parent_run_id: str | None = None,
        agent_type: AgentType | None = None,
        label: str = "",
        duration_ms: int | None = None,
        **payload: Any,
    ) -> "AgentEvent":
        return cls(
            event_type=event_type,
            run_id=run_id,
            parent_run_id=parent_run_id,
            agent_type=agent_type,
            label=label,
            duration_ms=duration_ms,
            payload=_redact(payload),
        )
