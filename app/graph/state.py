from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    request_id: str
    user_input: str
    intent: str
    context: dict[str, Any]
    retrieval_needed: bool
    selected_tool: str
    tool_args: dict[str, Any]
    tool_calls: list[dict[str, Any]]
    memory_ops: list[dict[str, Any]]
    tool_result: dict[str, Any]
    retrieval_results: list[dict[str, Any]]
    response: str
    errors: list[str]
    trace: list[dict[str, Any]]

