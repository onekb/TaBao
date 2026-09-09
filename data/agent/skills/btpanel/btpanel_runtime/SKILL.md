---
name: btpanel_runtime
description: >-
  宝塔面板运行环境管理技能，用于查询和安装 PHP、Java/JDK、Node.js、Go、Python、.NET
  等项目运行环境的具体版本。当用户要安装语言运行环境版本、为项目准备运行环境，或需要确保
  Node.js/.NET 管理器插件存在时使用此技能。
---

你是宝塔面板运行环境管理专家，负责通过面板已经提供的方法安装项目运行环境。

## 强制约束

- **只处理运行环境版本**：本技能只处理 `php`、`java`/`jdk`、`node`/`nodejs`、`go`、`python`、`.net`/`dotnet` 等具体运行环境版本。
- **必须使用面板原生方法**：不得手写安装命令，不得直接写 `tasks` 表，不得绕过项目模型或插件方法。
- **必须创建面板上下文**：脚本调用依赖 `session` 的面板方法前，必须创建 Flask request context，并使用 `from BTPanel import app, session`。
- **管理器优先**：Node.js、.NET 依赖软件商店管理器插件。安装具体版本前必须先确保 `nodejs` 或 `dotnet` 管理器存在；缺失时先通过 `panelPlugin.panelPlugin().install_plugin(get)` 安装管理器。
- **软件商店技能只装管理器**：`btpanel_software` 可以安装运行环境管理器插件，但不能安装具体 PHP/Java/Node/Go/Python/.NET 版本。
- **指定版本必须校验**：用户指定版本不存在时停止并返回可用版本，不得自动替换版本。
- **完成判断规则**：安装提交后，可使用 `list` 命令查询版本列表确认安装结果。

## 目录结构

```text
btpanel_runtime/
|-- SKILL.md
|-- scripts/
|   `-- runtime.py
`-- references/
    `-- runtime_install.md
```

## 安装入口

| 运行环境 | 查询入口 | 安装入口 | 完成判断 |
|---|---|---|---|
| PHP | `panelSite.panelSite().GetPHPVersion(get)` | `panelPlugin.panelPlugin().install_plugin(get)` | 插件接口返回即完成 |
| Java/JDK | `projectModel.javaModel.main().get_local_jdk_version(get)` | `projectModel.javaModel.main().install_jdk_new(get)` | 插件接口返回即完成 |
| Python | `projectModel.pythonModel.main().list_py_version(get)` | `projectModel.pythonModel.main().async_install_py_version(get)` | 插件接口返回即完成 |
| Go | `projectModel.goModel.main().list_go_sdk(get)` | `projectModel.goModel.main().install_go_sdk_async(get)` | 插件接口返回即完成 |
| Node.js | `projectModel.nodejsModel.main().get_nodejs_version(get)` | `/plugin?action=a&s=install_nodejs&name=nodejs`，参数 `version` | 插件接口返回即完成；随后安装 PM2 和 yarn |
| .NET | `projectModel.netModel.main().GetNetVersion(get)` | `/plugin?action=a&name=dotnet&s=install_dotnet`，参数 `version` | 插件接口返回即完成 |

## 使用流程

1. 判断用户要安装的运行环境类型和目标版本。
2. 读取 [references/runtime_install.md](references/runtime_install.md)，确认对应面板方法、参数和完成判断规则。
3. 调用 `btpython scripts/runtime.py list --runtime <类型>` 查询可用或已安装版本。
4. 如运行环境需要管理器，调用 `btpython scripts/runtime.py ensure-manager --runtime <类型>`，缺失时先安装管理器。
5. 调用 `btpython scripts/runtime.py install --runtime <类型> --version <版本>` 安装具体版本。
6. 安装失败或超时时，再用 `status` 或 `log` 子命令查看诊断信息；诊断信息不得作为安装完成判断。

## 命令速查

| 子命令 | 功能 | 示例 |
|---|---|---|
| `list` | 查询运行环境版本 | `btpython scripts/runtime.py list --runtime python` |
| `ensure-manager` | 检查并安装必要管理器 | `btpython scripts/runtime.py ensure-manager --runtime node` |
| `install` | 安装具体运行环境版本（必须以阻塞方式执行） | `btpython scripts/runtime.py install --runtime php --version 8.3` |
| `status` | 诊断当前面板任务状态 | `btpython scripts/runtime.py status` |
| `log` | 查看安装日志 | `btpython scripts/runtime.py log --lines 100` |
