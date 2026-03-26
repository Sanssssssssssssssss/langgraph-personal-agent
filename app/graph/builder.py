from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.graph.nodes.action import execute_retrieval, execute_tool
from app.graph.nodes.confirmation import handle_confirmation
from app.graph.nodes.intent import detect_intent
from app.graph.nodes.planning import plan_execution
from app.graph.routing import route_after_confirmation, route_after_planning
from app.graph.nodes.respond import respond
from app.graph.state import AgentState
from app.tools.registry import ToolRegistry


def build_graph(tool_registry: ToolRegistry):
    graph = StateGraph(AgentState)

    graph.add_node("detect_intent", detect_intent)
    graph.add_node("plan_execution", lambda state: plan_execution(state, tool_registry))
    graph.add_node("confirmation_node", lambda state: handle_confirmation(state, tool_registry))
    graph.add_node("tool_node", lambda state: execute_tool(state, tool_registry))
    graph.add_node("retrieval_node", lambda state: execute_retrieval(state, tool_registry))
    graph.add_node("respond_node", respond)

    graph.add_edge(START, "detect_intent")
    graph.add_edge("detect_intent", "plan_execution")
    graph.add_conditional_edges(
        "plan_execution",
        route_after_planning,
        {
            "tool_node": "tool_node",
            "retrieval_node": "retrieval_node",
            "respond_node": "respond_node",
            "confirmation_node": "confirmation_node",
        },
    )
    graph.add_conditional_edges(
        "confirmation_node",
        route_after_confirmation,
        {
            "tool_node": "tool_node",
            "respond_node": "respond_node",
        },
    )
    graph.add_edge("tool_node", "respond_node")
    graph.add_edge("retrieval_node", "respond_node")
    graph.add_edge("respond_node", END)

    return graph.compile()
