from __future__ import annotations

import argparse
import json
import sys

from app.services.agent import AgentSession, PersonalAgent

HELP_TEXT = """交互式 CLI 命令：
/help                 显示帮助
/trace on             开启每轮 trace 输出
/trace off            关闭每轮 trace 输出
/clear                清空当前会话内存和待确认动作
/session info         查看当前会话信息
/session save         将当前会话持久化
/session list         列出最近持久化会话
/session load <id>    加载指定持久化会话
/session new          新建一个持久化会话
/exit                 退出交互式会话

确认回复：
- 确认：yes / y / confirm / 是 / 确认
- 取消：no / n / cancel / 否 / 取消

文件命令：
- file ingest <path>
- file list
- file show <id>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LangGraph Personal Agent CLI")
    parser.add_argument("user_input", nargs="?", help="Single-shot command or natural-language request")
    parser.add_argument("-i", "--interactive", action="store_true", help="Start an interactive REPL session")
    parser.add_argument("--show-trace", action="store_true", help="Print graph trace after the response")
    parser.add_argument("--json", action="store_true", help="Print the full final state as JSON")
    parser.add_argument(
        "--persist-session",
        action="store_true",
        help="Persist the interactive or single-shot session to SQLite",
    )
    parser.add_argument(
        "--session-id",
        help="Resume an existing persisted session for single-shot or interactive mode",
    )
    return parser


def _print_trace(final_state: dict) -> None:
    print("\n[trace]")
    for event in final_state.get("trace", []):
        print(json.dumps(event, ensure_ascii=False, default=str))


def _print_session_info(session: AgentSession) -> None:
    print("[session]")
    print(f"id={session.get('session_id') or 'transient'}")
    print(f"persisted={bool(session.get('persisted'))}")
    print(f"messages={len(session.get('messages', []))}")
    print(f"awaiting_confirmation={bool(session.get('pending_confirmation'))}")


def _handle_session_command(command: str, agent: PersonalAgent, session: AgentSession) -> AgentSession:
    normalized = command.strip()
    lower = normalized.lower()
    if lower == "/session info":
        _print_session_info(session)
        return session
    if lower == "/session save":
        if session.get("persisted") and session.get("session_id"):
            saved = agent.session_store.save_session(session)
            print(f"会话已保存：{saved['session_id']}")
            return saved
        saved = agent.new_session(
            show_trace=session.get("show_trace", False),
            persist=True,
            title="Interactive CLI Session",
        )
        saved["messages"] = list(session.get("messages", []))
        saved["pending_confirmation"] = session.get("pending_confirmation")
        saved = agent.session_store.save_session(saved)
        print(f"已创建并保存会话：{saved['session_id']}")
        return saved
    if lower == "/session list":
        sessions = agent.list_sessions()
        print("[sessions]")
        if not sessions:
            print("暂无持久化会话。")
            return session
        for item in sessions:
            print(
                f"- id={item['id']} message_count={item.get('message_count', 0)} "
                f"awaiting_confirmation={item.get('awaiting_confirmation')} preview={item.get('preview', '')}"
            )
        return session
    if lower.startswith("/session load "):
        session_id = normalized.split(" ", 2)[2].strip()
        loaded = agent.load_session(session_id)
        print(f"已加载会话：{loaded['session_id']}")
        return loaded
    if lower == "/session new":
        created = agent.new_session(
            show_trace=session.get("show_trace", False),
            persist=True,
            title="Interactive CLI Session",
        )
        print(f"已创建新会话：{created['session_id']}")
        return created
    print("未知 session 命令，输入 /help 查看可用命令。")
    return session


def _handle_slash_command(command: str, agent: PersonalAgent, session: AgentSession) -> tuple[AgentSession, bool]:
    normalized = command.strip().lower()
    if normalized == "/help":
        print(HELP_TEXT)
        return session, False
    if normalized == "/exit":
        print("已退出交互式会话。")
        return session, True
    if normalized == "/clear":
        next_session: AgentSession = {
            "session_id": session.get("session_id", ""),
            "title": session.get("title"),
            "messages": [],
            "pending_confirmation": None,
            "show_trace": session.get("show_trace", False),
            "persisted": bool(session.get("persisted")),
        }
        if next_session.get("persisted") and next_session.get("session_id"):
            next_session = agent.session_store.save_session(next_session)
        print("已清空当前会话内存和待确认动作。")
        return next_session, False
    if normalized == "/trace on":
        session["show_trace"] = True
        print("trace 已开启。")
        return session, False
    if normalized == "/trace off":
        session["show_trace"] = False
        print("trace 已关闭。")
        return session, False
    if normalized.startswith("/session "):
        return _handle_session_command(command, agent, session), False

    print("未知命令，输入 /help 查看可用命令。")
    return session, False


def _build_start_session(
    agent: PersonalAgent,
    *,
    show_trace: bool,
    persist_session: bool,
    session_id: str | None,
) -> AgentSession:
    if session_id:
        session = agent.load_session(session_id)
        session["show_trace"] = show_trace or session.get("show_trace", False)
        return session
    return agent.new_session(
        show_trace=show_trace,
        persist=persist_session or agent.settings.session.auto_persist_interactive,
        title="Interactive CLI Session" if (persist_session or agent.settings.session.auto_persist_interactive) else None,
    )


def _run_interactive(
    agent: PersonalAgent,
    *,
    show_trace: bool,
    persist_session: bool,
    session_id: str | None,
) -> int:
    session = _build_start_session(
        agent,
        show_trace=show_trace,
        persist_session=persist_session,
        session_id=session_id,
    )
    print("进入交互式 CLI，会话只保留在当前终端；若启用持久化则可恢复。输入 /help 查看命令。")
    if session.get("persisted"):
        print(f"当前会话 id={session.get('session_id')}")

    while True:
        try:
            user_input = input("agent> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出交互式会话。")
            return 0

        if not user_input:
            continue

        if user_input.startswith("/"):
            session, should_exit = _handle_slash_command(user_input, agent, session)
            if should_exit:
                return 0
            continue

        final_state = agent.invoke(user_input, session=session)
        session = final_state["session"]
        print(final_state["response"])
        if session.get("show_trace"):
            _print_trace(final_state)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    agent = PersonalAgent()

    if args.interactive:
        if args.json:
            raise SystemExit("--json cannot be used with --interactive")
        return _run_interactive(
            agent,
            show_trace=args.show_trace,
            persist_session=args.persist_session,
            session_id=args.session_id,
        )

    if not args.user_input:
        raise SystemExit("user_input is required unless --interactive is used")

    session = None
    if args.session_id:
        session = agent.load_session(args.session_id)
    elif args.persist_session:
        session = agent.new_session(persist=True, title="Single Shot Session")

    final_state = agent.invoke(args.user_input, session=session)
    if args.json:
        print(json.dumps(final_state, ensure_ascii=False, indent=2, default=str))
        return 0

    print(final_state["response"])
    if final_state.get("session", {}).get("persisted"):
        print(f"[session] id={final_state['session'].get('session_id')}")
    if args.show_trace:
        _print_trace(final_state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
