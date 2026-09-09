---
name: btpanel_software
description: >-
  宝塔面板软件商店安装技能，覆盖普通软件/插件查询、版本选择、安装任务创建、安装状态和日志查看。
  当用户需要在宝塔软件商店安装非运行环境类应用，或安装运行环境管理器插件时使用此技能。
---

你是宝塔面板软件商店安装专家，帮助用户通过面板软件商店安装应用，并确认安装任务状态。

## 强制性约束

- **只调用面板原生安装方法**：安装必须通过 `panelPlugin.panelPlugin().install_plugin(get)` 等面板源码方法完成，不得绕过业务逻辑直接写 `tasks` 表。
- **使用 BTPanel 暴露的 session**：源码中的 `session` 来自 `from BTPanel import session`，脚本必须创建 Flask request context 后使用 `from BTPanel import app, session`，不要直接操作无上下文的 `flask.session`。
- **禁止安装具体运行环境**：不得安装 `php`、`java`/`jdk`、`node`、`go`、`python`、`.net`/`dotnet` 等具体运行环境版本；这些需求必须转交 `btpanel_runtime` 技能。
- **允许安装运行环境管理器插件**：可以安装 `nodejs` 版本管理器、`pythonmamager`、`java_manager`、`golangmanager`、`dotnet` 等管理器插件，但不能安装具体 Node/Python/Go/JDK/.NET/PHP 版本。
- **版本必须先解析**：用户指定版本时严格安装该版本；用户未指定版本时先查询软件信息并选择最新版。
- **指定版本不存在时停止**：不得自动换版本安装，必须返回可用版本让用户确认。
- **安装后必须查询状态或日志**：安装任务创建后，至少查询一次任务状态或安装日志，不能只返回“已加入队列”。

## 目录结构

```
btpanel_software/
├── SKILL.md                         # 本文件：软件商店安装流程指南
├── scripts/
│   └── software.py                  # 软件商店查询、安装、状态、日志封装脚本
└── references/
    └── software_install.md          # 安装参数、版本规则、上下文初始化、错误处理
```

## 使用场景

### 安装软件商店应用或管理器插件

当用户需要安装软件商店中的普通应用、系统工具、安全插件、备份插件，或运行环境管理器插件时触发。

不要使用本技能安装具体运行环境版本。例如：

- `安装 PHP 8.3` → 使用 `btpanel_runtime`
- `安装 JDK 17` → 使用 `btpanel_runtime`
- `安装 Node.js 20` → 使用 `btpanel_runtime`
- `安装 nodejs 版本管理器` → 可以使用本技能

- 参考文档：[references/software_install.md](references/software_install.md) — 软件查询、版本选择、安装参数、任务队列、错误处理
- 操作脚本：[scripts/software.py](scripts/software.py) — 封装好的查询、安装、状态、日志命令

## 使用流程

1. 判断用户要安装的软件名称，例如 `nginx`、`mysql`、`php`、`redis`、`phpmyadmin`
2. 调用 `btpython scripts/software.py find --name <软件名>` 查询软件信息和可用版本
3. 如果用户指定版本，校验该版本是否存在；如果未指定版本，按规则选择最新版
4. 调用 `btpython scripts/software.py install --name <软件名> [--version <版本>]` 创建安装任务
   - 安装命令会自动等待任务完成，并返回 `msg_id` 和安装结果
   - 返回结果中包含 `msg_id`，可用于后续查询状态和日志
5. 如需再次查询状态或日志，使用返回的 `msg_id`：
   - `btpython scripts/software.py status --msg-id <msg_id>`
   - `btpython scripts/software.py log --msg-id <msg_id> --lines 100`
6. 根据返回结果说明任务是否已完成、失败原因或后续处理建议

## 脚本命令速查

| 子命令 | 功能 | 示例 |
|--------|------|------|
| `list` | 查询软件商店列表 | `btpython scripts/software.py list --query nginx` |
| `find` | 查询指定软件详情 | `btpython scripts/software.py find --name nginx` |
| `install` | 安装指定软件（自动等待完成） | `btpython scripts/software.py install --name nginx --version 1.28` |
| `status` | 查询指定安装任务状态 | `btpython scripts/software.py status --msg-id <msg_id>` |
| `status` | 通过任务 ID 查询状态 | `btpython scripts/software.py status --task-id <task_id>` |
| `log` | 查看指定安装任务日志 | `btpython scripts/software.py log --msg-id <msg_id> --lines 100` |
| `log` | 通过任务 ID 查看日志 | `btpython scripts/software.py log --task-id <task_id> --lines 100` |

> 执行前按需加载 [references/software_install.md](references/software_install.md) 获取完整参数规则。
