from __future__ import annotations

import argparse
import json
import sys

from app.services.agent import PersonalAgent

HELP_TEXT = """交互式 CLI 命令：
/help        显示帮助
/trace on    开启每轮 trace 输出
/trace off   关闭每轮 trace 输出
/clear       清空当前终端会话内存和待确认动作
/exit        退出交互式会话

确认回复：
- 确认：yes / y / confirm / 是 / 确认
- 取消：no / n / cancel / 否 / 取消
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LangGraph Personal Agent CLI")
    parser.add_argument("user_input", nargs="?", help="Single-shot command or natural-language request")
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Start an interactive REPL session",
    )
    parser.add_argument(
        "--show-trace",
        action="store_true",
        help="Print graph trace after the response",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full final state as JSON",
    )
    return parser


def _print_trace(final_state: dict) -> None:
    print("\n[trace]")
    for event in final_state.get("trace", []):
        print(json.dumps(event, ensure_ascii=False, default=str))


def _handle_slash_command(command: str, agent: PersonalAgent, session: dict) -> tuple[dict, bool]:
    normalized = command.strip().lower()
    if normalized == "/help":
        print(HELP_TEXT)
        return session, False
    if normalized == "/exit":
        print("已退出交互式会话。")
        return session, True
    if normalized == "/clear":
        next_session = agent.new_session(show_trace=session.get("show_trace", False))
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

    print("未知命令，输入 /help 查看可用命令。")
    return session, False


def _run_interactive(agent: PersonalAgent, *, show_trace: bool) -> int:
    session = agent.new_session(show_trace=show_trace)
    print("进入交互式 CLI，会话只保留在当前终端。输入 /help 查看命令。")

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
        return _run_interactive(agent, show_trace=args.show_trace)

    if not args.user_input:
        raise SystemExit("user_input is required unless --interactive is used")

    final_state = agent.invoke(args.user_input)
    if args.json:
        print(json.dumps(final_state, ensure_ascii=False, indent=2, default=str))
        return 0

    print(final_state["response"])
    if args.show_trace:
        _print_trace(final_state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
