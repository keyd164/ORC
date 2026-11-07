# 数据模型 · V1.2

2026-10-27 原图后缀修复：新 images.stored_path 使用内容格式对应的.png/.jpg/.webp；历史.img路径保持不变，读取根据文件内容适配。无结构迁移，不改账单、原图字节或哈希。data/diagnostics仅存检查报告和查看副本，不登记为新上传，也不作为权威原图备份来源。

## 0.3.0 新增分析表

原七张业务表保留，新增两表，启动时幂等建表，纳入 app.db 完整备份。

| 表 | 字段与用途 |
|---|---|
| agent_runs | id、question、mode、status、state_json、created_at、updated_at、error_message；存储计划、工具结果、下一个工具索引及回答 |
| agent_steps | id、run_id、node、tool、args_json、result_json、status、error_message、elapsed_ms、created_at；工具调用及错误证据 |

启动将遗留 running 标为 interrupted，允许用户重试未完成工具。结果包含 observed_at，续跑可能结合不同时间快照，数据更新后应重新提问。存储使用 JSON，不使用 pickle。

SQLAlchemy 2.x 目前只用于新增受限查询层；原有业务事务不整体重写。query_only 限制业务查询连接，分析记录通过独立事务写入，并非 app.db 全局禁止写入。

## 原业务表（继续沿用）

当前数据库：`data/app.db`，保留原方案六表，V1.1 新增 duplicate_links，不删除现有数据。

| 表 | 职责 |
|---|---|
| upload_batches | 归档日期、数量、批次状态 |
| images | UUID、批次、归档日期、原图及处理图相对路径、哈希、识别状态、错误 |
| ocr_runs | 每次识别新增一条；引擎版本、原始文字、JSON、开始结束时间、错误 |
| bills | 当前有效字段、复核状态、重复状态、校验提示 |
| bill_field_values | 自动值、人工值、置信度、对应 OCR、字段确认状态 |
| duplicate_links | bill_id 唯一关联 canonical_bill_id，附创建时间，保留人工重复关系 |
| field_edit_logs | 字段前后值与复核操作、时间、原因 |

金额字段全部 INTEGER，单位分；API 账单读取为分、修改为元。所有可识别字段支持 NULL；人工传 null 保存 JSON `null` 和 invalid 状态，避免回退自动结果。人工修正与日志在同一事务提交。

相同账单编号未处理时标为 suspected，统计排除；人工指定原始账单后，重复照片记为 excluded，保留的记录无其他争议时恢复 none。禁止自关联、跨编号关联、循环和关联链。撤销恢复 suspected，修改编号失配时自动移除关联。确认/撤销与日志在同一事务中提交，不删除记录。相同日期同哈希重复上传直接返回已有图片 ID，初版不额外创建重复图片副本。

索引包括归档日期、哈希、图片状态、OCR 图片编号、账单编号、票面日期、房间与复核状态。图片与账单关联以 UUID 完成，账单编号不能作为图片主键。首版使用初始化建表与字段补齐，未来破坏性结构升级需单独增加迁移并先备份。

V1.1 升级：后端启动 init() 幂等创建 duplicate_links，旧备份恢复后同样自动补建；数据库和完整备份自动包含该表。
