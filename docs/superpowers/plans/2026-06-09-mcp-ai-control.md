# MCP AI Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make all MultiAgent Kanban operations AI-controllable via MCP Server + Orchestrator Swimlane

**Architecture:** Embed an MCP Server (SSE transport) in FastAPI. All MCP tools directly call Service layer. New `swimlane_type` field distinguishes `normal` swimlanes (existing behavior) from `orchestrator` swimlanes (injected with `--mcp-servers`). Same MCP Server exposes tools to external Claude clients.

**Tech Stack:** Python mcp SDK, FastAPI, Vue 3

---

### Task 1: Add dependency + swimlane_type to model/schema/migration

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/models/kanban.py`
- Modify: `backend/app/database.py`
- Modify: `backend/app/schemas/kanban.py`
- Modify: `backend/app/services/kanban_service.py`

- [ ] **Step 1: Add mcp dependency**

Edit `backend/requirements.txt` to add `mcp>=1.0.0`

- [ ] **Step 2: Add swimlane_type to Swimlane model**

In `backend/app/models/kanban.py`, add after `tools` field:
```python
swimlane_type = Column(String, nullable=False, default="normal")  # normal | orchestrator
```

- [ ] **Step 3: Add migration for swimlane_type**

In `backend/app/database.py`, add a new migration function and call it in `init_db()`:
```python
def _add_swimlane_type_column(conn):
    from sqlalchemy import inspect
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("swimlanes")]
    if "swimlane_type" not in columns:
        conn.execute(
            __import__("sqlalchemy").text(
                "ALTER TABLE swimlanes ADD COLUMN swimlane_type VARCHAR NOT NULL DEFAULT 'normal'"
            )
        )
```
Call it in `init_db()` after the existing migrations.

- [ ] **Step 4: Update all schemas**

In `backend/app/schemas/kanban.py`:
- `SwimlaneBrief`: add `swimlane_type: str = "normal"`
- `SwimlaneCreate`: add `swimlane_type: str = "normal"`
- `SwimlaneUpdate`: add `swimlane_type: Optional[str] = None`
- `SwimlaneResponse`: add `swimlane_type: str`
- `KanbanExportSwimlane`: add `swimlane_type: str = "normal"`

- [ ] **Step 5: Update SwimlaneService**

In `backend/app/services/kanban_service.py`:
- `add_swimlane()`: add `swimlane_type: str = "normal"` parameter, pass to Swimlane constructor
- `export_config()`: include `swimlane_type` in exported dict
- `import_config()`: include `swimlane_type` in add_swimlane call

---

### Task 2: Create MCP Server module

**Files:**
- Create: `backend/app/mcp_server.py`

- [ ] **Step 1: Create MCP server with all tools**

Create `backend/app/mcp_server.py` with:
- `create_mcp_server(ws_manager, settings)` factory function
- All tools as `@mcp.tool()` decorated async functions
- Each tool creates fresh Service instances via `async_session_factory()`
- Tools list:
  - Kanban: list_kanbans, get_kanban, create_kanban, update_kanban, delete_kanban
  - Swimlane: add_swimlane, update_swimlane, delete_swimlane, reorder_swimlanes
  - Card: list_cards, get_card, create_card, update_card, delete_card, move_card, get_card_logs
  - Approval: list_pending_approvals, approve_card, reject_card, reply_to_card
  - Schedule: list_schedules, create_schedule, update_schedule, delete_schedule, toggle_schedule
  - Settings: list_settings, get_setting, update_setting
  - System: get_system_status

---

### Task 3: Register MCP endpoints + AgentEngine modification

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/services/agent_engine.py`

- [ ] **Step 1: Mount MCP SSE endpoints in main.py**

In `backend/app/main.py`:
- Import `create_mcp_server` from `app.mcp_server`
- In `lifespan`, after creating mcp server, store on app state
- Mount MCP SSE transport at `/mcp` path

```python
# After app creation, register MCP
from app.mcp_server import create_mcp_server
mcp_server = create_mcp_server(ws_manager, settings)
app.mount("/mcp", mcp_server.sse_app())
```

- [ ] **Step 2: Modify AgentEngine._build_claude_args for orchestrator**

Add orchestrator prompt injection when `swimlane.swimlane_type == "orchestrator"`:
- Add `--mcp-servers` JSON config to args
- Inject orchestrator instruction into prompt

```python
# In _build_claude_args, after constructing parts:
if getattr(swimlane, 'swimlane_type', 'normal') == 'orchestrator':
    # Add MCP server config
    import json as _json
    mcp_config = _json.dumps({
        "kanban-mcp": {
            "url": "http://127.0.0.1:8000/mcp"
        }
    })
    args.extend(["--mcp-servers", mcp_config])

    # Add orchestrator instruction
    parts.append(
        "\n\n【编排任务指令】\n"
        "你是一个看板编排 Agent。你可以通过 MCP 工具调用看板系统的所有 API。\n"
        "你可以创建卡片、审批、修改配置、管理定时任务等。\n"
        "请根据当前看板状态和任务目标，自主决策并执行操作。\n"
        "所有可用的工具已通过 MCP 协议注入，你可以直接调用。\n"
    )
```

---

### Task 4: Frontend - SwimlaneConfig swimlane_type selector

**Files:**
- Modify: `frontend/src/components/SwimlaneConfig.vue`

- [ ] **Step 1: Add swimlane_type dropdown in config UI**

After the flow_mode selector in `SwimlaneConfig.vue`, add:
```html
<div class="form-group">
  <label>泳道类型</label>
  <select v-model="swimlane.swimlane_type">
    <option value="normal">普通泳道 — 纯 Prompt 执行</option>
    <option value="orchestrator">编排泳道 — 通过 MCP 工具管理系统</option>
  </select>
</div>
```

- [ ] **Step 2: Include swimlane_type in create/update API calls**

In `save()` method and `addSwimlane()` function, pass `swimlane_type` field.

---

### Task 5: Frontend - Show orchestrator badge

**Files:**
- Modify: `frontend/src/components/SwimlaneColumn.vue`

- [ ] **Step 1: Add orchestrator badge**

After the `flow-badge` span, add:
```html
<span v-if="swimlane.swimlane_type === 'orchestrator'" class="orchestrator-badge">编排</span>
```

- [ ] **Step 2: Add styling**

```css
.orchestrator-badge { background: #e8daef; color: #8e44ad; font-size: 11px; padding: 2px 8px; border-radius: 10px; }
```
