# 反向代理站点管理

宝塔面板反向代理站点操作指南，涵盖创建和删除。仅支持 Nginx。

---

## 可用方法

| 方法 | 作用 | 对应脚本命令 | 返回内容 |
|------|------|-------------|----------|
| `ListSites` | 查询面板所有站点列表（跨类型通用），返回站点ID、名称、类型、路径、备注等关键字段。反代站点还包含 `project_config` 中的代理目标信息 | `btpython scripts/proxy_site.py list-sites` | 站点列表数组，每项含 `id`/`name`/`project_type`/`path`/`ps`/`project_config` |
| `AddProxySite` | 创建反向代理站点，将请求代理转发到后端服务（HTTP/HTTPS/Unix Socket） | `btpython scripts/proxy_site.py add` | 成功：`status=True`、站点名、路径、代理配置等；失败：错误信息 |
| `DeleteProxySite` | 删除反向代理站点，清理Nginx配置、缓存、数据库记录，可选删除网站目录 | `btpython scripts/proxy_site.py delete` | 成功：`status=True`、`msg='反向代理项目删除成功！'`；失败：错误信息 |

---

## ListSites — 查询站点列表

查询面板中所有站点的列表，返回每个站点的关键字段。在执行删除操作前，**必须先调用此方法**获取正确的 `site_id` 和 `site_name`。

### 调用方式

```bash
btpython scripts/proxy_site.py list-sites
btpython scripts/proxy_site.py list-sites --project_type proxy
```

```python
from proxy_site import BtPanelProxySite
site = BtPanelProxySite()
result = site.list_sites()                  # 全部站点
result = site.list_sites(project_type='proxy')  # 仅反代站点
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `project_type` | 否 | 过滤站点类型，可选 `PHP`/`html`/`proxy`，不传则返回全部 | 删除反代站点时传 `proxy` |

### 返回值

返回 list[dict]，每项包含以下字段：

```python
[
    {
        "id": 128,
        "name": "192.168.10.194_7321",
        "project_type": "proxy",
        "path": "/www/wwwroot/192.168.10.194_7321",
        "ps": "192.168.10.194:7321",
        "project_config": ""
    }
]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 站点ID，**这就是 `DeleteProxySite` 需要的 `site_id` 参数** |
| `name` | str | 站点注册名，**这就是 `DeleteProxySite` 需要的 `site_name` 参数** |
| `project_type` | str | 站点类型，`proxy` 表示可通过代理脚本删除 |
| `path` | str | 网站根目录/缓存目录路径，用于判断是否需要删除目录 |
| `ps` | str | 站点备注，通常记录了原始域名 |
| `project_config` | str | 代理配置JSON，包含代理目标等详细信息 |

**使用模式**：删除前先 `list-sites --project_type proxy` 获取正确 `id` 和 `name`，再执行 `delete --site_id <id> --site_name <name>`。

---

## AddProxySite — 创建反向代理站点

创建一个反向代理站点，底层调用 `proxy.comMod.main().create()`。脚本自动处理域名解析、Punycode转换、端口提取、命名规则，AI 只需传入简洁参数即可。

### 调用方式

```bash
btpython scripts/proxy_site.py add --domains <域名> --proxy_pass <代理目标> --proxy_type <代理类型> --remark <备注> --proxy_host <传递主机头>
```

```python
from proxy_site import BtPanelProxySite
site = BtPanelProxySite()
result = site.add_proxy_site(domains='192.168.10.194:7321', proxy_pass='http://www.baidu.com', proxy_type='http', remark='192.168.10.194:7321', proxy_host='www.baidu.com')
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `domains` | 是 | 监听域名，格式为 `域名:端口`（如 `192.168.10.194:7321`）或纯域名（如 `www.example.com`，默认80端口）。多个域名用换行 `\n` 分隔 | 询问用户 |
| `proxy_pass` | 是 | 代理目标地址。HTTP类型必须以 `http://` 或 `https://` 开头；Unix类型必须以 `/` 开头且以 `.sock` 结尾 | 询问用户 |
| `proxy_type` | 否 | 代理类型：`http`（HTTP/HTTPS代理）或 `unix`（Unix Socket代理） | 默认 `http` |
| `remark` | 否 | 站点备注说明 | 默认为空 |
| `proxy_host` | 否 | 传递给后端的主机头（Host header），如 `$http_host`（传递原始主机头）或具体域名（如 `www.baidu.com`） | 默认 `$http_host`，即传递原始请求主机头 |

### 参数规则

- `domains`：至少包含一个域名；域名不能为泛解析 `*`；端口必须合法（1-65535）
- `proxy_pass`：HTTP类型必须以 `http://` 或 `https://` 开头；Unix类型路径必须以 `/` 开头且以 `.sock` 结尾，且文件必须存在
- `proxy_type`：仅支持 `http` 和 `unix`
- 仅支持 Nginx，若服务器使用 Apache 或其他 Web 服务器则无法创建

### 返回值

成功时返回 dict：

```python
{'status': True, 'msg': '反向代理项目添加成功！'}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | bool | `True`=创建成功，`False`=创建失败。核心判断字段 |
| `msg` | str | 成功时为 `反向代理项目添加成功！`；失败时为具体错误信息 |

失败时返回 dict：

```python
{'status': False, 'msg': '错误信息'}
```

### 站点命名规则

反向代理站点名称由域名和端口动态生成：
- 端口80：`site_name` = 域名本身（如 `www.example.com`）
- 非80端口且域名不存在：`site_name` = `域名_端口`（如 `192.168.10.194_7321`）
- 非80端口且域名已存在：`site_name` = `已有名称_端口`
- 网站目录路径：端口80时为 `/www/wwwroot/{site_name}`；非80端口时为 `/www/wwwroot/{site_name}_{端口}` 或 `/www/wwwroot/{site_name}`
- 删除时需要使用最终生成的 `site_name`

### 自动创建的文件和目录

- Nginx配置：`/www/server/panel/vhost/nginx/{site_name}.conf`
- 代理配置JSON：`/www/server/proxy_project/sites/{site_name}/{site_name}.json`
- 代理缓存目录：`{site_path}/proxy_cache_dir`
- 防火墙规则：非80端口自动放行

---

## DeleteProxySite — 删除反向代理站点

删除一个反向代理站点，清理Nginx配置、代理配置、缓存目录、日志文件和数据库记录。

### 调用方式

```bash
btpython scripts/proxy_site.py delete --site_id <站点ID> --site_name <站点名称> --remove_path <是否删除目录>
```

```python
from proxy_site import BtPanelProxySite
site = BtPanelProxySite()
result = site.delete_proxy_site(site_id='128', site_name='192.168.10.194_7321', remove_path=True)
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `site_id` | 是 | 站点在面板数据库中的ID（`sites` 表主键） | 从创建返回值获取，或通过面板站点列表查询 |
| `site_name` | 是 | 站点名称（面板中注册的名称），通常是 `域名` 或 `域名_端口` 格式 | 从创建返回值获取，或通过面板站点列表查询 |
| `remove_path` | 否 | 是否同时删除网站目录文件，`True`=删除（含缓存目录），`False`=保留 | 默认 `False`，**必须与用户确认** |

### 参数规则

- `site_id`：必须是面板 `sites` 表中存在的有效ID
- `site_name`：必须与 `site_id` 对应的 `name` 字段一致
- `remove_path`：涉及数据丢失风险，操作前**必须与用户确认**

### 删除操作范围

删除站点时会清理以下内容：
- Nginx配置文件：`/www/server/panel/vhost/nginx/{site_name}.conf`
- Nginx重定向配置目录
- 代理配置目录：`/www/server/proxy_project/sites/{site_name}/`
- Nginx扩展配置目录
- 日志文件
- 数据库记录（sites、domain 表）
- 可选：网站目录 `/www/wwwroot/{site_name}`（含缓存目录）
- 重载Nginx配置

### 返回值

```python
{'status': True, 'msg': '反向代理项目删除成功！'}   # 成功
{'status': False, 'msg': '错误原因'}                  # 失败
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | bool | `True`=删除成功，`False`=删除失败 |
| `msg` | str | 成功时为 `反向代理项目删除成功！`；失败时为具体错误信息 |

---

## 脚本文件

封装脚本 [scripts/proxy_site.py](../scripts/proxy_site.py) 提供 `BtPanelProxySite` 类：

- `list_sites(project_type=None)` → 查询站点列表
- `add_proxy_site(domains, proxy_pass, proxy_type='http', remark='', proxy_host='$http_host')` → 创建反向代理站点
- `delete_proxy_site(site_id, site_name, remove_path=False)` → 删除反向代理站点

---

## 错误码参考

| 错误码/信息 | 含义 | 处理建议 |
|-------------|------|----------|
| `仅支持Nginx` | 服务器未安装Nginx | 安装Nginx后再操作 |
| `域名不能为空` | domains参数为空 | 至少输入一个域名 |
| `代理目标不能为空` | proxy_pass参数为空 | 填写代理目标地址 |
| `代理目标必须以http://或https://开头` | HTTP类型proxy_pass格式不合法 | 添加协议前缀 |
| `unix文件路径必须以/开头` | Unix类型proxy_pass格式不合法 | 使用绝对路径 |
| `unix文件必须以.sock结尾` | Unix类型proxy_pass格式不合法 | 使用.sock文件 |
| `代理目标不存在` | Unix socket文件不存在 | 确认文件路径 |
| `主域名不能为泛解析` | 域名包含 `*` | 不使用泛解析 |
| `端口不合法` | 端口号不在合法范围 | 使用合法端口（1-65535） |
| `网站已存在` | 域名+端口组合已存在 | 更换域名或端口 |
| `id不能为空` | 删除时site_id为空 | 传入有效site_id |
| `指定站点不存在` | 删除时site_id不存在 | 确认正确的site_id |
| `检测到配置文件有错误` | Nginx配置语法错误 | 先修复配置再操作 |