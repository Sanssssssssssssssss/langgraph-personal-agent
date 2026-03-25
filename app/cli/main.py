from __future__ import annotations

import argparse
import json
import sys

from app.services.agent import PersonalAgent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LangGraph Personal Agent CLI")
    parser.add_argument("user_input", help="Single-shot command or natural-language request")
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


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    agent = PersonalAgent()
    final_state = agent.invoke(args.user_input)

    if args.json:
        print(json.dumps(final_state, ensure_ascii=False, indent=2, default=str))
        return 0

    print(final_state["response"])
    if args.show_trace:
        print("\n[trace]")
        for event in final_state.get("trace", []):
            print(json.dumps(event, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
