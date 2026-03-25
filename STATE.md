# STATE

## 当前状态
项目已完成阶段 0 骨架和最小阶段 1 闭环首版实现，并已通过基础测试、真实 PDF 导入验证以及 GitHub 首次推送。当前环境下向量层采用 `MilvusLiteStore` 兼容封装，在 `milvus-lite` 不可安装时自动回退到本地文件向量索引。

## 下一步
1. 增加交互式 CLI 会话模式
2. 为高风险写操作加入确认节点
3. 为 retrieval 增加 metadata/filter 能力
4. 评估引入真实 embedding 模型替换哈希 embedding

## 风险
- 范围膨胀
- 状态图后续复杂化
- 当前规则路由对自然语言输入覆盖有限
- 当前 embedding 仅用于骨架验证，检索质量有限
- 当前环境对 `milvus-lite` 分发不友好，需要兼容封装维持开发节奏

## 接班说明
新一轮开始时，先阅读 `PROJECT_BRIEF.md`、`REQUIREMENTS.md`、`ARCHITECTURE.md`、`DECISIONS.md`、`TASKS.md`、`STATE.md`，再查看 `README.md` 和阶段学习记录。
