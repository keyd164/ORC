这次我建议把学习路线从原来的 6 周扩展成一条更完整的 全栈开发 + AI Agent + 项目实战 + 简历求职 路线。重点不是学会很多框架，而是最终具备独立交付一个应用的能力。

还有一个很好的切入点：我检查了你上传的 `ktv-miniapp-v0.2.0.zip`。它已经包含微信小程序的 9 个页面、上传进度、记录管理、统计页面，以及调用后端的 API 封装。这可以作为你的第一个全栈项目基础。

不过，这个 ZIP 目前没有包含 Python 后端、OCR 服务和数据库实现。因此，简历应该以实际完成并验证的功能为准，后续逐步把它扩展为完整的全栈 AI Agent 项目，而不是直接把规划中的功能写成已有成果。

## 一、最终技术栈与 GitHub 学习仓库

我建议固定以下技术栈，至少前 8 周不再更换框架。

## 主项目技术栈

微信小程序

复用已有项目

Vue 3 + TypeScript

管理后台、ECharts

FastAPI

REST API、文件上传

SQLite + SQLAlchemy

数据持久化、业务查询

PaddleOCR

本地 OCR 识别

LangChain + LangGraph

Agent 与业务工作流

推荐学习仓库如下。这里区分了必学、参考和后续扩展，避免把所有项目都变成学习负担。

| 学习内容       | GitHub 仓库                                                                                                            | 学习要求           |
| ---------- | -------------------------------------------------------------------------------------------------------------------- | -------------- |
| Vue 3      | [vuejs/core](https://github.com/vuejs/core?utm_source=chatgpt.com)                                                   | 组件、响应式、生命周期    |
| TypeScript | [microsoft/TypeScript](https://github.com/microsoft/typescript/?utm_source=chatgpt.com)                              | 类型、接口、泛型基础     |
| Vite       | [vitejs/vite](https://github.com/vitejs/vite/blob/main/README.md?plain=1\&utm_source=chatgpt.com)                    | 创建和构建前端项目      |
| ECharts    | [apache/echarts](https://github.com/apache/echarts?utm_source=chatgpt.com)                                           | 统计图表和数据可视化     |
| FastAPI    | [fastapi/fastapi](https://github.com/fastapi?utm_source=chatgpt.com)                                                 | 接口、校验、异步与文件上传  |
| 全栈工程参考     | [fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template?utm_source=chatgpt.com) | 项目结构、测试、认证和部署  |
| OCR        | [PaddlePaddle/PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR?utm_source=chatgpt.com)                           | 本地图片文字识别       |
| Agent 框架   | [langchain-ai/langchain](https://github.com/langchain-ai/langchain?utm_source=chatgpt.com)                           | 工具调用和 Agent    |
| Agent 工作流  | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph?utm_source=chatgpt.com)                           | 状态、路由、持久化、人工审核 |
| Agent 实战课程 | [langchain-ai/langchain-academy](https://github.com/langchain-ai/langchain-academy?utm_source=chatgpt.com)           | 免费 Notebook 课程 |
| MCP 扩展     | [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk?utm_source=chatgpt.com)         | 标准化工具接口        |

其中，FastAPI 官方全栈模板采用 React、TypeScript、PostgreSQL 等技术，和你选定的 Vue 3 + SQLite 不完全一致。建议只借鉴其工程结构、测试、认证和部署思路，不要整套复制。

[image](https://www.google.com/s2/favicons?domain=https://fastapi.tiangolo.com\&sz=32)

FastAPI

+1



## 二、升级后的 10 周全栈 + Agent 学习计划

按每天 1–2 小时安排。这个计划的目标是形成一份能演示、能运行、能解释技术决策的项目作品集，而不是单纯刷教程。

### 第 1 周

前端基础

HTML / CSS / JavaScript / Git

学习 HTTP、JSON、Promise、`async/await`、浏览器调试和 Git 分支。先读懂已有小程序中的 `utils/api.js`，理解前端怎样向后端发送请求。

交付：整理现有小程序代码，补齐 README、环境说明和 Git 提交记录。

### 第 2 周

Vue 全栈前端

Vue 3 + TypeScript + Vite

学习组件、表单、表格、路由、状态管理、API 请求和异常提示。使用 ECharts 构建账单趋势、消费类型和异常统计图。

交付：独立运行的 Vue 3 管理后台原型。

### 第 3 周

后端开发

FastAPI + Pydantic

学习 REST API、请求校验、文件上传、异常处理、分页、CORS 和自动生成的接口文档。

交付：上传图片、查询记录、查看统计的可运行后端接口。

### 第 4 周

数据库

SQLite + SQLAlchemy + pytest

设计账单、图片、上传批次、字段修正历史和异常记录表。掌握关联查询、事务、索引、数据约束和单元测试。

交付：不依赖临时内存数据的账单管理系统。

### 第 5 周

OCR 实战

PaddleOCR + 字段提取

从统一格式的 KTV 消费账单中提取日期、金额、房间号、支付方式等字段。保留原始 OCR 文本，通过规则校验和人工修正处理错误。

交付：图片 → OCR → 结构化字段 → 数据库的完整处理链。

### 第 6 周

Agent 入门

LangChain 工具调用

编写查询账单、统计消费、查找异常、读取业务文档等工具。学习结构化输出、参数验证和工具调用日志。

交付：能使用真实业务数据回答问题的单 Agent。

### 第 7 周

Agent 工程化

LangGraph + RAG + 人工审核

把 Agent 组织为明确的执行流程，加入状态保存、错误重试、文档检索和高风险操作审批。

交付：可以追踪执行过程、能够在失败时恢复的 Agent 工作流。

### 第 8 周

全栈整合

小程序 + Vue 管理后台 + FastAPI

让两个前端共用同一套后端和数据库。完成多图上传、复核、数据筛选、图表统计、Agent 查询和报告导出。

交付：从前端到数据库、再到 Agent 的端到端业务流程。

### 第 9 周

质量与部署

测试、权限、安全、Docker

为接口、OCR 字段提取和 Agent 工具建立测试集。加入日志、上传文件校验、认证与权限控制，最后学习 Docker 和 GitHub Actions。

交付：可重复部署、可验证质量的项目版本。

### 第 10 周

简历与面试

GitHub 作品集 + 项目复盘 + 简历

整理架构图、演示视频、测试报告、部署说明和技术选型理由。准备项目介绍、技术难点、失败案例和优化思路。

交付：一个公开可展示的代码仓库、一份项目简历描述和一套面试讲解材料。

## 三、环境搭建：前端与后端分开

### 1. 创建 Vue 3 管理后台

安装 Node.js 的兼容 LTS 版本后执行：

```
npm create vite@latest web-admin -- --template vue-ts
cd web-admin
npm install
npm install vue-router pinia axios echarts
npm run dev
```

Vue 3、TypeScript 和 Vite 是前端主线；ECharts 用于可视化，Pinia 管理跨页面状态。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+3



### 2. 创建 FastAPI 后端

建议使用 Python 3.11 或其他经依赖验证的兼容版本：

```
mkdir backend
cd backend

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install fastapi "uvicorn[standard]" sqlalchemy pydantic-settings python-multipart
pip install pandas openpyxl pypdf python-docx
pip install langchain langgraph langchain-openai pytest httpx
```

创建 `app/main.py`，先实现一个最小接口：

```
from fastapi import FastAPIapp = FastAPI(title="KTV Bill Agent API")@app.get("/health")def health():    return {"status": "ok"}
```

运行：

```
uvicorn app.main:app --reload
```

访问 `http://127.0.0.1:8000/docs`，确认接口文档可以打开。

OCR 建议单独作为第 5 周任务安装。 PaddleOCR 的依赖和模型配置相对复杂，应根据操作系统、CPU/GPU 和所选模型安装，不要一开始就把 OCR、Agent 和前端全部堆在同一个环境中。

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 四、最终项目如何设计，才能体现全栈与 Agent 能力？

我建议把已有小程序升级为一个完整的业务系统，而不是另起一个 Todo、天气问答之类的练习项目。

## KTV 账单智能采集与分析系统

一个项目，覆盖前端、后端、数据库、OCR、Agent 和工程化。

[Mobility │Expensya](https://images.openai.com/static-rsc-4/2KSpXOOz__U39VsGCFK54f9YQUsCgVjXI9tKkU_4GuUKsR7Ujg61xJ1shBIxyoFjxUv82XcSdyADRNcOrvs4-NPHoBQkoHc5GfhtqfhRtgViyykx1moNh9CmS8Ws5ky1JU5y0mhvFZp_MAD6oSU121HMMxzavd_PtCoXZYVUR8E?purpose=inline)

前端：微信小程序 + Vue 3 管理后台

手机端负责多图上传、日期选择和账单复核；网页端负责数据工作台、异常管理、趋势图和 Agent 对话。

[FastAPI Path Operations for Teams - Other Models - SQLModel](https://images.openai.com/static-rsc-4/y5qwdhrCr1P7I_Y3DhXU1ckwbwbneLYsLGinj_cIHlKrc6PWA_AUVAGeCdUOIpYY6EeO9qrJ7tFcdxPLG56esLG0UGisoyGdS4DeBbDOhGJHh8kMm_uIobxVlLV7gTsRx66V-qUEXgDyuAJJHLZ_clVvBdWCEDbdzFckDpFifAM?purpose=inline)

后端：FastAPI + SQLite

统一管理上传批次、图片、账单、人工修正记录、统计和导出接口。原始 OCR 结果必须保留，人工修正不能被再次识别覆盖。

[Building Production Grade IDP with OCR, Vision LLMs and Agents \[Includes Code\] | by Edge Case | Medium](https://images.openai.com/static-rsc-4/-bxlwhYetq1p_QWbcPrH23mvCXc_ySmggD1gBQhCrDI9h8AS3iOPYEzFwLhQ4uQ3Ux3Jf_XV7a_GekIDfK543L5jYWzqZoCHu8B91As5-O3dwo6B1LNh1nCRphOlpEvq_Qm-SgF-cKH0g12WeEHDDUGa4hm5aATVb9uiPoe51yY?purpose=inline)

识别：PaddleOCR + 字段校验

OCR 负责识别文字，规则和结构化解析负责提取字段；低置信度或字段冲突进入人工复核。LLM 可以辅助处理疑难文本，但不能默认把模型输出当作真实金额。

[Beyond Toy Demos: AI Analytics at Enterprise Scale | Tellius](https://images.openai.com/static-rsc-4/M2EcnRfMA44qeBHs2EvO3CQQwZpApgLpo_yHMAd90NsO2OsQZuM6Mp0JdAbst_7Wzyrz13H5TeRsgAxmmQfEtQU1Mexr00hmBuzDqBuTUwDtfDK88kMggHwmtUk3SKVvd1VnYb21r2kokxEf3tRy23JBt3xE-TpxGrrRq8qz2pM?purpose=inline)

Agent：LangGraph + 业务工具

支持自然语言查询、异常汇总、跨日期统计、业务规则问答和报告生成。Agent 通过受限工具访问数据库，不直接执行任意 SQL 或修改账单。

建议的项目结构：

```
ktv-bill-agent/
├── miniapp/                 # 现有微信小程序
├── web-admin/               # Vue3 + TypeScript + ECharts
├── backend/
│   └── app/
│       ├── main.py
│       ├── api/             # HTTP 接口
│       ├── models/          # 数据模型
│       ├── schemas/         # 输入输出校验
│       ├── services/        # 业务逻辑
│       ├── ocr/             # OCR 与字段提取
│       ├── agent/           # LangChain / LangGraph
│       └── db/              # 数据库连接
├── data/                    # 本地测试数据，不提交敏感数据
├── tests/
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── evaluation.md
├── .env.example
├── .gitignore
└── README.md
```

### Agent 部分必须做出哪些亮点？

不要只做一个输入问题、返回答案的聊天窗口。至少完成以下 4 个能力：

1. 工具调用： 查询指定日期账单、计算消费合计、筛选异常记录。
2. 工作流编排： 根据用户意图选择查询、分析、文档检索或报告生成流程。
3. 结果验证： 金额、记录数和统计值由 SQL/Python 计算；Agent 负责组织回答。
4. 安全与可追踪： 保存工具调用日志、错误信息和数据来源；写操作需要授权与确认。

例如，用户提出“统计本月消费最高的房间，并找出金额异常的账单”，系统应该调用统计工具和异常查询工具，汇总真实结果，并返回可点击的账单记录，而不是让模型凭语言生成一个看似合理的答案。

## 五、简历怎么包装：岗位定位与项目描述

这条路线最适合对准以下岗位：

- AI 应用开发工程师 / AI Agent 应用开发工程师
- Python 后端开发工程师（AI 应用方向）
- 全栈开发工程师（AI 产品方向）

现阶段不建议把自己定位成大模型训练算法工程师。你的优势更应该体现为：能把模型能力接入实际业务系统，并具备数据处理、接口开发、流程控制和质量验证能力。

### 1. 当前版本：可以如实写进简历的项目经历

以下内容根据目前 ZIP 中能看到的小程序前端和 API 封装整理，没有把尚未实现的 OCR 或 Agent 写成已完成成果。

### KTV 账单智能采集与管理小程序｜个人项目（开发中）

**项目技术：** 微信小程序、JavaScript、HTTP API、Python（后端开发阶段）、Git

**项目介绍：** 面向统一收银系统生成的 KTV 消费账单，设计图片采集、记录管理、异常复核与统计分析流程，为后续接入本地 OCR、结构化数据存储和 AI Agent 业务分析提供应用基础。

**当前已完成工作：**

- 构建微信小程序多页面前端原型，覆盖首页、图片上传、上传记录、账单详情、异常管理、统计分析和系统设置等主要功能。
- 封装统一 API 请求模块，支持后端地址配置、图片上传进度反馈、请求异常提示及文件下载。
- 设计多图片上传、上传失败重试、记录查询与统计工作台的交互流程，并通过统一接口层对接后端服务。
- 梳理图片原始记录、人工复核与统计口径等业务需求，为后续数据持久化和识别质量评估提供设计依据。

**当前阶段说明：** 已有小程序前端与接口调用封装；Python 后端、数据库持久化、OCR 识别和 Agent 工作流尚需继续实现与验证。

这版适合你现在的项目阶段。它不会因为技术栈关键词写得太多，却在面试时无法展示代码而失分。

### 2. 完成全栈与 Agent 后，升级为核心项目

等后端、OCR、数据库、Agent 和测试真正完成后，可以升级成更有竞争力的项目描述。下面是目标模板，方括号中的数据必须由实际实验填写。

### KTV 账单智能识别与业务分析 Agent｜个人全栈项目

**技术栈：** 微信小程序、Vue 3、TypeScript、Vite、FastAPI、SQLite、SQLAlchemy、PaddleOCR、LangChain、LangGraph、pytest

**项目介绍：** 构建面向统一格式 KTV 消费账单的全栈数据处理系统，打通图片上传、OCR 识别、结构化数据管理、人工校正、业务统计和自然语言分析流程。

**核心工作：**

- **全栈架构：** 基于微信小程序和 Vue 3 管理后台构建双端应用，使用 FastAPI 提供统一业务 API，并通过 SQLite 持久化图片、账单、识别结果和人工修正记录。
- **OCR 数据处理：** 集成本地 PaddleOCR，结合规则解析和字段校验提取账单信息；保留原始识别文本，支持低置信度记录复核与修正历史追踪。
- **Agent 工作流：** 基于 LangChain 与 LangGraph 构建业务 Agent，封装账单查询、金额统计、异常筛选和报告生成等工具，支持自然语言驱动的业务分析。
- **可靠性与安全：** 为关键接口、字段提取和工具调用建立测试；采用参数校验、受限数据库查询和人工审批控制高风险操作。
- **效果评估：** 使用独立标注的账单测试集评估字段准确率、异常识别效果、接口成功率和 Agent 任务完成率，并记录测试规模与评估口径。

**量化成果：**

- OCR 字段级准确率：[实测结果]
- 测试账单数量：[实际数量]
- Agent 业务任务成功率：[实测结果]
- 自动化测试通过率：[实测结果]

**项目成果：** [填写实际完成的功能、部署方式、演示地址及可复现测试结果]。

两版之间最大的区别不是堆了多少技术名词，而是你能否证明每项能力确实实现了。 当前版本突出前端和接口封装；完成版则突出全栈交付、OCR 数据质量、Agent 工具编排和可验证的工程成果。

## 六、GitHub 作品集与简历要同步准备

简历之外，还应该让招聘者能快速验证项目质量。

| 作品集内容  | 需要准备的材料                                     |
| ------ | ------------------------------------------- |
| README | 项目背景、功能、技术栈、启动步骤、环境变量说明                     |
| 架构设计   | 前端、后端、数据库、OCR 和 Agent 的关系图                  |
| 演示材料   | 图片上传、账单校正、统计图、Agent 查询的截图或短视频               |
| 测试报告   | OCR 字段级准确率、接口测试、Agent 任务成功率及失败案例            |
| 工程质量   | `.gitignore`、依赖版本、示例配置、测试代码和 GitHub Actions |
| 项目复盘   | 为什么选择 LangGraph、如何控制数据库权限、如何处理 OCR 错误       |

项目最好从第一周开始就用 Git 管理。每完成一个模块就提交一次，保留有意义的提交记录，而不是最后一天一次性上传全部代码。

## 七、你现在最应该做的第一件事

先不要继续收集更多课程。 以当前的 KTV 小程序为起点，完成下面 4 个任务：

- 建立 GitHub 项目仓库并补齐项目 README。
- 创建 Vue 3 + TypeScript 管理后台，完成一个可展示的统计页面。
- 创建 FastAPI 后端，先打通 `/health` 和一条真实数据查询接口。
- 让小程序与后端成功通信，并用真实测试数据验证请求与响应。

完成这一步，你就从“学习 Agent 的人”进入了“正在构建全栈 AI 应用的人”。随后再接入 OCR 和 LangGraph，项目难度会更容易控制。

如果以求职为目标，优先保证一个完整、真实、可演示、可解释的全栈 Agent 项目，再考虑第二个项目或多 Agent 扩展。