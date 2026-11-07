# API 说明 · V1.2

2026-10-27 图片接口维护：上传除结构校验外执行完整解码；损坏/截断图片返回400，写文件和建图片记录前即拒绝。存储后缀根据真实内容选择png/jpg/webp，与原始文件名和客户端MIME无关。GET images/{id}/file 返回真实图像MIME及 inline 文件名，兼容历史.img路径；文件缺失404，文件头无法读取409。原图字节不转码、历史路径不自动重命名。

## 0.3.0 本地分析接口（/api/v1 前缀）

| 方法与路径 | 作用 |
|---|---|
| GET /agent/capabilities | 模式、工具和模型配置状态；not_probed 不表示模型可运行 |
| POST /agent/runs | JSON question（非空、最多1000字）、mode（rules/ollama，默认rules），同步执行并返回持久任务 |
| GET /agent/runs | 最近记录，limit 默认20、最大100 |
| GET /agent/runs/{id} | 计划、结果、回答、来源、步骤和错误 |
| POST /agent/runs/{id}/retry | 仅 failed/interrupted 可续跑，完成任务返回409 |
| GET /agent/runs/{id}/report | 完成任务的 Markdown 报告，否则409 |
| GET /agent/documents/{name} | 仅允许 business-rules.md，不允许任意文件路径 |

分析按归档日期，金额单位分。最多十年日期范围，未知意图/不明确范围失败，不猜测补齐。日期按 Asia/Shanghai。规则模式不调用模型；模型失败不转换成“模型成功”。任务失败返回200/status=failed，空问题或非法模式返回422。小程序分析超时120秒，模型规划超时60秒。

不存在任意 SQL、改账或删除工具。SQLAlchemy 固定查询计算实收、排行、明细与异常，回答返回来源和 observed_at，失败恢复保留已完成工具结果。

## 原业务接口

前缀 `/api/v1`；完整请求类型与 OpenAPI 在运行后 `/docs` 查看。

- GET health / fields：健康检查、可识别字段定义。
- POST batches：JSON `{ "business_date": "2026-10-25" }` 创建批次。
- POST uploads：multipart file、business_date、batch_id；JPEG/PNG/WebP，最多 15MB、四千万像素；同日重复返回 status=duplicate 与原 image_id。
- GET images：可按 business_date 查询；offset>=0，limit 为 1–500，默认 50。GET images/{id} 返回关联 bill_id；GET images/{id}/file 返回实际图像 MIME，后者 `thumbnail=true` 获取缩略图。
- POST images/{id}/recognize：进入单线程队列。GET images/{id}/ocr-runs：不可覆盖的完整历史。
- GET bills：start/end 按票面日期，room、bill_no、review_status、bill_status、min_amount/max_amount（分）筛选。
- GET bills/{id}：字段记录、修改历史、业务异常。
- PATCH bills/{id}/fields：JSON `{ "fields": { "received_amount": "80.00", "cashier": null }, "reason": "核对原图" }`；金额提交单位元，null 是明确空值；禁止修改内部状态字段。
- POST bills/{id}/review：`confirm_all=true` 明确确认未改动识别字段；存在缺失/异常时还需 `acknowledge_issues=true`；疑似重复返回 409。
- POST bills/{id}/duplicate：JSON `{ "canonical_bill_id": "保留的同编号账单 ID" }`；当前记录标为 excluded，保留原记录和日志，禁止自关联、不同编号及关联链。
- DELETE bills/{id}/duplicate：撤销人工重复关系，恢复疑似重复与暂停入账；GET bills/{id} 返回 canonical_bill_id。
- GET dashboard/distributions：start/end 按归档日期，返回 payment_methods、room_types、sample_count，仅统计有效账单。
- GET dashboard/summary：business_date 选择归档日期，正式金额返回分。
- GET dashboard/trend：start/end 归档日期；GET dashboard/rooms 同样支持 start/end，返回账单数、实收分、均单分、消费分钟；dashboard/exceptions 返回未处理异常，已确认排除重复不再列作待办。
- GET exports/bills：与账单相同筛选，format=csv/xlsx；导出金额单位元，CSV 带 BOM，表格公式字符转义。
- POST backups：创建完整包，返回 filename/download_url。GET backups/{filename}：下载。
- POST backups/verify：JSON `{ "filename": "backup_...zip" }`，验证本地备份；恢复仅脚本离线执行。

记录不存在 404，类型不合法 422，图片不支持 400，过大 413，待确认或重复未处理 409。当前无公网鉴权，限定本地练习环境使用。
