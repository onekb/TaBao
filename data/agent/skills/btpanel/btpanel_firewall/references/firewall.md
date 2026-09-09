# 防火墙管理

宝塔面板系统防火墙操作指南，支持 firewalld / ufw / iptables 三种防火墙后端。

---

## 可用方法

| 方法 | 作用 | 对应脚本命令 | 返回内容 |
|------|------|-------------|----------|
| `StartFirewall` | 启动系统防火墙，自动放行SSH/80/443/21/PanelPort等常用端口 | `btpython scripts/firewall_ops.py start` | `{'status': True/False, 'msg': '消息'}` |
| `StopFirewall` | 停止系统防火墙 | `btpython scripts/firewall_ops.py stop` | `{'status': True/False, 'msg': '消息'}` |
| `EnablePing` | 允许Ping协议（允许ICMP响应） | `btpython scripts/firewall_ops.py ping_enable` | `{'status': True/False, 'msg': '消息'}` |
| `DisablePing` | 禁止Ping协议（禁Ping） | `btpython scripts/firewall_ops.py ping_disable` | `{'status': True/False, 'msg': '消息'}` |
| `GetStatus` | 查看防火墙状态信息：运行状态、类型、端口规则数、Ping状态 | `btpython scripts/firewall_ops.py status` | 格式化文字描述 |
| `ListPortRules` | 查看端口规则列表 | `btpython scripts/firewall_ops.py port_list` | JSON分页数据，每项含端口、协议、来源IP、策略、链、备注等 |
| `AddPortRule` | 添加端口放行/拒绝规则 | `btpython scripts/firewall_ops.py port_add` | `{'status': True/False, 'msg': '消息'}` |
| `RemovePortRule` | 删除端口规则 | `btpython scripts/firewall_ops.py port_remove` | `{'status': True/False, 'msg': '消息'}` |

---

## StartFirewall — 启动防火墙

启动系统防火墙，并在启动时自动放行 SSH、80、443、39000-40000、21、面板端口等常用端口。

### 调用方式

```bash
btpython scripts/firewall_ops.py start
```

```python
from firewall_ops import BtPanelFirewall
fw = BtPanelFirewall()
result = fw.start_firewall()
```

### 参数

无需参数。

### 注意事项

- 启动时会尝试自动放行常用端口（SSH端口、80、443、21、39000-40000、面板端口）
- 如果常用端口已存在放行规则则跳过
- 返回 True 表示启动成功，但不代表所有常用端口都已成功放行

### 返回值

```python
{'status': True, 'msg': '防火墙已启动'}   # 成功
{'status': False, 'msg': '错误原因'}       # 失败
```

---

## StopFirewall — 停止防火墙

停止系统防火墙运行。

### 调用方式

```bash
btpython scripts/firewall_ops.py stop
```

```python
from firewall_ops import BtPanelFirewall
fw = BtPanelFirewall()
result = fw.stop_firewall()
```

### 参数

无需参数。

### 返回值

```python
{'status': True, 'msg': '防火墙已停止'}   # 成功
{'status': False, 'msg': '错误原因'}       # 失败
```

---

## EnablePing — 启用Ping协议

允许服务器响应ICMP PING请求（即允许被Ping）。

### 调用方式

```bash
btpython scripts/firewall_ops.py ping_enable
```

```python
from firewall_ops import BtPanelFirewall
fw = BtPanelFirewall()
result = fw.enable_ping()
```

### 参数

无需参数。

### 实现原理

修改 `/etc/sysctl.conf` 中的 `net.ipv4.icmp_echo_ignore_all=0`，然后执行 `sysctl -p` 使其生效。

### 返回值

```python
{'status': True, 'msg': '已允许Ping'}     # 成功
{'status': False, 'msg': '错误原因'}       # 失败（如sysctl.conf不可写或被安全软件锁定）
```

---

## DisablePing — 禁用Ping协议

禁止服务器响应ICMP PING请求（禁Ping），用于安全加固。

### 调用方式

```bash
btpython scripts/firewall_ops.py ping_disable
```

```python
from firewall_ops import BtPanelFirewall
fw = BtPanelFirewall()
result = fw.disable_ping()
```

### 参数

无需参数。

### 实现原理

修改 `/etc/sysctl.conf` 中的 `net.ipv4.icmp_echo_ignore_all=1`，然后执行 `sysctl -p` 使其生效。

### 返回值

```python
{'status': True, 'msg': '已禁止Ping'}     # 成功
{'status': False, 'msg': '错误原因'}       # 失败（如sysctl.conf不可写或被安全软件锁定）
```

---

## GetStatus — 查看防火墙状态

查看防火墙的完整状态信息，包括运行状态、防火墙类型、端口规则数量和Ping协议状态。结果以可读的文字格式返回。

### 调用方式

```bash
btpython scripts/firewall_ops.py status
```

```python
from firewall_ops import BtPanelFirewall
fw = BtPanelFirewall()
info = fw.get_status()
print(info['status_text'])
```

### 参数

无需参数。

### 返回值

命令行调用直接打印格式化文字描述。

Python调用返回字典：

| 字段 | 类型 | 说明 |
|------|------|------|
| `running` | bool | 防火墙是否正在运行 |
| `init_status` | bool | 防火墙环境是否初始化完成（iptables规则是否已加载） |
| `type` | str | 防火墙类型：`firewalld` / `ufw` / `iptables` |
| `port_count` | int | 当前端口规则条数 |
| `ping_enabled` | bool | Ping协议是否启用 |
| `status_text` | str | 格式化后的状态描述文字 |

示例输出文字：

```
防火墙状态：已启动
防火墙类型：firewalld
端口规则条数：12
Ping协议：已启用
```

---

## ListPortRules — 查看端口规则列表

查看系统防火墙当前的端口规则列表，支持按链筛选和搜索。

### 调用方式

```bash
btpython scripts/firewall_ops.py port_list --chain INPUT --query 80 --page 1 --page_size 20
```

```python
from firewall_ops import BtPanelFirewall
fw = BtPanelFirewall()
rules = fw.list_port_rules(chain='INPUT', query='', page=1, page_size=20)
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `chain` | 否 | 链类型：`INPUT`（入站规则）/ `OUTPUT`（出站规则）/ `ALL`（全部） | 默认 `ALL` |
| `query` | 否 | 搜索关键词，按端口号或备注模糊匹配 | 询问用户 |
| `page` | 否 | 分页页码，从1开始 | 默认 `1` |
| `page_size` | 否 | 每页显示条数 | 默认 `20` |

### 返回值字段说明

返回分页JSON数据，每条规则包含以下字段：

| 字段 | 说明 |
|------|------|
| `Port` | 端口号或端口范围（如 `80`、`8080-8090`） |
| `Protocol` | 协议类型：`tcp` / `udp` / `tcp-udp` |
| `Address` | 允许访问的来源IP地址，`ALL` 或 `Anywhere` 表示所有IP |
| `Strategy` | 策略：`accept`（允许）/ `drop`（拒绝） |
| `Chain` | 所属链：`INPUT`（入站）/ `OUTPUT`（出站） |
| `id` | 面板数据库记录ID（非0表示已在面板中管理），0表示系统级规则 |
| `sid` | 子ID，用于关联 |
| `brief` | 备注说明文字 |
| `domain` | 关联域名 |
| `addtime` | 规则添加时间 |
| `status` | 端口监听状态：`1`=正在监听 / `0`=未监听 / `-1`=未检查（端口范围或出站规则不检查） |

---

## AddPortRule — 添加端口规则

添加一条端口放行或拒绝规则。

**注意：防火墙未启动时无法添加规则，需先启动防火墙。**

### 调用方式

```bash
btpython scripts/firewall_ops.py port_add --port 80 --protocol tcp --address all --strategy accept --chain INPUT --brief "Web服务"
```

```python
from firewall_ops import BtPanelFirewall
fw = BtPanelFirewall()
result = fw.add_port_rule(port='80', protocol='tcp', address='all', strategy='accept', chain='INPUT', brief='Web服务')
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `port` | 是 | 端口号，支持单个端口（如 `80`）、范围（如 `8080-8090`） | 询问用户 |
| `protocol` | 否 | 协议：`tcp` / `udp` / `tcp/udp` | 默认 `tcp` |
| `address` | 否 | 来源IP地址，`all` 表示所有IP，也可填具体IP | 默认 `all` |
| `strategy` | 否 | 策略：`accept`（放行）/ `drop`（拒绝） | 默认 `accept` |
| `chain` | 否 | 链类型：`INPUT`（入站）/ `OUTPUT`（出站） | 默认 `INPUT` |
| `brief` | 否 | 备注说明文字 | 询问用户或留空 |
| `domain` | 否 | 关联域名 | 询问用户或留空 |

### 参数规则

- `port`：不能为空，1~65535之间
- `protocol`：只支持 `tcp`、`udp`、`tcp/udp`
- `address`：`all` 或有效IP地址格式
- 防火墙必须已启动，否则返回"请先启动防火墙后再设置规则！"

### 返回值

```python
{'status': True, 'msg': '端口 80 已放行'}   # 成功
{'status': False, 'msg': '错误原因'}          # 失败
```

---

## RemovePortRule — 删除端口规则

删除一条已有的端口规则。

### 调用方式

```bash
btpython scripts/firewall_ops.py port_remove --port 80 --protocol tcp --address all --strategy accept --chain INPUT
```

```python
from firewall_ops import BtPanelFirewall
fw = BtPanelFirewall()
result = fw.remove_port_rule(port='80', protocol='tcp', address='all', strategy='accept', chain='INPUT')
```

### 参数

| 参数 | 必填 | 说明 | 获取方式 |
|------|:--:|------|----------|
| `port` | 是 | 要删除的端口号 | 询问用户或从端口规则列表中获取 |
| `protocol` | 否 | 协议，需与添加时一致 | 默认 `tcp`，从列表获取 |
| `address` | 否 | 来源IP，需与添加时一致 | 默认 `all`，从列表获取 |
| `strategy` | 否 | 策略，需与添加时一致 | 默认 `accept`，从列表获取 |
| `chain` | 否 | 链类型，需与添加时一致 | 默认 `INPUT`，从列表获取 |
| `brief` | 否 | 备注 | 默认 `undefined` |
| `domain` | 否 | 域名 | 留空 |

### 修改规则的正确做法

由于修改规则涉及多个参数的复杂关联，本技能不提供直接修改规则的接口。如需修改已有规则，请使用 **先删除旧规则、再添加新规则** 的方式完成：

1. 调用 `port_list` 查看现有规则，获取待修改规则的参数
2. 调用 `port_remove` 删除旧规则
3. 调用 `port_add` 以新的参数添加规则

### 返回值

```python
{'status': True, 'msg': '端口 80 规则已删除'}   # 成功
{'status': False, 'msg': '错误原因'}              # 失败
```

---

## 脚本文件

封装脚本 [scripts/firewall_ops.py](../scripts/firewall_ops.py) 提供 `BtPanelFirewall` 类：

- `start_firewall()` → 启动防火墙
- `stop_firewall()` → 停止防火墙
- `enable_ping()` → 启用Ping
- `disable_ping()` → 禁用Ping
- `get_status()` → 获取防火墙状态，返回结构化数据 + 格式化文字
- `list_port_rules(chain, query, page, page_size)` → 查看端口规则列表
- `add_port_rule(port, protocol, address, strategy, chain, brief, domain)` → 添加端口规则
- `remove_port_rule(port, protocol, address, strategy, chain, brief, domain)` → 删除端口规则

---

## 错误码参考

| 错误信息 | 含义 | 处理建议 |
|----------|------|----------|
| 请先启动防火墙后再设置规则！ | 防火墙未启动 | 先执行 start 启动防火墙 |
| 目标端口不能为空 | 未传入端口参数 | 补全端口号 |
| 指定IP地址格式错误 | address参数格式不正确 | 检查IP格式或使用 `all` |
| 端口xxx已存在，请勿重复添加 | 端口规则已存在 | 检查现有规则或更换端口 |
| sysctl.conf不可写 | 系统加固或安全软件阻止了文件写入 | 关闭宝塔系统加固、云锁、安全狗等安全软件后重试 |
| 启动防火墙失败 | 防火墙服务启动异常 | 检查系统防火墙服务状态 |
