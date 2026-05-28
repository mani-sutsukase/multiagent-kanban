## Context

本项目是一个多 Agent 协作 Kanban 系统，面向企业单人单机使用。员工通过 Vue 前端配置看板和泳道，创建任务卡片，卡片在泳道流水线中自动流转，每个泳道由一个 Claude Code CLI 子进程负责处理。

系统为前后端分离架构：Vue 3 前端通过 HTTP REST API + WebSocket 与 Python FastAPI 后端通信，后端使用 SQLite 持久化数据。

## Goals / Non-Goals

**Goals:**
- 完整的看板/泳道/卡片的 CRUD 与状态机管理
- 三种流转模式（全自动、执行前审批、执行后审批）
- 驳回重做机制（基于 Claude Code session resume）
- 并行 Agent 执行引擎（多个并发 claude.exe 子进程）
- 定时任务调度器（APScheduler + cron 表达式）
- WebSocket 实时推送卡片状态变更
- 单人单机 SQLite 存储，零外部依赖部署

**Non-Goals:**
- 多用户/认证/权限系统
- 多节点分布式部署
- Agent 间的直接通信（仅流水线上下游数据传递）
- 非 Claude Code 的 Agent 支持
- 离线队列或持久化消息中间件

## 系统架构

```
┌──────────────────────────────────────────────────────────┐
│                    Vue 3 前端                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  │
│  │看板列表页  │  │看板详情页 │  │审批面板   │  │定时任务  │  │
│  │KanbanList │  │KanbanView│  │Approval  │  │Scheduler│  │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘  │
│       │              │              │            │        │
│  ┌────┴──────────────┴──────────────┴────────────┴───┐   │
│  │              API Client (axios + WebSocket)        │   │
│  └────────────────────────┬───────────────────────────┘   │
└───────────────────────────┼───────────────────────────────┘
                            │ HTTP REST + WebSocket
                            ▼
┌──────────────────────────────────────────────────────────┐
│                 Python FastAPI 后端                        │
│                                                           │
│  ┌────────────────────────────────────────────────────┐   │
│  │                  API 路由层                          │   │
│  │  /api/kanbans  /api/kanbans/{id}/swimlanes          │   │
│  │  /api/cards   /api/cards/{id}/logs                  │   │
│  │  /api/approvals  /api/schedules                     │   │
│  │  /ws (WebSocket 状态推送)                            │   │
│  └──────────────────────┬─────────────────────────────┘   │
│                         │                                   │
│  ┌──────────────────────┴─────────────────────────────┐   │
│  │                   服务层                              │   │
│  │  KanbanService │ CardService │ ScheduleService       │   │
│  │  ApprovalService │ LogService                        │   │
│  └──────────────────────┬─────────────────────────────┘   │
│                         │                                   │
│  ┌──────────────────────┴─────────────────────────────┐   │
│  │                 核心引擎                              │   │
│  │  CardEngine — 卡片状态机 & 流转控制                   │   │
│  │  └─ status: pending → running → waiting_approval     │   │
│  │                  → approved → next swimlane           │   │
│  │                  → rejected → running (驳回重做)      │   │
│  │                                                     │   │
│  │  AgentEngine — Claude Code 子进程管理                │   │
│  │  └─ ProcessPool: 管理多个 claude.exe 子进程           │   │
│  │  └─ 参数组装: prompt + skill + 模型 → CLI args       │   │
│  │  └─ stdout/stderr 流式捕获 → LogService              │   │
│  │  └─ session_id 持久化 → 驳回重做时 resume            │   │
│  │                                                     │   │
│  │  ScheduleEngine — 定时任务调度                        │   │
│  │  └─ APScheduler cron 触发器                          │   │
│  │  └─ 触发时调用 CardService.create_from_template()     │   │
│  └──────────────────────┬─────────────────────────────┘   │
│                         │                                   │
│  ┌──────────────────────┴─────────────────────────────┐   │
│  │               数据访问层 (Repository)                 │   │
│  │  KanbanRepo │ SwimlaneRepo │ CardRepo │ LogRepo     │   │
│  │  ApprovalRepo │ ScheduleRepo                         │   │
│  │  └─ SQLite (通过 SQLAlchemy 或 raw sqlite3)          │   │
│  └────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

## 数据模型

### SQLite 表结构

```sql
-- 看板表
CREATE TABLE kanbans (
    id          TEXT PRIMARY KEY,      -- UUID
    name        TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at  TEXT NOT NULL,         -- ISO 8601
    updated_at  TEXT NOT NULL
);

-- 泳道表
CREATE TABLE swimlanes (
    id              TEXT PRIMARY KEY,
    kanban_id       TEXT NOT NULL REFERENCES kanbans(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    sort_order      INTEGER NOT NULL,  -- 排序序号
    prompt          TEXT NOT NULL,      -- 固定 prompt
    skill           TEXT,               -- skill 引用（可选）
    tools           TEXT DEFAULT '[]',  -- JSON 数组: ["read", "edit", "bash", ...]
    flow_mode       TEXT NOT NULL DEFAULT 'auto'
                    -- 'auto' | 'pre_approval' | 'post_approval'
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

-- 卡片表
CREATE TABLE cards (
    id              TEXT PRIMARY KEY,
    kanban_id       TEXT NOT NULL REFERENCES kanbans(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    content         TEXT NOT NULL,
    model           TEXT NOT NULL,       -- 指定模型名
    current_swimlane_id TEXT REFERENCES swimlanes(id),
    status          TEXT NOT NULL DEFAULT 'pending',
                    -- 'pending' | 'running' | 'waiting_approval'
                    -- | 'approved' | 'rejected' | 'completed'
    session_id      TEXT,                -- Claude Code session_id，用于驳回重做
    rejection_note  TEXT,                -- 最近一次驳回批注
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

-- 卡片审批记录表
CREATE TABLE approvals (
    id              TEXT PRIMARY KEY,
    card_id         TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    swimlane_id     TEXT NOT NULL REFERENCES swimlanes(id),
    action          TEXT NOT NULL,       -- 'approved' | 'rejected'
    note            TEXT,                -- 审批/驳回批注
    created_at      TEXT NOT NULL
);

-- Agent 执行日志表
CREATE TABLE logs (
    id              TEXT PRIMARY KEY,
    card_id         TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    swimlane_id     TEXT NOT NULL REFERENCES swimlanes(id),
    attempt         INTEGER NOT NULL DEFAULT 1, -- 第几次执行（驳回重做递增）
    process_id      INTEGER,             -- OS 进程 PID
    stdout          TEXT DEFAULT '',      -- 完整 stdout
    stderr          TEXT DEFAULT '',      -- 完整 stderr
    exit_code       INTEGER,
    session_id      TEXT,                -- 本次执行的 session_id
    started_at      TEXT,
    finished_at     TEXT,
    created_at      TEXT NOT NULL
);

-- 定时任务表
CREATE TABLE schedules (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT DEFAULT '',
    cron_expr       TEXT NOT NULL,       -- cron 表达式
    enabled         INTEGER NOT NULL DEFAULT 1,
    -- 卡片模板
    card_title      TEXT NOT NULL,
    card_content    TEXT NOT NULL,
    card_model      TEXT NOT NULL,
    target_kanban_id    TEXT NOT NULL REFERENCES kanbans(id),
    target_swimlane_id  TEXT NOT NULL REFERENCES swimlanes(id),
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

-- 定时任务执行历史表
CREATE TABLE schedule_logs (
    id              TEXT PRIMARY KEY,
    schedule_id     TEXT NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    triggered_at    TEXT NOT NULL,
    created_card_id TEXT REFERENCES cards(id),
    status          TEXT NOT NULL,       -- 'success' | 'failed'
    error_message   TEXT,
    created_at      TEXT NOT NULL
);
```

### 索引

```sql
CREATE INDEX idx_swimlanes_kanban ON swimlanes(kanban_id, sort_order);
CREATE INDEX idx_cards_kanban ON cards(kanban_id);
CREATE INDEX idx_cards_status ON cards(status);
CREATE INDEX idx_cards_swimlane ON cards(current_swimlane_id, status);
CREATE INDEX idx_logs_card ON logs(card_id, swimlane_id, attempt);
CREATE INDEX idx_approvals_card ON approvals(card_id, swimlane_id);
CREATE INDEX idx_schedules_kanban ON schedules(target_kanban_id);
CREATE INDEX idx_schedule_logs_schedule ON schedule_logs(schedule_id);
```

## API 设计

### REST API

```
# 看板
GET    /api/kanbans                    # 列表
POST   /api/kanbans                    # 创建
GET    /api/kanbans/{id}               # 详情（含泳道）
PUT    /api/kanbans/{id}               # 更新
DELETE /api/kanbans/{id}               # 删除

# 泳道
POST   /api/kanbans/{id}/swimlanes     # 添加泳道
PUT    /api/swimlanes/{id}             # 更新泳道
DELETE /api/swimlanes/{id}             # 删除泳道
PUT    /api/kanbans/{id}/swimlanes/order  # 调整泳道顺序

# 卡片
GET    /api/kanbans/{id}/cards         # 看板内卡片列表
POST   /api/kanbans/{id}/cards         # 创建卡片
GET    /api/cards/{id}                 # 卡片详情
PUT    /api/cards/{id}                 # 更新卡片
DELETE /api/cards/{id}                 # 删除卡片

# 审批
GET    /api/approvals/pending          # 待审批卡片列表
POST   /api/cards/{id}/approve         # 批准
POST   /api/cards/{id}/reject          # 驳回（含批注body）

# 日志
GET    /api/cards/{id}/logs            # 卡片执行日志列表
GET    /api/logs/{id}/stdout           # 某次执行的完整 stdout
GET    /api/logs/{id}/stderr           # 某次执行的完整 stderr

# 定时任务
GET    /api/schedules                  # 列表
POST   /api/schedules                  # 创建
PUT    /api/schedules/{id}             # 更新
DELETE /api/schedules/{id}             # 删除
POST   /api/schedules/{id}/toggle      # 启用/停用
GET    /api/schedules/{id}/logs        # 执行历史
```

### WebSocket 事件

连接端点: `ws://localhost:8000/ws`

后端推送事件:
```json
{"type": "card_status_changed", "card_id": "...", "status": "running", "swimlane_id": "..."}
{"type": "card_log_update",      "card_id": "...", "log_id": "...", "stdout": "...", "append": true}
{"type": "card_needs_approval",  "card_id": "...", "swimlane_id": "...", "log_id": "..."}
{"type": "card_completed",       "card_id": "...", "swimlane_id": "..."}
{"type": "schedule_triggered",   "schedule_id": "...", "card_id": "..."}
```

## 卡片状态机

```
                    ┌──────────────────────────────────┐
                    │           卡片创建                   │
                    └────────┬─────────────────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │    pending       │ ← 进入某泳道
                    └────────┬─────────┘
                             │ AgentEngine 拾取
                             ▼
                    ┌──────────────────┐
              ┌────│    running       │
              │    └────────┬─────────┘
              │             │ Agent 执行完成
              │             ▼
              │    ┌──────────────────┐
              │    │  审批模式判断     │
              │    └──┬───────┬───────┘
              │       │       │
              │   ┌───┘       └───┐
              │   ▼               ▼
              │  auto        pre_approval
              │  │               │
              │  │               ▼
              │  │       ┌──────────────────┐
              │  │       │  等待审批         │ ◄── WebSocket 通知前端
              │  │       │  (waiting_       │
              │  │       │   approval)       │
              │  │       └────────┬─────────┘
              │  │              /   \
              │  │             /     \
              │  │            ▼       ▼
              │  │    ┌──────────┐ ┌──────────┐
              │  │    │ approved │ │ rejected │──┐
              │  │    └─────┬────┘ └──────────┘  │
              │  │          │                     │
              │  │          ▼                     │
              │  │    最后泳道?                    │
              │  │    ├── Yes → completed          │
              │  │    └── No  → 进入下一泳道        │
              │  │               pending            │
              │  │                                  │
              │  └──────────────────────────────────┘
              │                  ▲
              │                  │ (驳回重启)
              └──────────────────┘
```

## Decisions

### 1. FastAPI vs Flask/Django
- **选择**: FastAPI
- **理由**: 原生 async 支持，适合管理多个并发子进程和 WebSocket；自动 OpenAPI 文档；类型校验开箱即用

### 2. SQLite via SQLAlchemy vs aiosqlite
- **选择**: SQLAlchemy (async 模式) + aiosqlite
- **理由**: SQLAlchemy 提供 ORM 和 migration 管理（Alembic），aiosqlite 提供异步 SQLite 访问，与 FastAPI async 生态一致

### 3. APScheduler vs Celery
- **选择**: APScheduler (AsyncIOScheduler)
- **理由**: 单人单机场景无需 Celery 的分布式队列能力；APScheduler 内嵌在 FastAPI 进程中即可，部署简单

### 4. Vue 3 + Pinia vs Vuex
- **选择**: Vue 3 + Composition API + Pinia
- **理由**: Pinia 是 Vue 3 官方推荐的状态管理方案，TypeScript 友好，比 Vuex 轻量

### 5. WebSocket vs SSE vs Polling
- **选择**: WebSocket (前后端实时通信)
- **理由**: Agent 执行时需双向通信（前端可发指令），且日志流式传输需要全双工通道；FastAPI 原生支持 WebSocket

### 6. 子进程管理: asyncio.create_subprocess_exec vs subprocess.Popen
- **选择**: asyncio.create_subprocess_exec
- **理由**: 与 FastAPI async 运行时兼容，不阻塞事件循环；支持流式读取 stdout/stderr

### 7. 前端拖拽库
- **选择**: 待定 — vue-draggable-plus / @vueuse/gesture
- **理由**: 看板需要拖拽卡片到不同泳道，选择社区活跃的 Vue 3 兼容库

## 前端组件树

```
App.vue
├── Layout.vue (侧边导航 + 主内容区)
│   ├── KanbanList.vue           — 看板列表页
│   │   ├── KanbanCard.vue       — 看板摘要卡片
│   │   └── CreateKanbanDialog.vue
│   │
│   ├── KanbanView.vue           — 看板详情页
│   │   ├── SwimlaneColumn.vue   — 泳道列（含卡片列表）
│   │   │   ├── CardItem.vue     — 卡片（可拖拽）
│   │   │   │   ├── CardStatusIcon.vue
│   │   │   │   └── CardActions.vue
│   │   │   └── CreateCardDialog.vue
│   │   ├── SwimlaneConfig.vue   — 泳道配置面板
│   │   ├── SwimlaneOrderEditor.vue — 泳道排序
│   │   └── KanbanSettings.vue   — 看板设置
│   │
│   ├── ApprovalPanel.vue        — 审批面板
│   │   ├── PendingList.vue      — 待审批列表
│   │   ├── ApprovalDetail.vue   — 审批详情
│   │   │   ├── LogViewer.vue    — Agent 日志查看器
│   │   │   └── ApprovalActions.vue — 批准/驳回按钮
│   │   └── RejectDialog.vue     — 驳回批注对话框
│   │
│   ├── ScheduleManager.vue      — 定时任务管理
│   │   ├── ScheduleList.vue     — 任务列表
│   │   ├── ScheduleForm.vue     — 创建/编辑表单
│   │   └── ScheduleLogList.vue  — 执行历史
│   │
│   └── LogViewer.vue            — 卡片详情页的日志查看
│       ├── LogTimeline.vue      — 执行时间线
│       └── LogContent.vue       — stdout/stderr 内容
```

## Agent 执行引擎设计

### 进程管理

```python
class AgentEngine:
    """
    管理 Claude Code CLI 子进程的创建、监控和日志捕获。
    通过 asyncio 实现非阻塞并发进程管理。
    """

    # max_concurrent: 最大并行进程数（可配置，默认 3）
    # 使用 asyncio.Semaphore 控制并发度
    # 每个子进程启动时：
    #   1. 构建 CLI 参数
    #   2. 记录 session_id
    #   3. 流式读取 stdout/stderr → 存入日志表
    #   4. 进程退出 → 更新卡片状态
```

### CLI 参数组装

```python
# 根据泳道配置 + 卡片内容，构建 claude.exe 命令

def build_claude_args(card: Card, swimlane: Swimlane) -> list[str]:
    args = ["claude.exe"]

    # 卡片指定模型
    if card.model:
        args.extend(["--model", card.model])

    # 泳道固定 prompt（+ 如果驳回重做，附加上次批注）
    prompt = swimlane.prompt
    if card.rejection_note:
        prompt += f"\n\n【上次审核意见】\n{card.rejection_note}\n\n请根据审核意见改进。"
    args.extend(["-p", prompt])

    # 泳道 skill
    if swimlane.skill:
        args.extend(["--skill", swimlane.skill])

    # 如果驳回重做且有 session_id，使用 resume
    if card.session_id and card.status == "rejected":
        args.extend(["--resume", card.session_id])

    return args
```

### 日志流式捕获

```python
# 使用 asyncio.create_subprocess_exec 启动进程
# 逐行读取 stdout/stderr
# 每读取到新行就写入 logs 表 + 通过 WebSocket 推送给前端
# 这样员工在审批面板可以实时看到 Agent 的输出
```

## 定时任务设计

```python
class ScheduleEngine:
    """
    基于 APScheduler 的 AsyncIOScheduler，内嵌在 FastAPI 生命周期中。
    """
    # 启动时: 加载所有 enabled 的定时任务注册到 scheduler
    # 触发时: 调用 CardService.create_card() 用模板创建卡片
    # 任务执行后: 记录到 schedule_logs 表
    # CRUD 操作: 当 schedules 表变更时，动态更新 scheduler

    # scheduler 在 FastAPI startup 事件中初始化
    # 在 shutdown 事件中关闭
```

## 项目目录结构

```
multiagent/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI 入口
│   │   ├── config.py               # 配置
│   │   ├── database.py             # SQLAlchemy 引擎 + session
│   │   ├── models/                 # SQLAlchemy ORM 模型
│   │   │   ├── __init__.py
│   │   │   ├── kanban.py
│   │   │   ├── card.py
│   │   │   ├── log.py
│   │   │   ├── approval.py
│   │   │   └── schedule.py
│   │   ├── schemas/                # Pydantic 请求/响应模型
│   │   │   ├── __init__.py
│   │   │   ├── kanban.py
│   │   │   ├── card.py
│   │   │   ├── log.py
│   │   │   ├── approval.py
│   │   │   └── schedule.py
│   │   ├── routers/                # API 路由
│   │   │   ├── __init__.py
│   │   │   ├── kanbans.py
│   │   │   ├── cards.py
│   │   │   ├── approvals.py
│   │   │   ├── logs.py
│   │   │   ├── schedules.py
│   │   │   └── ws.py              # WebSocket
│   │   ├── services/               # 业务逻辑
│   │   │   ├── __init__.py
│   │   │   ├── kanban_service.py
│   │   │   ├── card_service.py
│   │   │   ├── card_engine.py      # 卡片状态机
│   │   │   ├── agent_engine.py     # Claude Code 子进程管理
│   │   │   ├── approval_service.py
│   │   │   ├── schedule_engine.py  # 定时任务
│   │   │   └── log_service.py
│   │   └── websocket_manager.py    # WebSocket 连接管理
│   ├── requirements.txt
│   ├── alembic.ini
│   └── alembic/                    # 数据库迁移
│       └── versions/
│
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.js
│   │   ├── router/
│   │   │   └── index.js
│   │   ├── stores/                 # Pinia stores
│   │   │   ├── kanban.js
│   │   │   ├── card.js
│   │   │   ├── approval.js
│   │   │   └── schedule.js
│   │   ├── api/                    # API 请求封装
│   │   │   ├── client.js           # axios 实例
│   │   │   ├── kanban.js
│   │   │   ├── card.js
│   │   │   ├── approval.js
│   │   │   └── schedule.js
│   │   ├── composables/            # 组合式函数
│   │   │   ├── useWebSocket.js
│   │   │   └── useCardDrag.js
│   │   ├── views/                  # 页面
│   │   │   ├── KanbanList.vue
│   │   │   ├── KanbanView.vue
│   │   │   ├── ApprovalPanel.vue
│   │   │   └── ScheduleManager.vue
│   │   └── components/             # 组件
│   │       ├── Layout.vue
│   │       ├── SwimlaneColumn.vue
│   │       ├── CardItem.vue
│   │       ├── LogViewer.vue
│   │       ├── CreateKanbanDialog.vue
│   │       ├── CreateCardDialog.vue
│   │       ├── RejectDialog.vue
│   │       ├── ScheduleForm.vue
│   │       └── ...
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
│
└── README.md
```

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| claude.exe 子进程崩溃导致任务丢失 | 捕获 exit_code，非零退出时自动标记卡片为 failed 并记录 stderr；支持手动重试 |
| 并行进程过多耗尽系统资源 | 可配最大并行数（默认 3），使用 Semaphore 控制 |
| Claude Code session resume 行为不可控 | 只在驳回重做场景使用 resume；限制最大 resume 次数防止死循环 |
| SQLite 并发写入冲突 | WAL 模式 + 使用 `BEGIN IMMEDIATE`；单人单机场景并发量低 |
| WebSocket 断连 | 前端实现自动重连 + 心跳检测 |
| 定时任务到期时应用未运行 | 启动时扫描 schedule_logs 检查错过的触发，可选择补执行 |
