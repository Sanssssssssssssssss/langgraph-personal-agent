from __future__ import annotations

import json
from pathlib import Path

from app.graph.state import AgentState


class TraceLogger:
    def __init__(self, trace_path: str | Path) -> None:
        self.trace_path = Path(trace_path)
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, state: AgentState) -> None:
        payload = {
            "request_id": state.get("request_id"),
            "user_input": state.get("user_input"),
            "intent": state.get("intent"),
            "tool_calls": state.get("tool_calls", []),
            "errors": state.get("errors", []),
            "trace": state.get("trace", []),
            "response": state.get("response"),
        }
        with self.trace_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")

