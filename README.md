# LangGraph Personal Agent

基于 LangGraph 的个人知识与任务管理 agent 骨架。当前已经完成阶段 0、最小阶段 1，以及阶段 2 的前两轮增强：交互式 CLI、destructive 确认节点、retrieval metadata/filter、文件清单命令和可配置确认策略。

## 当前能力
- 笔记管理：新增、列表、搜索、更新、删除
- 提醒管理：新增、列表、完成、取消
- 偏好管理：设置、读取、列表
- 文件管理：导入、列表、详情
- 知识检索：支持基础向量召回和 metadata/filter
- 调试追踪：记录 graph 节点路径、工具调用和错误上下文
- 交互式 CLI：支持 REPL、slash 命令和确认流

## 技术栈
- Python 3.13
- LangGraph
- SQLite
- Milvus Lite 兼容封装
- 文件系统

## 快速开始
1. 安装依赖
```powershell
py -3 -m pip install -e .
```

2. 单次运行
```powershell
py -3 run.py "note add LangGraph::先搭好状态图和工具边界"
py -3 run.py "note list"
py -3 run.py "file ingest C:\path\to\document.pdf"
py -3 run.py "file list"
py -3 run.py "file show 1"
py -3 run.py "retrieve LangGraph | filter:extension=.pdf"
```

3. 交互式运行
```powershell
py -3 run.py --interactive
```

4. 运行测试
```powershell
py -3 -m unittest discover -s tests -v
```

## VS Code
1. 在 VS Code 打开工作区根目录。
2. 运行任务 `Bootstrap Environment`。
3. 如需环境变量，复制 `.env.example` 为 `.env`。
4. 然后直接使用：
- Launch: `Run Personal Agent`
- Launch: `Run Unit Tests`
- Task: `Run Agent`
- Task: `Run Tests`

## 配置文件
- 默认运行配置位于 `configs/settings.toml`
- 示例配置位于 `configs/settings.example.toml`
- 当前支持的确认策略配置：

```toml
[confirmation]
destructive_actions = [
  "note.delete",
  "remind.cancel",
]
```

如果你希望 `note update` 也走确认，只需要把它加进去：

```toml
[confirmation]
destructive_actions = [
  "note.delete",
  "note.update",
  "remind.cancel",
]
```

## 命令参考
- `note add <title>::<content>`
- `note list`
- `note search <query>`
- `note update <id> <title>::<content>`
- `note delete <id>`
- `remind add <content> [| due:YYYY-MM-DD HH:MM]`
- `remind list`
- `remind done <id>`
- `remind cancel <id>`
- `preference set <key>=<value>`
- `preference get <key>`
- `preference list`
- `file ingest <path>`
- `file list`
- `file show <id>`
- `retrieve <query>`
- `retrieve <query> | filter:file_id=<id>,extension=<ext>,media_type=<type>,source_name=<name>`

## 交互式 CLI
可用 slash 命令：
- `/help`
- `/trace on`
- `/trace off`
- `/clear`
- `/exit`

确认回复：
- 确认：`yes`、`y`、`confirm`、`是`、`确认`
- 取消：`no`、`n`、`cancel`、`否`、`取消`

## 当前限制
- 当前仍是规则驱动的 intent 解析，不依赖 LLM
- 当前 embedding 仍以本地可运行为优先，不追求最终检索质量
- 若 `milvus-lite` 当前环境不可安装，系统会自动回退到本地文件向量索引
- 交互式 CLI 的消息历史只保留在当前终端进程，退出后不恢复

## 版本日志
- 所有版本更新记录位于 `logs/`
- 每次有效更新新增一个 `txt` 文件
- 可用 `scripts/new_update_log.ps1` 快速生成模板
