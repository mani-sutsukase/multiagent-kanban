## 1. 项目脚手架

- [x] 1.1 初始化 Python 后端项目: 创建目录结构, requirements.txt (FastAPI, uvicorn, SQLAlchemy[asyncio], aiosqlite, alembic, APScheduler, pydantic)
- [x] 1.2 创建 FastAPI 应用入口 main.py, 添加 CORS 中间件, 基础异常处理
- [x] 1.3 初始化 Vue 3 前端项目: Vite + Vue 3 + Pinia + Vue Router, 配置代理转发到后端
- [x] 1.4 创建后端 config.py 配置文件 (数据库路径, 最大并行进程数, claude.exe 路径等)
- [x] 1.5 创建数据库初始化模块 database.py (SQLAlchemy async engine + session 工厂)

## 2. 数据模型与数据库迁移

- [x] 2.1 定义 SQLAlchemy ORM 模型: Kanban, Swimlane, Card
- [x] 2.2 定义 SQLAlchemy ORM 模型: Log, Approval, Schedule, ScheduleLog
- [x] 2.3 配置 Alembic, 生成初始迁移, 创建 SQLite 数据库表
- [x] 2.4 定义 Pydantic schemas: KanbanCreate, KanbanUpdate, KanbanResponse
- [x] 2.5 定义 Pydantic schemas: SwimlaneCreate, SwimlaneUpdate, SwimlaneResponse, SwimlaneOrderRequest
- [x] 2.6 定义 Pydantic schemas: CardCreate, CardUpdate, CardResponse, CardStatusResponse
- [x] 2.7 定义 Pydantic schemas: LogResponse, ApprovalCreate, ApprovalResponse
- [x] 2.8 定义 Pydantic schemas: ScheduleCreate, ScheduleUpdate, ScheduleResponse, ScheduleLogResponse

## 3. 看板管理 API (后端)

- [x] 3.1 实现 KanbanService CRUD: create, get, list, update, delete (含 cascade 检查)
- [x] 3.2 实现 kanbans.py router: GET/POST /api/kanbans, GET/PUT/DELETE /api/kanbans/{id}
- [x] 3.3 实现 SwimlaneService: add_swimlane, update_swimlane, delete_swimlane (含运行中卡片保护)
- [x] 3.4 实现泳道排序: reorder_swimlanes (批量更新 sort_order)
- [x] 3.5 实现泳道路由: POST /api/kanbans/{id}/swimlanes, PUT/DELETE /api/swimlanes/{id}, PUT /api/swimlanes/order

## 4. 卡片管理 API (后端)

- [x] 4.1 实现 CardService CRUD: create_card (含自动分配到首泳道), get_card, update_card, delete_card
- [x] 4.2 实现卡片列表: list_cards_by_kanban (支持按泳道/状态过滤)
- [x] 4.3 实现 cards.py router: GET/POST /api/kanbans/{id}/cards, GET/PUT/DELETE /api/cards/{id}

## 5. 卡片引擎 (状态机)

- [x] 5.1 实现 CardEngine: advance_to_next_swimlane (卡片的跨泳道推进)
- [x] 5.2 实现 CardEngine: handle_swimlane_completion (Agent 完成后, 根据 flow_mode 决策: auto → 自动推进 / pre_approval → 等待审批)
- [x] 5.3 实现 CardEngine: handle_approval (批准后推进到下一泳道 / 非最后泳道检查)
- [x] 5.4 实现 CardEngine: handle_rejection (驳回后重置 card 状态为 running, 保存 rejection_note)
- [x] 5.5 实现 CardEngine: is_last_swimlane 判断逻辑

## 6. Agent 执行引擎

- [x] 6.1 实现 AgentEngine: _build_claude_args (组装 claude.exe CLI 参数: -p, --model, --skill, --resume)
- [x] 6.2 实现 AgentEngine: execute_card (使用 asyncio.create_subprocess_exec 启动子进程)
- [x] 6.3 实现 AgentEngine: _capture_output (流式读取 stdout/stderr, 逐行写入 LogService + WebSocket)
- [x] 6.4 实现 AgentEngine: _extract_session_id (从进程输出/环境捕获 session_id)
- [x] 6.5 实现 AgentEngine: 进程池并发控制 (asyncio.Semaphore, 可配 max_concurrent)
- [x] 6.6 实现 AgentEngine: _on_process_exit (exit_code 处理, 触发 CardEngine 流转决策)
- [x] 6.7 实现 AgentEngine: terminate_card (强制终止子进程, 用于删除运行中卡片)
- [x] 6.8 实现 AgentEngine: _ensure_claude_available (启动时校验 claude.exe 可执行)

## 7. 审批系统 API (后端)

- [x] 7.1 实现 ApprovalService: list_pending (查询所有 waiting_approval 卡片)
- [x] 7.2 实现 ApprovalService: approve (创建批准记录 + 触发卡片推进)
- [x] 7.3 实现 ApprovalService: reject (创建驳回记录 + 保存批注 + 触发重执行)
- [x] 7.4 实现 approvals.py router: GET /api/approvals/pending, POST /api/cards/{id}/approve, POST /api/cards/{id}/reject

## 8. 日志系统 (后端)

- [x] 8.1 实现 LogService: create_log (创建执行日志), update_log (更新结束信息)
- [x] 8.2 实现 LogService: append_output (追加 stdout/stderr 内容), get_log, get_card_logs
- [x] 8.3 实现 logs.py router: GET /api/cards/{id}/logs, GET /api/logs/{id}/stdout, GET /api/logs/{id}/stderr

## 9. WebSocket 实时推送

- [x] 9.1 实现 WebSocketManager: 管理连接池 (connect/disconnect/broadcast)
- [x] 9.2 实现 ws.py router: WebSocket 端点 /ws, 心跳检测, 自动重连
- [x] 9.3 后端集成: AgentEngine/ApprovalService 中调用 WebSocketManager 推送状态变更事件
- [x] 9.4 定义 WebSocket 事件类型: card_status_changed, card_log_update, card_needs_approval, card_completed, schedule_triggered

## 10. 定时任务系统

- [x] 10.1 实现 ScheduleService CRUD: create, get, list, update, delete (含 APScheduler 动态注册/移除)
- [x] 10.2 实现 ScheduleService: toggle (启用/停用, 对应 APScheduler add_job/pause_job)
- [x] 10.3 实现 ScheduleEngine: _create_card_from_template (触发时创建卡片)
- [x] 10.4 实现 ScheduleEngine: _log_execution (记录 schedule_logs)
- [x] 10.5 实现 ScheduleEngine: 应用启动时从数据库加载所有 enabled 任务
- [x] 10.6 实现 schedules.py router: GET/POST/PUT/DELETE /api/schedules, POST /api/schedules/{id}/toggle, GET /api/schedules/{id}/logs

## 11. 前端基础架构

- [x] 11.1 创建 Vue Router 配置: / (看板列表), /kanban/:id (看板详情), /approvals (审批面板), /schedules (定时任务)
- [x] 11.2 创建 Layout.vue: 侧边导航 + 主内容区, 导航项高亮, 审批面板未读数徽标
- [x] 11.3 创建 api/client.js: axios 实例配置 (baseURL, 错误拦截)
- [x] 11.4 创建前后端 API 调用封装: kanban.js, card.js, approval.js, schedule.js
- [x] 11.5 创建 composables/useWebSocket.js: WebSocket 连接管理, 自动重连, 事件分发
- [x] 11.6 创建 Pinia stores: kanbanStore, cardStore, approvalStore, scheduleStore

## 12. 前端看板管理页面

- [x] 12.1 实现 KanbanList.vue: 看板卡片列表, 显示名称/描述/泳道数/卡片数
- [x] 12.2 实现 CreateKanbanDialog.vue: 创建看板表单 (名称/描述)
- [x] 12.3 实现 KanbanView.vue: 看板详情页, 泳道横向排列, 显示泳道名称和卡片
- [x] 12.4 实现 SwimlaneColumn.vue: 泳道列组件, 显示该泳道所有卡片 (按状态分组)
- [x] 12.5 实现 CardItem.vue: 卡片组件, 显示标题/状态/模型, 可拖拽
- [x] 12.6 实现 CreateCardDialog.vue: 创建卡片表单 (标题/内容/模型/目标泳道)
- [x] 12.7 实现 SwimlaneConfig.vue: 泳道配置弹窗 (名称/prompt/skill/工具集/流转模式)
- [x] 12.8 实现 SwimlaneOrderEditor.vue: 泳道排序拖拽组件
- [x] 12.9 实现 KanbanSettings.vue: 看板设置面板 (编辑名称/描述, 删除看板)

## 13. 前端审批面板

- [x] 13.1 实现 ApprovalPanel.vue: 审批面板页, 卡片列表 (按看板分组, 显示泳道名)
- [x] 13.2 实现 ApprovalDetail.vue: 审批详情, 显示卡片内容 + 泳道提示词 + Agent 输出
- [x] 13.3 实现 LogViewer.vue: Agent 日志查看器 (stdout/stderr 分屏, 语法高亮, 自动滚动)
- [x] 13.4 实现 ApprovalActions.vue: 批准/驳回按钮, 驳回时弹出 RejectDialog
- [x] 13.5 实现 RejectDialog.vue: 驳回批注输入对话框 (必填)
- [x] 13.6 WebSocket 集成: 待审批计数实时更新, 新待审批卡片自动刷新

## 14. 前端定时任务管理

- [x] 14.1 实现 ScheduleManager.vue: 定时任务列表页 (显示 cron 表达式, 启用状态, 下次触发时间)
- [x] 14.2 实现 ScheduleForm.vue: 创建/编辑定时任务表单 (名称/cron/卡片模板/目标看板+泳道)
- [x] 14.3 实现 ScheduleLogList.vue: 执行历史列表 (触发时间, 创建卡片, 状态)

## 15. 前端卡片详情与日志

- [x] 15.1 实现卡片详情弹窗: 显示卡片信息 + 执行时间线
- [x] 15.2 实现 LogTimeline.vue: 泳道流转时间线组件 (每个泳道 + 每次尝试)
- [x] 15.3 实现 LogContent.vue: stdout/stderr 内容展示 (自动滚动, 行号)

## 16. 前后端集成与联调

- [x] 16.1 前端配置 Vite 代理到后端 FastAPI 开发服务器
- [ ] 16.2 端到端联调: 创建看板 → 配置泳道 → 创建卡片 → Agent 执行 → 查看日志 → 审批
- [ ] 16.3 端到端联调: 定时任务 → 自动创建卡片 → 流水线执行
- [ ] 16.4 端到端联调: 驳回重做 → resume session → 重新执行

## 17. 错误处理与边界场景

- [x] 17.1 后端全局异常处理器 (数据库错误, 进程错误, 参数校验)
- [x] 17.2 Agent 进程崩溃/超时处理, 卡片置为 blocked 状态
- [x] 17.3 泳道删除/看板删除的前置校验 (运行中卡片保护)
- [ ] 17.4 定时任务错过触发时间的补偿处理
- [x] 17.5 前端网络异常/WebSocket 断连的恢复与提示
