# TASKS

## Todo
- 引入真实 embedding 模型替换哈希 embedding
- 设计 FastAPI 接入层
- 扩展 destructive 确认策略到可配置层
- 评估会话历史持久化方案
- 增加更复杂的 retrieval filter 语法和 metadata 策略
- 评估 metadata filter 下的召回-过滤顺序优化

## In Progress
- 无

## Done
- 读取 PDF 并确认阶段规划、目录建议、推荐开发顺序
- 初始化 Git 仓库
- 创建 GitHub 公开仓库并完成首推
- 创建长期记忆文件
- 建立阶段 0 目录骨架
- 定义初版 state schema、图结构和模块边界
- 实现最小 CLI + LangGraph 闭环
- 接入 SQLite、文件系统和兼容向量索引
- 跑通 file ingest 与 retrieval
- 增加基础 trace 与测试
- 通过 5 个基础测试场景
- 增加 VS Code 本地运行配置
- 增加 logs 版本更新记录机制
- 补充初始化版本记录和当前更新记录
- 验证 VS Code 对应的 `.venv`、bootstrap 脚本和测试运行
- 增加交互式 CLI 会话模式
- 为高风险写操作加入 graph 级确认节点
- 通过阶段 2 第一刀的确认流与 REPL 测试
- 增加 retrieval metadata/filter 最小能力
- 通过 file_id / extension / media_type 过滤检索测试

## Blocked
- 无
