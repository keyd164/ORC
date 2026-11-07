# 0.2.0 验证记录

日期：2026-10-25。生效方案：V1.1。验证环境：本机 Windows、Python 3.12、Node.js 24。

| 验证 | 命令或方法 | 结果 |
|---|---|---|
| 后端业务回归 | `.venv\Scripts\python -m pytest backend/tests -q` | 14 passed |
| 小程序 JS 流程 | `frontend/miniapp-tests` 中 `npm test` | 7 passed，微信 API 模拟 |
| 小程序模板/样式 | 同目录 `npm run compile` | 9 页 WXML/WXSS 通过 wcc/wcsc 编译；JS/JSON 检查通过 |
| 真实本地 OCR 完整后端链路 | `.venv\Scripts\python scripts/smoke_pipeline.py` | 隔离临时目录上传合成票据，经真实 PaddleOCR、字段提取、人工复核接口、正式营业额、CSV/Excel、完整备份校验，全部通过 |
| 运行中的后端 | `/api/v1/health`、`/api/v1/dashboard/distributions` | HTTP 正常，数据库连接正常，新接口可用 |
| 方案原文保留 | V1.0 与用户原始附件 SHA-256 比较 | 一致，原始方案未覆盖 |
| 源码交付包 | `scripts/package_miniapp.py` | 35 个文件，ZIP 完整性通过；不含数据、私有本机配置或测试依赖 |

完整链路测试中，未复核实收为 0，确认后为 8000 分；重复同一图片返回已有记录，备份包含 1 张原图。测试数据位于临时目录并清理，未加入日常营业数据库。

尚未通过实际微信 AppID 下的开发者工具与手机真机验收，也没有真实票据集准确率报告。模拟 API 测试、模板编译以及合成票据链路测试不能替代这些验收。
