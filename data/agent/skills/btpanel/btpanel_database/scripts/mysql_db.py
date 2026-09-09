#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
宝塔面板MySQL数据库操作脚本
封装 AddDatabase、DeleteDatabase 和 ListDatabase 三个核心功能

使用方法:
    1. 命令行调用:
        python mysql_db.py add --name my_db --db_user my_user --password my_pass --codeing utf8mb4 --address 127.0.0.1
        python mysql_db.py delete --id 5 --name my_db
        python mysql_db.py list

    2. Python代码导入:
        from mysql_db import BtPanelDatabase
        db = BtPanelDatabase()
        result = db.add_database(name='my_db', db_user='my_user', password='my_pass', codeing='utf8mb4', address='127.0.0.1')
        result = db.delete_database(id=5, name='my_db')
        dbs = db.list_databases()
"""

import os
import sys
import argparse

# 切换到宝塔面板目录并加载模块
os.chdir('/www/server/panel/')
sys.path.insert(0, 'class/')
sys.path.insert(0, '/www/server/panel/')

import public
from database import database


class BtPanelDatabase:
    """宝塔面板数据库操作封装类"""

    def __init__(self):
        self.mysql_db = database()

    def add_database(self, name, db_user, password, codeing='utf8mb4', 
                     address='127.0.0.1', sid=0, ps='', pid=0):
        """
        创建MySQL数据库

        参数:
            name (str): 数据库名称，仅允许字母、数字、下划线、点、连字符
            db_user (str): 数据库用户名，规则同name
            password (str): 数据库密码，不能包含中文和特殊字符
            codeing (str): 字符集，可选: utf8, utf8mb4, gbk, big5
            address (str): 访问权限，127.0.0.1(本地), %(所有人), 具体IP, 逗号分隔多个IP
            sid (int): MySQL实例ID，0=本地，非0=远程
            ps (str): 数据库备注
            pid (int): 项目ID（关联网站）

        返回:
            dict: {'status': True/False, 'msg': '消息'}
        """
        args = {
            'name': str(name),
            'db_user': str(db_user),
            'password': str(password),
            'codeing': str(codeing),
            'address': str(address),
            'sid': str(sid),
            'ps': str(ps),
            'pid': str(pid)
        }
        
        get_obj = public.to_dict_obj(args)
        return self.mysql_db.AddDatabase(get_obj)

    def delete_database(self, db_id, name):
        """
        删除MySQL数据库

        参数:
            db_id (int/str): 数据库记录ID（面板数据库表中的主键）
            name (str): 数据库名称

        返回:
            dict: {'status': True/False, 'msg': '消息'}
        """
        args = {
            'id': str(db_id),
            'name': str(name)
        }
        
        get_obj = public.to_dict_obj(args)
        return self.mysql_db.DeleteDatabase(get_obj)

    def list_databases(self):
        """
        获取面板中所有MySQL数据库列表

        返回:
            list[dict]: 数据库列表，每项包含 id, name, username, password, accept, type
        """
        import json
        dbs = public.M('databases').field('id,name,username,password,accept,type').where("type=?", "MySQL").select()
        return dbs


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description='宝塔面板MySQL数据库操作脚本')
    subparsers = parser.add_subparsers(dest='action', help='操作类型')

    # 添加数据库子命令
    add_parser = subparsers.add_parser('add', help='创建数据库')
    add_parser.add_argument('--name', required=True, help='数据库名称')
    add_parser.add_argument('--db_user', required=True, help='数据库用户名')
    add_parser.add_argument('--password', required=True, help='数据库密码')
    add_parser.add_argument('--codeing', default='utf8mb4', help='字符集 (utf8/utf8mb4/gbk/big5)')
    add_parser.add_argument('--address', default='127.0.0.1', help='访问权限 (127.0.0.1/%/IP)')
    add_parser.add_argument('--sid', default=0, type=int, help='MySQL实例ID')
    add_parser.add_argument('--ps', default='', help='数据库备注')
    add_parser.add_argument('--pid', default=0, type=int, help='项目ID')

    # 删除数据库子命令
    del_parser = subparsers.add_parser('delete', help='删除数据库')
    del_parser.add_argument('--id', required=True, help='数据库记录ID')
    del_parser.add_argument('--name', required=True, help='数据库名称')

    # 查看数据库列表子命令
    subparsers.add_parser('list', help='查看所有MySQL数据库列表')

    args = parser.parse_args()

    if not args.action:
        parser.print_help()
        sys.exit(1)

    db = BtPanelDatabase()

    if args.action == 'add':
        result = db.add_database(
            name=args.name,
            db_user=args.db_user,
            password=args.password,
            codeing=args.codeing,
            address=args.address,
            sid=args.sid,
            ps=args.ps,
            pid=args.pid
        )
    elif args.action == 'delete':
        result = db.delete_database(
            db_id=args.id,
            name=args.name
        )
    elif args.action == 'list':
        import json
        dbs = db.list_databases()
        print(json.dumps(dbs, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 输出结果
    if result.get('status'):
        print(f"SUCCESS: {result.get('msg')}")
        sys.exit(0)
    else:
        print(f"ERROR: {result.get('msg')}")
        sys.exit(1)


if __name__ == '__main__':
    main()
