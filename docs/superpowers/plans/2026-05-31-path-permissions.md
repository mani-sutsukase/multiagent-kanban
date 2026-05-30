# 路径权限配置实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为卡片和泳道增加路径权限配置，解决 Claude CLI 无法访问工作目录文件的问题

**Architecture:** Card 和 Swimlane 模型各新增路径/权限字段；AgentEngine 运行时合并卡片+泳道的路径列表，构建 `CLAUDE_CODE_ALLOWED_PATHS` 环境变量；前端在 SwimlaneConfig、CreateCardDialog、CardDetailModal 中新增路径配置 UI

**Tech Stack:** Python FastAPI + SQLAlchemy + Vue 3 + Pinia

---

### Task 1: Card 模型新增字段

**Files:**
- Modify: `backend/app/models/card.py:28-35`

**改动：** 在 Card 表中新增 `local_path`、`local_path_permission`、`allowed_paths` 三个字段

- [ ] **添加字段到 Card 模型**

修改 `backend/app/models/card.py`，在 `user_reply` 字段后添加：

```python
    local_path = Column(String, nullable=True)           # 卡片级工作目录
    local_path_permission = Column(String, nullable=False, default="read_write")  # read_only / read_write
    allowed_paths = Column(Text, nullable=False, default="[]")  # JSON: [{"path":"...","permission":"read_only"|"read_write"}]
```

- [ ] **运行验证**

```bash
cd backend && python -c "from app.models.card import Card; cols = [c.name for c in Card.__table__.columns]; assert 'local_path' in cols; assert 'local_path_permission' in cols; assert 'allowed_paths' in cols; print('OK')"
```
期望输出: `OK`

- [ ] **Commit**

```bash
git add backend/app/models/card.py
git commit -m "feat: add path permission fields to Card model"
```

---

### Task 2: Swimlane 模型新增字段

**Files:**
- Modify: `backend/app/models/kanban.py:41-43`

在 Swimlane 的 `wait_for_reply` 字段后添加：

```python
    local_path_permission = Column(String, nullable=False, default="read_write")  # read_only / read_write
    allowed_paths = Column(Text, nullable=False, default="[]")  # JSON: [{"path":"...","permission":"read_only"|"read_write"}]
```

- [ ] **修改 `backend/app/models/kanban.py`**

```python
# 在 wait_for_reply 字段后添加
    local_path_permission = Column(String, nullable=False, default="read_write")
    allowed_paths = Column(Text, nullable=False, default="[]")
```

- [ ] **运行验证**

```bash
cd backend && python -c "from app.models.kanban import Swimlane; cols = [c.name for c in Swimlane.__table__.columns]; assert 'local_path_permission' in cols; assert 'allowed_paths' in cols; print('OK')"
```
期望输出: `OK`

- [ ] **Commit**

```bash
git add backend/app/models/kanban.py
git commit -m "feat: add path permission fields to Swimlane model"
```

---

### Task 3: 数据库迁移函数

**Files:**
- Modify: `backend/app/database.py:28-34`

在 `init_db` 中注册 4 个新的迁移函数，新增 4 个迁移实现。

- [ ] **在 `init_db` 中注册迁移**

修改 `backend/app/database.py:28-34`，添加：

```python
        # 迁移：为 cards 表添加 local_path 等字段
        await conn.run_sync(_add_card_path_fields)
        # 迁移：为 swimlanes 表添加 local_path_permission 等字段
        await conn.run_sync(_add_swimlane_path_fields)
```

- [ ] **添加迁移函数实现**

在文件末尾添加：

```python
def _add_card_path_fields(conn):
    """为已有数据库添加 local_path, local_path_permission, allowed_paths 列（幂等）"""
    from sqlalchemy import inspect
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("cards")]
    if "local_path" not in columns:
        conn.execute(
            __import__("sqlalchemy").text(
                "ALTER TABLE cards ADD COLUMN local_path VARCHAR"
            )
        )
    if "local_path_permission" not in columns:
        conn.execute(
            __import__("sqlalchemy").text(
                "ALTER TABLE cards ADD COLUMN local_path_permission VARCHAR NOT NULL DEFAULT 'read_write'"
            )
        )
    if "allowed_paths" not in columns:
        conn.execute(
            __import__("sqlalchemy").text(
                "ALTER TABLE cards ADD COLUMN allowed_paths TEXT NOT NULL DEFAULT '[]'"
            )
        )


def _add_swimlane_path_fields(conn):
    """为已有数据库添加 local_path_permission, allowed_paths 列（幂等）"""
    from sqlalchemy import inspect
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("swimlanes")]
    if "local_path_permission" not in columns:
        conn.execute(
            __import__("sqlalchemy").text(
                "ALTER TABLE swimlanes ADD COLUMN local_path_permission VARCHAR NOT NULL DEFAULT 'read_write'"
            )
        )
    if "allowed_paths" not in columns:
        conn.execute(
            __import__("sqlalchemy").text(
                "ALTER TABLE swimlanes ADD COLUMN allowed_paths TEXT NOT NULL DEFAULT '[]'"
            )
        )
```

- [ ] **Commit**

```bash
git add backend/app/database.py
git commit -m "feat: add database migration for path permission columns"
```

---

### Task 4: Card Schema 更新

**Files:**
- Modify: `backend/app/schemas/card.py:5-9,19-34`

为 `CardCreate` 和 `CardResponse` 添加新字段。

- [ ] **修改 `CardCreate`**

```python
class CardCreate(BaseModel):
    title: str
    content: str = ""
    model: str = "claude-sonnet-4-20250514"
    target_swimlane_id: Optional[str] = None
    local_path: Optional[str] = None
    local_path_permission: str = "read_write"
    allowed_paths: str = "[]"
```

- [ ] **修改 `CardResponse`**

在 `user_reply` 字段后添加：

```python
    local_path: Optional[str] = None
    local_path_permission: str = "read_write"
    allowed_paths: str = "[]"
```

- [ ] **验证**

```bash
cd backend && python -c "from app.schemas.card import CardCreate, CardResponse; print('OK')"
```
期望输出: `OK`

- [ ] **Commit**

```bash
git add backend/app/schemas/card.py
git commit -m "feat: update Card schemas with path permission fields"
```

---

### Task 5: Swimlane Schema 更新

**Files:**
- Modify: `backend/app/schemas/kanban.py`

为 `SwimlaneBrief`、`SwimlaneCreate`、`SwimlaneUpdate`、`SwimlaneResponse` 添加 `local_path_permission` 和 `allowed_paths`。

- [ ] **`SwimlaneBrief`** — 在 `wait_for_reply` 后添加：

```python
    local_path_permission: str = "read_write"
    allowed_paths: str = "[]"
```

- [ ] **`SwimlaneCreate`** — 在 `wait_for_reply` 后添加：

```python
    local_path_permission: str = "read_write"
    allowed_paths: str = "[]"
```

- [ ] **`SwimlaneUpdate`** — 添加：

```python
    local_path_permission: Optional[str] = None
    allowed_paths: Optional[str] = None
```

- [ ] **`SwimlaneResponse`** — 在 `wait_for_reply` 后添加：

```python
    local_path_permission: str = "read_write"
    allowed_paths: str = "[]"
```

- [ ] **验证**

```bash
cd backend && python -c "from app.schemas.kanban import SwimlaneBrief, SwimlaneCreate, SwimlaneUpdate, SwimlaneResponse; print('OK')"
```
期望输出: `OK`

- [ ] **Commit**

```bash
git add backend/app/schemas/kanban.py
git commit -m "feat: update Swimlane schemas with path permission fields"
```

---

### Task 6: 后端 Service 透传新字段

**Files:**
- Modify: `backend/app/services/card_service.py:13-18`
- Modify: `backend/app/services/kanban_service.py:63-88`

- [ ] **更新 `CardService.create_card()`**

添加 `local_path`、`local_path_permission`、`allowed_paths` 参数：

```python
    async def create_card(self, kanban_id: str, title: str, content: str = "",
                          model: str = "claude-sonnet-4-20250514",
                          target_swimlane_id: str = None,
                          local_path: str = None,
                          local_path_permission: str = "read_write",
                          allowed_paths: str = "[]") -> Card:
```

并在 Card 构造时透传：

```python
        card = Card(
            kanban_id=kanban_id,
            title=title,
            content=content,
            model=model,
            current_swimlane_id=target_swimlane_id,
            local_path=local_path,
            local_path_permission=local_path_permission,
            allowed_paths=allowed_paths,
            status="pending",
        )
```

- [ ] **更新 `SwimlaneService.add_swimlane()`**

添加 `local_path_permission`、`allowed_paths` 参数：

```python
    async def add_swimlane(self, kanban_id: str, name: str, prompt: str = "",
                           skill: str = None, tools: str = "[]",
                           flow_mode: str = "auto",
                           local_path: str = None,
                           wait_for_reply: str = "0",
                           local_path_permission: str = "read_write",
                           allowed_paths: str = "[]") -> Swimlane:
```

并在 Swimlane 构造时添加：

```python
        swimlane = Swimlane(
            ...
            local_path=local_path,
            local_path_permission=local_path_permission,
            allowed_paths=allowed_paths,
            wait_for_reply=wait_for_reply,
        )
```

- [ ] **更新路由透传：`backend/app/routers/kanbans.py:105-117`**

修改创建泳道的路由，将新字段从请求体透传到 service：

```python
            swimlane = await swimlane_service.add_swimlane(
                kanban_id=kanban_id,
                name=data.name,
                prompt=data.prompt,
                skill=data.skill,
                tools=data.tools,
                flow_mode=data.flow_mode,
                local_path=data.local_path,
                wait_for_reply=data.wait_for_reply,
                local_path_permission=data.local_path_permission,
                allowed_paths=data.allowed_paths,
            )
```

- [ ] **更新 `_card_to_response()` — `backend/app/routers/cards.py:19-27`**

为新字段添加映射：

```python
def _card_to_response(card) -> CardResponse:
    return CardResponse(
        id=card.id, kanban_id=card.kanban_id, title=card.title, content=card.content,
        model=card.model, current_swimlane_id=card.current_swimlane_id,
        status=card.status, session_id=card.session_id, rejection_note=card.rejection_note,
        result=card.result, last_prompt=card.last_prompt, last_output=card.last_output,
        user_reply=card.user_reply,
        local_path=card.local_path, local_path_permission=card.local_path_permission,
        allowed_paths=card.allowed_paths,
        created_at=card.created_at, updated_at=card.updated_at,
    )
```

- [ ] **更新路由透传：`backend/app/routers/kanbans.py:119-132`**

修改更新泳道的路由，添加 `local_path_permission` 和 `allowed_paths` 到 update data：

```python
        update_data = data.model_dump(exclude_none=True)
        swimlane = await swimlane_service.update(swimlane_id, **update_data)
```

`SwimlaneUpdate` 的 `model_dump(exclude_none=True)` 会自动包含非 None 的新字段，所以不需要额外改动。

- [ ] **更新路由响应：`backend/app/routers/kanbans.py:50-70`**

修改 `_kanban_to_response()` 中的 `SwimlaneBrief` 构造，添加新字段。由于 `SwimlaneBrief` 使用 `from_attributes = True`，ORM 属性会自动映射，无需手动传递。

- [ ] **验证**

```bash
cd backend && python -c "from app.routers.kanbans import router; from app.services.card_service import CardService; print('OK')"
```
期望输出: `OK`

- [ ] **Commit**

```bash
git add backend/app/services/card_service.py backend/app/services/kanban_service.py backend/app/routers/kanbans.py
git commit -m "feat: pass through path permission fields in services and routes"
```

---

### Task 7: AgentEngine 路径合并逻辑

**Files:**
- Modify: `backend/app/services/agent_engine.py:264-294`

在 `execute_card()` 中，构建 `CLAUDE_CODE_ALLOWED_PATHS` 环境变量，合并卡片和泳道的路径。

- [ ] **修改 `execute_card()` 中的路径处理逻辑**

在 `build_claude_args` 调用之后，保存提示词之前，添加路径合并：

```python
            args, full_prompt = self._build_claude_args(card, swimlane)

            # ---- 路径权限合并 ----
            all_allowed_paths = []

            # 卡片路径
            card_local = getattr(card, 'local_path', None) or ''
            if card_local.strip():
                perm = getattr(card, 'local_path_permission', 'read_write') or 'read_write'
                all_allowed_paths.append({
                    "path": card_local.strip(),
                    "permission": perm,
                })
            card_extra = getattr(card, 'allowed_paths', None) or '[]'
            if card_extra.strip():
                try:
                    extra = json.loads(card_extra)
                    if isinstance(extra, list):
                        all_allowed_paths.extend(extra)
                except (json.JSONDecodeError, TypeError):
                    pass

            # 泳道路径
            swim_local = swimlane.local_path or ''
            if swim_local.strip():
                sw_perm = getattr(swimlane, 'local_path_permission', 'read_write') or 'read_write'
                all_allowed_paths.append({
                    "path": swim_local.strip(),
                    "permission": sw_perm,
                })
            sw_extra = getattr(swimlane, 'allowed_paths', None) or '[]'
            if sw_extra.strip():
                try:
                    extra = json.loads(sw_extra)
                    if isinstance(extra, list):
                        all_allowed_paths.extend(extra)
                except (json.JSONDecodeError, TypeError):
                    pass

            # 去重（按路径去重，保留最后一个的权限设置）
            seen = {}
            for item in all_allowed_paths:
                seen[item["path"]] = item["permission"]
            unique_paths = [{"path": p, "permission": perm} for p, perm in seen.items()]

            # 设置 cwd：卡片 local_path > 泳道 local_path > None
            cwd_override = card_local.strip() or swim_local.strip() or None

            # 构建 CLAUDE_CODE_ALLOWED_PATHS 环境变量
            if unique_paths:
                path_list = [p["path"] for p in unique_paths]
                proc_env["CLAUDE_CODE_ALLOWED_PATHS"] = ";".join(path_list)

            # 为 read_only 路径追加提示词说明
            read_only_paths = [p["path"] for p in unique_paths if p["permission"] == "read_only"]
            if read_only_paths:
                read_only_note = "\n\n【文件访问说明】\n以下路径仅允许读取，不允许修改任何文件：\n"
                for rp in read_only_paths:
                    read_only_note += f"- {rp}\n"
                full_prompt += read_only_note
            # ---- 路径权限合并结束 ----

            cmd = subprocess.list2cmdline(args)
```

同时需要修改 cwd 变量的赋值，用新的 `cwd_override` 替换原来的 `cwd`：

```python
            # 原来的 cwd 赋值替换为：
            cwd = cwd_override
```

- [ ] **添加 `import json` 到文件头部**

```python
import asyncio
import os
import re
import json  # 添加
import subprocess
```

- [ ] **验证**

```bash
cd backend && python -c "from app.services.agent_engine import agent_engine; print('OK')"
```
期望输出: `OK`

- [ ] **Commit**

```bash
git add backend/app/services/agent_engine.py
git commit -m "feat: merge card and swimlane paths into CLAUDE_CODE_ALLOWED_PATHS"
```

---

### Task 8: SwimlaneConfig.vue 路径权限 UI

**Files:**
- Modify: `frontend/src/components/SwimlaneConfig.vue`

在现有的本地工作目录输入框下增加权限下拉框和额外可访问路径列表。

- [ ] **添加权限下拉框** — 在 `local_path` 行下方：

```html
            <div class="form-group">
              <label>本地工作目录</label>
              <div class="path-row">
                <input v-model="swimlane.local_path" placeholder="留空使用全局配置，例如 D:\my-project" />
                <button class="btn-sm btn-browse" type="button" @click="openBrowser(swimlane)">选择</button>
              </div>
              <div class="permission-row">
                <span class="field-hint">配置后将在该目录启动 Claude，使用该目录的 CLAUDE.md 等配置</span>
                <select v-model="swimlane.local_path_permission" class="permission-select">
                  <option value="read_write">读写权限</option>
                  <option value="read_only">只读权限</option>
                </select>
              </div>
            </div>
```

- [ ] **添加 CSS**：

```css
.permission-row { display: flex; align-items: center; justify-content: space-between; margin-top: 4px; }
.permission-select { font-size: 12px; padding: 3px 6px; border: 1px solid #ddd; border-radius: 4px; }
```

- [ ] **添加额外可访问路径 UI** — 在 `local_path` 组之后、`</div>` 之前：

```html
            <div class="form-group extra-paths">
              <label>额外可访问路径</label>
              <div v-for="(ap, apIdx) in swimlane.allowed_paths_arr" :key="apIdx" class="extra-path-row">
                <input v-model="ap.path" class="extra-path-input" placeholder="D:\other\path" />
                <select v-model="ap.permission" class="permission-select">
                  <option value="read_write">读写</option>
                  <option value="read_only">只读</option>
                </select>
                <button class="btn-sm btn-danger" type="button" @click="removeExtraPath(swimlane, apIdx)">×</button>
              </div>
              <button class="btn-sm btn-browse" type="button" @click="addExtraPath(swimlane)">+ 添加路径</button>
            </div>
```

- [ ] **添加 CSS**：

```css
.extra-paths { margin-top: 8px; }
.extra-path-row { display: flex; gap: 6px; margin-bottom: 6px; }
.extra-path-input { flex: 1; padding: 6px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; outline: none; }
```

- [ ] **修改 script 部分的 `addSwimlane()`** — 初始化新字段：

```javascript
function addSwimlane() {
  localSwimlanes.value.push({
    id: '__new__' + Date.now(),
    name: '',
    prompt: '',
    skill: '',
    tools: '[]',
    flow_mode: 'auto',
    local_path: '',
    local_path_permission: 'read_write',
    allowed_paths: '[]',
    allowed_paths_arr: [],
  })
}
```

- [ ] **添加 `allowed_paths` 与 `allowed_paths_arr` 的同步逻辑**

在 `localSwimlanes` 初始化后，为每个泳道解析 `allowed_paths` JSON 到 `allowed_paths_arr`；保存时反向序列化回 JSON。

在 `<script>` 中添加工具函数：

```javascript
function parseAllowedPaths(sw) {
  try {
    const parsed = JSON.parse(sw.allowed_paths || '[]')
    sw.allowed_paths_arr = Array.isArray(parsed) ? parsed : []
  } catch {
    sw.allowed_paths_arr = []
  }
}

function serializeAllowedPaths(sw) {
  sw.allowed_paths = JSON.stringify(sw.allowed_paths_arr || [])
}
```

在 `localSwimlanes` 初始化后遍历解析：

```javascript
const raw = JSON.parse(JSON.stringify(props.swimlanes))
raw.forEach(sw => {
  if (!sw.local_path_permission) sw.local_path_permission = 'read_write'
  if (!sw.allowed_paths) sw.allowed_paths = '[]'
  parseAllowedPaths(sw)
})
localSwimlanes.value = raw
```

- [ ] **添加 `addExtraPath` 和 `removeExtraPath` 函数**：

```javascript
function addExtraPath(swimlane) {
  if (!swimlane.allowed_paths_arr) swimlane.allowed_paths_arr = []
  swimlane.allowed_paths_arr.push({ path: '', permission: 'read_only' })
}

function removeExtraPath(swimlane, idx) {
  swimlane.allowed_paths_arr.splice(idx, 1)
}
```

- [ ] **修改 `save()` 函数** — 在保存前序列化 `allowed_paths_arr`：

```javascript
async function save() {
  for (const s of localSwimlanes.value) {
    serializeAllowedPaths(s)
    // ... existing save logic
  }
}
```

确保 `addSwimlane` 和 `updateSwimlane` 调用时包含新字段：

```javascript
      await kanbanStore.addSwimlane(props.kanbanId, {
        name: s.name, prompt: s.prompt, skill: s.skill || null,
        flow_mode: s.flow_mode,
        local_path: s.local_path || null,
        wait_for_reply: s.wait_for_reply || '0',
        local_path_permission: s.local_path_permission || 'read_write',
        allowed_paths: s.allowed_paths || '[]',
      })
```

```javascript
      await kanbanStore.updateSwimlane(s.id, {
        name: s.name, prompt: s.prompt, skill: s.skill || null,
        flow_mode: s.flow_mode,
        local_path: s.local_path || null,
        wait_for_reply: s.wait_for_reply || '0',
        local_path_permission: s.local_path_permission || 'read_write',
        allowed_paths: s.allowed_paths || '[]',
      })
```

- [ ] **Commit**

```bash
git add frontend/src/components/SwimlaneConfig.vue
git commit -m "feat: add path permission UI to swimlane config"
```

---

### Task 9: CreateCardDialog.vue 路径配置

**Files:**
- Modify: `frontend/src/components/CreateCardDialog.vue`

在表单底部新增可折叠的「路径配置」区域。

- [ ] **添加折叠面板 UI** — 在 `目标泳道` 选择框之后、按钮之前：

```html
        <div class="form-group">
          <div class="collapse-header" @click="showPathConfig = !showPathConfig">
            <span>{{ showPathConfig ? '▾' : '▸' }} 路径配置</span>
            <span class="field-hint">设置 Claude 可访问的文件目录和权限</span>
          </div>
          <div v-if="showPathConfig" class="collapse-body">
            <div class="form-group">
              <label>工作目录</label>
              <input v-model="localPath" placeholder="例如 D:\my-project" />
            </div>
            <div class="form-group">
              <label>目录权限</label>
              <select v-model="localPathPermission">
                <option value="read_write">读写权限</option>
                <option value="read_only">只读权限</option>
              </select>
            </div>
            <div class="form-group">
              <label>额外可访问路径</label>
              <div v-for="(ap, idx) in allowedPathsArr" :key="idx" class="extra-path-row">
                <input v-model="ap.path" class="extra-path-input" placeholder="D:\other\path" />
                <select v-model="ap.permission" class="perm-select">
                  <option value="read_write">读写</option>
                  <option value="read_only">只读</option>
                </select>
                <button class="btn-sm btn-danger" type="button" @click="allowedPathsArr.splice(idx, 1)">×</button>
              </div>
              <button class="btn-sm btn-browse" type="button" @click="allowedPathsArr.push({ path: '', permission: 'read_only' })">+ 添加路径</button>
            </div>
          </div>
        </div>
```

- [ ] **添加 CSS**：

```css
.collapse-header { display: flex; align-items: center; gap: 8px; cursor: pointer; padding: 8px 0; user-select: none; }
.collapse-header:hover { color: #3498db; }
.collapse-body { padding: 12px; background: #f8f9fa; border-radius: 8px; margin-top: 4px; }
.extra-path-row { display: flex; gap: 6px; margin-bottom: 6px; }
.extra-path-input { flex: 1; padding: 6px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; }
.perm-select { font-size: 12px; padding: 3px 6px; border: 1px solid #ddd; border-radius: 4px; }
```

- [ ] **添加响应式变量和提交逻辑**

在 `<script setup>` 中添加：

```javascript
const showPathConfig = ref(false)
const localPath = ref('')
const localPathPermission = ref('read_write')
const allowedPathsArr = ref([])
```

修改 `submit()` 函数，传递路径字段：

```javascript
async function submit() {
  await cardStore.create(props.kanbanId, {
    title: title.value,
    content: content.value,
    model: model.value,
    target_swimlane_id: targetSwimlaneId.value,
    local_path: localPath.value || null,
    local_path_permission: localPathPermission.value,
    allowed_paths: JSON.stringify(allowedPathsArr.value),
  })
  emit('created')
}
```

- [ ] **Commit**

```bash
git add frontend/src/components/CreateCardDialog.vue
git commit -m "feat: add path config section to create card dialog"
```

---

### Task 10: CardDetailModal.vue 路径信息显示

**Files:**
- Modify: `frontend/src/components/CardDetailModal.vue`

在卡片详情左侧面板中，新增路径配置显示区域。

- [ ] **添加路径信息显示** — 在 `Claude Session` 字段之后、提示词区域之前：

```html
            <div v-if="card.local_path || hasExtraPaths" class="detail-field">
              <label>文件访问路径</label>
              <div class="path-info">
                <div v-if="card.local_path" class="path-info-item">
                  <span class="path-info-label">工作目录：</span>
                  <span class="path-info-value">{{ card.local_path }}</span>
                  <span class="perm-badge" :class="card.local_path_permission || 'read_write'">
                    {{ (card.local_path_permission || 'read_write') === 'read_write' ? '读写' : '只读' }}
                  </span>
                </div>
                <div v-for="(ap, idx) in parsedAllowedPaths" :key="idx" class="path-info-item">
                  <span class="path-info-label">额外路径：</span>
                  <span class="path-info-value">{{ ap.path }}</span>
                  <span class="perm-badge" :class="ap.permission">
                    {{ ap.permission === 'read_write' ? '读写' : '只读' }}
                  </span>
                </div>
              </div>
            </div>
```

- [ ] **添加 computed 属性** — 在 `<script setup>` 中：

```javascript
const hasExtraPaths = computed(() => {
  return parsedAllowedPaths.value.length > 0
})

const parsedAllowedPaths = computed(() => {
  try {
    const raw = props.card.allowed_paths || '[]'
    return JSON.parse(raw)
  } catch {
    return []
  }
})
```

- [ ] **添加 CSS**：

```css
.path-info { display: flex; flex-direction: column; gap: 4px; }
.path-info-item { display: flex; align-items: center; gap: 6px; font-size: 13px; flex-wrap: wrap; }
.path-info-label { color: #95a5a6; white-space: nowrap; }
.path-info-value { font-family: monospace; color: #2c3e50; word-break: break-all; }
.perm-badge { font-size: 11px; padding: 1px 6px; border-radius: 4px; font-weight: 600; white-space: nowrap; }
.perm-badge.read_write { color: #27ae60; background: #d5f5e3; }
.perm-badge.read_only { color: #e67e22; background: #fdebd0; }
```

- [ ] **Commit**

```bash
git add frontend/src/components/CardDetailModal.vue
git commit -m "feat: show path permissions in card detail modal"
```

---

### Task 11: 完整验证

- [ ] **后端启动测试**

```bash
cd backend && python -c "
from app.models.card import Card
from app.models.kanban import Swimlane
from app.schemas.card import CardCreate, CardResponse
from app.schemas.kanban import SwimlaneBrief, SwimlaneCreate, SwimlaneUpdate, SwimlaneResponse
from app.services.card_service import CardService
from app.services.kanban_service import SwimlaneService
from app.services.agent_engine import agent_engine
print('All imports OK')
"
```
期望输出: `All imports OK`

- [ ] **前端构建检查**

```bash
cd frontend && npx vite build 2>&1 | tail -5
```
期望输出: 无错误，显示构建成功

- [ ] **最终 Commit**

```bash
git add -A
git commit -m "feat: complete path permissions for cards and swimlanes"
```
