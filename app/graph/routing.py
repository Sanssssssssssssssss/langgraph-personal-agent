from __future__ import annotations

from app.graph.state import AgentState


def route_after_planning(state: AgentState) -> str:
    return state.get("route_target", "respond_node")


def route_after_confirmation(state: AgentState) -> str:
    if state.get("confirmation_response") == "confirmed":
        return "tool_node"
    return "respond_node"
