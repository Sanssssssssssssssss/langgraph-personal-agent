from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.graph.nodes.action import execute_retrieval, execute_tool
from app.graph.nodes.intent import detect_intent, route_after_intent
from app.graph.nodes.respond import respond
from app.graph.state import AgentState
from app.tools.registry import ToolRegistry


def build_graph(tool_registry: ToolRegistry):
    graph = StateGraph(AgentState)

    graph.add_node("detect_intent", detect_intent)
    graph.add_node("tool_node", lambda state: execute_tool(state, tool_registry))
    graph.add_node("retrieval_node", lambda state: execute_retrieval(state, tool_registry))
    graph.add_node("respond_node", respond)

    graph.add_edge(START, "detect_intent")
    graph.add_conditional_edges(
        "detect_intent",
        route_after_intent,
        {
            "tool_node": "tool_node",
            "retrieval_node": "retrieval_node",
            "respond_node": "respond_node",
        },
    )
    graph.add_edge("tool_node", "respond_node")
    graph.add_edge("retrieval_node", "respond_node")
    graph.add_edge("respond_node", END)

    return graph.compile()

