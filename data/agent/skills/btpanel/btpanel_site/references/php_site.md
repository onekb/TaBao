# PHP 站点管理

宝塔面板 PHP 站点操作指南，涵盖创建和删除。

---

## 可用方法

| 方法 | 作用 | 对应脚本命令 | 返回内容 |
|------|------|-------------|----------|
| `ListSites` | 查询面板所有站点列表（跨类型通用），返回站点ID、名称、类型、路径、备注等关键字段 | `btpython scripts/php_site.py list-sites` | 站点列表数组，每项含 `id`/`name`/`project_type`/`path`/`ps`/`project_config` |
| `GetPHPVersions` | 查询面板已安装的可用PHP版本，用于创建PHP站点时选择版本 | `btpython scripts/php_site.py php-versions` | 版本列表数组，每项含 `version`/`name`/`status` |
| `AddSite` | 创建PHP站点，自动生成Nginx/Apache配置、目录结构、防火墙规则 | `btpython scripts/php_site.py add` | 成功：`siteStatus=True`、`siteId`、站点名、路径、配置文件路径等；失败：错误信息 |
| `DeleteSite` | 删除PHP站点，可同时删除目录、FTP、数据库 | `btpython scripts/php_site.py delete` | 成功：`status=True`、`msg='SITE_DEL_SUCCESS'`；失败：错误信息 |

---

## ListSites — 查询站点列表

查询面板中所有站点的列表，返回每个站点的关键字段。在执行删除操作前，**必须先调用此方法**获取正确的 `site_id` 和 `domain`（webname）。

### 调用方式

```bash
btpython scripts/php_site.py list-sites
btpython scripts/php_site.py list-sites --project_type PHP
```

```python
from php_site import BtPanelPhpSite
site = BtPanelPhpSite()
result = site.list_sites()                 # 全部站点
result = site.list_sites(project_type='PHP')  # 仅PHP站点
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `project_type` | 否 | 过滤站点类型，可选 `PHP`/`html`/`proxy`，不传则返回全部 | 删除PHP站点时传 `PHP` |

### 返回值

返回 list[dict]，每项包含以下字段：

```python
[
    {
        "id": 126,
        "name": "192.168.10.194_9321",
        "project_type": "PHP",
        "path": "/www/wwwroot/192.168.10.194_9321",
        "ps": "192.168.10.194:9321",
        "project_config": ""
    }
]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 站点ID，**这就是 `DeleteSite` 需要的 `site_id` 参数** |
| `name` | str | 站点注册名（webname），**这就是 `DeleteSite` 需要的 `domain` 参数** |
| `project_type` | str | 站点类型，`PHP` 表示可通过PHP脚本删除 |
| `path` | str | 网站根目录绝对路径，用于 `delete_path` 决策 |
| `ps` | str | 站点备注说明 |
| `project_config` | str | 站点配置JSON，PHP站点通常记录额外配置信息 |

**使用模式**：删除前先 `list-sites --project_type PHP` 获取正确 `id` 和 `name`，再执行 `delete --site_id <id> --domain <name>`。

---

## GetPHPVersions — 查询可用PHP版本

查询面板当前已安装的PHP版本，创建PHP站点时必须先调用此方法确认可选版本。

### 调用方式

```bash
btpython scripts/php_site.py php-versions
```

```python
from php_site import BtPanelPhpSite
site = BtPanelPhpSite()
result = site.get_php_versions()
```

### 参数

无参数。

### 返回值

返回 list[dict]，每项包含以下字段：

```python
[
    {"version": "00", "name": "纯静态", "status": True},
    {"version": "80", "name": "PHP-80", "status": True},
    {"version": "74", "name": "PHP-74", "status": True}
]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `version` | str | 版本编号，**这就是 `AddSite` 需要的 `php_version` 参数值**。`00`=纯静态，`80`=PHP8.0，`74`=PHP7.4 |
| `name` | str | 版本显示名，`PHP-80`/`纯静态`/`自定义`，用于展示给用户选择 |
| `status` | bool | `True`=已安装可用，`False`=未安装不可用。只用 `status=True` 的版本 |

**使用模式**：创建PHP站点前先 `php-versions` 获取可用版本列表，展示给用户选择，然后将选中的 `version` 值传给 `add --php_version <version>`。

---

## AddSite — 创建PHP站点

创建一个 PHP 站点，底层调用 `panelSite().AddSite()`。脚本自动处理 domain 格式转换（`192.168.1.x_8080` → `192.168.1.x:8080`）、端口提取、webname JSON 构建，AI 只需传入简洁参数即可。

### 调用方式

```bash
btpython scripts/php_site.py add --domain <域名或IP端口> --site_path <网站目录> --php_version <PHP版本> --ps <备注>
```

```python
from php_site import BtPanelPhpSite
site = BtPanelPhpSite()
result = site.add_site(domain='www.example.com', site_path='/www/wwwroot/www.example.com')
result = site.add_site(domain='192.168.10.194_9321', site_path='/www/wwwroot/192.168.10.194_9321', php_version='80')
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `domain` | 是 | 网站域名或IP端口组合。域名格式：`www.example.com`（默认80端口）；IP+端口格式：`192.168.10.194_9321`（下划线分隔IP与端口）或 `192.168.10.194:9321`（冒号分隔） | 询问用户 |
| `site_path` | 是 | 网站根目录绝对路径，如 `/www/wwwroot/www.example.com` 或 `/www/wwwroot/192.168.10.194_9321` | 询问用户，或默认取 `/www/wwwroot/{domain}` |
| `php_version` | 否 | PHP版本编号，如 `80`(PHP8.0)、`74`(PHP7.4)、`00`(纯静态无PHP)。纯静态项目传 `00` | 默认 `00`（纯静态），若用户指定PHP项目则询问用户 |
| `ps` | 否 | 网站备注说明 | 默认 `来自AI助手` |
| `ftp` | 否 | 是否创建FTP账户，`true`/`false` | 默认 `false`，需与用户确认 |
| `sql` | 否 | 是否创建数据库，`false`/`MySQL` | 默认 `false`，需与用户确认 |

### 参数规则

- `domain`：支持域名（如 `www.example.com`）、IP+端口（如 `192.168.10.194_9321`）；端口默认80；域名必须匹配正则 `^([\w\-\*]{1,100}\.){1,24}([\w\-]{1,24}|[\w\-]{1,24}\.[\w\-]{1,24})$` 或为合法IP；不支持泛解析 `*`
- `site_path`：绝对路径，不能包含空格或换行符，不能以 `.` 结尾，不能设置到系统关键目录（如 `/`、`/etc`、`/usr`）
- `php_version`：必须为面板已安装的PHP版本编号（可通过面板PHP管理页面查询可用版本），`00` 表示纯静态

### domain 格式转换说明

底层 `panelSite.AddSite` 要求 `webname` 中 domain 为 `域名:端口` 格式（如 `192.168.10.194:9321`），但用户通常输入 `192.168.10.194_9321`（宝塔面板常用下划线格式）。脚本自动处理此转换：
- `192.168.10.194_9321` → 内部转换为 `192.168.10.194:9321`，端口提取为 `9321`
- `www.example.com` → 端口默认 `80`，内部为 `www.example.com`（不带端口后缀）
- `192.168.10.194:9321` → 端口提取为 `9321`，内部保持原格式

### 返回值

成功时返回 dict：

```python
{
    'siteStatus': True,     # 站点创建是否成功（核心判断字段）
    'siteId': 126,          # 站点在面板数据库中的ID（用于后续删除、查询等操作）
    'ftpStatus': False,     # FTP是否创建成功（仅当ftp=true时关注）
    'databaseStatus': False # 数据库是否创建成功（仅当sql=MySQL时关注）
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `siteStatus` | bool | `True`=创建成功，`False`=创建失败。这是判断操作结果的核心字段 |
| `siteId` | int | 站点ID，删除站点时需要此ID |
| `ftpStatus` | bool | 仅当请求创建FTP时返回，`True`=FTP创建成功 |
| `ftpUser` | str | 仅当FTP创建成功时返回，FTP用户名 |
| `ftpPass` | str | 仅当FTP创建成功时返回，FTP密码 |
| `databaseStatus` | bool | 仅当请求创建数据库时返回，`True`=数据库创建成功 |
| `databaseUser` | str | 仅当数据库创建成功时返回，数据库用户名 |
| `databasePass` | str | 仅当数据库创建成功时返回，数据库密码 |
| `databaseName` | str | 仅当数据库创建成功时返回，数据库名 |

失败时返回 dict：

```python
{'status': False, 'msg': '错误信息'}  # 常见：SITE_ADD_ERR_DOMAIN_EXISTS / SITE_ADD_ERR_PORT / SITE_ADD_ERR_PHPEMPTY
```

### 站点名称命名规则

- 域名站点：`siteName` = 域名本身（如 `www.example.com`）
- IP端口站点：若同名IP已存在，`siteName` 自动追加 `_端口`（如 `192.168.10.194_9321`）
- 删除时 `webname` 参数应使用此 `siteName`，而非原始 domain 输入

---

## DeleteSite — 删除PHP站点

删除一个 PHP 站点及其相关配置，可选择是否同时删除网站目录、FTP账户、数据库。

### 调用方式

```bash
btpython scripts/php_site.py delete --site_id <站点ID> --domain <站点名称> --delete_path <是否删除目录> --ftp <是否删除FTP> --database <是否删除数据库>
```

```python
from php_site import BtPanelPhpSite
site = BtPanelPhpSite()
result = site.delete_site(site_id='126', domain='192.168.10.194_9321', delete_path=True, ftp=False, database=False)
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `site_id` | 是 | 站点在面板数据库中的ID，创建站点时返回的 `siteId` 字段值 | 从创建返回值获取，或通过面板站点列表查询 |
| `domain` | 是 | 站点名称（webname），即面板中注册的站点名，通常是 `域名` 或 `IP_端口` 格式 | 从创建返回值获取，或通过面板站点列表查询 |
| `delete_path` | 否 | 是否同时删除网站目录文件，`True`=删除，`False`=保留 | 默认 `True`，**必须与用户确认** |
| `ftp` | 否 | 是否同时删除站点关联的FTP账户 | 默认 `False`，**必须与用户确认** |
| `database` | 否 | 是否同时删除站点关联的数据库 | 默认 `False`，**必须与用户确认** |

### 参数规则

- `site_id`：必须是面板 `sites` 表中存在的有效ID
- `domain`：必须是面板 `sites` 表中对应 `site_id` 的 `name` 字段值
- `delete_path`、`ftp`、`database`：涉及数据丢失风险，操作前**必须与用户确认**

### 返回值

```python
{'status': True, 'msg': 'SITE_DEL_SUCCESS'}   # 成功
{'status': False, 'msg': '错误原因'}            # 失败
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | bool | `True`=删除成功，`False`=删除失败 |
| `msg` | str | 成功时为 `SITE_DEL_SUCCESS`；失败时为具体错误信息 |

### 删除操作范围

删除站点时会清理以下内容：
- Nginx/Apache 配置文件
- 反向代理配置、重定向配置、目录保护配置
- 伪静态规则文件、日志文件、SSL证书配置
- open_basedir 配置
- 防火墙端口规则（非80端口）
- 数据库记录（sites、domain、binding 表）
- 可选：网站目录文件、FTP账户、数据库

---

## 脚本文件

封装脚本 [scripts/php_site.py](../scripts/php_site.py) 提供 `BtPanelPhpSite` 类：

- `list_sites(project_type=None)` → 查询站点列表
- `get_php_versions()` → 查询可用PHP版本
- `add_site(domain, site_path, php_version='00', ps='来自AI助手', ftp=False, sql=False)` → 创建PHP站点
- `delete_site(site_id, domain, delete_path=True, ftp=False, database=False)` → 删除PHP站点

---

## 错误码参考

| 错误码/信息 | 含义 | 处理建议 |
|-------------|------|----------|
| `SITE_ADD_ERR_DOMAIN_EXISTS` | 域名+端口组合已存在 | 更换域名或端口 |
| `SITE_ADD_ERR_PORT` | 端口不合法 | 使用合法端口（1-65535） |
| `SITE_ADD_ERR_PHPEMPTY` | PHP版本号为空 | 传入有效PHP版本或 `00` |
| `SITE_ADD_ERR_DOMAIN` | 域名格式不合法 | 使用合法域名或IP |
| `SITE_ADD_ERR_DOMAIN_TOW` | 域名包含泛解析 `*` | 不使用泛解析 |
| `SITE_ADD_ERR_WRITE` | 配置文件写入失败 | 检查Nginx/Apache配置 |
| `PATH_ERROR` | 网站目录路径不合法 | 使用合法绝对路径 |
| `指定站点不存在` | 删除时站点ID不存在 | 确认正确的site_id |
| `检测到配置文件有错误` | Nginx/Apache配置存在语法错误 | 先修复配置文件再操作 |