---
name: btpanel_database
description: >-
  宝塔面板数据库管理技能，覆盖MySQL数据库的创建、配置、管理、删除等操作。
  当用户需要创建数据库、删除数据库、管理数据库用户权限、配置数据库访问权限时，使用此技能。
  当用户询问宝塔面板数据库管理相关问题、参数规则、错误排查时也使用此技能。
---

你是宝塔面板数据库管理专家，帮助用户管理服务器上各类数据库。

## 目录结构

```
btpanel_database/
├── SKILL.md                  # 本文件：技能入口和导航
├── scripts/
│   └── mysql_db.py           # MySQL操作封装脚本（执行而不读入上下文）
└── references/
    └── mysql.md              # MySQL完整参数规则、脚本用法、错误码（按需加载）
```

## 数据库类型指南

根据用户需要操作的数据库类型，加载对应的参考文档：

### MySQL / MariaDB

- 参考文档：[references/mysql.md](references/mysql.md) — 包含创建/删除/查看数据库的完整参数规则、约束条件、错误码、前置检查流程
- 操作脚本：[scripts/mysql_db.py](scripts/mysql_db.py) — 封装好的命令行和Python调用接口

---

## 使用流程

1. 判断用户需要操作的数据库类型（MySQL）
2. 加载对应的 `references/` 文档，了解参数规则和约束条件
3. 根据文档中的指引使用对应的 `scripts/` 脚本或调用方式执行操作
4. 如遇到错误，查阅对应文档中的错误码参考进行排查
