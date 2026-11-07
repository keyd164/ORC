# KTV 账单微信小程序

最终操作端为微信原生小程序，首页两个入口：**账单采集**、**数据管理**。日常操作不需要启动网页工作台。

当前生效方案：[V1.2 全栈与本地分析升级](docs/plan-v1.2.md)，未调整部分沿用 [V1.1](docs/plan-v1.1.md) 与 [完整方案 V1.0](docs/plan-v1.0.md)。[进度与验收](docs/progress.md) 如实记录已验证与待验证项。

源码交付分两类：`dist/ktv-miniapp-v0.3.0.zip` 仅用于微信开发者工具导入；`dist/ktv-fullstack-v0.3.0.zip` 包含后端、小程序、网页、测试、脚本和文档。两者都不含真实账单数据或已安装依赖，完整包解压后仍按下方步骤安装环境。

## 本地业务分析（0.3.0 新增）

小程序进入“数据管理 → 本地业务分析 / Agent”；可选网页进入“业务分析”。可以提问：

- “统计本月实收合计”
- “统计本月消费最高的房间，并找出金额异常的账单”
- “查询 2026-10-25 账单明细”
- “营业额口径是什么”

默认选择“规则查询”，无需模型即可调用真实数据库。LangGraph 组织规划、查询、回答流程，LangChain 工具校验参数，SQLAlchemy 执行受限只读查询；金额与数量由数据库计算。结果带来源、执行日志，可下载 Markdown 报告。失败任务可以从已保存工具进度重试。

规则模式是固定意图和日期解析，不是大模型推理；文档使用本地关键词检索，不是向量 RAG。可选 Ollama 模式需要另行在本机安装、下载并运行支持结构化输出的本地模型，再在启动后端前设置：

```powershell
$env:KTV_OLLAMA_MODEL = '你已下载的本地模型名称'
$env:KTV_OLLAMA_URL = 'http://127.0.0.1:11434'
.\scripts\run_backend.bat
```

当前机器未验证真实本地模型，不能把规则模式测试作为大模型成功率。模型地址仅允许本机，拒绝云模型信息，关闭托管追踪；没有任意 SQL、改账或删除工具。账单修改仍在详情人工操作。

环境变量模板在 `.env.example`，当前启动器读取系统环境变量，不会自动加载 `.env`。Docker/Compose 与 GitHub Actions 配置已提供，但实际 Docker 构建、远端 CI、认证权限及公开仓库发布仍待完成；不把配置文件等同于部署成功。

## 项目目录结构与作用

以下结构对应当前项目。第三方依赖、Git 内部文件和缓存内容已折叠；运行时目录会按实际操作生成，不需要手工创建全部文件。

```text
E:\KTV-ORC\
├── README.md                      项目总说明、目录、启动与使用方法
├── AGENTS.md                      后续开发必须遵守的持续约束
├── .gitignore                     排除数据库、图片、依赖、缓存和备份等文件
│
├── docs/                          方案、设计、接口和验收文档
│   ├── plan-current.md            当前生效方案的入口
│   ├── plan-v1.0.md               用户提供的完整原始方案，保留不覆盖
│   ├── plan-v1.1.md               小程序作为最终操作端的修订方案
│   ├── plan-v1.2.md               全栈与只读业务分析升级方案
│   ├── business-rules.md          受限工具检索的业务规则知识
│   ├── evaluation.md              OCR、规则路由和模型评测口径及结果
│   ├── ocr-testing.md             两张图测试、人工标注和OCR性能评测操作
│   ├── verification-v0.3.0.md     新版测试与未验证项
│   ├── references/               用户提供的学习路线原文归档
│   ├── architecture.md            各端如何连接、识别与处理数据
│   ├── database.md                数据表、金额存储、修正和重复关系
│   ├── api.md                     小程序与后端通信的接口说明
│   ├── acceptance-tests.md        测试方法与人工验收清单
│   ├── progress.md                当前已完成、已验证及未验收项
│   ├── verification-v0.2.0.md     0.2.0 版本的验证证据
│   └── CHANGELOG.md               功能调整、方案更新与修复记录
│
├── backend/                       电脑上运行的 Python 后端
│   ├── app/                       后端程序代码
│   │   ├── main.py                服务入口和接口：上传、复核、统计、导出等
│   │   ├── db.py                  数据目录配置、建表、连接和事务管理
│   │   ├── agent/                 本地只读业务分析模块
│   │   │   ├── api.py             提问、历史、重试、来源和报告接口
│   │   │   ├── schemas.py         问题、工具计划和日期范围类型约束
│   │   │   ├── repository.py      SQLAlchemy 受限查询，SQLite 强制只读
│   │   │   ├── tools.py           LangChain 工具与本地关键词文档检索
│   │   │   └── workflow.py        LangGraph、规则/模型规划、状态日志与恢复
│   │   └── services/              OCR 和数据处理服务
│   │       ├── preprocessing.py   图片方向校正、透视处理与温和增强
│   │       ├── ocr_service.py     单线程识别队列、OCR 历史、重复状态维护
│   │       ├── ocr_engine.py      正式识别与专项评测共用的模型配置和输出适配
│   │       ├── ocr_metrics.py     人工答案规范化、逐字段与核心全匹配准确率
│   │       ├── field_extractor.py 标签字段提取、金额转换、业务规则校验
│   │       └── backup_service.py  完整备份、哈希校验与离线恢复
│   ├── config/                    后端业务配置
│   │   └── bill_fields.json       字段代码和票面中文标签的对应关系
│   ├── tests/                     后端自动化测试
│   │   ├── test_system.py         上传、复核、统计、去重、备份等测试
│   │   ├── test_agent.py          分析口径、只读限制、来源和失败恢复测试
│   │   ├── test_ocr_metrics.py    标注元/分、准确率分母、重复和失败计分测试
│   │   └── fixtures/              固定日期的规则路由评测任务
│   ├── Dockerfile                后端本地容器构建配置，尚待实际构建验证
│   ├── requirements.txt           基础后端与测试依赖
│   ├── requirements-ocr.txt       基础依赖加本地 OCR 和图像处理依赖
│   └── requirements-lock.txt      已验证环境的完整依赖版本
│
├── frontend/                      所有操作界面和前端验证工具
│   ├── miniapp/                   最终使用的微信原生小程序；开发者工具导入这里
│   │   ├── README.md              小程序单独导入和使用说明
│   │   ├── app.js                 小程序启动与后端地址读取
│   │   ├── app.json               页面注册、底部导航和全局窗口配置
│   │   ├── app.wxss               所有页面共用的样式
│   │   ├── project.config.json    微信开发者工具的项目配置与 AppID
│   │   ├── sitemap.json           小程序页面索引规则
│   │   ├── utils/                 页面共用的工具函数
│   │   │   ├── api.js             请求、上传、下载与连接地址保存
│   │   │   └── ui.js              状态中文、日期、金额展示和操作确认
│   │   └── pages/                 小程序的 10 个原生页面
│   │       ├── home/              首页：账单采集、数据管理两个入口
│   │       ├── upload/            拍照选图、归档日期、上传进度和失败重试
│   │       ├── records/           上传历史、日期筛选、分页与识别状态刷新
│   │       ├── manage/            数据管理入口和营业概况
│   │       ├── bills/             账单搜索筛选、查看详情与筛选导出
│   │       ├── detail/            原图、字段修正、复核、重复处理和历史
│   │       ├── exceptions/        待复核、字段异常、疑似重复和识别失败
│   │       ├── stats/             趋势、房间消费、支付方式及包厢类型分布
│   │       ├── settings/          后端连接、全部导出、备份校验及下载
│   │       └── agent/             本地分析、来源跳转、步骤日志和报告下载
│   │
│   ├── miniapp-tests/             小程序开发验证；不是微信导入目录
│   │   ├── package.json           流程测试和编译检查的运行命令与依赖
│   │   ├── package-lock.json      验证工具的依赖版本锁定
│   │   ├── flows.test.cjs         模拟微信 API 的页面操作流程测试
│   │   ├── compile.cjs            WXML/WXSS 编译及脚本、配置检查
│   │   └── node_modules/          安装生成的测试工具依赖，不提交 Git
│   │
│   └── dashboard/                 可选 PC 网页辅助工具，小程序不依赖它
│       ├── src/                   网页界面代码
│       │   ├── App.vue            概览、账单、上传、异常及设置界面
│       │   ├── main.ts            TypeScript 网页应用启动入口
│       │   ├── types.ts           账单、图片、统计和分析结果的类型定义
│       │   ├── api/               类型化请求封装 client.ts
│       │   ├── components/        本地分析交互组件 AgentConsole.vue
│       │   └── style.css          网页全局样式
│       ├── tsconfig.json          严格 TypeScript 检查配置
│       ├── index.html             网页入口文件
│       ├── vite.config.js         网页开发服务、接口转发和构建配置
│       ├── package.json           网页依赖与启动、构建命令
│       ├── package-lock.json      网页依赖版本锁定
│       ├── node_modules/          安装生成的网页依赖，不提交 Git
│       └── dist/                  网页构建产物，可重新生成
│           └── assets/            构建后的脚本和样式
│
├── scripts/                       电脑上的启动、维护和验证脚本
│   ├── run_backend.bat            双击启动后端，已运行或失败时给出提示
│   ├── check_backend.py           启动前检查服务健康和 8000 端口占用
│   ├── run_dashboard.bat          启动可选 PC 网页工具
│   ├── init_db.py                 初始化数据库和数据目录
│   ├── backup.py                  在电脑创建并校验完整备份
│   ├── restore.py                 校验备份并按参数执行离线恢复
│   ├── package_miniapp.py         生成小程序包与完整项目源码包
│   ├── evaluate_agent.py          固定日期规则路由评测，不读取真实账单
│   ├── benchmark_ocr.py           真实图片OCR效果、耗时、内存与预处理对比评测
│   ├── test_ocr.bat               放好图片后双击运行OCR专项测试
│   ├── smoke_ocr.py               使用合成票据验证真实本地 OCR 环境
│   └── smoke_pipeline.py          隔离临时数据验证上传至备份完整链路
│
├── data/                          本机运行数据，不提交 Git，需要完整备份
│   ├── app.db                     SQLite：图片记录、账单、OCR、修改和重复关系
│   ├── uploads/                   原始账单图片，按归档日期分子目录保存
│   │   └── YYYY-MM-DD/            某个归档日期的原图；有上传时生成
│   ├── processed/                 OCR 使用的处理图，不覆盖原图
│   ├── thumbnails/                列表展示用的小尺寸缩略图
│   ├── exports/                   预留的导出文件目录；当前接口直接返回文件
│   ├── backups/                   完整备份 ZIP 包
│   ├── ocr-smoke/                 OCR 环境测试生成的合成图片和识别结果
│   ├── diagnostics/               原图完整性检查报告与独立查看副本，不入营业库
│   └── ocr-evaluation/            独立的OCR评测数据，不进入营业数据库
│       ├── images/               放自己的真实测试原图
│       ├── expected.json         按原图人工填写的标准答案，使用时生成
│       └── results/              每次运行独立的结果、耗时CSV和处理图
│
├── dist/                          项目交付包，与网页的 dist 目录不同
│   ├── ktv-miniapp-v0.2.0.zip      保留的旧版小程序源码包
│   ├── ktv-miniapp-v0.3.0.zip      新版小程序源码包，不含后端和业务数据
│   └── ktv-fullstack-v0.3.0.zip    完整源码包，含后端/两端/测试/文档，不含业务数据
├── .github/workflows/             GitHub Actions 自动化检查配置
├── compose.yaml                   本地后端容器与数据卷配置
├── .dockerignore                  构建时排除真实数据、依赖及私有配置
├── .env.example                   本地环境变量说明模板，不含真实密钥
├── .venv/                         本机 Python 虚拟环境，可按依赖清单重新安装
│   ├── Scripts/                   本项目 python.exe 等运行命令
│   ├── Lib/                       已安装的 Python 第三方库
│   └── Include/                   虚拟环境使用的头文件目录
├── .pytest_cache/                 测试工具自动生成的缓存
└── .git/                          Git 版本管理内部数据，不手动修改
```

### 小程序每个页面里的文件是什么

`pages/` 下每个页面目录通常都有以下文件，本项目的页面共用 `app.wxss`，因此目前没有单独的 `index.wxss`：

| 文件 | 作用 |
|---|---|
| `index.js` | 页面数据和操作逻辑，例如点击上传、保存修正、刷新列表 |
| `index.wxml` | 页面显示内容和结构，例如输入框、按钮、账单列表 |
| `index.json` | 页面配置，例如标题、是否允许下拉刷新 |
| `index.wxss`（按需添加） | 只影响该页面的样式；不添加时使用全局样式 |

### 日常操作主要找哪里

| 目的 | 对应位置 |
|---|---|
| 打开小程序 | 微信开发者工具导入 `frontend/miniapp/` |
| 启动电脑后端 | 双击 `scripts/run_backend.bat` |
| 修改小程序界面 | `frontend/miniapp/pages/`，共用样式在 `app.wxss` |
| 调整票面字段标签 | `backend/config/bill_fields.json` |
| 调整字段提取和校验 | `backend/app/services/field_extractor.py` |
| 查看真实账单和原图存储 | `data/app.db`、`data/uploads/`；正常通过小程序查看和修改 |
| 查看当前方案和剩余工作 | `docs/plan-current.md`、`docs/progress.md` |
| 获取小程序源码包 | `dist/ktv-miniapp-v0.3.0.zip` |

`__pycache__/` 也可能出现在 Python 代码目录下，是自动生成的运行缓存，不是业务数据。OCR 模型缓存通常保存在用户目录的 `.paddlex/official_models/`，不在项目的 `data/` 中。依赖、缓存和构建包可重新生成；`data/` 中的数据库与账单图片是需要保留的实际数据。完整恢复请使用备份流程，不直接手工编辑数据库或改动图片文件。

## 开始使用

### 测试你自己的两张 OCR 图片

把原图放入 `E:\KTV-ORC\data\ocr-evaluation\images\`（目录已创建），然后双击 `scripts/test_ocr.bat`。报告保存在 `data/ocr-evaluation/results/run_.../`，不写入营业数据库。字段准确率需要对照原图填写人工答案，未标注时不计算准确率。

重复性能和预处理对比：`.venv\Scripts\python scripts/benchmark_ocr.py --repeat 5 --variant both`。图片位置、标准答案格式、准确率、平均/P95耗时、内存及测试限制见 [OCR 测试说明](docs/ocr-testing.md)。

### 使用小程序

1. 在电脑双击 `scripts/run_backend.bat`。电脑运行 OCR、保存图片和数据库，需要保持开机。后端健康检查：`http://127.0.0.1:8000/api/v1/health`。
2. 在微信开发者工具中**导入 `frontend/miniapp` 目录**。当前配置为游客 AppID，实际微信预览/真机调试使用你自己的小程序 AppID 与开发者账号。项目无运行时 npm 依赖，不需要“构建 npm”。
3. 在小程序底部“设置”中输入电脑后端地址并测试连接。电脑模拟器可填 `http://127.0.0.1:8000`；手机填写电脑实际网络 IP，例如 `http://192.168.1.10:8000`（仅示例）。手机与电脑需可互访，并允许后端端口访问。
4. 开发调试时按微信开发者工具要求配置本地网络请求校验；`project.config.json` 已设置开发用 `urlCheck: false`。这不代表正式发布已满足平台网络要求，也不能保证所有真机环境均允许 HTTP。
5. 首页“账单采集”选择日期和图片、上传；“上传记录”自动刷新排队任务；点击进入详情核对。
6. 首页“数据管理”提供账单查询、复核、异常处理、重复确认、营业趋势、房间统计和分布图；“设置”提供导出和完整备份。

### 双击启动脚本后看起来没有反应

后端是服务程序，启动后不会自动打开网页或微信。新版启动脚本会显示运行地址并保留窗口：已运行时提示无需重复启动，端口占用或环境缺失时显示原因，启动失败时保留错误信息。可以打开健康检查地址确认，返回 `status: ok` 和 `database: ok` 即表示后端正常。

### 上传原图显示“损坏”或无法直接打开

早期版本将原图统一命名为 `.img`，即使内容是完整 PNG/JPEG，也可能无法被桌面看图工具正确识别。新版本按真实文件头保存 `.png`、`.jpg` 或 `.webp`，不按上传文件名猜格式，不重编码原图；上传时同时检查文件结构和完整像素解码。

旧 `.img` 原图和数据库关联继续保留，通过小程序或 `/api/v1/images/{图片ID}/file` 访问会返回真实图像 MIME 与正确后缀文件名。不要直接改名数据库所指向的原件；如需桌面打开，可在其他目录复制一份并根据检测到的真实格式使用后缀。当前问题的本地检查报告和 PNG 副本在 `data/diagnostics/`，副本不作为新的营业图片入库。

首次 OCR 下载公开模型，之后复用电脑本地缓存。原始账单不发送给外部 OCR 服务。微信相机/相册等功能的实际账号隐私声明与权限按开发者工具和微信平台提示完成配置。

## 核对与统计规则

- 归档日期和票面日期分别保存；统计按归档日期，账单列表日期筛选按票面日期。
- 手机表单金额单位元，后端读取/统计为整数分。无法辨认的字段可“确认空值”后保存，不猜填。
- 仅保存修改过的字段。刷新与自动轮询不会覆盖未保存修正；平台支持时离开未保存表单会提示。
- OCR 历史和原图保留。重新识别只更新未确认字段，不覆盖人工值和明确空值。
- 营业额仅包含已结、已复核、无重复争议账单。相同日期和文件哈希直接返回原图片，不重复存储。
- 不同照片同编号首先全部暂停入账；在详情指定保留的原始账单，当前照片记为重复排除。支持撤销，撤销后重新暂停同编号记录入账。均有日志。
- 样本量明确显示；识别完成率不能当作识别准确率。

## 导出、备份和恢复

小程序账单页按当前筛选导出 CSV/Excel；设置页可导出全部 Excel/CSV。Excel 可预览并由用户选择保存；CSV 和 ZIP 通过“最近下载文件”打开平台文件菜单，手动保存到其他位置。

完整备份先生成 SQLite 一致快照，再打包原图、处理图、缩略图与哈希清单。由小程序创建并校验，可下载。大备份受微信和设备存储限制，也可在电脑备份：

```powershell
.venv\Scripts\python scripts/backup.py
.venv\Scripts\python scripts/restore.py data/backups/backup_时间.zip
```

恢复前关闭后端与访问数据库的程序。默认仅校验；实际恢复加 `--apply`，恢复前自动备份现有数据。整库恢复保留为电脑离线操作，不在小程序运行中替换数据库。备份请另存其他设备。

## 环境与开发

本机已建立 Python 3.12 `.venv` 并安装依赖。重新安装使用 Python 3.12：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r backend/requirements-lock.txt
.venv\Scripts\python scripts/init_db.py
```

数据在 `data/`，通过 `KTV_DATA_DIR` 可改变目录；时长校验阈值 `KTV_DURATION_TOLERANCE_MINUTES` 默认 15。仅使用一个后端进程、一个 OCR 工作线程，不设置多个 workers。接口详情启动后查看 `http://127.0.0.1:8000/docs`。

```powershell
.venv\Scripts\python -m pytest backend/tests -q
cd frontend/miniapp-tests
npm ci
npm test
npm run compile
```

JS 流程测试使用模拟微信 API，模板使用 wcc/wcsc 编译器检查；这些不能替代开发者工具和真机测试。实际本地 OCR 环境烟雾测试可运行 `scripts/smoke_ocr.py`，不作为真实票据精度证明。

完整后端链路可运行 `.venv\Scripts\python scripts/smoke_pipeline.py`，自动使用临时数据验证上传至备份全流程，不污染日常数据。历史结果见 [0.2.0 验证记录](docs/verification-v0.2.0.md)，升级结果见 [0.3.0 验证记录](docs/verification-v0.3.0.md)。新版源码包位于 `dist/ktv-miniapp-v0.3.0.zip`，可运行 `scripts/package_miniapp.py` 重新生成。规则路由评测运行 `scripts/evaluate_agent.py`，详见 [评测口径](docs/evaluation.md)。

PC 网页代码保留在 `frontend/dashboard`，仅作辅助开发工具；如有需要另行运行 `scripts/run_dashboard.bat`，小程序不依赖该服务。

## 方案维护

开发约束见 `AGENTS.md`，当前方案入口 `docs/plan-current.md`。用户每次更新方案，保存新版本并同步实现、设计、接口、数据库、验收及变更记录，保留历史。
