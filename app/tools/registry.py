from __future__ import annotations

from pathlib import Path
from typing import Any

from app.retrieval.service import RetrievalService
from app.storage.db import SQLiteStorage
from app.storage.files import FileStorage
from app.storage.vector_store import MilvusLiteStore


class ToolRegistry:
    DEFAULT_DESTRUCTIVE_ACTIONS = (
        "note.delete",
        "remind.cancel",
    )

    def __init__(
        self,
        sqlite_storage: SQLiteStorage,
        file_storage: FileStorage,
        vector_store: MilvusLiteStore,
        retrieval_service: RetrievalService,
        destructive_actions: tuple[str, ...] | list[str] | set[str] | None = None,
    ) -> None:
        self.sqlite_storage = sqlite_storage
        self.file_storage = file_storage
        self.vector_store = vector_store
        self.retrieval_service = retrieval_service
        self.destructive_actions = set(destructive_actions or self.DEFAULT_DESTRUCTIVE_ACTIONS)

    def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        handlers = {
            "note": self._handle_note,
            "remind": self._handle_remind,
            "preference": self._handle_preference,
            "file_ingest": self._handle_file_ingest,
            "retrieval": self._handle_retrieval,
        }
        if tool_name not in handlers:
            return {"status": "noop", "message": "未命中工具，返回帮助信息。"}
        return handlers[tool_name](args)

    def requires_confirmation(self, tool_name: str, args: dict[str, Any]) -> bool:
        return self._action_key(tool_name, args.get("action")) in self.destructive_actions

    def build_pending_action(
        self,
        tool_name: str,
        args: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not self.requires_confirmation(tool_name, args):
            return None

        description = self._build_action_description(tool_name, args.get("action"), args)
        prompt = f"即将{description}。请输入 yes / no（或 确认 / 取消）。"
        return {
            "tool": tool_name,
            "args": dict(args),
            "prompt": prompt,
            "cancel_message": f"已取消：{description}。",
        }

    def _action_key(self, tool_name: str, action: str | None) -> str:
        return f"{tool_name}.{action}" if action else tool_name

    def _build_action_description(
        self,
        tool_name: str,
        action: str | None,
        args: dict[str, Any],
    ) -> str:
        if tool_name == "note" and action == "delete":
            return f"删除笔记 #{args['id']}"
        if tool_name == "remind" and action == "cancel":
            return f"取消提醒 #{args['id']}"
        if tool_name == "note" and action == "update":
            return f"执行 note.update（笔记 #{args['id']}）"
        return f"执行 {tool_name}.{action}"

    def _handle_note(self, args: dict[str, Any]) -> dict[str, Any]:
        action = args["action"]
        if action == "add":
            note = self.sqlite_storage.create_note(args["title"], args["content"])
            return {
                "status": "success",
                "message": f"已创建笔记 #{note['id']}：{note['title']}",
                "records": [note],
                "display_keys": ("id", "title", "updated_at"),
                "memory_ops": [{"kind": "note_write", "id": note["id"]}],
            }
        if action == "list":
            notes = self.sqlite_storage.list_notes()
            return {
                "status": "success",
                "message": f"当前共有 {len(notes)} 条笔记。",
                "records": notes,
                "display_keys": ("id", "title", "updated_at"),
                "memory_ops": [{"kind": "note_read", "count": len(notes)}],
            }
        if action == "search":
            notes = self.sqlite_storage.search_notes(args["query"])
            return {
                "status": "success",
                "message": f"笔记搜索命中 {len(notes)} 条。",
                "records": notes,
                "display_keys": ("id", "title", "updated_at"),
                "memory_ops": [{"kind": "note_search", "query": args["query"]}],
            }
        if action == "update":
            note = self.sqlite_storage.update_note(args["id"], args["title"], args["content"])
            return {
                "status": "success",
                "message": f"已更新笔记 #{note['id']}。",
                "records": [note],
                "display_keys": ("id", "title", "updated_at"),
                "memory_ops": [{"kind": "note_update", "id": note["id"]}],
            }
        if action == "delete":
            self.sqlite_storage.delete_note(args["id"])
            return {
                "status": "success",
                "message": f"已删除笔记 #{args['id']}。",
                "memory_ops": [{"kind": "note_delete", "id": args["id"]}],
            }
        raise ValueError(f"Unsupported note action: {action}")

    def _handle_remind(self, args: dict[str, Any]) -> dict[str, Any]:
        action = args["action"]
        if action == "add":
            reminder = self.sqlite_storage.create_reminder(args["content"], args.get("due_at"))
            return {
                "status": "success",
                "message": f"已创建提醒 #{reminder['id']}。",
                "records": [reminder],
                "display_keys": ("id", "content", "status", "due_at"),
                "memory_ops": [{"kind": "reminder_write", "id": reminder["id"]}],
            }
        if action == "list":
            reminders = self.sqlite_storage.list_reminders()
            return {
                "status": "success",
                "message": f"当前共有 {len(reminders)} 条提醒。",
                "records": reminders,
                "display_keys": ("id", "content", "status", "due_at"),
                "memory_ops": [{"kind": "reminder_read", "count": len(reminders)}],
            }
        if action in {"done", "cancel"}:
            reminder = self.sqlite_storage.update_reminder_status(args["id"], action)
            return {
                "status": "success",
                "message": f"提醒 #{reminder['id']} 已标记为 {reminder['status']}。",
                "records": [reminder],
                "display_keys": ("id", "content", "status", "due_at"),
                "memory_ops": [
                    {
                        "kind": "reminder_update",
                        "id": reminder["id"],
                        "status": reminder["status"],
                    }
                ],
            }
        raise ValueError(f"Unsupported reminder action: {action}")

    def _handle_preference(self, args: dict[str, Any]) -> dict[str, Any]:
        action = args["action"]
        if action == "set":
            pref = self.sqlite_storage.set_preference(args["key"], args["value"])
            return {
                "status": "success",
                "message": f"已设置偏好 {pref['key']}={pref['value']}",
                "records": [pref],
                "display_keys": ("key", "value", "updated_at"),
                "memory_ops": [{"kind": "preference_set", "key": pref["key"]}],
            }
        if action == "get":
            pref = self.sqlite_storage.get_preference(args["key"])
            records = [pref] if pref else []
            message = f"偏好 {args['key']} 存在。" if pref else f"未找到偏好 {args['key']}。"
            return {
                "status": "success",
                "message": message,
                "records": records,
                "display_keys": ("key", "value", "updated_at"),
                "memory_ops": [{"kind": "preference_get", "key": args["key"]}],
            }
        if action == "list":
            prefs = self.sqlite_storage.list_preferences()
            return {
                "status": "success",
                "message": f"当前共有 {len(prefs)} 项偏好。",
                "records": prefs,
                "display_keys": ("key", "value", "updated_at"),
                "memory_ops": [{"kind": "preference_list", "count": len(prefs)}],
            }
        raise ValueError(f"Unsupported preference action: {action}")

    def _handle_file_ingest(self, args: dict[str, Any]) -> dict[str, Any]:
        action = args["action"]
        if action == "list":
            files = self.sqlite_storage.list_files()
            return {
                "status": "success",
                "message": f"当前共有 {len(files)} 个已导入文件。",
                "records": files,
                "display_keys": (
                    "id",
                    "source_name",
                    "extension",
                    "media_type",
                    "chunk_count",
                    "created_at",
                ),
                "memory_ops": [{"kind": "file_list", "count": len(files)}],
            }
        if action == "show":
            file_record = self.sqlite_storage.get_file(args["id"])
            preview_chunks = self.sqlite_storage.list_file_chunks(args["id"], limit=3)
            message_lines = [
                f"文件 #{file_record['id']} 详情。",
                f"- source_name={file_record.get('source_name')}",
                f"- extension={file_record.get('extension')}",
                f"- media_type={file_record.get('media_type')}",
                f"- chunk_count={file_record.get('chunk_count')}",
            ]
            if preview_chunks:
                message_lines.append("- chunk_preview:")
                for chunk in preview_chunks:
                    message_lines.append(
                        f"  - chunk_index={chunk['chunk_index']} text={chunk['text'][:80]}"
                    )
            return {
                "status": "success",
                "message": "\n".join(message_lines),
                "records": [file_record],
                "display_keys": (
                    "id",
                    "source_name",
                    "extension",
                    "media_type",
                    "chunk_count",
                    "created_at",
                ),
                "memory_ops": [{"kind": "file_show", "id": file_record["id"]}],
            }
        if action != "ingest":
            raise ValueError(f"Unsupported file action: {action}")

        source_path = Path(args["path"]).expanduser().resolve()
        stored = self.file_storage.store_file(source_path)
        text = self.file_storage.extract_text(stored["stored_path"])
        chunks = self.retrieval_service.chunk_text(text)
        file_record = self.sqlite_storage.create_file(
            original_path=str(source_path),
            stored_path=stored["stored_path"],
            source_name=stored["source_name"],
            extension=stored["extension"],
            media_type=stored["media_type"],
            checksum=stored["checksum"],
            chunk_count=len(chunks),
        )
        self.sqlite_storage.upsert_file_chunks(
            file_id=file_record["id"],
            source_path=stored["stored_path"],
            source_name=stored["source_name"],
            extension=stored["extension"],
            media_type=stored["media_type"],
            chunks=chunks,
        )
        self.vector_store.upsert_file_chunks(file_record["id"], stored["stored_path"], chunks)
        return {
            "status": "success",
            "message": f"文件已导入 #{file_record['id']}，共 {len(chunks)} 个分片。",
            "records": [file_record],
            "display_keys": ("id", "source_name", "extension", "chunk_count", "created_at"),
            "memory_ops": [{"kind": "file_ingest", "id": file_record["id"], "chunks": len(chunks)}],
        }

    def _handle_retrieval(self, args: dict[str, Any]) -> dict[str, Any]:
        filters = args.get("filters", {})
        results = self.retrieval_service.retrieve(
            args["query"],
            self.vector_store,
            self.sqlite_storage,
            filters=filters,
        )
        if not results:
            return {
                "status": "success",
                "message": "未检索到相关知识。",
                "results": [],
            }
        lines = ["检索结果："]
        if filters:
            lines.append(f"- filters={filters}")
        for item in results:
            lines.append(
                f"- file_id={item['file_id']} source_name={item.get('source_name')} "
                f"extension={item.get('extension')} score={item['score']:.4f} text={item['text'][:80]}"
            )
        return {
            "status": "success",
            "message": "\n".join(lines),
            "results": results,
        }
