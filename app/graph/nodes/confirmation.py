from __future__ import annotations

from app.graph.nodes.common import append_trace
from app.graph.state import AgentState
from app.tools.registry import ToolRegistry

CONFIRM_TOKENS = {"yes", "y", "confirm", "是", "确认"}
CANCEL_TOKENS = {"no", "n", "cancel", "否", "取消"}


def handle_confirmation(state: AgentState, tool_registry: ToolRegistry) -> AgentState:
    pending_action = state.get("pending_action")
    if state.get("intent") == "confirmation":
        if not pending_action:
            trace = append_trace(
                state,
                "confirmation_node",
                {"status": "missing_pending_action"},
            )
            return {
                "tool_result": {"status": "cancelled", "message": "当前没有待确认的操作。"},
                "awaiting_confirmation": False,
                "pending_action": None,
                "trace": trace,
            }

        response = state.get("confirmation_response", "").strip().lower()
        if response in CONFIRM_TOKENS:
            trace = append_trace(
                state,
                "confirmation_node",
                {
                    "status": "confirmed",
                    "tool": pending_action["tool"],
                    "action": pending_action["args"].get("action"),
                },
            )
            return {
                "selected_tool": pending_action["tool"],
                "tool_args": pending_action["args"],
                "awaiting_confirmation": False,
                "pending_action": None,
                "confirmation_prompt": "",
                "confirmation_response": "confirmed",
                "trace": trace,
            }

        if response in CANCEL_TOKENS:
            trace = append_trace(
                state,
                "confirmation_node",
                {
                    "status": "cancelled",
                    "tool": pending_action["tool"],
                    "action": pending_action["args"].get("action"),
                },
            )
            return {
                "tool_result": {"status": "cancelled", "message": pending_action["cancel_message"]},
                "awaiting_confirmation": False,
                "pending_action": None,
                "confirmation_prompt": "",
                "confirmation_response": "cancelled",
                "trace": trace,
            }

        reprompt = pending_action["prompt"] + "\n请输入 yes / no（或 确认 / 取消）。"
        trace = append_trace(
            state,
            "confirmation_node",
            {"status": "invalid_response", "response": state.get("confirmation_response", "")},
        )
        return {
            "tool_result": {"status": "awaiting_confirmation", "message": reprompt},
            "awaiting_confirmation": True,
            "pending_action": pending_action,
            "confirmation_prompt": reprompt,
            "confirmation_response": "invalid",
            "trace": trace,
        }

    pending_action = tool_registry.build_pending_action(
        state["selected_tool"],
        state.get("tool_args", {}),
    )
    if pending_action is None:
        trace = append_trace(state, "confirmation_node", {"status": "noop"})
        return {"trace": trace}

    trace = append_trace(
        state,
        "confirmation_node",
        {
            "status": "prompted",
            "tool": pending_action["tool"],
            "action": pending_action["args"].get("action"),
        },
    )
    return {
        "tool_result": {"status": "awaiting_confirmation", "message": pending_action["prompt"]},
        "awaiting_confirmation": True,
        "pending_action": pending_action,
        "confirmation_prompt": pending_action["prompt"],
        "confirmation_response": "",
        "trace": trace,
    }


def route_after_confirmation(state: AgentState) -> str:
    if state.get("confirmation_response") == "confirmed":
        return "tool_node"
    return "respond_node"
