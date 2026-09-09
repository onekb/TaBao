# HTML 静态站点管理

宝塔面板 HTML 静态站点操作指南，涵盖创建和删除。

---

## 可用方法

| 方法 | 作用 | 对应脚本命令 | 返回内容 |
|------|------|-------------|----------|
| `ListSites` | 查询面板所有站点列表（跨类型通用），返回站点ID、名称、类型、路径、备注等关键字段 | `btpython scripts/html_site.py list-sites` | 站点列表数组，每项含 `id`/`name`/`project_type`/`path`/`ps`/`project_config` |
| `AddHtmlSite` | 创建HTML静态站点，自动生成Nginx/Apache配置、目录结构、默认文档（index.html/404.html） | `btpython scripts/html_site.py add` | 成功：`siteStatus=True`、`siteId`、站点名、路径等；失败：错误信息 |
| `DeleteHtmlSite` | 删除HTML静态站点，清理配置和数据库记录 | `btpython scripts/html_site.py delete` | 成功：`status=True`、`msg='删除项目成功'`；失败：错误信息 |

---

## ListSites — 查询站点列表

查询面板中所有站点的列表，返回每个站点的关键字段。在执行删除操作前，**必须先调用此方法**获取正确的 `project_name`（HTML站点）或 `site_id`/`site_name`。

### 调用方式

```bash
btpython scripts/html_site.py list-sites
btpython scripts/html_site.py list-sites --project_type html
```

```python
from html_site import BtPanelHtmlSite
site = BtPanelHtmlSite()
result = site.list_sites()                # 全部站点
result = site.list_sites(project_type='html')  # 仅HTML站点
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `project_type` | 否 | 过滤站点类型，可选 `PHP`/`html`/`proxy`，不传则返回全部 | 根据操作需要选择，删除HTML站点时传 `html` |

### 返回值

返回 list[dict]，每项包含以下字段：

```python
[
    {
        "id": 1,
        "name": "www.example.com",
        "project_type": "html",
        "path": "/www/wwwroot/www.example.com",
        "ps": "网站备注",
        "project_config": ""
    }
]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 站点ID（HTML站点删除不使用此字段，但可用于跨脚本定位） |
| `name` | str | 站点注册名，**这就是 `DeleteHtmlSite` 需要的 `project_name` 参数** |
| `project_type` | str | 站点类型，`html` 表示可通过HTML脚本删除 |
| `path` | str | 网站根目录绝对路径，用于了解站点目录位置 |
| `ps` | str | 站点备注说明 |
| `project_config` | str | 站点配置JSON，HTML站点通常为空 |

**使用模式**：删除前先 `list-sites --project_type html` 获取正确 `name`，再执行 `delete --project_name <name>`。

---

## AddHtmlSite — 创建HTML静态站点

创建一个纯静态站点，底层调用 `htmlModel().create_project()`。脚本自动处理 domain 格式转换、webname JSON 构建、端口提取，AI 只需传入简洁参数即可。

### 调用方式

```bash
btpython scripts/html_site.py add --domain <域名或IP端口> --site_path <网站目录> --ps <备注>
```

```python
from html_site import BtPanelHtmlSite
site = BtPanelHtmlSite()
result = site.add_html_site(domain='www.example.com', site_path='/www/wwwroot/www.example.com')
result = site.add_html_site(domain='192.168.10.194_9321', site_path='/www/wwwroot/192.168.10.194_9321')
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `domain` | 是 | 网站域名或IP端口组合。域名格式：`www.example.com`（默认80端口）；IP+端口格式：`192.168.10.194_9321`（下划线分隔）或 `192.168.10.194:9321`（冒号分隔） | 询问用户 |
| `site_path` | 是 | 网站根目录绝对路径，如 `/www/wwwroot/www.example.com` | 询问用户，或默认取 `/www/wwwroot/{domain}` |
| `ps` | 否 | 网站备注说明 | 默认为空 |
| `ftp` | 否 | 是否创建FTP账户，`true`/`false` | 默认 `false`，需与用户确认 |

### 参数规则

- `domain`：支持域名和IP+端口；域名必须匹配正则 `^([\w\-*]{1,100}\.){1,24}([\w\-]{1,24}|[\w\-]{1,24}\.[\w\-]{1,24})$` 或为合法IP；不支持泛解析 `*`
- `site_path`：绝对路径，不能包含空白字符，不能以 `.` 结尾，不能设置到系统关键目录
- HTML站点不支持PHP版本和数据库配置

### domain 格式转换说明

底层 `htmlModel.create_project` 要求 `webname` 中 domain 为 `域名:端口` 格式，脚本自动转换：
- `192.168.10.194_9321` → 内部转换为 `192.168.10.194:9321`，端口为 `9321`
- `www.example.com` → 端口默认 `80`
- `192.168.10.194:9321` → 端口提取为 `9321`

### 返回值

成功时返回 dict：

```python
{
    'siteStatus': True,     # 站点创建是否成功（核心判断字段）
    'siteId': 10,           # 站点在面板数据库中的ID
    'ftpStatus': False      # FTP是否创建成功
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `siteStatus` | bool | `True`=创建成功，`False`=创建失败。核心判断字段 |
| `siteId` | int | 站点ID，删除站点时需要此ID |
| `ftpStatus` | bool | 仅当请求创建FTP时返回，`True`=FTP创建成功 |
| `ftpUser` | str | 仅当FTP创建成功时返回，FTP用户名 |
| `ftpPass` | str | 仅当FTP创建成功时返回，FTP密码 |

失败时返回 dict：

```python
{'status': False, 'msg': '错误信息'}  # 常见：SITE_ADD_ERR_DOMAIN_EXISTS / SITE_ADD_ERR_PORT / PATH_ERROR
```

### 站点名称命名规则

- 域名站点：`siteName` = 域名本身（如 `www.example.com`）
- IP端口站点：若同名IP已存在，`siteName` 自动追加 `_端口`（如 `192.168.10.194_9321`）
- HTML站点的配置文件命名规则为 `html_{siteName}.conf`

### 自动创建的文件

创建站点时会自动生成：
- `index.html` — 默认首页（从面板模板复制）
- `404.html` — 自定义404页面
- `.user.ini` — PHP防跨站配置（open_basedir限制）
- Nginx配置：`/www/server/panel/vhost/nginx/html_{siteName}.conf`
- Apache配置：`/www/server/panel/vhost/apache/html_{siteName}.conf`

---

## DeleteHtmlSite — 删除HTML静态站点

删除一个 HTML 静态站点，清理配置文件和数据库记录。

### 调用方式

```bash
btpython scripts/html_site.py delete --project_name <站点名称>
```

```python
from html_site import BtPanelHtmlSite
site = BtPanelHtmlSite()
result = site.delete_html_site(project_name='www.example.com')
result = site.delete_html_site(project_name='192.168.10.194_9321')
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `project_name` | 是 | 站点名称（面板中注册的项目名），即 `sites` 表中的 `name` 字段值。通常是域名或 `IP_端口` 格式 | 从创建返回值获取，或通过面板站点列表查询 |

### 参数规则

- `project_name`：必须是面板 `sites` 表中存在的、`project_type='html'` 的站点名称

### 删除操作范围

删除站点时会清理以下内容：
- Nginx配置：`/www/server/panel/vhost/nginx/html_{project_name}.conf`
- Apache配置：`/www/server/panel/vhost/apache/html_{project_name}.conf`
- 伪静态规则：`/www/server/panel/vhost/rewrite/html_{project_name}.conf`
- 防跨站配置
- 数据库记录（sites、domain 表）
- **注意：HTML站点删除不会自动删除网站目录文件**，目录需手动清理

### 返回值

```python
{'status': True, 'msg': '删除项目成功'}   # 成功
{'status': False, 'msg': '指定项目不存在: xxx'} # 失败
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | bool | `True`=删除成功，`False`=删除失败 |
| `msg` | str | 成功时为 `删除项目成功`；失败时为具体错误信息 |

---

## 脚本文件

封装脚本 [scripts/html_site.py](../scripts/html_site.py) 提供 `BtPanelHtmlSite` 类：

- `list_sites(project_type=None)` → 查询站点列表
- `add_html_site(domain, site_path, ps='', ftp=False)` → 创建HTML静态站点
- `delete_html_site(project_name)` → 删除HTML静态站点

---

## 错误码参考

| 错误码/信息 | 含义 | 处理建议 |
|-------------|------|----------|
| `SITE_ADD_ERR_DOMAIN_EXISTS` | 域名+端口组合已存在 | 更换域名或端口 |
| `SITE_ADD_ERR_PORT` | 端口不合法 | 使用合法端口（1-65535） |
| `SITE_ADD_ERR_DOMAIN` | 域名格式不合法 | 使用合法域名或IP |
| `SITE_ADD_ERR_DOMAIN_TOW` | 域名包含泛解析 | 不使用泛解析 |
| `SITE_ADD_ERR_WRITE` | 配置文件写入失败 | 检查Nginx/Apache配置 |
| `PATH_ERROR` | 网站目录路径不合法 | 使用合法绝对路径 |
| `指定项目不存在` | 删除时站点不存在 | 确认正确的project_name |
| `网站目录路径不能包含空白字符` | 路径含空格 | 移除空格 |
| `网站目录结尾不可以是 "."` | 路径以点结尾 | 移除末尾的点 |
| `检测到配置文件有错误` | Nginx/Apache配置语法错误 | 先修复配置再操作 |