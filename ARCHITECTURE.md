# ARCHITECTURE

## 技术栈
- Python 3.13
- LangGraph 作为编排层
- SQLite 作为结构化存储与 session 持久化层
- Milvus Lite 兼容封装作为向量层
- 文件系统作为原始文件存储
- TOML 配置文件作为运行时策略入口

## 模块设计
- `app/cli`：命令行入口，负责单次模式、REPL、slash 命令、session 恢复、trace 展示
- `app/graph`：状态定义、节点实现、图构建与路由
- `app/tools`：工具注册表、工具执行、确认策略判定
- `app/storage`：SQLite、向量索引、文件读写
- `app/retrieval`：文本切分、embedding、检索与 metadata 过滤
- `app/observability`：trace 和运行日志
- `app/services`：高层应用服务封装与 session 生命周期管理
- `app/settings.py`：运行配置加载与路径解析

## 数据模型
- Notes：`id`、`title`、`content`、`created_at`、`updated_at`
- Reminders：`id`、`content`、`status`、`due_at`、`created_at`、`updated_at`
- Preferences：`key`、`value`、`updated_at`
- Files：`id`、`original_path`、`stored_path`、`source_name`、`extension`、`media_type`、`checksum`、`chunk_count`、`created_at`
- File Chunks：`id`、`file_id`、`chunk_index`、`source_path`、`source_name`、`extension`、`media_type`、`text`、`created_at`
- Sessions：`id`、`title`、`status`、`awaiting_confirmation`、`pending_action`、`show_trace`、`created_at`、`updated_at`
- Session Messages：`id`、`session_id`、`turn_index`、`role`、`content`、`created_at`
- Session Snapshots：`session_id`、`preview`、`message_count`、`updated_at`

## LangGraph 主图
- `detect_intent`：仅负责解析用户输入
- `plan_execution`：根据 intent、tool、确认策略决定执行目标
- `confirmation_node`：处理 destructive 操作确认和确认回复
- `tool_node`：执行 `note`、`remind`、`preference`、`file_ingest`
- `retrieval_node`：执行 `retrieval`
- `respond_node`：汇总结果并生成用户输出

## State 原则
关键 state 字段：
- `request_id`
- `session_id`
- `user_input`
- `intent`
- `messages`
- `selected_tool`
- `tool_args`
- `retrieval_needed`
- `requires_confirmation`
- `route_target`
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
- 路由由 graph planning 层控制
- 输入解析与执行规划拆开，避免 `detect_intent` 同时做太多事
- 存储实现与工具调用解耦
- destructive 确认优先在 graph state 中表达，不放在 CLI 层硬编码执行逻辑
- retrieval 先做“向量召回 + 本地 metadata 过滤”的最小实现
- session 持久化暂由 `PersonalAgent + SessionStore` 管理，不直接侵入 graph 节点

## CLI 会话原则
- 单次模式与交互模式共用同一个 `PersonalAgent.invoke(...)` 接口
- 非持久化会话仍保留在当前终端内存
- 持久化会话通过 `--persist-session`、`--session-id` 和 `/session ...` 命令管理
- slash 命令只在 CLI 层处理，不进入 graph

## 调试原则
- 每次请求记录 `request_id`
- session 场景下额外记录 `session_id`
- 节点执行路径进入 trace
- 工具调用、确认节点状态和错误上下文写入 trace 日志
