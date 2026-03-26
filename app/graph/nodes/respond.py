from __future__ import annotations

from app.graph.nodes.common import append_trace
from app.graph.state import AgentState


def _format_records(items: list[dict], keys: tuple[str, ...]) -> str:
    lines = []
    for item in items:
        parts = [f"{key}={item.get(key)}" for key in keys if key in item]
        lines.append(" - " + ", ".join(parts))
    return "\n".join(lines) if lines else " - 无"


def respond(state: AgentState) -> AgentState:
    if state.get("errors"):
        response = "执行失败：\n" + "\n".join(f"- {error}" for error in state["errors"])
    elif state.get("tool_result"):
        result = state["tool_result"]
        response = result.get("message", "操作完成。")
        if result.get("records"):
            response = response + "\n" + _format_records(
                result["records"],
                result.get("display_keys", ()),
            )
    else:
        response = (
            "当前是最小骨架版 personal agent。可用命令包括："
            "note/remind/preference/file ingest|list|show/retrieve。"
        )

    trace = append_trace(
        state,
        "respond_node",
        {"response_preview": response[:120]},
    )
    return {"response": response, "trace": trace}
