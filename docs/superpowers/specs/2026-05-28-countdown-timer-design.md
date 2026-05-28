# 侧边栏定时任务倒计时 — 设计文档

## 概述

在 MultiAgent 看板系统的侧边栏（Layout.vue）中，显示距离最近一个定时看板任务执行时间的实时倒计时。

## 架构

采用后端提供 `next_run_time`、前端本地倒计时的轻量方案：

```
┌─────────────────────┐     GET /api/schedules       ┌──────────────────────┐
│   APScheduler       │  ─────────────────────────▶   │   schedule router    │
│   (schedule_engine) │  ◀────────────────────────    │                      │
│                     │   返回含 next_run_time 的列表  │                      │
└─────────────────────┘                               └──────────────────────┘
                                                               │
                                                               ▼
┌─────────────────────┐                               ┌──────────────────────┐
│   Layout.vue        │  ◀── 读取 store 最近任务 ───  │   schedule.js        │
│   (侧边栏倒计时组件)  │                               │   (Pinia store)      │
│   setInterval(1s)   │                               │   schedules[]        │
└─────────────────────┘                               └──────────────────────┘
```

## 改动清单

### 1. 后端 — `services/schedule_engine.py`

新增 `get_next_run_time(schedule_id: str) -> str | None` 方法，从 APScheduler 中获取指定 job 的下一次执行时间。

```python
def get_next_run_time(self, schedule_id: str) -> str | None:
    job = self.scheduler.get_job(schedule_id)
    if job and job.next_run_time:
        return job.next_run_time.isoformat()
    return None
```

### 2. 后端 — `schemas/schedule.py`

`ScheduleResponse` 增加可选字段：

```python
next_run_time: Optional[str] = None
```

### 3. 后端 — `routers/schedules.py`

在 `list_schedules`、`create_schedule`、`update_schedule` 三个路由中，通过 `schedule_engine.get_next_run_time(s.id)` 获取并填充 `next_run_time` 字段。

### 4. 前端 — `components/Layout.vue`

在侧边栏导航项下方添加倒计时显示区域：

- 使用 `useScheduleStore` 获取 schedules 列表
- `onMounted` 时调用 `scheduleStore.fetchAll()` 并设置定时刷新（每 60 秒一次）
- 计算属性 `nearestSchedule`：从 enabled 且 next_run_time 非空的 schedule 中选最近的一条
- 使用 `setInterval(1000)` 每秒更新倒计时字符串
- 倒计时归零时自动刷新 store

#### 显示逻辑

```
┌──────────────────────┐
│   📋 看板             │
│   ✅ 审批   (N)       │
│   ⏰ 定时任务          │
│   📄 日志             │
│──────────────────────│
│   ⏱ 下一任务          │
│   02:35:18           │  ← 红色粗体，每秒刷新
│   测试任务-数据采集    │  ← 灰色小字，任务名称
└──────────────────────┘
```

- 倒计时文本格式：`HH:MM:SS`（如 `02:35:18`）
- 当无 enabled 任务时，隐藏整个倒计时区域
- 当倒计时超过 24 小时，显示天数 + 时间（如 `1天 03:22:15`）

## 边界情况

| 场景 | 行为 |
|------|------|
| 无任何定时任务 | 隐藏倒计时区域 |
| 所有任务已禁用 | 隐藏倒计时区域 |
| 定时任务存在但无 next_run_time | 忽略该任务 |
| 倒计时归零 | 自动触发 store 刷新，获取最新 next_run_time |
| 任务被删除/禁用 | 下一次 store 刷新（60s 内）自动更新显示 |

## 未涉及的范围

- 不改动 WebSocket 逻辑（依赖定时刷新 store）
- 不改动 ScheduleManager 页面（仅侧边栏新增）
- 不新增后端 API（复用现有 GET /api/schedules）
