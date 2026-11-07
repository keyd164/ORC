# 架构与实现约定 · V1.2

2026-10-27 上传完整性维护：入库前验证图片结构并完整解码，按真实格式保存标准后缀，原始字节不转码。历史.img仍由内容检测返回正确MIME和inline文件名。缩略图生成错误和损坏文件有明确错误，原件与查看副本分离；修复不修改历史账单与OCR记录。

## 0.3.0 全栈与只读分析

小程序保持首页双入口，新增第10页 agent；可选网页迁移 Vue 3 + TypeScript 严格检查。两端共用分析接口。

LangGraph 流程：规划 → 逐个 LangChain StructuredTool → 证据回答。默认 rules 规划器只解析支持的意图与日期；可选 ChatOllama 通过结构化 Plan 规划。SQLAlchemy 固定查询计算金额/数量，业务连接强制 query_only。旧账单写入与复核仍使用原 sqlite3 事务层，不宣称全量 ORM 迁移。

节点状态 JSON 保存到 agent_runs，参数/结果/耗时/错误保存到 agent_steps。采用应用层节点持久化，不是 LangGraph SqliteSaver。失败后重建图并从 next_tool 继续；旧结果保留 observed_at，数据改变后重新提问刷新。没有自动改账或审批后写入能力。

文档工具仅关键词检索 business-rules.md，不宣称向量RAG。模型仅本机本地权重，关闭托管追踪；结果来源可跳转详情或查看规则，报告由用户下载。Docker/Compose、GitHub Actions 已配置，实际运行分别记录。

参考：[LangGraph 持久化](https://reference.langchain.com/python/langgraph/checkpoints)、[SQLAlchemy SELECT](https://docs.sqlalchemy.org/en/20/core/selectable.html)、[Ollama 结构化输出](https://ollama.com/blog/structured-outputs)。

## 原业务链路（继续沿用）

生效方案见 `plan-current.md`。最终日常操作端为微信原生小程序：首页双入口，采集与数据管理；Vue 工作台保留为可选辅助工具。小程序直接请求 FastAPI，不嵌入网页、不要求运行 Vite。Python OCR 与 SQLite 仍在电脑运行。

## 数据流

OCR 专项评测与业务识别共用 services/ocr_engine.py 的模型配置及输出适配；benchmark_ocr.py 在独立目录直接调用，不创建上传、账单或数据库记录。原图/预处理比较、重复计时和人工标签计分由独立评测服务完成，详见 ocr-testing.md。各评测运行保留独立输出目录。

日期批次 → 图片验证/SHA-256 → 原图和缩略图 → 单 OCR 线程 → EXIF/保守透视/温和增强 → PaddleOCR → 不可覆盖的 OCR 历史 → 标签字段提取和校验 → 人工修正/复核 → 正式统计及导出。

图片接口返回真实图像 MIME。上传记录分页，每页 50 张；图片详情直接返回关联 bill_id，不再在手机上遍历全部账单找详情。

## 小程序

10 个原生页面：首页、上传、记录、管理、账单列表、详情、异常、统计、设置、业务分析。公用 utils/api.js 处理地址持久化、请求错误、上传、下载；utils/ui.js 处理状态中文、元/分展示、日期、操作锁和确认。

逐张上传失败后继续，重试跳过成功与同图重复记录。排队列表/详情仅可见时每 5 秒刷新；隐藏/卸载停止，未保存表单不刷新。中文字段表单只提交显式修改；清空写 null。复核明确确认字段和异常。重复关系可确认、查看原始记录、撤销并记录日志。

统计使用原生条形视图展示趋势与分布，不引入图表运行时 npm 包。Excel 由平台文档接口打开，CSV/ZIP 下载到小程序本地后由用户选择处理；不自动向他人发消息。备份从小程序触发后端，恢复仍为电脑离线操作。

## 后端和数据一致性

集中路由 app/main.py、数据层 app/db.py、业务服务 app/services/。进程内事务锁保护数据写入和备份快照；仅单进程、单模型线程。启动恢复 queued/processing。OCR 失败保留原图/错误历史，不虚构业务值。人工值及空值不被重识别覆盖。

重复关系表 duplicate_links 与旧数据表兼容初始化；处理后原始账单仍必须符合已复核、已结条件才入账。未解决同编号争议暂停统计；已排除重复不再占待办数量。

当前没有商业权限体系，不部署到公网。模型只下载公开权重，不上传票据。真实图片字段空间排序和局部二次 OCR 待标注样本调优。微信实际 AppID/开发者工具/真机验收独立记录，不将本地编译当作微信发布成功。

参考：[PaddleOCR 官方接口](https://www.paddleocr.ai/v3.0.0/en/version3.x/pipeline_usage/OCR.html)、[微信官方测试工具仓库](https://github.com/wechat-miniprogram/miniprogram-simulate)、[文件下载接口](https://developers.weixin.qq.com/miniprogram/dev/api/network/download/wx.downloadFile.html)。
