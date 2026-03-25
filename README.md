# LangGraph Personal Agent

基于 LangGraph 的个人知识与任务管理 agent 骨架。当前版本聚焦阶段 0 和最小阶段 1：把目录、状态、工具边界、存储边界、CLI、最小 graph、SQLite、Milvus Lite 和基础调试链路先跑通。

## 当前能力
- 笔记管理：新增、列表、搜索、更新、删除
- 提醒管理：新增、列表、完成、取消
- 偏好管理：设置、读取、列表
- 文件导入：支持 `txt`、`md`、`pdf`
- 知识检索：基于 Milvus Lite 的基础向量召回
- 调试追踪：记录节点路径、工具调用、错误上下文

## 技术选型
- Python 3.13
- LangGraph
- SQLite
- Milvus Lite
- 文件系统

## 快速开始
1. 安装依赖
```powershell
py -3 -m pip install -e .
```

2. 运行 CLI
```powershell
py -3 run.py "note add LangGraph::先搭好状态图和工具边界"
py -3 run.py "note list"
py -3 run.py "remind add 明天下午复盘架构"
py -3 run.py "preference set language=zh-CN"
py -3 run.py "file ingest C:\path\to\document.pdf"
py -3 run.py "retrieve LangGraph 的核心编排层负责什么"
```

3. 查看追踪输出
```powershell
py -3 run.py "note list" --show-trace
```

4. 运行测试
```powershell
py -3 -m unittest discover -s tests -v
```

## 目录
- `app/cli`：命令行入口
- `app/graph`：LangGraph 状态、节点、builder
- `app/tools`：工具注册表和工具实现
- `app/storage`：SQLite、Milvus Lite、文件存储
- `app/retrieval`：切分与 embedding
- `app/observability`：trace 日志
- `data/`：上传文件、数据库、trace 等运行期数据
- `docs/learning`：阶段学习记录

## 第一版命令约定
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
- `retrieve <query>`

## 当前限制
- 当前是规则驱动的 intent 解析，不依赖 LLM。
- 当前检索使用本地哈希 embedding，重点是把存储与流程骨架跑通。
- 当前环境下若 `milvus-lite` 不可安装，系统会自动降级到本地文件向量索引，接口保持不变。
- 当前仅提供单次 CLI 调用，后续再扩展 API/Web UI。
