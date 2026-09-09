# AI 项目辅助操作

宝塔面板 AI 项目辅助操作指南，涵盖项目控制、域名管理、日志查询、项目修改、项目删除和 SSL 证书申请。

---

## 可用方法

| 方法 | 作用 | 对应脚本命令 | 返回内容 |
|------|------|-------------|----------|
| `StartProject` | 启动项目。动态项目执行 start_cmd 并通过 nohup 后台运行；静态项目从 Nginx 配置中移除 bt-stop.html 规则 | `btpython scripts/ai_site.py start` | 成功: status=True, msg='项目启动成功'; 失败: 错误信息 |
| `StopProject` | 停止项目。动态项目执行 stop_cmd 或 kill PID 并删除 PID 文件；静态项目在 Nginx 配置中插入 bt-stop.html 规则 | `btpython scripts/ai_site.py stop` | 成功: status=True, msg='项目已停止'; 失败: 错误信息 |
| `RestartProject` | 重启项目（先停后启） | `btpython scripts/ai_site.py restart` | 成功: status=True; 失败: 错误信息 |
| `GetProjectList` | 获取 AI 项目列表（分页） | `btpython scripts/ai_site.py list` | 分页数据: page/size/count/data[] |
| `GetProjectStat` | 获取单个项目状态（含运行状态、监听端口） | `btpython scripts/ai_site.py stat` | 项目详情: run/listen/listen_ok 等 |
| `AddDomain` | 添加域名到项目 | `btpython scripts/ai_site.py add-domain` | 成功: status=True; 失败: 错误信息 |
| `DelDomain` | 从项目删除域名 | `btpython scripts/ai_site.py del-domain` | 成功: status=True; 失败: 错误信息 |
| `GetDomain` | 获取项目的域名列表 | `btpython scripts/ai_site.py get-domain` | 域名列表: [{id, name, pid, port, addtime, cn_name}] |
| `GetLogList` | 获取可查看的日志列表（从 ai_config.json 的 logs 字段动态读取） | `btpython scripts/ai_site.py log-list` | 日志列表: [{name, path}] |
| `GetLogContent` | 查看指定日志内容 | `btpython scripts/ai_site.py log-content` | 日志文本内容 |
| `ModifyProject` | 修改项目配置 | `btpython scripts/ai_site.py modify` | 成功: status=True; 失败: 错误信息 |
| `RemoveProject` | 删除项目（清理所有关联数据） | `btpython scripts/ai_site.py remove` | 成功: status=True; 失败: 错误信息 |

---

## StartProject — 启动项目

启动指定 AI 项目。动态项目通过 nohup 后台执行 start_cmd 并写入 PID 文件；静态项目从 Nginx 配置中移除 bt-stop.html 重写规则使站点可访问。

### 调用方式

```bash
btpython scripts/ai_site.py start --project_name <项目名称>
```

```python
from ai_site import BtPanelAiSite
site = BtPanelAiSite()
result = site.start_project(project_name='my_project')
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `project_name` | 是 | 项目名称 | 询问用户 |

### 参数规则

- `project_name`：必须是已在面板中创建的 AI 项目名称

### 动态/静态项目启停逻辑差异

**动态项目：**
- 执行 `start_cmd`，通过 `nohup` 后台运行
- PID 写入 `{project_path}/.aiproject/{project_name}.pid`
- 状态检测：检查 PID 文件 → 检查 `/proc/{pid}` 是否存在 → 检查进程是否僵尸

**静态项目：**
- 从 Nginx 配置中移除 `bt-stop.html` 重写规则
- 重载 Nginx
- 状态检测：检查 Nginx 配置是否包含 `bt-stop.html`

### 返回值

```python
{'status': True, 'msg': '项目启动成功'}             # 成功
{'status': False, 'msg': '指定项目不存在: xxx'}      # 项目不存在
{'status': False, 'msg': '动态项目未配置启动命令'}    # 缺启动命令
```

---

## StopProject — 停止项目

停止指定 AI 项目。动态项目执行 stop_cmd 或直接 kill PID 并删除 PID 文件；静态项目在 Nginx 配置中插入 bt-stop.html 规则使站点显示停止页。

### 调用方式

```bash
btpython scripts/ai_site.py stop --project_name <项目名称>
```

```python
result = site.stop_project(project_name='my_project')
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `project_name` | 是 | 项目名称 | 询问用户 |

### 参数规则

- `project_name`：必须是已在面板中创建的 AI 项目名称

### 动态/静态差异

**动态项目：** 执行 `stop_cmd`；若无 stop_cmd 则直接 kill PID；删除 PID 文件

**静态项目：** 在 Nginx 配置中插入 `bt-stop.html` 重写规则，所有请求显示停止页

### 返回值

```python
{'status': True, 'msg': '项目已停止'}             # 成功
{'status': False, 'msg': '指定项目不存在: xxx'}    # 项目不存在
```

---

## RestartProject — 重启项目

重启指定 AI 项目，先执行停止再执行启动（间隔 1 秒）。

### 调用方式

```bash
btpython scripts/ai_site.py restart --project_name <项目名称>
```

```python
result = site.restart_project(project_name='my_project')
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `project_name` | 是 | 项目名称 | 询问用户 |

### 返回值

```python
{'status': True}                              # 成功
{'status': False, 'msg': '错误信息'}           # 失败
```

---

## GetProjectList — 项目列表

分页获取 AI 项目列表，支持搜索和排序。

### 调用方式

```bash
btpython scripts/ai_site.py list
btpython scripts/ai_site.py list --p 1 --limit 10 --search my_project
```

```python
result = site.get_project_list(p=1, limit=20, search=None, order='id desc')
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `p` | 否 | 当前页码 | 默认 1 |
| `limit` | 否 | 每页条数 | 默认 20 |
| `search` | 否 | 搜索关键词（匹配项目名称和备注） | 询问用户或留空 |
| `order` | 否 | 排序方式 | 默认 `id desc` |

### 返回值

```python
{
    "page": 1,
    "size": 20,
    "count": 1,
    "data": [
        {
            "id": 1,
            "name": "my_project",
            "path": "/www/wwwroot/my_project",
            "ps": "项目备注",
            "status": 1,
            "project_config": {...},
            "addtime": "2024-01-01 12:00:00",
            "run": true,
            "listen": [3000],
            "listen_ok": true
        }
    ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `page` | int | 当前页码 |
| `size` | int | 每页条数 |
| `count` | int | 总记录数 |
| `data` | list | 项目列表 |
| `data[].id` | int | 项目在数据库中的 ID |
| `data[].name` | str | 项目名称 |
| `data[].path` | str | 项目根目录路径 |
| `data[].ps` | str | 项目备注 |
| `data[].status` | int | 面板状态（1=正常） |
| `data[].project_config` | str | 项目配置 JSON 字符串 |
| `data[].addtime` | str | 创建时间 |
| `data[].run` | bool | 项目是否正在运行 |
| `data[].listen` | list | 项目监听端口列表 |
| `data[].listen_ok` | bool | 端口是否正常监听 |

---

## GetProjectStat — 项目状态

获取指定 AI 项目的详细运行状态，包含运行状态、监听端口等实时信息。

### 调用方式

```bash
btpython scripts/ai_site.py stat --project_name <项目名称>
```

```python
result = site.get_project_stat(project_name='my_project')
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `project_name` | 是 | 项目名称 | 询问用户 |

### 返回值

返回增强后的项目信息，与 `GetProjectList` 的 `data[]` 条目结构一致，包含 `run`、`listen`、`listen_ok` 等实时状态字段。

```python
{
    "id": 1,
    "name": "my_project",
    "path": "/www/wwwroot/my_project",
    "ps": "项目备注",
    "status": 1,
    "project_config": {...},
    "addtime": "2024-01-01 12:00:00",
    "run": true,
    "listen": [3000],
    "listen_ok": true
}
```

---

## AddDomain — 添加域名

为指定 AI 项目添加域名，添加后自动重建 Nginx 配置并重载。

### 调用方式

```bash
btpython scripts/ai_site.py add-domain --project_name <项目名称> --domain <域名>
```

```python
result = site.add_domain(project_name='my_project', domain='example.com:443')
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `project_name` | 是 | 项目名称 | 询问用户 |
| `domain` | 是 | 域名，格式 `example.com` 或 `example.com:443` | 询问用户 |

### 参数规则

- `domain`：格式为 `域名:端口`（如 `example.com:80` 或 `example.com:443`）；纯域名默认 80 端口；域名不可为泛解析 `*`；域名不可重复

### 返回值

```python
{'status': True, 'msg': '域名添加成功'}        # 成功
{'status': False, 'msg': '指定项目不存在'}      # 项目不存在
{'status': False, 'msg': '域名格式错误'}        # 域名不合法
{'status': False, 'msg': '域名已存在'}          # 域名已被占用
```

---

## DelDomain — 删除域名

从指定 AI 项目删除域名，删除后自动重建 Nginx 配置并重载。

### 调用方式

```bash
btpython scripts/ai_site.py del-domain --project_name <项目名称> --domain <域名>
```

```python
result = site.del_domain(project_name='my_project', domain='example.com')
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `project_name` | 是 | 项目名称 | 询问用户 |
| `domain` | 是 | 要删除的域名 | 询问用户 |

### 返回值

```python
{'status': True, 'msg': '域名删除成功'}        # 成功
{'status': False, 'msg': '指定项目不存在'}      # 项目不存在
{'status': False, 'msg': '域名不存在'}          # 域名未绑定到此项目
```

---

## GetDomain — 获取域名列表

获取指定 AI 项目的域名列表，从数据库中查询该项目绑定的所有域名。

### 调用方式

```bash
btpython scripts/ai_site.py get-domain --project_name <项目名称>
```

```python
result = site.get_domain(project_name='my_project')
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `project_name` | 是 | 项目名称 | 询问用户 |

### 返回值

返回域名列表，每个条目包含域名的详细信息：

```python
[
    {
        "id": 1,
        "name": "example.com",
        "pid": 10,
        "port": 80,
        "addtime": "2024-01-01 12:00:00",
        "cn_name": "example.com"
    },
    {
        "id": 2,
        "name": "www.example.com",
        "pid": 10,
        "port": 80,
        "addtime": "2024-01-02 10:00:00",
        "cn_name": "www.example.com"
    }
]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 域名记录 ID |
| `name` | str | 域名（punycode 编码） |
| `pid` | int | 所属项目 ID |
| `port` | int | 绑定端口 |
| `addtime` | str | 添加时间 |
| `cn_name` | str | 中文域名（解码后，用于展示） |

---

## GetLogList — 日志列表

获取指定 AI 项目的可查看日志列表，从 `ai_config.json` 的 `logs` 字段动态读取。

### 调用方式

```bash
btpython scripts/ai_site.py log-list --project_name <项目名称>
```

```python
result = site.get_log_list(project_name='my_project')
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `project_name` | 是 | 项目名称 | 询问用户 |

### 返回值

返回日志分类列表，每个条目包含日志名称和文件路径：

```python
[
    {"name": "Nginx访问日志", "path": "/www/wwwlogs/ai/my_project_access.log"},
    {"name": "Nginx错误日志", "path": "/www/wwwlogs/ai/my_project_error.log"},
    {"name": "后端服务", "path": "/www/wwwroot/my_project/.aiproject/backend.log"}
]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | str | 日志分类名称，用于展示给用户选择 |
| `path` | str | 日志文件的完整路径，**传给 `GetLogContent` 的 `log_path` 参数** |

---

## GetLogContent — 查看日志内容

查看指定日志文件的最后 N 行内容。

### 调用方式

```bash
btpython scripts/ai_site.py log-content --project_name <项目名称> --log_path <日志路径> --lines <行数>
```

```python
result = site.get_log_content(project_name='my_project', log_path='/www/wwwlogs/ai/my_project_access.log', lines=100)
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `project_name` | 是 | 项目名称 | 从 `GetLogList` 调用上下文获取 |
| `log_path` | 是 | 日志文件完整路径 | 从 `GetLogList` 返回的 `path` 字段获取 |
| `lines` | 否 | 获取最后多少行 | 默认 100 |

### 返回值

返回日志文本字符串（不是 dict），直接展示给用户查看：

```
192.168.1.1 - - [01/Jan/2024:12:00:00 +0800] "GET / HTTP/1.1" 200 1234
192.168.1.2 - - [01/Jan/2024:12:00:01 +0800] "GET /api/data HTTP/1.1" 200 567
...
```

---

## ModifyProject — 修改项目配置

修改指定 AI 项目的配置项，只需传入要修改的字段，未传入的字段保持不变。动态项目修改后自动重启（先停后启），静态项目重载 Nginx。

### 调用方式

```bash
btpython scripts/ai_site.py modify --project_name <项目名称> --ports '[{"port":4000,"label":"Web服务"}]' --start_cmd "npm run prod"
```

```python
result = site.modify_project(project_name='my_project', ports=[{"port":4000,"label":"Web服务"}], start_cmd='npm run prod')
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `project_name` | 是 | 项目名称（不可修改） | 询问用户 |
| `project_path` | 否 | 新的项目路径 | 询问用户或留空 |
| `project_ps` | 否 | 新的备注信息 | 询问用户或留空 |
| `ports` | 否 | 新的端口列表，格式：`[{"port":3000,"label":"Web服务"}]` | 询问用户或留空 |
| `start_cmd` | 否 | 新的启动命令 | 询问用户或留空 |
| `stop_cmd` | 否 | 新的停止命令 | 询问用户或留空 |
| `is_power_on` | 否 | 是否开机启动，`1`=是，`0`=否 | 询问用户或留空 |
| `run_user` | 否 | 新的运行用户 | 询问用户或留空 |
| `environment` | 否 | 新的环境变量 | 询问用户或留空 |

### 参数规则

- `project_name` 和 `project_mode` 不可修改
- 修改后动态项目会自动重启（先停后启），静态项目会重载 Nginx
- 只需传入要修改的字段，未传入的字段保持不变
- `ports` 为端口对象列表，每项包含 `port`（端口号）和 `label`（服务名称）；面板会检测端口是否被其他 AI 项目或系统进程占用
- `project_path` 必须是存在的绝对路径

### 返回值

```python
{'status': True, 'msg': '修改项目成功'}              # 成功
{'status': False, 'msg': '指定项目不存在: xxx'}       # 项目不存在
{'status': False, 'msg': '项目目录不存在: xxx'}       # 项目路径不存在
```

---

## RemoveProject — 删除项目

删除指定 AI 项目，清理所有关联数据。**注意：不删除项目代码目录**。

### 调用方式

```bash
btpython scripts/ai_site.py remove --project_name <项目名称>
```

```python
result = site.remove_project(project_name='my_project')
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `project_name` | 是 | 项目名称 | 询问用户，**删除前必须与用户确认** |

### 参数规则

- `project_name`：必须是已在面板中创建的 AI 项目名称
- **必须与用户确认后再执行删除操作**

### 清理范围

删除项目时会清理以下内容：

- 停止运行中的项目
- 删除数据库记录（sites 表、domain 表）
- 删除 Nginx 配置文件
- 删除 well-known 验证配置
- 删除 PID 文件
- 删除 `ai_config.json` 配置文件
- 如果 `.aiproject` 目录为空则删除
- **注意：不删除项目代码目录**

### 返回值

```python
{'status': True, 'msg': '删除项目成功'}             # 成功
{'status': False, 'msg': '指定项目不存在: xxx'}      # 项目不存在
```

---

## SSL 证书申请

为 AI 项目绑定的域名申请 SSL 证书。

### 前提条件

1. 项目已在面板中创建（`project_type='AI'`）
2. 项目状态为运行中（动态项目需有进程运行中）
3. 域名已添加到项目
4. 域名已正确解析到服务器 IP

### 申请流程

```
用户/面板触发 SSL 申请
    ↓
acme_v2.py 识别 project_type='AI'
    ↓
读取 ai_config.json 中的 ssl_path（默认: /www/wwwroot/ai_ssl/{project_name}）
    ↓
在该路径下创建 .well-known/acme-challenge/ 验证文件
    ↓
Nginx 配置的 /.well-known/ location 指向该路径
    ↓
证书颁发机构访问验证文件确认域名所有权
    ↓
证书申请成功，证书文件写入 ssl_path 目录
    ↓
Nginx 配置自动添加 SSL 相关配置块
```

### 证书路径

SSL 证书文件存放于：`/www/wwwroot/ai_ssl/{project_name}/`

---

## 脚本文件

封装脚本 [scripts/ai_site.py](../scripts/ai_site.py) 提供 `BtPanelAiSite` 类：

- `start_project(project_name)` → 启动项目
- `stop_project(project_name)` → 停止项目
- `restart_project(project_name)` → 重启项目
- `get_project_list(p=1, limit=20, search=None, order='id desc')` → 项目列表
- `get_project_stat(project_name)` → 项目状态
- `add_domain(project_name, domain)` → 添加域名
- `del_domain(project_name, domain)` → 删除域名
- `get_domain(project_name)` → 获取域名列表
- `get_log_list(project_name)` → 日志列表
- `get_log_content(project_name, log_path, lines=100)` → 日志内容
- `modify_project(project_name, ...)` → 修改项目
- `remove_project(project_name)` → 删除项目

> 配置管理（修改 ports/start_cmd/stop_cmd/domains/logs）通过直接编辑 `{project_path}/.aiproject/ai_config.json` 完成，面板动态识别变更。

---

## 错误码参考

| 错误码/信息 | 含义 | 处理建议 |
|-------------|------|----------|
| `指定项目不存在` | project_name 对应的 AI 项目在面板中不存在 | 确认项目名称，可先通过 `GetProjectList` 查询 |
| `动态项目未配置启动命令` | 动态项目缺少 `start_cmd` | 先通过 `ModifyProject` 配置启动命令 |
| `项目目录不存在` | project_path 不存在于磁盘 | 确认目录路径是否正确 |
| `域名格式错误` | 域名不合法 | 使用正确的域名格式，如 `example.com` 或 `example.com:443` |
| `域名已存在` | 域名已被其他项目或站点绑定 | 更换域名或检查域名归属 |
| `域名不存在` | 要删除的域名未绑定到此项目 | 确认域名是否正确绑定 |
| `指定端口已被其它应用占用` | 端口冲突 | 更换端口号 |
| `检测到配置文件有错误` | Nginx 配置语法错误 | 先修复配置再操作 |
