from __future__ import annotations

from app.graph.nodes.common import append_error, append_trace
from app.graph.state import AgentState
from app.tools.registry import ToolRegistry


def execute_tool(state: AgentState, tool_registry: ToolRegistry) -> AgentState:
    selected_tool = state["selected_tool"]
    tool_args = state.get("tool_args", {})
    tool_calls = list(state.get("tool_calls", []))
    memory_ops = list(state.get("memory_ops", []))
    try:
        result = tool_registry.execute(selected_tool, tool_args)
        tool_calls.append({"tool": selected_tool, "args": tool_args, "status": result["status"]})
        memory_ops.extend(result.get("memory_ops", []))
        trace = append_trace(
            state,
            "tool_node",
            {"tool": selected_tool, "status": result["status"]},
        )
        return {
            "tool_result": result,
            "tool_calls": tool_calls,
            "memory_ops": memory_ops,
            "trace": trace,
        }
    except Exception as exc:
        errors = append_error(state, f"Tool execution failed: {exc}")
        trace = append_trace(
            state,
            "tool_node",
            {"tool": selected_tool, "status": "error", "error": str(exc)},
        )
        return {"errors": errors, "trace": trace}


def execute_retrieval(state: AgentState, tool_registry: ToolRegistry) -> AgentState:
    tool_args = state.get("tool_args", {})
    query = tool_args.get("query", state["user_input"])
    filters = tool_args.get("filters", {})
    try:
        result = tool_registry.execute("retrieval", {"query": query, "filters": filters})
        trace = append_trace(
            state,
            "retrieval_node",
            {
                "query": query,
                "filters": filters,
                "hits": len(result.get("results", [])),
            },
        )
        return {
            "tool_result": result,
            "retrieval_results": result.get("results", []),
            "tool_calls": list(state.get("tool_calls", []))
            + [{"tool": "retrieval", "args": {"query": query, "filters": filters}, "status": result["status"]}],
            "trace": trace,
        }
    except Exception as exc:
        errors = append_error(state, f"Retrieval failed: {exc}")
        trace = append_trace(
            state,
            "retrieval_node",
            {"query": query, "filters": filters, "status": "error", "error": str(exc)},
        )
        return {"errors": errors, "trace": trace}
