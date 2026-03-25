from __future__ import annotations

import re
from uuid import uuid4

from app.graph.nodes.common import append_trace
from app.graph.state import AgentState


def _parse_kv_payload(payload: str) -> tuple[str, str]:
    if "::" in payload:
        title, content = payload.split("::", 1)
        return title.strip(), content.strip()
    return payload[:30].strip() or "Untitled", payload.strip()


def _parse_note(user_input: str) -> tuple[str, dict]:
    match = re.match(r"^note\s+(add|list|search|update|delete)\s*(.*)$", user_input, flags=re.I)
    if not match:
        return "unknown", {}
    action = match.group(1).lower()
    payload = match.group(2).strip()
    if action == "add":
        title, content = _parse_kv_payload(payload)
        return "note", {"action": action, "title": title, "content": content}
    if action == "list":
        return "note", {"action": action}
    if action == "search":
        return "note", {"action": action, "query": payload}
    if action == "update":
        note_id, _, rest = payload.partition(" ")
        title, content = _parse_kv_payload(rest.strip())
        return "note", {
            "action": action,
            "id": int(note_id),
            "title": title,
            "content": content,
        }
    if action == "delete":
        return "note", {"action": action, "id": int(payload)}
    return "unknown", {}


def _parse_reminder(user_input: str) -> tuple[str, dict]:
    match = re.match(r"^remind\s+(add|list|done|cancel)\s*(.*)$", user_input, flags=re.I)
    if not match:
        return "unknown", {}
    action = match.group(1).lower()
    payload = match.group(2).strip()
    if action == "add":
        content, _, due_part = payload.partition("| due:")
        return "remind", {"action": action, "content": content.strip(), "due_at": due_part.strip() or None}
    if action == "list":
        return "remind", {"action": action}
    return "remind", {"action": action, "id": int(payload)}


def _parse_preference(user_input: str) -> tuple[str, dict]:
    match = re.match(r"^preference\s+(set|get|list)\s*(.*)$", user_input, flags=re.I)
    if not match:
        return "unknown", {}
    action = match.group(1).lower()
    payload = match.group(2).strip()
    if action == "set":
        key, _, value = payload.partition("=")
        return "preference", {"action": action, "key": key.strip(), "value": value.strip()}
    if action == "get":
        return "preference", {"action": action, "key": payload}
    return "preference", {"action": action}


def _parse_file(user_input: str) -> tuple[str, dict]:
    match = re.match(r"^file\s+ingest\s+(.+)$", user_input, flags=re.I)
    if not match:
        return "unknown", {}
    return "file_ingest", {"action": "ingest", "path": match.group(1).strip().strip('"')}


def _parse_retrieval(user_input: str) -> tuple[str, dict]:
    match = re.match(r"^retrieve\s+(.+)$", user_input, flags=re.I)
    if not match:
        return "unknown", {}
    return "retrieval", {"query": match.group(1).strip()}


def _parse_natural_language(user_input: str) -> tuple[str, dict]:
    lowered = user_input.lower()
    if "提醒" in user_input:
        content = user_input.replace("提醒我", "").replace("请提醒我", "").strip()
        return "remind", {"action": "add", "content": content or user_input, "due_at": None}
    if "偏好" in user_input and "设置" in user_input and "=" in user_input:
        key, _, value = user_input.split("=", 1)
        return "preference", {"action": "set", "key": key.split()[-1].strip(), "value": value.strip()}
    if "笔记" in user_input and ("记" in user_input or "新增" in user_input):
        payload = user_input.replace("记一条笔记", "").replace("记录笔记", "").replace("新增笔记", "").strip("：: ")
        title, content = _parse_kv_payload(payload or user_input)
        return "note", {"action": "add", "title": title, "content": content}
    if "搜索笔记" in user_input or "查笔记" in user_input:
        query = re.sub(r"^(搜索笔记|查笔记)", "", user_input).strip("：: ")
        return "note", {"action": "search", "query": query}
    if "导入文件" in user_input:
        path = user_input.replace("导入文件", "").strip("：: ")
        return "file_ingest", {"action": "ingest", "path": path.strip('"')}
    if lowered.startswith("what") or "检索" in user_input or "知识库" in user_input:
        return "retrieval", {"query": user_input}
    return "chat", {"message": user_input}


def detect_intent(state: AgentState) -> AgentState:
    user_input = state["user_input"].strip()
    parsers = [_parse_note, _parse_reminder, _parse_preference, _parse_file, _parse_retrieval]
    selected_tool = "chat"
    tool_args: dict = {"message": user_input}
    intent = "chat"
    retrieval_needed = False

    for parser in parsers:
        candidate_tool, candidate_args = parser(user_input)
        if candidate_tool != "unknown":
            selected_tool = candidate_tool
            tool_args = candidate_args
            intent = candidate_tool
            retrieval_needed = candidate_tool == "retrieval"
            break
    else:
        selected_tool, tool_args = _parse_natural_language(user_input)
        intent = selected_tool
        retrieval_needed = selected_tool == "retrieval"

    trace = append_trace(
        state,
        "detect_intent",
        {
            "intent": intent,
            "selected_tool": selected_tool,
            "tool_args": tool_args,
        },
    )
    return {
        "request_id": state.get("request_id") or str(uuid4()),
        "intent": intent,
        "selected_tool": selected_tool,
        "tool_args": tool_args,
        "retrieval_needed": retrieval_needed,
        "trace": trace,
    }


def route_after_intent(state: AgentState) -> str:
    if state.get("retrieval_needed"):
        return "retrieval_node"
    if state.get("selected_tool") in {"note", "remind", "preference", "file_ingest"}:
        return "tool_node"
    return "respond_node"

