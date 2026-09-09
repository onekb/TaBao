# 创建 AI 项目

宝塔面板 AI 项目创建操作指南，涵盖动态项目和静态项目的完整参数规则。

---

## 可用方法

| 方法 | 作用 | 对应脚本命令 | 返回内容 |
|------|------|-------------|----------|
| `CreateProject` | 创建AI项目并接入面板。底层调用 `aiModel.main().create_project()`。面板自动生成 Nginx 配置、写入 ai_config.json、创建数据库记录、为重载 Nginx | `btpython scripts/ai_site.py create` | 成功：`status=True`、`project_id`；失败：错误信息 |

---

## CreateProject — 创建 AI 项目

创建一个 AI 项目，底层调用 `aiModel.main().create_project()`。脚本自动处理 Nginx 配置生成、ai_config.json 写入、数据库记录创建，AI 只需传入简洁参数即可。

### 调用方式

```bash
btpython scripts/ai_site.py create --project_name <名称> --project_path <路径> --project_mode <模式> --ports <端口列表JSON> --start_cmd <启动命令> --stop_cmd <停止命令> --domains <域名列表> --project_ps <备注> --is_power_on <开机启动> --run_user <运行用户> --environment <环境变量> --logs <日志配置>
```

```python
from ai_site import BtPanelAiSite
site = BtPanelAiSite()
result = site.create_project(project_name='my_project', project_path='/www/wwwroot/my_project', project_mode='dynamic', ports=[{"port":3000,"label":"Web服务"}], start_cmd='npm run start', stop_cmd='npm run stop')
```

### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 | 获取方式 |
|------|------|:--:|--------|------|----------|
| `project_name` | string | 是 | — | 项目名称，仅支持字母、数字、下划线。全局唯一 | 询问用户 |
| `project_path` | string | 是 | — | 项目根目录绝对路径，必须先创建好 | 询问用户 |
| `project_mode` | string | 否 | `dynamic` | 项目模式：`dynamic`（动态）或 `static`（静态） | 询问用户或留空 |
| `project_ps` | string | 否 | 空 | 项目备注信息，显示在面板列表中 | 询问用户或留空 |
| `ports` | list/str | 🔶 | — | 端口列表，动态项目必填。格式：`[{"port":3000,"label":"Web服务"}]` | 询问用户 |
| `start_cmd` | string | 🔶 | — | 启动命令，动态项目必填。如 `"npm run start"` | 询问用户 |
| `stop_cmd` | string | 🔶 | — | 停止命令，动态项目必填。如 `"npm run stop"` | 询问用户 |
| `domains` | list/str | 否 | 空 | 域名列表。格式：`["example.com:80", "www.example.com:80"]` | 询问用户或留空 |
| `is_power_on` | int | 否 | `0` | 是否开机启动：`1`=是，`0`=否 | 询问用户或留空 |
| `run_user` | string | 否 | `www` | 运行用户 | 询问用户或留空 |
| `environment` | string | 否 | 空 | 环境变量（如 `NODE_ENV=production`） | 询问用户或留空 |
| `logs` | dict/str | 否 | 空 | 自定义日志配置，JSON dict 格式 | 询问用户或留空 |

> 🔶 = 动态项目必填，静态项目可忽略

### 参数规则

- `project_name`：正则 `^\w+$`（仅字母、数字、下划线）；全局唯一，不可重复；不可使用面板保留名称（`default`、`localhost`）
- `project_path`：必须是存在的绝对路径，AI 应在调用前创建
- `project_mode`：仅支持 `dynamic` 或 `static`
- `ports`：端口对象列表，每项包含 `port`（端口号）和 `label`（服务名称，如"前端服务"、"后端API"）；面板会检测端口是否被其他 AI 项目或系统进程占用
- `domains`：每个域名格式为 `域名:端口`（如 `example.com:80` 或 `example.com:443`）；域名不可为泛解析 `*`；域名不可重复
- `logs`：dict 格式，key 为日志分类名称，value 为日志文件路径

### 返回值

成功时返回 dict：

```python
{'status': True, 'msg': '添加AI项目成功', 'data': 项目ID}
```

失败时返回 dict：

```python
{'status': False, 'msg': '错误原因'}
```

常见错误信息：

| 错误信息 | 含义 | 处理 |
|---------|------|------|
| `项目名称格式不正确` | project_name 不符合正则 | 修正名称 |
| `指定项目名称已存在` | 同名项目已存在 | 更换名称 |
| `项目目录不存在` | project_path 不存在 | 先创建目录 |
| `项目模式必须为 dynamic 或 static` | project_mode 值错误 | 修正为 dynamic 或 static |
| `动态项目必须提供启动命令` | 缺 start_cmd | 补充启动命令 |
| `动态项目必须提供停止命令` | 缺 stop_cmd | 补充停止命令 |
| `动态项目必须配置端口` | 缺 ports | 补充端口 |
| `指定端口已被其它应用占用` | 端口冲突 | 更换端口 |
| `域名格式错误` | 域名不合法 | 修正域名 |
| `指定域名已存在` | 域名被其他站点占用 | 更换域名 |

### `ai_config.json` 生成结果

创建成功后，脚本在 `{project_path}/.aiproject/ai_config.json` 写入：

```json
{
    "ssl_path": "/www/wwwroot/ai_ssl/my_project",
    "project_name": "my_project",
    "project_path": "/www/wwwroot/my_project",
    "ports": [{"port": 3000, "label": "Web服务"}],
    "primary_port": 3000,
    "start_cmd": "cd /www/wwwroot/my_project && npm run start",
    "stop_cmd": "cd /www/wwwroot/my_project && npm run stop",
    "is_power_on": 0,
    "run_user": "www",
    "project_mode": "dynamic",
    "domains": ["example.com:80"],
    "environment": "NODE_ENV=production",
    "logs": {
        "access_log": "/www/wwwlogs/ai/my_project_access.log",
        "error_log": "/www/wwwlogs/ai/my_project_error.log",
        "后端服务": "/www/wwwroot/my_project/.aiproject/backend.log"
    }
}
```

> `access_log` 和 `error_log` 由面板自动生成，AI 在 `logs` 参数中只需配置项目自身的业务日志分类（如上方"后端服务"）。

### logs 参数格式

创建项目时可在 `logs` 参数中配置自定义日志：

```python
logs = {
    "后端服务": "/www/wwwroot/my_project/.aiproject/backend.log",
    "前端构建": "/www/wwwroot/my_project/.aiproject/frontend_build.log",
    "数据库日志": "/www/wwwroot/my_project/.aiproject/db.log",
    "定时任务": "/www/wwwroot/my_project/.aiproject/cron.log"
}
```

命令行传递时使用 JSON 字符串：

```bash
--logs '{"后端服务":"/path/to/backend.log","前端构建":"/path/to/build.log"}'
```

AI 可以配置任意数量、任意名称的日志分类，面板会动态展示。

### 项目目录结构

创建成功后，标准项目目录结构：

```
/www/wwwroot/{project_name}/
├── .aiproject/                    # AI 项目专用目录（面板自动创建，外部 404 拦截）
│   ├── ai_config.json             # 项目完整配置（面板自动写入）
│   └── {project_name}.pid         # 进程 PID 文件（启动后自动生成）
├── index.html                     # 静态项目入口（仅静态项目需要）
├── server.js / app.py / main.go   # 后端入口文件（动态项目）
└── ...                            # 项目其他代码文件
```

---

## 脚本文件

封装脚本 [scripts/ai_site.py](../scripts/ai_site.py) 提供 `BtPanelAiSite` 类：

- `create_project(project_name, project_path, project_mode='dynamic', ...)` → 创建AI项目
