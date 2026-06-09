# MCP AI Control Design

## 概述

将 MultiAgent Kanban 系统所有操作改造为 AI 可控。通过内嵌 MCP Server，既为编排泳道提供 Tool Use 能力，也对外暴露给 Claude Desktop 等客户端。

## 架构

```
FastAPI 应用 (port 8000)
├── REST API /api/*          (不变)
├── WebSocket /ws             (不变)
├── MCP Server
│   ├── GET  /mcp            (SSE 连接端点)
│   └── POST /mcp            (Client Message 端点)
│
│   所有 MCP tools → 直接调用 Service 层
│   (KanbanService, CardService, ApprovalService, etc.)
│
├── Swimlane 新增字段: swimlane_type
│   - "normal"       → 现有行为，纯 prompt 执行
│   - "orchestrator" → 注入 MCP tools，可调用系统 API
│
└── AgentEngine 修改
    - orchestrator 泳道执行时:
      claude --mcp-servers "http://127.0.0.1:8000/mcp" ...
    - normal 泳道行为不变
```

## Tools 清单

### Kanban 管理
| Tool | 参数 | 说明 |
|------|------|------|
| `list_kanbans` | - | 列出所有看板 |
| `get_kanban` | `kanban_id: str` | 获取看板详情（含泳道） |
| `create_kanban` | `name: str, description?: str` | 创建看板 |
| `update_kanban` | `kanban_id: str, name?: str, description?: str` | 更新看板 |
| `delete_kanban` | `kanban_id: str` | 删除看板 |

### Swimlane 管理
| Tool | 参数 | 说明 |
|------|------|------|
| `add_swimlane` | `kanban_id, name, prompt, flow_mode, skill?, swimlane_type?, ...` | 添加泳道 |
| `update_swimlane` | `swimlane_id, ...` | 更新泳道 |
| `delete_swimlane` | `swimlane_id: str` | 删除泳道 |
| `reorder_swimlanes` | `kanban_id: str, swimlane_ids: str[]` | 重新排序 |

### Card 管理
| Tool | 参数 | 说明 |
|------|------|------|
| `list_cards` | `kanban_id?, swimlane_id?, status?` | 列出卡片 |
| `get_card` | `card_id: str` | 获取卡片详情 |
| `create_card` | `kanban_id, title, content?, target_swimlane_id?` | 创建卡片 |
| `update_card` | `card_id, title?, content?, status?` | 更新卡片 |
| `delete_card` | `card_id: str` | 删除卡片 |
| `move_card` | `card_id: str, target_swimlane_id: str` | 移动卡片到其他泳道 |
| `get_card_logs` | `card_id: str` | 获取卡片执行日志 |

### 审批 & 回复
| Tool | 参数 | 说明 |
|------|------|------|
| `list_pending_approvals` | - | 列出待审批卡片 |
| `approve_card` | `card_id: str, note?: str` | 审批通过 |
| `reject_card` | `card_id: str, note?: str` | 审批驳回 |
| `reply_to_card` | `card_id: str, reply: str` | 回复等待回复的卡片 |

### 定时任务
| Tool | 参数 | 说明 |
|------|------|------|
| `list_schedules` | - | 列出所有定时任务 |
| `create_schedule` | `cron_expr, card_title, target_kanban_id, ...` | 创建定时任务 |
| `update_schedule` | `schedule_id, ...` | 更新定时任务 |
| `delete_schedule` | `schedule_id: str` | 删除定时任务 |
| `toggle_schedule` | `schedule_id: str` | 启用/禁用定时任务 |

### 设置 & 系统
| Tool | 参数 | 说明 |
|------|------|------|
| `list_settings` | - | 列出所有设置 |
| `get_setting` | `key: str` | 获取设置 |
| `update_setting` | `key: str, value: str` | 更新设置 |
| `get_system_status` | - | 系统状态（活跃卡片数、队列长度等） |

## 编排泳道执行流程

```
1. _card_picker_loop 选取 pending 卡片
       │
2. 获取卡片的当前泳道 swimlane
       │
3. 检查 swimlane.swimlane_type
       │
       ├── "normal" → 现有流程 (execute_card)
       │
       └── "orchestrator"
            ├── _build_claude_args() 添加 --mcp-servers "http://127.0.0.1:8000/mcp"
            ├── prompt 追加指令："你可以调用以下工具来管理系统..."
            ├── 启动 Claude CLI 子进程（带 MCP 连接）
            ├── Claude 可通过工具调用：创建卡片、审批、修改配置等
            ├── 子进程退出后
            │   ├── exit_code=0 → handle_swimlane_completion()
            │   └── exit_code≠0 → errored
            └── 同现有清理流程
```

## 外部客户端连接

外部 Claude Desktop 客户端可通过 `http://<host>:8000/mcp` 连接 MCP Server，获得全部工具操作看板系统。

## 实现步骤

1. **添加依赖**：`mcp` Python 包
2. **创建 MCP Server**：`backend/app/mcp_server.py` — 所有 Tool 实现
3. **注册到 FastAPI**：`main.py` — 挂载 MCP SSE 端点
4. **Swimlane 模型迁移**：添加 `swimlane_type` 字段，默认 `"normal"`
5. **AgentEngine 改造**：编排泳道执行时注入 `--mcp-servers`
6. **前端适配**：泳道编辑页面显示 swimlane_type 选项
7. **前端显示**：看板视图标识编排泳道

## 不变的部分

- 所有现有的 REST API、WebSocket、Service 层完全不变
- 普通泳道（normal）的行为完全不变
- 数据库现有迁移逻辑不变
- 前端现有功能不变（仅新增编排泳道标识）
