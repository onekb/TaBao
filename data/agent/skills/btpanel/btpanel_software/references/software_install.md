# 软件商店安装

宝塔面板软件商店查询、安装、状态和日志查看指南。本技能只安装普通软件/插件和运行环境管理器插件，不安装具体运行环境版本。

---

## 可用方法

| 方法 | 作用 | 对应脚本命令 | 返回内容 |
|------|------|-------------|----------|
| `list` | 查询软件商店列表，可按关键词过滤 | `btpython scripts/software.py list --query nginx` | JSON，包含匹配软件列表 |
| `find` | 查询指定软件信息和可用版本 | `btpython scripts/software.py find --name nginx` | JSON，包含软件详情和版本列表 |
| `install` | 创建软件安装任务（自动等待完成） | `btpython scripts/software.py install --name nginx --version 1.28` | JSON，包含 msg_id、安装结果 |
| `status` | 查询指定安装任务状态 | `btpython scripts/software.py status --msg-id <msg_id>` | JSON，包含 msg_id、task_id、软件名、状态码、状态描述、日志文件路径 |
| `status` | 通过任务 ID 查询状态 | `btpython scripts/software.py status --task-id <task_id>` | JSON，同上 |
| `log` | 查看指定安装任务日志 | `btpython scripts/software.py log --msg-id <msg_id> --lines 100` | JSON，包含日志文件路径、总行数、日志内容 |
| `log` | 通过任务 ID 查看日志 | `btpython scripts/software.py log --task-id <task_id> --lines 100` | JSON，同上 |

---

## 安装入口

安装必须调用面板原生方法：

```python
import panelPlugin

result = panelPlugin.panelPlugin().install_plugin(get)
```

不要直接写 `tasks` 表。`install_plugin()` 内部会完成依赖检查、互斥检查、系统限制检查、任务创建、日志初始化、任务触发和消息创建等业务逻辑。

---

## 运行环境边界

本技能禁止安装具体运行环境版本：

| 禁止示例 | 正确技能 |
|----------|----------|
| 安装 PHP 8.3 | `btpanel_runtime` |
| 安装 JDK 17 | `btpanel_runtime` |
| 安装 Node.js 20 | `btpanel_runtime` |
| 安装 Go 1.22 | `btpanel_runtime` |
| 安装 Python 3.12 | `btpanel_runtime` |
| 安装 .NET 8 | `btpanel_runtime` |

本技能允许安装运行环境管理器插件：

| 允许示例 | 说明 |
|----------|------|
| `nodejs` | Node.js 版本管理器插件 |
| `pythonmamager` | Python 版本管理器/项目管理插件 |
| `java_manager` | Java/JDK 管理器插件 |
| `golangmanager` | Go 版本管理器插件 |
| `dotnet` | .NET 管理器插件 |

如果用户要安装具体版本，应切换到 `btpanel_runtime`，由运行环境管理技能先确保管理器存在，再调用面板项目模型或插件方法安装具体版本。

---

## Flask / session 上下文

`panelPlugin.py` 中的 session 来源是：

```python
from BTPanel import session, cache, send_file
```

脚本调用面板方法前必须创建 Flask request context，并使用 `BTPanel.session`：

```python
from BTPanel import app, session

with app.test_request_context('/plugin?action=install_plugin', method='POST'):
    session['uid'] = 1
    session['login'] = True
    session['download_url'] = public.GetConfigValue('download') or public.get_url()
    session['rootPath'] = '/www'
    session['setupPath'] = '/www/server'
```

然后调用 `common.panelAdmin` 的基础初始化方法补齐源码依赖：

```python
from common import panelAdmin

admin = panelAdmin()
admin.setSession()
admin.checkWebType()
admin.checkConfig()
admin.GetOS()
```

不要在无 request context 的情况下直接 import 后调用 `panelPlugin.install_plugin()`，否则可能出现 `Working outside of request context`、`KeyError: 'server_os'`、`KeyError: 'download_url'` 等错误。

---

## install 参数

```bash
btpython scripts/software.py install --name <软件名> [--version <版本>] [--type 0] [--force false]
```

| 参数 | 必填 | 说明 | 默认值 |
|------|:--:|------|--------|
| `name` | 是 | 软件内部名称，如 `nginx`、`mysql`、`php`、`redis`、`phpmyadmin` | 无 |
| `version` | 否 | 目标版本。指定时必须存在；未指定时自动选择最新版 | 自动选择最新版 |
| `type` | 否 | 安装方式，传给面板原生方法。`0` 通常表示极速安装，源码会按系统调整 | `0` |
| `force` | 否 | 是否强制忽略部分资源限制 | `false` |

脚本会把参数转换为面板原生方法需要的字段：

```python
{
    "sName": "nginx",
    "version": "1.28",
    "min_version": "",
    "type": "0",
    "force": "false"
}
```

---

## 版本规则

### 用户指定版本

1. 先查询 `find --name <软件名>` 获取版本列表
2. 将用户输入与以下候选值匹配：
   - `m_version`
   - `m_version.version`
   - `version`
3. 匹配成功后传入对应的 `m_version` 和 `version`
4. 匹配失败时停止安装，返回可用版本列表让用户确认

### 用户未指定版本

默认选择最新版：

1. 优先从版本列表中选择纯数字语义版本的最大值，例如 `8.3 > 8.2 > 7.4`
2. `mariadb_10.5`、`openresty`、`Tengine`、`AliSQL` 等分支版本不与主线数字版本混选，除非用户明确指定
3. 如果没有纯数字语义版本，则使用软件商店返回的第一个可安装版本，并在输出中说明选择来源

---

## 安装流程

1. 初始化 `/www/server/panel` 运行环境和 `BTPanel.session`
2. 调用 `panelPlugin.panelPlugin().get_soft_find()` 查询软件详情
3. 解析用户指定版本或默认最新版
4. 调用 `panelPlugin.panelPlugin().install_plugin()` 创建安装任务
5. 脚本自动等待任务完成，返回 `msg_id` 和安装结果
6. 如需再次查询状态或日志，使用返回的 `msg_id`

---

## 状态与日志

安装命令执行后会自动等待任务完成，并返回以下信息：

```json
{
  "selected": {
    "name": "mysql",
    "version": "5.7.44",
    "m_version": "5.7",
    "min_version": "44",
    "source": "specified"
  },
  "install_args": {...},
  "result": {
    "status": true,
    "msg_id": "93e66640a0a2704b",
    "msg": "已将安装任务添加到队列!"
  },
  "install_result": {
    "status": true,
    "msg": "安装mysql-5.7已结束",
    "soft_name": "mysql-5.7",
    "install_status": "安装mysql-5.7结束",
    "file_name": "/www/server/panel/logs/installed/mysql-5.7_xxx.log",
    "task_id": 82
  }
}
```

如需再次查询状态，使用返回的 `msg_id`：

```bash
btpython scripts/software.py status --msg-id 93e66640a0a2704b
```

或使用任务 ID：

```bash
btpython scripts/software.py status --task-id 82
```

查看安装日志：

```bash
btpython scripts/software.py log --msg-id 93e66640a0a2704b --lines 100
```

或通过任务 ID：

```bash
btpython scripts/software.py log --task-id 82 --lines 100
```

`status` 和 `log` 通过消息盒子系统查询指定任务的状态和日志，而不是查询当前后台执行的任务（可能是其他程序添加的任务）。

---

## 常见错误

| 错误 | 原因 | 处理建议 |
|------|------|----------|
| `Working outside of request context` | 未创建 Flask request context | 使用脚本提供的上下文初始化，不要直接调用面板类 |
| `KeyError: 'server_os'` | session 未补齐系统信息 | 调用 `panelAdmin().GetOS()` |
| `KeyError: 'download_url'` | session 未补齐下载节点 | 设置 `session['download_url']` |
| `指定插件不存在` | 软件名不正确或软件列表未刷新 | 使用 `list --query <关键词>` 查找内部名称 |
| `依赖以下软件` | 缺少依赖软件 | 先安装返回信息中的依赖软件 |
| `请到[软件商店]先卸载` | 存在互斥软件 | 需要用户确认后处理互斥软件 |
| `至少需要...` | CPU/内存不满足版本要求 | 换版本或升级服务器配置 |
| `仅支持...系统` | 当前系统不满足软件版本限制 | 换版本或换系统 |
