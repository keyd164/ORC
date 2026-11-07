# 两张账单如何测试 OCR

## 1. 图片放哪里

将两张原始图片复制到 `E:\KTV-ORC\data\ocr-evaluation\images\`。目录已创建，支持 JPG/JPEG、PNG、WebP。可以保留原文件名，也可以改为 `bill_a.jpg`、`bill_b.jpg`，文件扩展名要和实际文件一致。

```text
data/ocr-evaluation/
├── images/                     放你自己的两张原图
│   ├── bill_a.jpg              示例文件名，实际文件名可以不同
│   └── bill_b.jpg
├── expected.json               由你核对原图填写的标准答案，可先不提供
└── results/
    └── run_日期_时间_微秒/       每次评测单独建目录，不覆盖之前结果
        ├── report.json         配置、耗时、内存、准确率和逐张结果
        ├── timings.csv         可用 Excel 打开的逐次耗时表，UTF-8 BOM
        ├── manual-review.json  机器提取结果供你对照，不是标准答案
        ├── *.ocr.json          PaddleOCR 原始文本、框和置信度
        └── *.png               本次处理图及可选预热图
```

评测不依赖后端服务，不创建上传批次、不写 `data/app.db`、不把测试账单计入营业额、不修改原图。所有图片、人工答案和结果在被 Git 排除的 `data/` 内。不要把真实图片放到 `backend/tests/` 或公开仓库。

## 2. 先看两张图能识别成什么

放好图片后，双击 `scripts/test_ocr.bat`。或者在项目根目录打开 PowerShell：

```powershell
cd E:\KTV-ORC
.venv\Scripts\python scripts/benchmark_ocr.py
```

默认加载正式业务使用的同一套 PaddleOCR 配置，先预热一次，再按顺序处理每张图片一次。打开窗口打印的本次 `report.json`：

- `records[].raw_text`：OCR 文字。
- `records[].values`：提取出的账单字段，金额单位是**分**。
- `records[].confidence`：字段置信度；它不等于准确率。
- `records[].issues`：缺失、金额、时间和低置信度提示。
- `*.png`：核对预处理有没有误裁剪、扭曲或损伤浅色文字。

没有人工答案时，准确率为 `null`，不是 0，也不会把 OCR 自己输出的值当作正确答案。

首次缺少模型会下载公开权重，原始票据始终本地处理。若提示依赖缺失，按 README 安装 `backend/requirements-ocr.txt`。脚本对输入执行与上传一致的格式、15MB和四千万像素限制。

## 3. 建立人工标准答案，才可以评价准确率

先按当前文件名生成空标注模板：

```powershell
.venv\Scripts\python scripts/benchmark_ocr.py --init-labels
```

该命令不加载模型，只生成 `data/ocr-evaluation/expected.json`，已有文件不会覆盖。每张图先是空对象，表示尚未标注。打开后**对照原图人工填写**。以下仅展示格式，数值和编号都要替换为实际原图内容：

```json
{
  "samples": {
    "bill_a.jpg": {
      "bill_no": "原图上的账单编号",
      "room_name": "V11",
      "received_amount": "80.00"
    },
    "bill_b.jpg": {
      "bill_no": "第二张原图上的账单编号",
      "room_name": "V15",
      "received_amount": "20.00"
    }
  }
}
```

注意：

- `samples` 中的文件名必须与图片一致；子目录图片写 `子目录/文件名.jpg`。
- 人工答案金额用**元**，推荐写字符串 `"80.00"`；脚本转换为整数分比较。机器输出的 `8000` 分不能直接粘到这里当作 `8000` 元。
- 没有标注的字段不进入准确率分母。确认原图应为空时写 `null`；看不清而尚未确定时先不写该字段。
- 不要把 `manual-review.json` 或 OCR 原文直接复制成标准答案，这会造成自我验证。

重新运行评测即可得到逐字段对错。日期格式 `YYYY-MM-DD`，完整时间 `YYYY-MM-DD HH:mm:ss`，时长为整数分钟。不要用上传归档日期代替票面日期。

| 常用字段 | 含义 |
|---|---|
| bill_no / bill_date / room_name | 账单编号 / 票面日期 / 房间 |
| open_time / close_time | 开房 / 关房完整时间 |
| duration_minutes | 消费分钟数 |
| total_amount / receivable_amount / received_amount | 消费合计 / 应收 / 实收，标注单位元 |
| bill_status | 票面结算状态，例如“已结” |

这10个核心字段全部人工标注的图片才进入 `core_exact_match_rate` 分母；只标3个字段时可以算这3项准确率，但不宣称核心字段全匹配率。

## 4. 测速度、稳定性与预处理效果

两张图片各重复5次，对比原图与预处理：

```powershell
.venv\Scripts\python scripts/benchmark_ocr.py --repeat 5 --variant both
```

该命令共进行 `2张 × 5次 × 2种方式 = 20次` 正式识别，外加一次不计入统计的预热；只加载一个模型、串行运行。准确率每种方式只取每张图的第一次正式结果，所以仍只有2个图片样本，不会伪装成20张独立样本。

`report.json` 中的重要指标：

| 指标 | 解释 |
|---|---|
| model_load_seconds | 导入并创建模型的耗时；首次下载也可能计入，不是每张图的识别耗时 |
| preprocess_seconds / ocr_seconds / extract_seconds | 每次预处理 / 模型预测 / 字段提取校验耗时 |
| total_seconds | 图片验证到字段提取的同步耗时，不含网络、队列、数据库和结果JSON写入 |
| mean_seconds / median_seconds | 成功识别尝试的平均 / 中位耗时 |
| p95_seconds_nearest_rank | 成功尝试耗时的最近秩P95；样本少时通常接近最大值 |
| completed_images_per_minute | 成功次数除以所有正式尝试累计耗时，换算每分钟数量；不是并发或整套服务吞吐 |
| completion_rate | 正式尝试完成比例；返回了文字并不代表字段正确 |
| rss_baseline_mb / rss_sampled_peak_mb | 本评测进程的RSS起始值和每50ms采样峰值；包含模型和本次运行内存，不含子进程/显存，不是操作系统严格峰值 |
| field_accuracy / per_field | 所有已人工标注字段的准确率 / 每个字段准确率，显示真实分母 |
| core_exact_match_rate | 10个核心字段全部匹配的图片比例，仅计算完整标注图片 |

性能比较应使用同一台电脑、模型版本、线程配置、相同图片及分辨率，尽量停止其他OCR任务；不要把首次模型下载当作稳定速度。两种方式按原图、预处理顺序运行，小样本可能受缓存影响，不能据此给出严谨的速度优势结论。

若想看不预热的第一张预测，可加 `--warmup 0`；这仍不是严格“无磁盘模型缓存”的冷启动测试。测试连续20张不同真实票据的稳定性，需要真正准备20张图；将两张重复10次只能说明重复负载表现。

## 5. 只有两张图，怎么判断效果

先核对两张的账单编号、房间、实收和时间是否与人工读取一致，比较原图和预处理图的错误，保存失败原因。两张图足够验证基本链路和发现问题，不足以证明方案中的95%/90%准确率目标，也不足以估计可靠的P95。

后续准备50–100张人工标注的独立票据，覆盖阴影、倾斜、透视、遮挡、浅字、不同金额和房间，调规则用的图片与最终验收图片分开。只有完成独立测试，才记录真实OCR准确率。
