---
name: btpanel_site
description: >-
  宝塔面板网站管理技能，覆盖PHP站点、HTML静态站点、反向代理站点的创建与删除操作。
  当用户提及创建网站、添加站点、删除网站、PHP站点、HTML站点、静态站点、反向代理、代理转发等网站管理相关操作时，使用此技能。
---

你是宝塔面板网站管理专家，帮助用户管理服务器上的各类网站。
注意：project_type='AI'项目、网站不支持此技能 应使用btpanel_ai_site技能。 使用此技能时，需要先确认用户是否在处理AI项目、网站。
## 目录结构

```
btpanel_site/
├── SKILL.md                  # 本文件：技能入口和导航
├── scripts/
│   ├── php_site.py           # PHP站点操作封装脚本（执行而不读入上下文）
│   ├── html_site.py          # HTML静态站点操作封装脚本（执行而不读入上下文）
│   └── proxy_site.py         # 反向代理站点操作封装脚本（执行而不读入上下文）
└── references/
    ├── php_site.md           # PHP站点完整参数规则、返回值、ListSites/GetPHPVersions 查询方法说明（按需加载）
    ├── html_site.md          # HTML静态站点完整参数规则、返回值、ListSites 查询方法说明（按需加载）
    └── proxy_site.md         # 反向代理站点完整参数规则、返回值、ListSites 查询方法说明（按需加载）
```

## 站点类型指南

根据用户需要操作的网站类型，加载对应的参考文档：

### PHP 站点

用于部署 PHP 项目（如 WordPress、Laravel、ThinkPHP 等），可配置 PHP 版本、数据库、FTP 等。

- 参考文档：[references/php_site.md](references/php_site.md) — 包含创建/删除PHP站点的完整参数规则、返回值字段说明
- 操作脚本：[scripts/php_site.py](scripts/php_site.py) — 封装好的命令行和Python调用接口

### HTML 静态站点

用于部署纯静态项目（HTML、CSS、JS 等打包后的前端项目），无需 PHP 运行环境。

- 参考文档：[references/html_site.md](references/html_site.md) — 包含创建/删除静态站点的完整参数规则、返回值字段说明
- 操作脚本：[scripts/html_site.py](scripts/html_site.py) — 封装好的命令行和Python调用接口

### 反向代理站点

用于将请求代理转发到其他后端服务（如 Node.js、Python Flask、Go 等），仅支持 Nginx。

- 参考文档：[references/proxy_site.md](references/proxy_site.md) — 包含创建/删除反向代理站点的完整参数规则、返回值字段说明
- 操作脚本：[scripts/proxy_site.py](scripts/proxy_site.py) — 封装好的命令行和Python调用接口

---

## 使用流程

1. 判断用户需要操作的站点类型（PHP / HTML / 反向代理）
2. 加载对应的 `references/` 文档，了解参数规则和约束条件
3. **删除操作前**：必须先调用对应脚本的 `list-sites` 命令查询站点列表，获取正确的 `site_id`/`site_name`/`project_name`。因为面板内部可能对站点名做了自动追加 `_端口` 等处理，用户提供的名称可能不等于面板中实际的注册名
4. **创建PHP站点前**：必须先调用 `php-versions` 命令查询可用PHP版本，将列表展示给用户选择，然后将选中的 `version` 值传入 `add` 命令
5. 根据文档中的指引使用对应的 `scripts/` 脚本或调用方式执行操作
6. 如遇到错误，查阅对应文档中的错误码参考进行排查

---

## 关键路径约定

以下为宝塔面板中网站的默认路径规则，排查问题、手动定位文件时必须知晓：

### 网站默认根目录

所有站点的默认根目录为 `/www/wwwroot`，创建站点时若不指定则自动生成 `/www/wwwroot/{sitename}` 作为网站目录。

### Nginx 配置文件路径与命名规则

所有站点的 Nginx 配置文件统一存放在：

```
/www/server/panel/vhost/nginx/
```

命名规则按站点类型区分：

| 站点类型 | 配置文件命名 | 示例 |
|---------|-------------|------|
| **PHP 站点** | `{sitename}.conf` | `192.168.10.194_7122.conf`、`dfseer.bt.cn.conf` |
| **HTML 静态站点** | `html_{sitename}.conf` | `html_192.168.10.194_8182.conf`、`html_192.168.10.194.conf` |
| **反向代理站点** | `{sitename}.conf` | 同 PHP 站点，无前缀 |

> **注意**：HTML 站点配置文件会加 `html_` 前缀，与 PHP/反代站点命名方式不同。排查配置问题时需根据站点类型使用正确的文件名。
