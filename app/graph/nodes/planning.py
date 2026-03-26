from __future__ import annotations

from app.graph.nodes.common import append_trace
from app.graph.state import AgentState
from app.tools.registry import ToolRegistry


def plan_execution(state: AgentState, tool_registry: ToolRegistry) -> AgentState:
    intent = state.get("intent", "chat")
    selected_tool = state.get("selected_tool", "chat")
    tool_args = state.get("tool_args", {})

    if intent == "confirmation":
        route_target = "confirmation_node"
        requires_confirmation = False
        retrieval_needed = False
    else:
        requires_confirmation = tool_registry.requires_confirmation(selected_tool, tool_args)
        retrieval_needed = selected_tool == "retrieval"
        if requires_confirmation:
            route_target = "confirmation_node"
        elif retrieval_needed:
            route_target = "retrieval_node"
        elif selected_tool in {"note", "remind", "preference", "file_ingest"}:
            route_target = "tool_node"
        else:
            route_target = "respond_node"

    trace = append_trace(
        state,
        "plan_execution",
        {
            "intent": intent,
            "selected_tool": selected_tool,
            "route_target": route_target,
            "requires_confirmation": requires_confirmation,
            "retrieval_needed": retrieval_needed,
        },
    )
    return {
        "requires_confirmation": requires_confirmation,
        "retrieval_needed": retrieval_needed,
        "route_target": route_target,
        "trace": trace,
    }
