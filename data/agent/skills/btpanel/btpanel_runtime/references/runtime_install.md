# 运行环境安装参考

本文档记录 `btpanel_runtime` 技能安装运行环境时必须遵守的源码入口、参数和完成判断规则。

## 核心原则

- 不直接写 `tasks` 表。
- 不手写 `wget`、`bash install_xxx.sh` 等安装命令。
- 不绕过项目模型或插件方法。
- 脚本必须创建 Flask request context，并使用 `from BTPanel import app, session`。
- 缺少 Node.js/.NET 管理器插件时，先通过软件商店原生 `panelPlugin.panelPlugin().install_plugin(get)` 安装管理器。
- 安装完成后可使用 `list` 命令查询版本列表确认安装结果。
- Node.js 版本安装完成后，必须继续为对应版本安装 PM2 和 yarn。

## 方法映射

| 运行环境 | 查询方法 | 安装方法 | 参数 | 完成判断 |
|---|---|---|---|---|
| PHP | `panelSite.panelSite().GetPHPVersion(get)` | `panelPlugin.panelPlugin().install_plugin(get)` | `sName=php`, `version`, `min_version`, `type` | 版本列表中出现目标 PHP 版本且 `status=True` |
| Java/JDK | `projectModel.javaModel.main().get_local_jdk_version(get)` | `projectModel.javaModel.main().install_jdk_new(get)` | `version` | 列表中目标版本 `operation` 为 `1` 或 `2` |
| Python | `projectModel.pythonModel.main().list_py_version(get)` | `projectModel.pythonModel.main().async_install_py_version(get)` | `version` | `sdk.all` 或 `sdk.streamline` 中目标版本 `installed=True` |
| Go | `projectModel.goModel.main().list_go_sdk(get)` | `projectModel.goModel.main().install_go_sdk_async(get)` | `version` | `installed` 列表包含目标版本；输入 `1.22.5` 时按 `go1.22.5` 判断 |
| Node.js | `projectModel.nodejsModel.main().get_nodejs_version(get)` | `/plugin?action=a&s=install_nodejs&name=nodejs` | `version` | 安装接口返回即代表版本安装完成 |
| .NET | `projectModel.netModel.main().GetNetVersion(get)` | `/plugin?action=a&name=dotnet&s=install_dotnet` | `version` | 安装接口返回即代表版本安装完成 |

## 管理器规则

### Node.js

安装具体 Node.js 版本前必须存在：

```text
/www/server/panel/plugin/nodejs
```

缺失时先安装软件商店插件 `nodejs`。管理器未安装完成前，不继续安装具体 Node.js 版本。

Node.js 版本安装入口：

```python
panelPlugin.panelPlugin().a(public.to_dict_obj({
    'name': 'nodejs',
    's': 'install_nodejs',
    'version': version
}))
```

Node.js 版本安装接口返回后，继续为同一个版本安装 PM2 和 yarn：

```python
panelPlugin.panelPlugin().a(public.to_dict_obj({
    'name': 'nodejs',
    's': 'install_module',
    'version': version,
    'module': 'pm2'
}))
panelPlugin.panelPlugin().a(public.to_dict_obj({
    'name': 'nodejs',
    's': 'install_module',
    'version': version,
    'module': 'yarn'
}))
```

### .NET

安装具体 .NET 版本前必须存在：

```text
/www/server/panel/plugin/dotnet
```

缺失时先安装软件商店插件 `dotnet`。管理器未安装完成前，不继续安装具体 .NET 版本。

.NET 版本安装入口：

```python
panelPlugin.panelPlugin().a(public.to_dict_obj({
    'name': 'dotnet',
    's': 'install_dotnet',
    'version': version
}))
```

## 参数示例

安装 PHP：

```bash
btpython scripts/runtime.py install --runtime php --version 8.3
```

安装 JDK：

```bash
btpython scripts/runtime.py install --runtime java --version jdk-17.0.10
```

安装 Python：

```bash
btpython scripts/runtime.py install --runtime python --version 3.12.3
```

安装 Go：

```bash
btpython scripts/runtime.py install --runtime go --version 1.22.5
```

安装 Node.js：

```bash
btpython scripts/runtime.py ensure-manager --runtime node
btpython scripts/runtime.py install --runtime node --version v20.15.0
```

安装 .NET：

```bash
btpython scripts/runtime.py ensure-manager --runtime dotnet
btpython scripts/runtime.py install --runtime dotnet --version 8.0.100
```

## 上下文要求

脚本调用面板方法前必须创建 Flask request context：

```python
from BTPanel import app, session

ctx = app.test_request_context('/plugin?action=install_plugin', method='POST')
ctx.push()
```

不得直接在无上下文环境中调用依赖 `session` 的面板方法；不得使用 `from flask import session` 替代 `BTPanel.session`。

## 常见错误

| 错误 | 原因 | 处理建议 |
|---|---|---|
| 缺少管理器插件 | Node.js/.NET 管理器未安装 | 先执行 `ensure-manager` |
| 版本号不存在 | 指定版本不在面板可安装列表中 | 先用 `list` 查询可用版本 |
| 版本参数信息错误 | 版本格式不符合模型解析规则 | 按查询结果中的版本格式传参 |
| `Working outside of request context` | 未创建 Flask request context | 使用脚本封装入口执行 |
| 安装超时 | 列表轮询未看到目标版本，或 Node 模块文件未出现 | 查看 `log` 或面板安装日志 |
