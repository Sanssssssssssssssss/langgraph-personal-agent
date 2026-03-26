# STATE

## 当前状态
项目已完成阶段 0 骨架、最小阶段 1 闭环，以及阶段 2 的一组基础能力：交互式 CLI、destructive 确认、retrieval metadata/filter、文件清单命令、配置化确认策略、会话历史持久化草案、graph planning 职责拆分。当前环境下向量层继续使用 `MilvusLiteStore` 兼容封装，在 `milvus-lite` 不可安装时自动回退到本地文件向量索引。

## 下一步
1. 设计 session 摘要压缩和历史裁剪方案
2. 继续推进 graph execution 层职责拆分
3. 增加更复杂的 retrieval filter 语法和 metadata 策略
4. 评估 metadata filter 下的召回-过滤顺序优化
5. 规划 FastAPI 接入层

## 风险
- 范围膨胀
- 状态图后续复杂化
- 当前规则路由对自然语言输入覆盖有限
- 当前 embedding 仅用于骨架验证，检索质量有限
- 当前 session 持久化第一版还没有摘要压缩，历史很长时会变重
- 当前环境对 `milvus-lite` 分发不友好，需要兼容封装维持开发节奏

## 接班说明
新一轮开始时，先阅读 `PROJECT_BRIEF.md`、`REQUIREMENTS.md`、`ARCHITECTURE.md`、`DECISIONS.md`、`TASKS.md`、`STATE.md`，再查看 `README.md`、`logs/` 和阶段学习记录。
