# CLAUDE.md

## 项目概览

**MultiAgent Kanban** — 多 Agent 协作看板系统。用户在看板中创建卡片，卡片按泳道（Swimlane）流转，每个泳道可配置 Claude CLI 执行任务，支持自动推进 / 审批后推进两种模式。

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Vue 3 (Composition API) + Pinia + Vue Router + Axios |
| 构建 | Vite 5 |
| 后端 | Python 3 + FastAPI + SQLAlchemy (async) + aiosqlite |
| 数据库 | SQLite（单文件, `backend/data/multiagent.db`） |
| 调度 | APScheduler (AsyncIOScheduler) |
| Agent | asyncio subprocess 管理 `claude.exe` CLI |
| 实时通信 | WebSocket（卡片状态 / 日志流推送） |
| 配置 | Pydantic BaseSettings（环境变量 + `.env` 文件） |

## 目录结构

```
D:\p\multiagent\
├── CLAUDE.md                       # 本项目文件
├── start-all.bat                   # 一键启动前后端
├── back-starter.bat / .ps1         # 后端启动脚本
├── front-starter.bat / .ps1        # 前端启动脚本
│
├── backend/
│   ├── alembic.ini / alembic/      # 数据库迁移骨架（实际用 create_all）
│   ├── data/                       # SQLite DB 存储（gitignored）
│   └── app/
│       ├── main.py                 # FastAPI 入口：lifespan、路由注册、WebSocket、_card_picker_loop
│       ├── config.py               # Pydantic Settings（database_url, claude_path, max_concurrent 等）
│       ├── database.py             # Async SQLAlchemy engine + session_factory + get_db 依赖
│       ├── websocket_manager.py    # WebSocket 连接管理 + broadcast
│       ├── models/                 # SQLAlchemy ORM 模型
│       │   ├── kanban.py           # Kanban, Swimlane
│       │   ├── card.py             # Card
│       │   ├── log.py              # Log（执行日志）
│       │   ├── approval.py         # Approval（审批记录）
│       │   ├── schedule.py         # Schedule, ScheduleLog（定时任务）
│       │   └── setting.py          # Setting（键值对配置）
│       ├── schemas/                # Pydantic 请求/响应模型
│       ├── routers/                # FastAPI REST 路由
│       │   ├── kanbans.py, cards.py, approvals.py, logs.py
│       │   ├── schedules.py, settings.py, browse.py, ws.py
│       └── services/               # 业务逻辑层
│           ├── kanban_service.py   # KanbanService, SwimlaneService
│           ├── card_service.py     # CardService（CRUD）
│           ├── card_engine.py      # CardEngine（状态机：推进、审批、驳回）
│           ├── agent_engine.py     # AgentEngine（管理 claude 子进程）
│           ├── approval_service.py # ApprovalService
│           ├── schedule_engine.py  # ScheduleEngine（APScheduler 管理）
│           └── log_service.py      # LogService
│
├── frontend/
│   ├── package.json                # Vue 3 + Pinia + Vue Router + Axios + Vite
│   ├── vite.config.js              # Vite 配置，代理 /api → :8000，/ws → ws://:8000
│   └── src/
│       ├── main.js / App.vue       # 入口
│       ├── router/index.js         # 6 个子路由（均在 Layout 下）
│       ├── api/                    # Axios API 封装
│       ├── stores/                 # Pinia stores（kanban, card, approval, schedule, setting）
│       ├── composables/            # useWebSocket.js（自动重连 + 心跳）
│       ├── views/                  # 页面级组件
│       └── components/             # 可复用组件
│
└── openspec/                       # OpenSpec 设计文档（proposal, design, specs）
```

## 架构关键点

### 前后端通信
- **REST API**: 前端 Axios → `/api/*` → Vite 代理 → `http://localhost:8000/api/*`
- **WebSocket**: 前端 `ws://host/ws` → Vite 代理 → `ws://localhost:8000/ws`
- **端口**: 后端 8000，前端 5173

### WebSocket 事件类型
| type | 方向 | 说明 |
|------|------|------|
| `card_status_changed` | 后端→前端 | 卡片状态变更（pending/running/blocked/waiting_approval/completed） |
| `card_log_update` | 后端→前端 | Agent 执行日志行实时推送 |
| `card_needs_approval` | 后端→前端 | 卡片需要审批 |
| `card_completed` | 后端→前端 | 卡片完成（移到最后一泳道） |
| `schedule_triggered` | 后端→前端 | 定时任务触发生成卡片 |
| `ping` / `pong` | 双向 | WebSocket 心跳（30s 间隔） |

## 核心数据流

### 卡片创建 → 自动执行 → 泳道流转

```
用户创建卡片 (status=pending)
       │
       ▼
_card_picker_loop (5s 轮询)
  select pending cards
       │
       ▼
  循环内对每张待处理卡片：
    1. card.status = "running" + commit + broadcast
    2. asyncio.create_task(_safe_execute_card())
       │
       ▼
  agent_engine.execute_card()
    1. 获取信号量 (max_concurrent=3)
    2. 检查 claude 命令是否可用 →
       不可用 → status=blocked + broadcast (已修复)
       可用   → 构建 cli args, 启动子进程
    3. 实时捕获 stdout/stderr → 写入 Log + WebSocket 推送
    4. 子进程退出 →
       exit_code=0 → card_engine.handle_swimlane_completion()
       exit_code≠0 → status=blocked + broadcast
       │
       ▼
  card_engine.handle_swimlane_completion()
    ┌─ flow_mode=auto ───────────────────────────┐
    │   advance_to_next_swimlane()               │
    │   ├─ 有下一泳道 → status=pending (回到轮询) │
    │   └─ 已是最后一泳道 → status=completed      │
    ├─ flow_mode=pre_approval ───────────────────┤
    │   status=waiting_approval (等待用户审批)     │
    │   审批通过 → advance_to_next_swimlane()     │
    │   审批驳回 → status=running + rejection_note│
    └────────────────────────────────────────────┘
```

### Card 状态枚举
`pending → running → waiting_approval / completed / blocked → (流转或结束)`

## 关键文件速查

| 文件 | 重要内容 |
|------|---------|
| `backend/app/main.py:74-106` | `_card_picker_loop()` — 核心轮询逻辑 |
| `backend/app/main.py:36-56` | `_safe_execute_card()` — Agent 执行安全包装 |
| `backend/app/main.py:59-71` | `_get_polling_interval()` — 从数据库读取轮询间隔 |
| `backend/app/services/agent_engine.py` | `AgentEngine` — claude CLI 子进程管理 |
| `backend/app/services/agent_engine.py:48-60` | `_build_claude_args()` — 构建 CLI 参数 |
| `backend/app/services/agent_engine.py:133-185` | `execute_card()` — 执行入口（已修复 broadcast bug） |
| `backend/app/services/card_engine.py:46-59` | `handle_swimlane_completion()` — 泳道完成后的决策逻辑 |
| `backend/app/services/card_engine.py:23-44` | `advance_to_next_swimlane()` — 推进到下一泳道 |
| `backend/app/services/schedule_engine.py` | `ScheduleEngine` — APScheduler 定时任务引擎 |
| `backend/app/websocket_manager.py` | WebSocket 连接管理与广播 |
| `frontend/src/composables/useWebSocket.js` | 前端 WebSocket 自动重连与心跳 |
| `frontend/src/components/Layout.vue:111-136` | WebSocket 事件注册 + 倒计时显示 |
| `frontend/src/views/KanbanView.vue` | 看板详情页（泳道列 + 卡片列表） |
| `frontend/src/components/SwimlaneColumn.vue` | 泳道列组件（按 `current_swimlane_id` 过滤卡片） |

## 已知问题 / 已修复

### 已修复：Claude 不可用时缺少 WebSocket 广播
- **位置**: `agent_engine.py:execute_card()` (第 133-148 行)
- **问题**: 当 `_ensure_claude_available()` 返回 False 时，卡片被设为 `blocked` 但没有 WebSocket 广播通知前端
- **修复**: 添加了 `card_status_changed` 广播，状态为 `blocked`

## 运行方式

```bash
# 方式一：一键启动（两个窗口）
start-all.bat

# 方式二：分别启动
# 终端 1 - 后端
cd backend && python -m uvicorn app.main:app --reload --port 8000

# 终端 2 - 前端
cd frontend && npm run dev
```

- 前端: `http://localhost:5173`
- API: `http://localhost:8000`
- Swagger 文档: `http://localhost:8000/docs`

## 配置

### 环境变量（`MULTIAGENT_` 前缀）
| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MULTIAGENT_DATABASE_URL` | sqlite+aiosqlite:///.../data/multiagent.db | 数据库 URL |
| `MULTIAGENT_MAX_CONCURRENT_PROCESSES` | 3 | 最大并行 Agent 数 |
| `MULTIAGENT_CLAUDE_PATH` | claude | claude CLI 路径 |
| `MULTIAGENT_CLAUDE_GIT_BASH_PATH` | "" | claude 的 Git Bash 路径 |
| `MULTIAGENT_LOG_MAX_LENGTH` | 100000 | 单条日志最大字符数 |
| `MULTIAGENT_WS_HEARTBEAT_INTERVAL` | 30 | WebSocket 心跳间隔(秒) |

### 数据库配置（Setting 表，可通过设置页面修改）
| key | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| `polling_interval` | int | 5 | 卡片轮询间隔(秒) |
| `available_models` | JSON array string | claude-sonnet-4-20250514 等 | 可选模型列表 |
