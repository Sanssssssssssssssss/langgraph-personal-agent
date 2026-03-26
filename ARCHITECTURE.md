# ARCHITECTURE

## 技术栈
- Python 3.13
- LangGraph 作为编排层
- SQLite 作为结构化存储
- Milvus Lite 作为向量存储
- 文件系统作为原始文件存储

## 模块设计
- `app/cli`：命令行入口，负责接收输入、展示响应和 trace
- `app/graph`：状态定义、节点实现、图构建与路由
- `app/tools`：工具注册表与工具执行逻辑
- `app/storage`：SQLite、Milvus Lite、文件读写
- `app/retrieval`：文本切分、embedding、检索服务
- `app/observability`：trace 和运行日志
- `app/models`：后续模型抽象保留位
- `app/services`：高层应用服务封装

## 数据模型
- Notes：`id`、`title`、`content`、`created_at`、`updated_at`
- Reminders：`id`、`content`、`status`、`due_at`、`created_at`、`updated_at`
- Preferences：`key`、`value`、`updated_at`
- Files：`id`、`original_path`、`stored_path`、`media_type`、`checksum`、`chunk_count`、`created_at`
- Retrieval Chunks：`id`、`file_id`、`chunk_index`、`text`、`source_path`、`source_name`、`extension`、`media_type`、`vector`

## LangGraph 主图
- `detect_intent`：解析用户输入并写入 state
- `confirmation_node`：处理 destructive 操作确认和确认回复
- `tool_node`：执行 note/remind/preference/file_ingest
- `retrieval_node`：执行 retrieval
- `respond_node`：汇总结果并生成用户输出

## State 原则
- 初版 state 字段：
  - `request_id`
  - `user_input`
  - `intent`
  - `context`
  - `messages`
  - `retrieval_needed`
  - `requires_confirmation`
  - `selected_tool`
  - `tool_args`
  - `awaiting_confirmation`
  - `pending_action`
  - `confirmation_prompt`
  - `confirmation_response`
  - `tool_calls`
  - `memory_ops`
  - `tool_result`
  - `retrieval_results`
  - `response`
  - `errors`
  - `trace`

## 接口原则
- 工具只负责完成动作，不负责路由
- 路由由 graph 控制
- 存储实现与工具调用解耦
- 检索链路后续可替换 embedding、reranker、hybrid retrieval
- destructive 确认优先在 graph state 中表达，不放在 CLI 层硬编码执行逻辑
- retrieval 先做“向量召回 + 本地 metadata 过滤”的最小实现，后续再演进到更复杂 filter/metadata pipeline

## CLI 会话原则
- 单次模式与交互模式共用同一个 `PersonalAgent.invoke(...)` 接口
- 交互式会话消息只保留在当前终端内存，不写入 SQLite
- slash 命令只在 CLI 层处理，不进入 graph

## Retrieval Metadata 原则
- 文件导入时自动提取并保存 `source_name`、`extension`、`media_type`
- 检索时先向量召回，再用 chunk/file metadata 做本地过滤
- 过滤字段第一版固定为 `file_id`、`source_name`、`extension`、`media_type`

## 调试原则
- 每次请求记录 request_id
- 节点执行路径进入 trace
- 工具调用和错误上下文写入 trace 日志
