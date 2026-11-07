# 0.3.0 验证记录

2026-10-26，生效方案V1.2。

- 后端22项 pytest通过（原14 + 新增8）。验证金额口径、来源、数据库只读、失败续跑与重启恢复。
- 小程序8项模拟API流程通过，10页WXML/WXSS及JS/JSON检查通过。
- 网页 TypeScript 严格检查及Vite构建通过。TypeScript选5.9系列以兼容当前vue-tsc；不将最新依赖安装成功等同于兼容。
- 规则路由固定评测10/10，不代表LLM或真实票据任务成功率。
- Python依赖检查通过，完整版本见requirements-lock.txt。LangChain1.4.7、LangGraph1.2.17、SQLAlchemy2.1.6。
- 用户路线原文已归档，V1.0/V1.1原方案保留。
- 新版后端实际 HTTP 验证：“统计本月实收合计并找出异常账单”在 rules 模式 completed，4个执行步骤、2个工具结果；报告下载HTTP200。记录留在本机分析历史中，不修改账单。
- 两类源码交付：dist/ktv-miniapp-v0.3.0.zip 供开发者工具导入，dist/ktv-fullstack-v0.3.0.zip 包含后端、两端、测试与文档。均不含真实业务数据、虚拟环境、node_modules或私有配置。

未验证/未完成：真实Ollama模型规划（本机未运行或配置）、向量RAG、Agent写操作审批、全量ORM迁移、认证权限、Docker实际构建运行、GitHub远端CI/发布、微信真机、真实票据准确率。配置文件存在不代表已部署。
