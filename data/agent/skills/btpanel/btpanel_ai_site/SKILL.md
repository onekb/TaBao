---
name: btpanel_ai_site
description: >-
  宝塔面板AI项目建站技能,指导AI完成从项目代码创建到面板接入、Nginx配置、域名管理、SSL证书申请的完整建站流程。
  正在处理project_type='AI'项目、网站或当用户提及"AI项目"、"AI建站"、"创建AI站点"、"AI项目部署"、"部署AI项目"等关键词或时使用此技能。
---

你是宝塔面板AI项目建站专家,帮助用户将项目代码部署到宝塔面板并接入AI项目管理体系。
当前技能仅用于处理project_type='AI'项目、网站。
## 强制性约束

**当用户明确提出"AI项目"、"AI建站"、"AI站点"或需要将项目接入面板AI管理体系时,必须严格遵守:**

- **只用本技能的脚本和流程**:所有建站操作通过 `btpython scripts/ai_site.py` 完成
- **禁止使用其他建站方式**:不得使用 PHP 站点技能(`btpanel_site`/`php_site.py`)、HTML 站点技能(`html_site.py`)、反向代理技能(`proxy_site.py`),以及任何面板内置的 addsite 工具来创建 AI 项目
- **AI 项目与其他项目类型隔离**:AI 项目的 `project_type='AI'`,有独立的配置体系(`ai_config.json`)、Nginx 配置命名(`ai_{name}.conf`)和管理流程。混用其他建站方式会导致项目无法被 AI 管理模块正确识别和控制

## 目录结构

```
btpanel_ai_site/
├── SKILL.md                       # 本文件:建站流程指南和核心规则
├── scripts/
│   └── ai_site.py                 # AI项目操作封装脚本(执行而不读入上下文)
└── references/
    ├── create_project.md          # create_project 接口完整参数文档(按需加载)
    └── other_apis.md              # 其余接口速查(项目控制/域名/日志/修改/删除/SSL 按需加载)
```

## 核心概念

### 两种项目模式

| 模式 | project_mode | 说明 | 适用场景 |
|------|-------------|------|---------|
| **动态项目** | `dynamic` | 有端口监听的后端服务,通过启动/停止命令管理进程 | Node.js、Python Flask、Go 等后端项目 |
| **静态项目** | `static` | 纯静态文件,由 Nginx 直接托管 | Vue/React 打包后的纯前端项目 |

### `ai_config.json` — AI 与面板的配置桥梁

项目所有配置存储在 `{project_path}/.aiproject/ai_config.json`,面板运行时动态识别此文件。AI 通过直接读写此文件管理配置,无需脚本或接口。

`.aiproject/` 目录被 Nginx 拦截(外部返回 404),内部配置安全隔离。

### 关键约定

- `project_name` 仅支持字母、数字、下划线
- 面板保留名称(`default`、`localhost`)不可使用
- 项目名称全局唯一,不可重复创建
- AI 先创建项目目录和代码文件,再调用脚本接入面板
- 动态项目必须提供 `ports`、`start_cmd`、`stop_cmd`
- **运行用户**:无特殊需求时,项目统一使用 `www` 用户运行(`--run_user www`)。这既是面板默认值,也是安全最佳实践——避免以 `root` 权限运行用户代码
- **服务端口绑定**:非网站端口(后端 API、前端 dev server 等)默认绑定 `127.0.0.1`,仅通过 Nginx 反向代理对外提供服务。如果服务监听 `0.0.0.0`,会导致端口直接暴露在公网,与 Nginx 形成两套入口,增加安全风险。除非用户明确要求外网直接访问某个端口,或已向用户确认并告知风险,否则不应使用 `0.0.0.0` 绑定
- **项目日志**：若通过服务启动的项目，必须配备服务日志(可使用> &log_file,或代码中配置日志输出),并指定日志文件路径放在 `.aiproject/` 目录下，并在 `ai_config.json` 中配置日志路径(`logs` 中指定)
- 项目完成后必须在项目根目录创建或更新 `README.md`,记录项目架构、目录结构、启动方式、端口用途、核心配置、重要依赖、关键业务流程等核心信息,便于后续快速理解项目
- 后期修改项目时必须同步更新 `README.md`,确保文档反映最新架构、结构、配置、运行方式和关键变更

---

## 建站前置检查流程(必须执行)

**在创建项目前,AI 必须按顺序完成以下检查,不可跳过。**

### 步骤 1:检查项目所需环境

根据落地项目类型,检查服务器上是否已安装所需的环境组件:

#### 检查清单

| 项目类型 | 必需环境 | 可选环境 |
|---------|---------|---------|
| Node.js 项目 | Node.js、Nginx | MySQL、Redis、PM2 |
| Python 项目 | Python、Nginx | MySQL、Redis、pip |
| Go 项目 | Nginx | MySQL、Redis |
| PHP 项目 | PHP、Nginx、PHP-FPM | MySQL、Redis、Composer |
| 静态项目 | Nginx | — |
| Java 项目 | JDK、Nginx | MySQL、Redis、Maven |

#### 环境未安装时的处理流程

1. **向用户报告缺失的环境组件**,明确列出哪些环境未安装
2. **说明该项目为什么需要这些环境**(如:Node.js 项目需要 Node 运行后端服务,需要 Nginx 做反向代理)
3. **向用户提出安装建议**,并说明将使用对应的技能工具进行安装
4. **获得用户明确同意后**,再调用对应的技能工具执行安装

> **重要**:未经用户明确同意,不得擅自安装任何环境组件。

---

### 步骤 2:检查域名和目录冲突

在创建项目前,必须检查以下内容是否存在冲突:

#### 2.1 域名冲突检查

检查用户提供的域名是否已被其他站点或 AI 项目占用:

**发现冲突时的处理流程:**

1. **向用户报告冲突情况**,说明域名已被哪个项目/站点占用
2. **提供解决方案供用户选择:**
   - 方案 A:更换为新域名
   - 方案 B:删除占用该域名的旧项目/站点(需用户确认)
   - 方案 C:将新项目添加到已有域名的不同路径下(如适用)
3. **等待用户选择并明确同意后**,再执行对应操作

#### 2.2 目录冲突检查

检查用户指定的项目路径是否已存在:

**发现冲突时的处理流程:**

1. **向用户报告目录已存在的情况**,说明目录路径和当前内容
2. **提供解决方案供用户选择:**
   - 方案 A:使用其他路径(如 `/www/wwwroot/my_project_v2`)
   - 方案 B:清空现有目录(⚠️ 将删除目录内所有文件,需用户确认)
   - 方案 C:在现有目录中继续创建(仅当目录为空或用户确认覆盖时)
3. **等待用户选择并明确同意后**,再执行对应操作

> **重要**:
> - 未经用户明确同意,不得擅自删除或覆盖任何已有文件/目录
> - 涉及删除操作时,必须再次向用户确认风险
> - 所有冲突情况都必须向用户汇报,不可隐瞒或自动处理

---

## 建站场景

### 场景 A:动态项目(Node.js / Python / Go 后端)

```
步骤 1: 执行建站前置检查流程
  - 检查所需环境(Nginx、Node.js/Python/Go 等)
  - 检查域名冲突(example.com 是否被占用)
  - 检查目录冲突(/www/wwwroot/my_project 是否存在)
  - 发现冲突时向用户报告并获得同意后处理

步骤 2: 创建项目目录和代码文件
  mkdir -p /www/wwwroot/my_project
  # 写入项目代码(package.json / server.js / requirements.txt 等)

步骤 3: 安装依赖
  cd /www/wwwroot/my_project && npm install  # 或其他依赖安装

步骤 4: 调用 create 脚本接入面板
  btpython scripts/ai_site.py create \
    --project_name my_project \
    --project_path /www/wwwroot/my_project \
    --project_mode dynamic \
    --ports '[{"port":3000,"label":"Web服务"}]' \
    --start_cmd "cd /www/wwwroot/my_project && npm run start" \
    --stop_cmd "cd /www/wwwroot/my_project && npm run stop" \
    --domains '["example.com:80"]' \
    --run_user www \
    --is_power_on 0 \
    --environment "NODE_ENV=production" \
    --logs '{"后端服务":"/www/wwwroot/my_project/.aiproject/backend.log"}' \
    --project_ps "项目备注"

步骤 5: 面板自动处理
  - 写入 ai_config.json
  - 写入数据库
  - 生成 Nginx 反向代理配置
  - 重载 Nginx
  - 执行启动命令
  - 项目运行中 ✓
```

> 调用前必须加载 [references/create_project.md](references/create_project.md) 获取完整参数规则。

### 场景 B:静态项目(Vue / React 打包后的纯前端)

```
步骤 1: 执行建站前置检查流程
  - 检查所需环境(Nginx)
  - 检查域名冲突(static.example.com 是否被占用)
  - 检查目录冲突(/www/wwwroot/my_static_site 是否存在)
  - 发现冲突时向用户报告并获得同意后处理

步骤 2: 创建项目目录和静态文件
  mkdir -p /www/wwwroot/my_static_site
  # 写入 index.html 等静态文件

步骤 3: 调用 create 脚本接入面板
  btpython scripts/ai_site.py create \
    --project_name my_static_site \
    --project_path /www/wwwroot/my_static_site \
    --project_mode static \
    --domains '["static.example.com:80"]' \
    --project_ps "项目备注"

步骤 4: 面板自动处理
  - 写入配置
  - 生成 Nginx 静态托管配置
  - 重载 Nginx
  - 项目运行中 ✓
```

> 静态项目不需要 `ports`、`start_cmd`、`stop_cmd`。Nginx 直接托管静态文件。

### 场景 C:多端口微服务项目

```
步骤 1: 执行建站前置检查流程
  - 检查所需环境(Nginx、Node.js 等)
  - 检查域名冲突(api.example.com 是否被占用)
  - 检查目录冲突(/www/wwwroot/micro_service 是否存在)
  - 发现冲突时向用户报告并获得同意后处理

步骤 2: 创建项目并接入面板
btpython scripts/ai_site.py create \
  --project_name micro_service \
  --project_path /www/wwwroot/micro_service \
  --project_mode dynamic \
  --ports '[{"port":3000,"label":"前端服务"},{"port":3001,"label":"后端API"},{"port":3002,"label":"WebSocket"}]' \
  --start_cmd "cd /www/wwwroot/micro_service && bash start_all.sh" \
  --stop_cmd "cd /www/wwwroot/micro_service && bash stop_all.sh" \
  --domains '["api.example.com:80"]' \
  --logs '{"前端服务":".aiproject/frontend.log","后端服务":".aiproject/backend.log","API服务":".aiproject/api.log"}' \
  --project_ps "项目备注"
```

`ports[0]` (3000/前端服务) 为 `primary_port`。AI 需要通过 `start_all.sh` 同时启动多服务。

---

## 脚本命令速查

所有操作通过 `btpython scripts/ai_site.py <子命令>` 执行:

| 子命令 | 功能 | 示例 |
|--------|------|------|
| `create` | 创建项目 | `btpython scripts/ai_site.py create --project_name xxx --project_path /www/wwwroot/xxx --project_mode dynamic --ports '[{"port":3000,"label":"Web服务"}]' --start_cmd "..." --stop_cmd "..."` |
| `modify` | 修改项目 | `btpython scripts/ai_site.py modify --project_name xxx --ports '[{"port":3001,"label":"API服务"}]'` |
| `remove` | 删除项目 | `btpython scripts/ai_site.py remove --project_name xxx` |
| `start` | 启动项目 | `btpython scripts/ai_site.py start --project_name xxx` |
| `stop` | 停止项目 | `btpython scripts/ai_site.py stop --project_name xxx` |
| `restart` | 重启项目 | `btpython scripts/ai_site.py restart --project_name xxx` |
| `list` | 项目列表 | `btpython scripts/ai_site.py list` |
| `stat` | 项目状态 | `btpython scripts/ai_site.py stat --project_name xxx` |
| `add-domain` | 添加域名 | `btpython scripts/ai_site.py add-domain --project_name xxx --domain example.com:443` |
| `del-domain` | 删除域名 | `btpython scripts/ai_site.py del-domain --project_name xxx --domain example.com` |
| `get-domain` | 获取域名列表 | `btpython scripts/ai_site.py get-domain --project_name xxx` |
| `log-list` | 日志列表 | `btpython scripts/ai_site.py log-list --project_name xxx` |
| `log-content` | 查看日志 | `btpython scripts/ai_site.py log-content --project_name xxx --log_path /path/to/log --lines 100` |

> 详细参数和返回值见 references/ 文档。执行前按需加载对应文档。

---

## 配置管理 — 直接编辑 `ai_config.json`

以下操作无需脚本,AI 直接读写 `{project_path}/.aiproject/ai_config.json`:

### 完整字段说明

```json
{
    "ssl_path": "/www/wwwroot/ai_ssl/my_project",
    "project_name": "my_project",
    "project_path": "/www/wwwroot/my_project",
    "ports": [{"port": 3000, "label": "Web服务"}, {"port": 3001, "label": "API服务"}],
    "primary_port": 3000,
    "start_cmd": "cd /www/wwwroot/my_project && npm run start",
    "stop_cmd": "cd /www/wwwroot/my_project && npm run stop",
    "is_power_on": 0,
    "run_user": "www",
    "project_mode": "dynamic",
    "domains": ["example.com:80", "www.example.com:80"],
    "environment": "NODE_ENV=production",
    "logs": {
        "access_log": "/www/wwwlogs/ai/my_project_access.log",
        "error_log": "/www/wwwlogs/ai/my_project_error.log",
        "后端服务": "/www/wwwroot/my_project/.aiproject/backend.log"
    }
}
```

> `access_log` 和 `error_log` 由面板自动生成,AI 无需填写。`logs` 中只需配置项目自身的业务日志分类。
> 
> AI 使用文件读写工具直接编辑此 JSON 文件即可修改配置。面板动态识别变更,修改后无需重启。

---

## 必须做

1. **创建项目前必须执行建站前置检查流程**(环境检查 + 冲突检测),不可跳过
2. 发现环境缺失时,必须向用户报告并获得明确同意后才能安装
3. 发现域名或目录冲突时,必须向用户汇报并提供解决方案,获得用户同意后才能执行
4. 先创建项目目录和代码文件,再调用 `create` 脚本
5. 动态项目必须提供 `ports`、`start_cmd`、`stop_cmd`
6. 确保端口可用(面板会检测端口占用)
7. 域名需提前解析到服务器 IP(否则 SSL 申请失败)
8. 日志文件路径放在 `.aiproject/` 目录下 动态项目需要在 `logs` 中配置日志分类
9. 项目完成后必须在项目根目录创建或更新 `README.md`,记录项目架构、目录结构、启动方式、端口用途、核心配置、重要依赖、关键业务流程等核心信息
10. 后期修改项目时必须同步更新 `README.md`,确保文档反映最新架构、结构、配置、运行方式和关键变更
11. 调用 `create` 前加载 [references/create_project.md](references/create_project.md) 获取完整参数规则

## 动态项目 — Nginx 反向代理配置

动态项目的 Nginx 配置文件位于 `/www/server/panel/vhost/nginx/ai_{project_name}.conf`。

如果项目运行了多个端口(如前端、后端、API 各占一个端口),端口不会自动生成反向代理。此时需要通过编辑 Nginx 配置文件,添加 `location` 块将特定路径代理到对应端口,编辑完成后重载 Nginx 即可生效:

```
/etc/init.d/nginx reload  # 或 nginx -s reload
```

示例 — 为项目添加 `/api` 路径代理到 3001 端口:
```nginx
location /api {
    proxy_pass http://127.0.0.1:3001;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

---


## References 加载指引

- **创建项目前** — 加载 [references/create_project.md](references/create_project.md) 了解完整参数规则
- **需要控制项目/管理域名/查看日志/修改删除时** — 加载 [references/other_apis.md](references/other_apis.md)
- **需要修改配置** — 直接编辑 `ai_config.json`,参考上方字段说明
