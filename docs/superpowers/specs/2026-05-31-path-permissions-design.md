# 路径权限配置设计

## 概述

为 MultiAgent Kanban 系统的泳道和卡片增加文件路径权限配置，解决 Claude CLI 在工作目录下无法访问文件的问题。

## 数据模型

### Card 表新增字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `local_path` | String, nullable | None | 卡片级工作目录 |
| `local_path_permission` | String | `"read_write"` | `"read_only"` / `"read_write"` |
| `allowed_paths` | Text | `"[]"` | JSON 数组，元素 `{"path":"...","permission":"read_only"\|"read_write"}` |

### Swimlane 表新增字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `local_path_permission` | String | `"read_write"` | `"read_only"` / `"read_write"`（`local_path` 字段已有） |
| `allowed_paths` | Text | `"[]"` | JSON 数组，元素 `{"path":"...","permission":"read_only"\|"read_write"}` |

## 后端改动

### Schema（Pydantic）

- `CardCreate` / `CardUpdate` / `CardResponse`: 新增 `local_path`, `local_path_permission`, `allowed_paths`
- `SwimlaneCreate` / `SwimlaneUpdate` / `SwimlaneResponse` / `SwimlaneBrief`: 新增 `local_path_permission`, `allowed_paths`

### Service

- `CardService.create_card()`: 透传新字段
- `CardService.update_card()`: 透传新字段（已通用）
- `SwimlaneService.add_swimlane()`: 透传新字段
- `SwimlaneService.update()`: 透传新字段（已通用）

### AgentEngine

- `execute_card()`: 读取卡片和泳道的路径配置，合并所有路径
- `_build_allowed_paths_env()`: 新方法，构建 `CLAUDE_CODE_ALLOWED_PATHS` 环境变量
- 工作目录优先级：`卡片.local_path` > `泳道.local_path` > None
- read_only 路径：在提示词末尾追加 `【文件访问说明】` 段落

### Database 迁移

- `database.py`: 新增 `_add_card_local_path()`, `_add_card_allowed_paths()`, `_add_swimlane_local_path_permission()`, `_add_swimlane_allowed_paths()` 迁移函数

## 前端改动

### SwimlaneConfig.vue

在现有的目录选择器和路径输入框旁增加：
- 权限下拉框（只读 / 读写）
- 额外可访问路径列表，每个条目包含路径 + 权限下拉 + 删除按钮
- 添加路径按钮，复用目录浏览器

### CreateCardDialog.vue

- 新增可折叠的「路径配置」区域
- 工作目录 + 权限 + 额外路径列表（结构与泳道配置相同）
- 复用目录浏览器组件

### CardDetailModal.vue

- 在编辑模式下显示路径配置
- 查看模式下显示路径和权限概要
- 编辑模式下可修改

### 目录浏览器

- 复用现有 SwimlaneConfig 中的 browse-dialog
- 可提取为独立组件供多处复用

## 运行时行为

```
AgentEngine.execute_card():
  1. 读取卡片路径配置（local_path, local_path_permission, allowed_paths）
  2. 读取泳道路径配置（local_path, local_path_permission, allowed_paths）
  3. 合并所有路径：
     - cwd = card.local_path ?? swimlane.local_path ?? None
     - CLAUDE_CODE_ALLOWED_PATHS 包含所有路径
  4. 对 read_only 路径，在提示词末尾追加只读说明
  5. 启动 Claude 子进程
```

## 未涉及

- 前端目录浏览器提取为独立组件（可后续优化，当前在各组件内保留实现）
- Claude CLI 的 `CLAUDE_CODE_ALLOWED_TOOLS` 限制（当前仅使用 `CLAUDE_CODE_ALLOWED_PATHS` + 提示词约束）
