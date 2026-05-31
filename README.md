# MultiAgent Kanban

多 Agent 协作看板系统。在看板中创建卡片，卡片按泳道（Swimlane）流转，每个泳道可配置 Claude CLI 自动执行任务，支持自动推进和审批后推进两种模式。

## 系统架构

```
┌─────────────┐     REST / WebSocket     ┌──────────────┐
│   Frontend  │ ◄──────────────────────► │   Backend    │
│  Vue 3 +    │     localhost:5173       │  FastAPI +   │
│  Pinia      │     localhost:8000       │  SQLAlchemy  │
└─────────────┘                          └──────┬───────┘
                                                │ subprocess
                                                ▼
                                        ┌──────────────┐
                                        │  Claude CLI   │
                                        │  (Agent 执行)  │
                                        └──────────────┘
```

| 层 | 技术 |
|---|------|
| 前端 | Vue 3 (Composition API) + Pinia + Vue Router + Axios |
| 构建 | Vite 5 |
| 后端 | Python 3.10+ + FastAPI + SQLAlchemy (async) + aiosqlite |
| 数据库 | SQLite（单文件, `backend/data/multiagent.db`） |
| 调度 | APScheduler (AsyncIOScheduler) |
| Agent | asyncio subprocess 管理 `claude.exe` CLI |
| 实时通信 | WebSocket（卡片状态 / 日志流推送） |

## 功能特性

- **看板管理** — 创建多个看板，每个看板包含若干泳道
- **卡片生命周期** — 创建卡片后自动流转泳道，实时状态跟踪
- **泳道模式** — 支持 `auto`（自动推进）和 `pre_approval`（审批后推进）两种模式
- **Agent 执行** — 每张卡片分配 Claude CLI 执行任务，实时推送日志
- **定时任务** — APScheduler 驱动的定时创建卡片
- **审批系统** — 审批模式下，泳道完成后需用户审批才能进入下一泳道
- **可配置轮询** — 通过设置页面调整卡片轮询间隔
- **离线包构建** — 支持构建包含 Portable Python + 所有依赖的离线分发包

## 快速开始

### 前置要求

- Python 3.10+
- Node.js 18+
- Claude CLI（`claude` 命令可用）

### 方式一：普通环境

```bash
# 1. 运行环境搭建脚本
setup.bat

# 2. 一键启动（前后端同时启动）
start-all.bat
```

### 方式二：分别启动

```bash
# 终端 1 - 后端
cd backend
python -m uvicorn app.main:app --reload --port 8000

# 终端 2 - 前端
cd frontend
npm run dev
```

### 访问地址

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| API | http://localhost:8000 |
| Swagger 文档 | http://localhost:8000/docs |

### 构建离线分发包

```bash
build-package.bat
```

该脚本会下载 Portable Python 并预装所有 Python 和 npm 依赖到项目目录中。打包整个项目目录分发给目标机器，目标机器无需安装 Python / Node.js，也无需网络访问，直接运行 `start-all.bat` 即可。

## 核心数据流

### 卡片创建 → 自动执行 → 泳道流转

```
用户创建卡片 (status=pending)
       │
       ▼
_card_picker_loop (可配置轮询间隔，默认 5s)
  扫描 pending 卡片
       │
       ▼
  对每张待处理卡片：
    1. 标记 running + WebSocket 广播
    2. AgentEngine 执行：
       - 获取信号量 (max_concurrent=3)
       - 启动 claude CLI 子进程
       - 实时捕获 stdout/stderr → Log + WebSocket 推送
       - 子进程退出
       │
       ▼
  handle_swimlane_completion()
    ├─ flow_mode=auto ────────── 自动进入下一泳道或完成
    └─ flow_mode=pre_approval ── 等待用户审批后推进
```

### 卡片状态

```
pending → running → waiting_approval / completed / blocked → (流转或结束)
```

## 配置

### 环境变量（`MULTIAGENT_` 前缀）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MULTIAGENT_DATABASE_URL` | `sqlite+aiosqlite:///data/multiagent.db` | 数据库 URL |
| `MULTIAGENT_MAX_CONCURRENT_PROCESSES` | `3` | 最大并行 Agent 数 |
| `MULTIAGENT_CLAUDE_PATH` | `claude` | claude CLI 路径 |
| `MULTIAGENT_CLAUDE_GIT_BASH_PATH` | `""` | claude 的 Git Bash 路径 |
| `MULTIAGENT_LOG_MAX_LENGTH` | `100000` | 单条日志最大字符数 |
| `MULTIAGENT_WS_HEARTBEAT_INTERVAL` | `30` | WebSocket 心跳间隔(秒) |

### 数据库配置（通过设置页面可修改）

| key | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| `polling_interval` | int | 5 | 卡片轮询间隔(秒) |
| `available_models` | JSON array | `claude-sonnet-4-20250514` 等 | 可选模型列表 |

## WebSocket 事件

| type | 方向 | 说明 |
|------|------|------|
| `card_status_changed` | 后端→前端 | 卡片状态变更 |
| `card_log_update` | 后端→前端 | Agent 执行日志行实时推送 |
| `card_needs_approval` | 后端→前端 | 卡片需要审批 |
| `card_completed` | 后端→前端 | 卡片完成 |
| `schedule_triggered` | 后端→前端 | 定时任务触发生成卡片 |
| `ping` / `pong` | 双向 | WebSocket 心跳（30s 间隔） |

## 目录结构

```
D:\p\multiagent\
├── CLAUDE.md                    # 项目说明（开发者参考）
├── start-all.bat                # 一键启动前后端
├── setup.bat                    # 环境搭建脚本
├── build-package.bat            # 离线包构建脚本
├── back-starter.bat / .ps1      # 后端启动脚本
├── front-starter.bat / .ps1     # 前端启动脚本
│
├── backend/
│   ├── requirements.txt         # Python 依赖
│   ├── .env                     # 环境配置
│   ├── data/                    # SQLite DB 存储（gitignored）
│   ├── alembic.ini / alembic/   # 数据库迁移骨架
│   └── app/
│       ├── main.py              # FastAPI 入口
│       ├── config.py            # Pydantic 配置
│       ├── database.py          # SQLAlchemy 引擎与会话
│       ├── websocket_manager.py # WebSocket 管理
│       ├── models/              # SQLAlchemy ORM 模型
│       │   ├── kanban.py        # Kanban, Swimlane
│       │   ├── card.py          # Card
│       │   ├── log.py           # 执行日志
│       │   ├── approval.py      # 审批记录
│       │   ├── schedule.py      # 定时任务
│       │   └── setting.py       # 键值对配置
│       ├── schemas/             # Pydantic 请求/响应模型
│       ├── routers/             # REST 路由
│       └── services/            # 业务逻辑层
│           ├── kanban_service.py
│           ├── card_service.py
│           ├── card_engine.py   # 卡片状态机
│           ├── agent_engine.py  # Claude CLI 进程管理
│           ├── approval_service.py
│           ├── schedule_engine.py
│           └── log_service.py
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js           # Vite 配置
│   └── src/
│       ├── main.js / App.vue    # 入口
│       ├── router/index.js
│       ├── api/                 # Axios API 封装
│       ├── stores/              # Pinia stores
│       ├── composables/         # useWebSocket
│       ├── views/               # 页面组件
│       └── components/          # 可复用组件
│
└── openspec/                    # 设计文档
```
