## Why

企业员工在日常工作中经常面临重复性、多工序的任务流程（如内容审核、报告生成、代码审查等），每个工序需要不同的专业技能。现有方案要么依赖人工逐一处理，效率低下；要么需要复杂的 AI Agent 编排平台，学习成本高。

本系统将 **Kanban 看板的直观性** 与 **多 Agent 自动化流水线** 结合，让员工通过简单的看板配置，将重复性任务交给多个 Claude Code Agent 自动串行处理，同时保留关键节点的人工审批能力。

## What Changes

- **新建** 一个前后端分离的多 Agent 协作 Kanban 应用
- 后端使用 Python (FastAPI)，前端使用 Vue 3，数据库使用 SQLite，单人单机模式
- 引入 Agent 执行引擎，通过 `claude.exe` CLI 子进程驱动任务
- 引入定时任务调度器，支持 cron 表达式自动创建卡片

### 具体新增功能

| 功能 | 说明 |
|------|------|
| **看板管理** | 创建/编辑/删除看板，配置泳道流水线 |
| **泳道配置** | 每个泳道绑定固定 prompt、skill、工具集、流转模式 |
| **卡片管理** | 创建卡片（标题/内容/模型），卡片的看板内生命周期管理 |
| **卡片流转** | 全自动 / 执行前审批 / 执行后审批 三种流转模式 |
| **驳回重做** | 员工驳回 + 批注 → 使用 Claude Code session resume 继续对话 |
| **Agent 执行引擎** | 并行启动多个 claude.exe 子进程，捕获 stdout/stderr |
| **审批系统** | 查看 Agent 日志，批准/驳回操作 |
| **定时任务** | cron 表达式配置定时创建卡片 |
| **日志系统** | 每张卡片在每个泳道的完整执行轨迹 |

## Capabilities

### New Capabilities

- `kanban-management`: 看板的创建、编辑、删除，泳道的有序配置与调整
- `card-lifecycle`: 卡片的创建、状态机流转、跨泳道推进
- `card-flow-modes`: 三种流转模式（全自动、执行前审批、执行后审批）及驳回重做
- `agent-engine`: Claude Code CLI 子进程的启动、并行管理、会话恢复、日志捕获
- `approval-system`: 员工审批面板，Agent 日志查看，批注与驳回机制
- `scheduled-tasks`: cron 表达式配置的定时任务，自动创建卡片
- `logs`: 卡片执行轨迹记录与展示

### Modified Capabilities

<!-- 无已有 capability 需要修改 -->

## Impact

- 新建整个项目，无现有代码影响
- 依赖环境：需安装 `claude.exe` CLI（由 Anthropic Claude Code 提供）
- 运行时需访问 LLM API（通过 Claude Code 配置的 API key）
- 存储：SQLite 单文件数据库，默认存储在项目本地
