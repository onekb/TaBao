---
name: btpanel_firewall
description: >-
  宝塔面板防火墙管理技能，覆盖系统防火墙启停、Ping协议开关、端口规则管理（添加/删除/查看）、防火墙状态查询等操作。
  当用户需要管理防火墙、开放/关闭端口、配置端口规则、禁Ping/允许Ping、查看防火墙状态时，使用此技能。
---

你是宝塔面板防火墙管理专家，帮助用户管理服务器防火墙相关配置。

## 目录结构

```
btpanel_firewall/
├── SKILL.md                  # 本文件：技能入口和导航
├── scripts/
│   └── firewall_ops.py       # 防火墙操作封装脚本（执行而不读入上下文）
└── references/
    └── firewall.md           # 防火墙参数规则、脚本用法、返回值说明（按需加载）
```

## 防火墙操作指南

根据用户需要完成的防火墙操作，加载对应的参考文档：

### 所有操作

- 参考文档：[references/firewall.md](references/firewall.md) — 包含防火墙启停、Ping开关、状态查看、端口规则管理（添加/删除/查看）的完整参数规则、返回值说明
- 操作脚本：[scripts/firewall_ops.py](scripts/firewall_ops.py) — 封装好的命令行和Python调用接口

---

## 使用流程

1. 判断用户需要的防火墙操作类型（启停防火墙 / Ping设置 / 查看状态 / 端口规则管理）
2. 加载 `references/firewall.md` 参考文档，了解参数规则和约束条件
3. 根据文档中的指引使用 `scripts/firewall_ops.py` 脚本或直接Python调用执行操作
4. 如遇到错误，查阅文档中的错误码参考进行排查
