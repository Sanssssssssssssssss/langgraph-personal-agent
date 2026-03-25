from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.graph.state import AgentState


def append_trace(state: AgentState, node: str, detail: dict[str, Any]) -> list[dict[str, Any]]:
    trace = list(state.get("trace", []))
    trace.append(
        {
            "ts": datetime.now(UTC).isoformat(),
            "node": node,
            "detail": detail,
        }
    )
    return trace


def append_error(state: AgentState, message: str) -> list[str]:
    errors = list(state.get("errors", []))
    errors.append(message)
    return errors

