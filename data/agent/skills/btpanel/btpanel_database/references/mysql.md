# MySQL 数据库管理

宝塔面板 MySQL 数据库操作指南。

---

## 可用方法

| 方法 | 作用 | 对应脚本命令 | 返回内容 |
|------|------|-------------|----------|
| `AddDatabase` | 创建一个MySQL数据库，同时创建同名用户并授予该数据库的全部权限。支持指定字符集、访问权限（本地/IP/所有人） | `btpython scripts/mysql_db.py add` | `{'status': True/False, 'msg': 'ADD_SUCCESS' 或错误信息}` |
| `DeleteDatabase` | 删除一个MySQL数据库及关联用户。若启用了回收站则移入回收站，否则永久删除 | `btpython scripts/mysql_db.py delete` | `{'status': True/False, 'msg': 'DEL_SUCCESS' 或错误信息}` |
| `ListDatabase` | 查看面板中所有MySQL数据库列表 | `btpython scripts/mysql_db.py list` | JSON数组，每项含 `name`, `username`, `accept`, `type` |

---

## AddDatabase — 创建数据库

创建一个 MySQL 数据库并自动创建同名用户、授予权限。

### 调用方式

```bash
btpython scripts/mysql_db.py add --name <数据库名> --db_user <用户名> --password <密码> --codeing <字符集> --address <访问权限>
```

```python
from mysql_db import BtPanelDatabase
db = BtPanelDatabase()
result = db.add_database(name='my_db', db_user='my_user', password='my_pass', codeing='utf8mb4', address='127.0.0.1')
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `name` | 是 | 数据库名称 | 询问用户 |
| `db_user` | 是 | 数据库用户名 | 询问用户 |
| `password` | 是 | 数据库密码 | 询问用户；留空则自动生成16位MD5密码 |
| `codeing` | 是 | 字符集，可选 `utf8` / `utf8mb4` / `gbk` / `big5` | 询问用户，默认推荐 `utf8mb4` |
| `address` | 是 | 访问权限：`127.0.0.1`（本地）/ `%`（所有人）/ 具体IP / 逗号分隔多IP | 询问用户，默认 `127.0.0.1` |
| `sid` | 否 | MySQL实例ID，0=本地数据库，非0=远程数据库 | 默认 `0`，远程数据库需询问用户 |
| `ps` | 否 | 数据库备注描述 | 询问用户或留空 |
| `pid` | 否 | 关联的项目ID | 默认 `0` |

### 参数规则

- `name`、`db_user`：仅允许 `^[\w\.-]+$`，不区分大小写；UTF-8编码不超过64字节（name）/ 32字节（db_user）
- `password`：禁止中文和特殊符号（，。？！；：""''（）【】《》￥&）
- `name`、`db_user`：禁止使用保留名称 `root`、`mysql`、`test`、`sys`、`panel_logs`
- `address`：不能为空或为 `ip`，需填写具体值
- `db_user` 长度：旧版MySQL限制16字节，MySQL 5.7/8.0/8.4/9.0 支持到32字节

### 返回值

```python
{'status': True, 'msg': 'ADD_SUCCESS'}   # 成功
{'status': False, 'msg': '错误原因'}      # 失败
```

---

## DeleteDatabase — 删除数据库

删除一个 MySQL 数据库及其关联用户。

### 调用方式

```bash
btpython scripts/mysql_db.py delete --id <数据库ID> --name <数据库名>
```

```python
from mysql_db import BtPanelDatabase
db = BtPanelDatabase()
result = db.delete_database(id=5, name='my_db')
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `id` | 是 | 数据库在面板中的记录ID | 从数据库列表中获取（面板 SQLite 数据库 `databases` 表主键） |
| `name` | 是 | 数据库名称 | 询问用户或从数据库列表中获取 |

### 删除流程

1. 通过 `id` 和 `name` 在面板数据库中查找记录
2. 若为本地数据库且启用回收站 → 移入回收站
3. 否则 → 删除 MySQL 数据库 → 删除关联用户 → `flush privileges`
4. 清理配额记录 → 删除面板数据库记录

### 回收站机制

回收站由 `data/recycle_bin_db.pl` 文件控制。仅本地数据库（sid=0）生效，远程数据库直接永久删除。

### 返回值

```python
{'status': True, 'msg': 'DEL_SUCCESS'}   # 成功
{'status': False, 'msg': '错误原因'}      # 失败
```

---
## ListDatabase — 查看数据库列表

查看面板中所有MySQL数据库列表，返回每个数据库的名称、用户名、访问权限、类型，密码已脱敏不显示。

### 调用方式

```bash
btpython scripts/mysql_db.py list
```

### 参数

无需参数。

### 返回值

JSON数组，每项包含以下字段：

| 字段 | 说明 |
|------|------|
| `name` | 数据库名称 |
| `username` | 数据库用户名 |
| `accept` | 允许访问的IP（`127.0.0.1` 本地 / `%` 所有人 / 具体IP） |
| `type` | 数据库类型，固定为 `MySQL` |

```json
[
    {
        "name": "my_database",
        "username": "my_user",
        "accept": "127.0.0.1",
        "type": "MySQL"
    }
]
```

---
## 脚本文件

封装脚本 [scripts/mysql_db.py](../scripts/mysql_db.py) 提供 `BtPanelDatabase` 类：

- `add_database(name, db_user, password, codeing, address, sid=0, ps='', pid=0)` → 创建数据库
- `delete_database(db_id, name)` → 删除数据库
- `list_databases()` → 查看数据库列表，返回 `[{"id": <数据库ID>, "name": <数据库名>, "username": <用户名>, "password": <数据库密码>, "accept": <允许访问IP>, "type": "MySQL"}]`

---

## 错误码参考

| 错误码 | 含义 | 处理建议 |
|--------|------|----------|
| 1045 | 用户名或密码错误 | 重置密码后重试 |
| 1049 | 数据库不存在 | 检查数据库名称 |
| 1044 | 无访问权限或数据库不存在 | 检查用户权限 |
| 1062 | 数据库已存在 | 更换名称 |
| 1142 | 用户权限不足 | 使用root账户操作 |
| 1010 | 无权限删除数据库 | 检查是否有非数据库文件 |
| 1146 | 数据表不存在 | 检查表名 |
| 2002 | 本地服务器无法连接 | 检查MySQL服务状态 |
| 2003 | 数据库服务器连接失败 | 检查MySQL是否启动 |
| 23000 | 外键约束冲突 | 检查外键依赖 |
| 6 | 无权限删除数据库 | 检查是否有非数据库文件 |
