from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.services.agent import PersonalAgent


class PersonalAgentTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)
        for relative in [
            "data/uploads",
            "data/processed",
            "data/benchmarks",
        ]:
            (self.base_dir / relative).mkdir(parents=True, exist_ok=True)
        self.agent = PersonalAgent(base_dir=self.base_dir)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_note_roundtrip(self) -> None:
        add_state = self.agent.invoke("note add 架构草案::先固定状态和边界")
        self.assertIn("已创建笔记", add_state["response"])

        list_state = self.agent.invoke("note list")
        self.assertIn("当前共有 1 条笔记", list_state["response"])

        search_state = self.agent.invoke("note search 状态")
        self.assertIn("命中 1 条", search_state["response"])

    def test_reminder_flow(self) -> None:
        self.agent.invoke("remind add 明天复盘架构")
        list_state = self.agent.invoke("remind list")
        self.assertIn("当前共有 1 条提醒", list_state["response"])

        done_state = self.agent.invoke("remind done 1")
        self.assertIn("done", done_state["response"])

    def test_preference_flow(self) -> None:
        set_state = self.agent.invoke("preference set language=zh-CN")
        self.assertIn("已设置偏好", set_state["response"])

        get_state = self.agent.invoke("preference get language")
        self.assertIn("存在", get_state["response"])

    def test_file_ingest_and_retrieval(self) -> None:
        sample = self.base_dir / "sample.txt"
        sample.write_text("LangGraph 负责显式编排状态、节点与路由。", encoding="utf-8")

        ingest_state = self.agent.invoke(f'file ingest "{sample}"')
        self.assertIn("文件已导入", ingest_state["response"])

        retrieve_state = self.agent.invoke("retrieve LangGraph 负责什么")
        self.assertIn("检索结果", retrieve_state["response"])

    def test_trace_logging(self) -> None:
        state = self.agent.invoke("note add Trace::检查路径")
        self.assertTrue(state["trace"])
        trace_file = self.base_dir / "data" / "benchmarks" / "trace.log"
        self.assertTrue(trace_file.exists())


if __name__ == "__main__":
    unittest.main()
