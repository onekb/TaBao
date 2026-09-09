---
name: btpanel_mail
description: 宝塔邮局管理技能，提供邮局服务管理、域名配置、邮箱账户管理、DNS 解析配置等功能
author: Baota Team
category: mail
tags:
  - mail
  - postfix
  - dovecot
  - email
  - 邮局
---

# Skill: btpanel_mail

# 宝塔邮局管理技能

宝塔邮局（BT Mail）是基于宝塔面板的企业级邮件系统管理工具，提供完整的邮件服务器搭建、域名配置、邮箱账户管理、DNS 解析配置等功能。

![宝塔邮局](/www/server/panel/data/agent/skills/btpanel_mail/icon/ico-mail_sys.png)

## 功能概述

本技能提供以下核心功能：

| 功能模块 | 描述 |
|---------|------|
| **邮局初始化** | 一键安装和配置 Postfix、Dovecot、Rspamd 等邮件服务 |
| **域名管理** | 添加、删除、查询邮件域名 |
| **邮箱账户** | 创建、删除、批量管理邮箱账户 |
| **DNS 解析** | 自动配置 MX、SPF、DKIM、DMARC 等 DNS 记录 |
| **服务监控** | 检查邮件服务运行状态 |
| **证书管理** | SSL 证书配置和自动续签 |

## 核心服务组件

宝塔邮局依赖以下核心服务：

| 服务 | 端口 | 用途 |
|------|------|------|
| **Postfix** | 25 (SMTP) | 邮件发送和接收 |
| **Dovecot** | 143 (IMAP), 993 (IMAPS) | 邮件收取 |
| **Rspamd** | 11333 | 垃圾邮件过滤 |
| **OpenDKIM** | - | 邮件签名验证 |

## AI 使用约束（重要）

使用本技能时，AI **必须**遵循以下原则：

### 🚫 绝对禁止的操作

1. **禁止任何手动操作**：无论什么情况下，都不得使用手动命令行操作（如 `os.system`、`public.ExecShell` 等直接执行系统命令）
2. **禁止绕过面板接口**：所有操作必须通过宝塔面板已封装的接口进行
3. **禁止修改配置文件**：不得直接编辑 `/etc/postfix/`、`/etc/dovecot/` 等配置文件

### ✅ 必须遵守的规则

1. **接口选择**：根据授权状态自动选择可用接口
   - 内部判断授权状态，不向用户展示判断过程
   - 只展示操作步骤和结果
2. **检查安装状态**：在执行任何操作前，必须先检查邮局是否已安装
3. **初始化检查**：检查邮局是否已初始化，未初始化时调用 `setup_mail_sys`
4. **服务状态检查**：可以使用检测类接口检查服务状态
5. **密码强度**：创建邮箱时使用符合强度要求的密码（大小写字母 + 数字，长度≥8）
6. **批量操作提示**：批量创建邮箱时先告知用户操作内容
7. **数据安全**：不主动泄露邮箱密码等敏感信息

### 接口使用说明

| 接口类型 | 可用功能 | 说明 |
|---------|---------|------|
| **完整功能** | 所有接口 | 包括安装、初始化、自动 DNS 配置等 |
| **基础功能** | 核心接口 | 包括初始化、域名管理、邮箱管理等 |

## 执行流程示例

```
AI: 我将为您执行以下操作：
    1. 检查邮局安装状态
    2. [如未安装] 安装邮局服务
    3. 检查邮局初始化状态
    4. [如未初始化] 初始化邮局系统
    5. 检查邮局服务状态（Postfix、Dovecot、Rspamd）
    6. 添加域名 example.com
    7. 配置 DNS 解析记录
    正在获取数据，请稍候...
    [调用接口]
    [展示结果]
```

**注意**：内部会自动判断可用接口，不向用户展示判断过程。

---

## Python 接口调用方法

### 完整调用流程（内部实现）

```python
import sys
import os
import time
import json
sys.path.insert(0, '/www/server/panel')
sys.path.insert(0, '/www/server/panel/class')
os.chdir('/www/server/panel')

from mod.base import public_aap as public

# 内部函数：检查授权状态（不展示给用户）
def _check_auth():
    auth_file = '/www/server/panel/data/auth_list.json'
    if os.path.exists(auth_file):
        try:
            auth_data = json.loads(public.readFile(auth_file))
            ltd = auth_data.get('ltd', 0)
            current_time = int(time.time())
            return ltd > current_time
        except:
            return False
    return False

# 内部函数：根据授权选择接口（不展示给用户）
def _get_mail_interface():
    if _check_auth():
        from mailModel.mainModel import main as MailMain
        from mailModel.manageModel import main as MailManage
        return MailMain(), MailManage(), True
    else:
        MAIL_SYS_PLUGIN = '/www/server/panel/plugin/mail_sys/mail_sys_main.py'
        if not os.path.exists(MAIL_SYS_PLUGIN):
            return None, None, False
        sys.path.insert(0, '/www/server/panel/plugin/mail_sys')
        from mail_sys_main import mail_sys_main as MailMain
        return MailMain(), None, False

# 获取接口（内部操作）
mail, manage, has_full_access = _get_mail_interface()

if not mail:
    print("邮局服务不可用")
    sys.exit(1)

class Args:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

# 对外展示的步骤（用户可见）
print("="*60)
print("宝塔邮局部署")
print("="*60)

# 步骤 1: 检查安装状态
print("\n[步骤 1] 检查邮局安装状态...")
if has_full_access:
    install_check = manage.install_status(None)
    if not install_check.get('status', False):
        print("正在安装邮局服务...")
        manage.install_service(None)
        print("安装任务已提交，请等待完成后重试")
        sys.exit(0)
else:
    if not os.path.exists('/www/server/panel/plugin/mail_sys/mail_sys_main.py'):
        print("邮局插件未安装")
        sys.exit(1)

print("✓ 邮局已安装")

# 步骤 2: 检查初始化状态
print("\n[步骤 2] 检查邮局初始化状态...")
init_check = mail.check_mail_sys(None)
if not init_check.get('status', False):
    print("正在初始化邮局系统...")
    args = Args(
        domain='example.com',
        a_record='mail.example.com',
        ips='1.2.3.4'
    )
    result = mail.setup_mail_sys(args)
    print(f"初始化完成：{result.get('msg', '')}")
else:
    print("✓ 邮局已初始化")

# 步骤 3: 检查服务状态
print("\n[步骤 3] 检查服务状态...")
status = mail.get_service_status(None)
print(f"Postfix: {'✓' if status['data']['postfix'] else '✗'}")
print(f"Dovecot: {'✓' if status['data']['dovecot'] else '✗'}")
print(f"Rspamd: {'✓' if status['data']['rspamd'] else '✗'}")
```

### 核心接口方法

#### 1. 检查邮局初始化状态

```python
result = mail.check_mail_sys(None)

# 已初始化返回
{
    "status": True,
    "msg": "邮局系统已经存在，重装之前请先卸载!"
}

# 未初始化返回
{
    "status": False,
    "msg": "之前没有安装过邮局系统，请放心安装!"
}

# 判断逻辑
if result['status']:
    print("邮局已初始化")
else:
    print("需要初始化邮局系统")
```

#### 2. 初始化邮局系统

```python
# 注意：mailModel 和插件版本各有自己的 setup_mail_sys 实现
# 使用时通过已选择的 mail 对象调用

class Args:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

args = Args(
    domain='example.com',      # 主域名
    a_record='mail.example.com',  # A 记录
    ips='1.2.3.4'              # 服务器 IP
)

result = mail.setup_mail_sys(args)
```

#### 3. 检查服务状态

```python
result = mail.get_service_status(None)

# 返回示例
{
    "status": True,
    "data": {
        "postfix": True,      # Postfix 状态
        "dovecot": True,      # Dovecot 状态
        "rspamd": True,       # Rspamd 状态
        "opendkim": False,    # OpenDKIM 状态
        "change_rspamd": False
    }
}
```

#### 4. 添加域名

```python
# 方法一：标准添加（需要 DNS 验证）
args = Args(
    domain='example.com',
    a_record='mail.example.com',
    ips='1.2.3.4'
)
result = mail.add_domain(args)

# 方法二：跳过 DNS 验证（推荐）
args = Args(
    domain='example.com',
    a_record='mail.example.com',
    ips='1.2.3.4',
    mailboxes=1000,           # 邮箱数量限制
    mailbox_quota='1 GB',     # 单个邮箱配额
    quota='10 GB',            # 域名总配额
    rate_limit=12             # 发送频率限制
)
result = mail.add_domain_new(args)
```

#### 5. 创建邮箱账户

```python
# 单个创建
args = Args(
    username='user@example.com',
    full_name='User Name',
    password='Password123',    # 必须包含大小写字母和数字，长度≥8
    quota='1 GB',
    is_admin=0,
    active=1
)
result = mail.add_mailbox(args)

# 批量创建
args = Args(
    content=json.dumps([
        "user1|user1@example.com|Password123|1|GB",
        "user2|user2@example.com|Password123|1|GB"
    ])
)
result = mail.add_mailbox_multiple(args)
```

#### 6. 自动配置 DNS 解析（完整功能可用）

```python
# 注意：此接口仅在完整功能下可用
args = Args(
    domain='example.com',
    a_record='mail.example.com'
)
result = mail.auto_create_dns_record(args)

# 自动创建以下 DNS 记录：
# - MX 记录：指向 mail.example.com
# - A 记录：mail.example.com 解析到服务器 IP
# - SPF 记录：v=spf1 a mx ~all
# - DKIM 记录：default._domainkey 签名
# - DMARC 记录：v=DMARC1;p=quarantine
```

#### 7. 查询域名列表

```python
result = mail.get_domain_name(None)

# 返回示例
{
    "status": True,
    "data": ["example.com", "test.com"]
}
```

#### 8. 查询邮箱列表

```python
args = Args(p=1, size=50)
result = mail.get_mailboxs(args)

# 返回示例
{
    "status": True,
    "data": [
        {
            "username": "user@example.com",
            "full_name": "User Name",
            "quota": 1073741824,
            "active": 1,
            "domain": "example.com"
        }
    ],
    "page": "分页 HTML"
}
```

#### 9. 删除域名

```python
# mailModel 和插件版本都支持此接口
args = Args(domain='example.com')
result = mail.delete_domain(args)

# 返回示例
{
    "status": True,
    "msg": "删除域成功! (example.com)"
}
```

#### 10. 删除邮箱

```python
# mailModel 和插件版本都支持此接口
args = Args(username='user@example.com')
result = mail.delete_mailbox(args)

# 返回示例
{
    "status": True,
    "msg": "删除邮箱用户成功! (user@example.com)"
}
```

#### 10. 发送邮件

```python
# mailModel 和插件版本都支持此接口
args = Args(
    username='user@example.com',
    mail_from='user@example.com',
    mail_to=['user1@example.com'],
    subject='测试邮件',
    content='这是一封测试邮件。',
    subtype='html',
    smtp_server='localhost'
)
result = mail.send_mail(args)

# 返回示例
{
    "status": True,
    "msg": "发送邮件成功"
}
```

---

## 接口可用性对照表

| 接口名称 | 完整功能 | 基础功能 | 说明              |
|---------|-----------|---------|-----------------|
| `install_service` | ✅ | ❌ | 安装邮局服务          |
| `install_status` | ✅ | ❌ | 检查安装状态          |
| `check_mail_sys` | ✅ | ✅ | 检查初始化状态         |
| `setup_mail_sys` | ✅ | ✅ | 初始化邮局系统         |
| `get_service_status` | ✅ | ✅ | 检查服务状态          |
| `add_domain` | ✅ | ✅ | 添加域名            |
| `add_domain_new` | ✅ | ✅ | 添加域名（跳过 DNS 验证） |
| `add_mailbox` | ✅ | ✅ | 创建邮箱            |
| `add_mailbox_multiple` | ✅ | ✅ | 批量创建邮箱          |
| `get_domain_name` | ✅ | ✅ | 查询域名列表          |
| `get_mailboxs` | ✅ | ✅ | 查询邮箱列表          |
| `auto_create_dns_record` | ✅ | ❌ | 自动配置 DNS        |
| `delete_domain` | ✅ | ✅ | 删除域名            |
| `delete_mailbox` | ✅ | ✅ | 删除邮箱            |
| `send_mail` | ✅ | ✅ | 发送邮件            |

**重要提示**：
- ✅ 表示接口可用
- ❌ 表示接口不可用
- **完整功能**：包含所有邮局管理功能
- **基础功能**：包含核心邮局管理功能

---

## 常用场景示例

### 场景一：完整部署流程

```python
#!/usr/bin/env python3
import sys
import os
import json
import time
sys.path.insert(0, '/www/server/panel')
sys.path.insert(0, '/www/server/panel/class')
os.chdir('/www/server/panel')

from mod.base import public_aap as public

# 内部函数：检查授权状态
def _check_auth():
    auth_file = '/www/server/panel/data/auth_list.json'
    if os.path.exists(auth_file):
        try:
            auth_data = json.loads(public.readFile(auth_file))
            ltd = auth_data.get('ltd', 0)
            current_time = int(time.time())
            return ltd > current_time
        except:
            return False
    return False

# 内部函数：根据授权选择接口
def _get_mail_interface():
    if _check_auth():
        from mailModel.mainModel import main as MailMain
        from mailModel.manageModel import main as MailManage
        return MailMain(), MailManage(), True
    else:
        MAIL_SYS_PLUGIN = '/www/server/panel/plugin/mail_sys/mail_sys_main.py'
        if not os.path.exists(MAIL_SYS_PLUGIN):
            return None, None, False
        sys.path.insert(0, '/www/server/panel/plugin/mail_sys')
        from mail_sys_main import mail_sys_main as MailMain
        return MailMain(), None, False

print("="*60)
print("宝塔邮局部署")
print("="*60)

# 获取接口（内部操作，不展示给用户）
mail, manage, has_full_access = _get_mail_interface()

if not mail:
    print("\n✗ 邮局服务不可用")
    sys.exit(1)

class Args:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

# 步骤 1: 检查安装状态
print("\n[步骤 1] 检查邮局安装状态...")
if has_full_access:
    install_check = manage.install_status(None)
    if not install_check.get('status', False):
        print("正在安装邮局服务...")
        install_result = manage.install_service(None)
        print(f"安装结果：{install_result.get('msg', '')}")
        print("请等待安装完成后重新运行")
        sys.exit(0)
else:
    if not os.path.exists('/www/server/panel/plugin/mail_sys/mail_sys_main.py'):
        print("✗ 邮局插件未安装")
        sys.exit(1)

print("✓ 邮局已安装")

# 步骤 2: 检查初始化状态
print("\n[步骤 2] 检查邮局初始化状态...")
init_check = mail.check_mail_sys(None)
if not init_check.get('status', False):
    print("正在初始化邮局系统...")
    args = Args(
        domain='example.com',
        a_record='mail.example.com',
        ips='1.2.3.4'
    )
    result = mail.setup_mail_sys(args)
    print(f"初始化完成：{result.get('msg', '')}")
else:
    print("✓ 邮局已初始化")

# 步骤 3: 检查服务状态
print("\n[步骤 3] 检查服务状态...")
status = mail.get_service_status(None)
print(f"Postfix: {'✓ 运行中' if status['data']['postfix'] else '✗ 未运行'}")
print(f"Dovecot: {'✓ 运行中' if status['data']['dovecot'] else '✗ 未运行'}")
print(f"Rspamd: {'✓ 运行中' if status['data']['rspamd'] else '✗ 未运行'}")

# 步骤 4: 添加域名
print("\n[步骤 4] 添加域名...")
args = Args(
    domain='example.com',
    a_record='mail.example.com',
    ips='1.2.3.4',
    mailboxes=1000,
    mailbox_quota='1 GB',
    quota='10 GB',
    rate_limit=12
)
result = mail.add_domain_new(args)
print(f"域名添加：{result.get('msg', '')}")

# 步骤 5: 自动配置 DNS（完整功能）
if has_full_access:
    print("\n[步骤 5] 自动配置 DNS...")
    args = Args(domain='example.com', a_record='mail.example.com')
    result = mail.auto_create_dns_record(args)
    print(f"DNS 配置：{result.get('msg', '')}")
else:
    print("\n[步骤 5] 跳过 DNS 自动配置")
    print("   请手动配置 DNS 记录")

# 步骤 6: 创建管理员邮箱
print("\n[步骤 6] 创建管理员邮箱...")
args = Args(
    username='admin@example.com',
    full_name='Admin',
    password='AdminPass123',
    quota='2 GB',
    is_admin=1,
    active=1
)
result = mail.add_mailbox(args)
print(f"邮箱创建：{result.get('msg', '')}")

print("\n" + "="*60)
print("邮局配置完成!")
print("="*60)
```

### 场景二：批量创建测试邮箱

```python
#!/usr/bin/env python3
import sys
import os
import json
import time
sys.path.insert(0, '/www/server/panel')
sys.path.insert(0, '/www/server/panel/class')
os.chdir('/www/server/panel')

from mod.base import public_aap as public

# 内部函数：检查授权状态
def _check_auth():
    auth_file = '/www/server/panel/data/auth_list.json'
    if os.path.exists(auth_file):
        try:
            auth_data = json.loads(public.readFile(auth_file))
            ltd = auth_data.get('ltd', 0)
            current_time = int(time.time())
            return ltd > current_time
        except:
            return False
    return False

# 内部函数：根据授权选择接口
def _get_mail_interface():
    if _check_auth():
        from mailModel.mainModel import main as MailMain
        from mailModel.manageModel import main as MailManage
        return MailMain(), MailManage(), True
    else:
        MAIL_SYS_PLUGIN = '/www/server/panel/plugin/mail_sys/mail_sys_main.py'
        if not os.path.exists(MAIL_SYS_PLUGIN):
            return None, None, False
        sys.path.insert(0, '/www/server/panel/plugin/mail_sys')
        from mail_sys_main import mail_sys_main as MailMain
        return MailMain(), None, False

mail, manage, has_full_access = _get_mail_interface()

if not mail:
    print("邮局服务不可用")
    sys.exit(1)

class Args:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

# 检查安装状态
if has_full_access:
    install_check = manage.install_status(None)
    if not install_check.get('status', False):
        print("邮局未安装")
        sys.exit(1)

# 检查初始化状态
check_result = mail.check_mail_sys(None)
if not check_result.get('status', False):
    print("邮局未初始化")
    sys.exit(1)

domain = 'example.com'
count = 50
password = 'TestPass123'

print(f"开始创建 {count} 个测试邮箱...")

success = 0
fail = 0

for i in range(1, count + 1):
    args = Args(
        username=f'test{i}@{domain}',
        full_name=f'Test User {i}',
        password=password,
        quota='1 GB',
        is_admin=0,
        active=1
    )
    
    result = mail.add_mailbox(args)
    if result.get('status', False):
        success += 1
    else:
        fail += 1

print(f"创建完成：成功 {success} 个，失败 {fail} 个")
```

---

## 数据库结构

宝塔邮局使用 SQLite 数据库存储配置，数据库文件位于：

- **主数据库**: `/www/vmail/postfixadmin.db`
- **日志数据库**: `/www/vmail/postfixmaillog.db`

### 主要数据表

#### domain 表（域名）

| 字段 | 类型 | 说明 |
|------|------|------|
| domain | TEXT | 域名 |
| a_record | TEXT | A 记录 |
| mailboxes | INTEGER | 邮箱数量限制 |
| mailbox_quota | INTEGER | 单个邮箱配额（字节） |
| quota | INTEGER | 域名总配额（字节） |
| rate_limit | INTEGER | 发送频率限制 |
| created | DATETIME | 创建时间 |

#### mailbox 表（邮箱）

| 字段 | 类型 | 说明 |
|------|------|------|
| username | TEXT | 邮箱地址 |
| full_name | TEXT | 显示名称 |
| password | TEXT | 加密密码 |
| password_encode | TEXT | 可解密密码 |
| quota | INTEGER | 配额（字节） |
| domain | TEXT | 所属域名 |
| active | INTEGER | 是否启用 |
| is_admin | INTEGER | 是否管理员 |
| created | DATETIME | 创建时间 |
| modified | DATETIME | 修改时间 |

---

## 配置文件位置

| 文件 | 路径 | 说明 |
|------|------|------|
| Postfix 主配置 | `/etc/postfix/main.cf` | Postfix 配置 |
| Dovecot 主配置 | `/etc/dovecot/dovecot.conf` | Dovecot 配置 |
| Rspamd 配置 | `/etc/rspamd/` | Rspamd 配置目录 |
| 虚拟邮箱目录 | `/www/vmail/` | 邮箱数据存储 |
| 邮局插件目录 | `/www/server/panel/plugin/mail_sys/` | 插件文件 |
| 邮局模型目录 | `/www/server/panel/class/mailModel/` | 核心代码 |
| 授权文件 | `/www/server/panel/data/auth_list.json` | 授权信息 |
| 安装检测文件 | `/etc/postfix/sqlite_virtual_domains_maps.cf` | 邮局安装标志 |

---

## 接口实现说明

### setup_mail_sys 接口

`setup_mail_sys` 接口在两个版本中各有实现：

| 版本 | 文件位置 | 类名 |
|------|---------|------|
| **完整功能** | `/www/server/panel/class/mailModel/mainModel.py` | `main` (mailModel.mainModel) |
| **基础功能** | `/www/server/panel/plugin/mail_sys/mail_sys_main.py` | `mail_sys_main` |

**使用方式**：
```python
# 通过已选择的 mail 对象调用，不要混用
result = mail.setup_mail_sys(args)
```

### 接口选择逻辑（内部实现）

```python
def _get_mail_interface():
    """
    根据授权状态选择可用接口
    此函数为内部实现，不向用户展示
    """
    # 检查授权状态
    auth_file = '/www/server/panel/data/auth_list.json'
    has_full_access = False
    
    if os.path.exists(auth_file):
        try:
            auth_data = json.loads(public.readFile(auth_file))
            ltd = auth_data.get('ltd', 0)
            current_time = int(time.time())
            has_full_access = ltd > current_time
        except:
            pass
    
    # 根据授权选择接口
    if has_full_access:
        from mailModel.mainModel import main as MailMain
        from mailModel.manageModel import main as MailManage
        return MailMain(), MailManage(), True
    else:
        MAIL_SYS_PLUGIN = '/www/server/panel/plugin/mail_sys/mail_sys_main.py'
        if not os.path.exists(MAIL_SYS_PLUGIN):
            return None, None, False
        sys.path.insert(0, '/www/server/panel/plugin/mail_sys')
        from mail_sys_main import mail_sys_main as MailMain
        return MailMain(), None, False
```

---

## 故障排查

### 1. 邮局未安装

```python
# 完整功能
from mailModel.manageModel import main as MailManage
manage = MailManage()
result = manage.install_status(None)
print(f"安装状态：{result.get('status', False)}")

# 基础功能
if not os.path.exists('/www/server/panel/plugin/mail_sys/mail_sys_main.py'):
    print("邮局插件未安装")
```

### 2. 邮局未初始化

```python
# 两个版本都使用此接口检查
result = mail.check_mail_sys(None)
if not result.get('status', False):
    print("邮局未初始化，需要执行 setup_mail_sys")
    # 调用初始化接口
    args = Args(domain='example.com', ...)
    mail.setup_mail_sys(args)
```

### 3. 服务无法启动

```bash
# 检查服务状态
systemctl status postfix
systemctl status dovecot
systemctl status rspamd

# 查看日志
journalctl -u postfix -f
journalctl -u dovecot -f
```

### 4. 接口导入错误

```python
# 完整功能
try:
    from mailModel.mainModel import main as MailMain
    from mailModel.manageModel import main as MailManage
    print("✓ 接口导入成功")
except Exception as e:
    print(f"✗ 导入失败：{e}")

# 基础功能
MAIL_SYS_PLUGIN = '/www/server/panel/plugin/mail_sys/mail_sys_main.py'
if os.path.exists(MAIL_SYS_PLUGIN):
    try:
        sys.path.insert(0, '/www/server/panel/plugin/mail_sys')
        from mail_sys_main import mail_sys_main as MailMain
        print("✓ 接口导入成功")
    except Exception as e:
        print(f"✗ 导入失败：{e}")
```

### 5. 域名 DNS 验证失败

检查 DNS 记录是否正确配置：

```bash
# 检查 MX 记录
dig MX example.com

# 检查 A 记录
dig mail.example.com

# 检查 SPF 记录
dig TXT example.com
```

### 6. 邮箱无法登录

- 检查密码强度是否符合要求
- 确认邮箱状态是否为 active=1
- 检查 Dovecot 服务是否运行
- 验证 IMAP 端口（143/993）是否开放

---

## 安全建议

1. **启用 SSL/TLS**: 为邮件服务配置 SSL 证书
2. **强密码策略**: 密码必须包含大小写字母和数字，长度≥8
3. **定期更新**: 保持 Postfix、Dovecot 为最新版本
4. **监控日志**: 定期检查邮件日志发现异常
5. **限制发送频率**: 设置合理的 rate_limit 防止滥用
6. **配置防火墙**: 仅开放必要的端口（25、143、993、995）
7. **使用面板接口**：所有操作必须通过面板接口，禁止手动操作

---

## 重要提示

### 🚫 禁止的操作

- **禁止手动操作**：不得使用 `os.system`、`public.ExecShell` 等直接执行系统命令
- **禁止修改配置文件**：不得直接编辑 `/etc/postfix/`、`/etc/dovecot/` 等配置文件
- **禁止绕过面板接口**：所有操作必须通过宝塔面板已封装的接口进行
- **禁止混用接口**：mailModel 和插件版本的接口不要混用

### ✅ 推荐的做法

- **接口选择**：内部自动判断可用接口，不向用户展示判断过程
- **检查安装状态**：操作前检查邮局是否已安装
- **检查初始化状态**：操作前使用 `check_mail_sys` 检查
- **初始化操作**：未初始化时使用 `setup_mail_sys` 进行初始化
- **检查服务状态**：可以使用检测类接口检查服务状态
- **用户可见输出**：只展示操作步骤和结果，不展示接口判断逻辑
