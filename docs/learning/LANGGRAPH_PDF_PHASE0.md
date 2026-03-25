# LANGGRAPH PDF Phase 0 学习记录

## 本轮学习重点
- 先跑通，再优化
- 结构先于功能
- 所有能力都可替换
- 从第一天开始考虑调试
- 按阶段交付，不跨阶段扩展

## 对当前实现的直接影响
- 先做 `CLI + 最小 graph + 工具闭环`，不先做复杂 UI
- 把 state、节点、路由显式化，避免把逻辑散落在 if/else
- 提前设计 `SQLite + Milvus Lite + 文件系统` 的边界
- 每次请求记录 trace，便于定位节点流转、工具调用和错误来源
- 保留 `models/`、`services/`、`observability/` 目录，为后续替换留位

## 与 PDF 对齐的开发顺序
1. 定目录、state、图骨架、数据库边界
2. 跑通最小 graph 和最小工具系统
3. 接 SQLite 和 Milvus Lite
4. 跑通文件导入和基础 retrieval
5. 打通 trace、日志和调试链路

## 当前未做
- 复杂状态图拆分
- 自动化评测
- 本地模型服务
- OTel/Prometheus/Grafana
- GraphRAG、多 agent

