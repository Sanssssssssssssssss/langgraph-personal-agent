from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.cli.main import main as cli_main
from app.services.agent import PersonalAgent


class PersonalAgentTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)
        for relative in [
            "data/uploads",
            "data/processed",
            "data/benchmarks",
            "configs",
        ]:
            (self.base_dir / relative).mkdir(parents=True, exist_ok=True)
        self.agent = PersonalAgent(base_dir=self.base_dir)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_note_roundtrip(self) -> None:
        add_state = self.agent.invoke("note add 架构草案::先固定状态和边界")
        self.assertEqual("架构草案", add_state["tool_result"]["records"][0]["title"])

        list_state = self.agent.invoke("note list")
        self.assertEqual(1, len(list_state["tool_result"]["records"]))

        search_state = self.agent.invoke("note search 状态")
        self.assertEqual(1, len(search_state["tool_result"]["records"]))

    def test_reminder_flow(self) -> None:
        self.agent.invoke("remind add 明天下午复盘架构")
        list_state = self.agent.invoke("remind list")
        self.assertEqual(1, len(list_state["tool_result"]["records"]))

        done_state = self.agent.invoke("remind done 1")
        self.assertIn("done", done_state["response"])

    def test_preference_flow(self) -> None:
        set_state = self.agent.invoke("preference set language=zh-CN")
        self.assertEqual("language", set_state["tool_result"]["records"][0]["key"])

        get_state = self.agent.invoke("preference get language")
        self.assertEqual("zh-CN", get_state["tool_result"]["records"][0]["value"])

    def test_file_ingest_and_retrieval(self) -> None:
        sample = self.base_dir / "sample.txt"
        sample.write_text("LangGraph 负责显式编排状态、节点与路由。", encoding="utf-8")

        ingest_state = self.agent.invoke(f'file ingest "{sample}"')
        self.assertEqual("sample.txt", ingest_state["tool_result"]["records"][0]["source_name"])

        retrieve_state = self.agent.invoke("retrieve LangGraph 负责什么")
        self.assertTrue(retrieve_state["retrieval_results"])
        self.assertEqual("sample.txt", retrieve_state["retrieval_results"][0]["source_name"])

    def test_retrieval_filter_by_file_id(self) -> None:
        first = self.base_dir / "first.txt"
        second = self.base_dir / "second.md"
        first.write_text("Alpha 文档只讨论 LangGraph 状态图。", encoding="utf-8")
        second.write_text("Beta 文档只讨论提醒和偏好。", encoding="utf-8")

        self.agent.invoke(f'file ingest "{first}"')
        self.agent.invoke(f'file ingest "{second}"')

        filtered = self.agent.invoke("retrieve 文档 | filter:file_id=2")
        self.assertIn("filters={'file_id': 2}", filtered["response"])
        self.assertTrue(filtered["retrieval_results"])
        self.assertTrue(all(item["file_id"] == 2 for item in filtered["retrieval_results"]))

    def test_retrieval_filter_by_extension(self) -> None:
        sample_txt = self.base_dir / "extension_case.txt"
        sample_md = self.base_dir / "extension_case.md"
        sample_txt.write_text("文本文件里有 Alpha 检索内容。", encoding="utf-8")
        sample_md.write_text("Markdown 文件里有 Alpha 检索内容。", encoding="utf-8")

        self.agent.invoke(f'file ingest "{sample_txt}"')
        self.agent.invoke(f'file ingest "{sample_md}"')

        filtered = self.agent.invoke("retrieve Alpha | filter:extension=.md")
        self.assertTrue(filtered["retrieval_results"])
        self.assertTrue(all(item["extension"] == ".md" for item in filtered["retrieval_results"]))

    def test_retrieval_filter_by_media_type(self) -> None:
        sample = self.base_dir / "media_type_case.md"
        sample.write_text("media type filter 文档。", encoding="utf-8")

        self.agent.invoke(f'file ingest "{sample}"')
        filtered = self.agent.invoke("retrieve filter | filter:media_type=text/markdown")
        self.assertTrue(filtered["retrieval_results"])
        self.assertTrue(all(item["media_type"] == "text/markdown" for item in filtered["retrieval_results"]))

    def test_file_list_and_show(self) -> None:
        sample = self.base_dir / "inventory.md"
        sample.write_text("file inventory test", encoding="utf-8")

        self.agent.invoke(f'file ingest "{sample}"')

        list_state = self.agent.invoke("file list")
        self.assertEqual(1, len(list_state["tool_result"]["records"]))
        self.assertEqual("inventory.md", list_state["tool_result"]["records"][0]["source_name"])

        show_state = self.agent.invoke("file show 1")
        self.assertEqual(1, show_state["tool_result"]["records"][0]["id"])
        self.assertIn("chunk_preview", show_state["response"])

    def test_trace_logging(self) -> None:
        state = self.agent.invoke("note add Trace::检查路径")
        self.assertTrue(state["trace"])
        trace_file = self.base_dir / "data" / "benchmarks" / "trace.log"
        self.assertTrue(trace_file.exists())

    def test_single_shot_delete_requires_confirmation(self) -> None:
        self.agent.invoke("note add 待删除::阶段2确认节点")

        state = self.agent.invoke("note delete 1")
        self.assertTrue(state["awaiting_confirmation"])
        self.assertIn("yes / no", state["response"])

        list_state = self.agent.invoke("note list")
        self.assertEqual(1, len(list_state["tool_result"]["records"]))

    def test_confirmation_yes_executes_delete(self) -> None:
        self.agent.invoke("note add 待删除::阶段2确认节点")
        session = self.agent.new_session()

        prompt_state = self.agent.invoke("note delete 1", session=session)
        self.assertTrue(prompt_state["awaiting_confirmation"])
        session = prompt_state["session"]

        confirm_state = self.agent.invoke("yes", session=session)
        self.assertFalse(confirm_state["awaiting_confirmation"])
        self.assertIn("#1", confirm_state["response"])

        list_state = self.agent.invoke("note list")
        self.assertEqual([], list_state["tool_result"]["records"])

    def test_confirmation_no_cancels_delete(self) -> None:
        self.agent.invoke("note add 保留::取消删除")
        session = self.agent.new_session()

        prompt_state = self.agent.invoke("note delete 1", session=session)
        session = prompt_state["session"]

        cancel_state = self.agent.invoke("取消", session=session)
        self.assertFalse(cancel_state["awaiting_confirmation"])
        self.assertIn("已取消", cancel_state["response"])

        list_state = self.agent.invoke("note list")
        self.assertEqual(1, len(list_state["tool_result"]["records"]))

    def test_invalid_confirmation_keeps_pending_action(self) -> None:
        self.agent.invoke("note add 保留::无效确认")
        session = self.agent.new_session()

        prompt_state = self.agent.invoke("note delete 1", session=session)
        session = prompt_state["session"]

        invalid_state = self.agent.invoke("maybe later", session=session)
        self.assertTrue(invalid_state["awaiting_confirmation"])
        self.assertIn("yes / no", invalid_state["response"])

    def test_confirmation_policy_can_require_note_update(self) -> None:
        settings_path = self.base_dir / "configs" / "settings.toml"
        settings_path.write_text(
            """
[storage]
sqlite_path = "data/processed/personal_agent.db"
milvus_path = "data/processed/personal_agent_milvus.db"
upload_dir = "data/uploads"

[runtime]
trace_path = "data/benchmarks/trace.log"

[confirmation]
destructive_actions = ["note.update", "remind.cancel"]
""".strip(),
            encoding="utf-8",
        )
        agent = PersonalAgent(base_dir=self.base_dir)
        agent.invoke("note add 配置化::确认策略")

        state = agent.invoke("note update 1 配置化::更新后需要确认")
        self.assertTrue(state["awaiting_confirmation"])
        self.assertIn("note.update", state["pending_action"]["prompt"])

    def test_interactive_cli_slash_commands(self) -> None:
        with (
            patch("app.cli.main.PersonalAgent", return_value=self.agent),
            patch.object(sys, "argv", ["run.py", "--interactive"]),
            patch("builtins.input", side_effect=["/help", "/trace on", "/clear", "/exit"]),
            patch("sys.stdout", new_callable=io.StringIO) as mock_stdout,
        ):
            cli_main()

        output = mock_stdout.getvalue()
        self.assertIn("进入交互式 CLI", output)
        self.assertIn("/help", output)
        self.assertIn("trace 已开启", output)
        self.assertIn("已清空当前会话内存和待确认动作", output)
        self.assertIn("已退出交互式会话", output)


if __name__ == "__main__":
    unittest.main()
