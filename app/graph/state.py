from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    request_id: str
    session_id: str
    user_input: str
    intent: str
    context: dict[str, Any]
    messages: list[dict[str, str]]
    retrieval_needed: bool
    requires_confirmation: bool
    selected_tool: str
    tool_args: dict[str, Any]
    awaiting_confirmation: bool
    pending_action: dict[str, Any] | None
    confirmation_prompt: str
    confirmation_response: str
    tool_calls: list[dict[str, Any]]
    memory_ops: list[dict[str, Any]]
    tool_result: dict[str, Any]
    retrieval_results: list[dict[str, Any]]
    response: str
    errors: list[str]
    trace: list[dict[str, Any]]
    route_target: str
