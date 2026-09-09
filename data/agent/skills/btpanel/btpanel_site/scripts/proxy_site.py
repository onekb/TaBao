#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
宝塔面板反向代理站点操作脚本
封装 AddProxySite、DeleteProxySite、ListSites 三个核心功能

使用方法:
    1. 命令行调用:
        btpython scripts/proxy_site.py add --domains 192.168.10.194:7321 --proxy_pass http://www.baidu.com --proxy_type http --remark 192.168.10.194:7321 --proxy_host www.baidu.com
        btpython scripts/proxy_site.py delete --site_id 128 --site_name 192.168.10.194_7321 --remove_path 1
        btpython scripts/proxy_site.py list-sites --project_type proxy

    2. Python代码导入:
        from proxy_site import BtPanelProxySite
        site = BtPanelProxySite()
        result = site.add_proxy_site(domains='192.168.10.194:7321', proxy_pass='http://www.baidu.com', proxy_type='http')
        result = site.delete_proxy_site(site_id='128', site_name='192.168.10.194_7321', remove_path=True)
        result = site.list_sites()
"""

import os
import sys
import json
import argparse

os.chdir('/www/server/panel/')
sys.path.insert(0, 'class/')
sys.path.insert(0, '/www/server/panel/')

import public
from mod.project.proxy.comMod import main as ProxyModel


class BtPanelProxySite:
    """宝塔面板反向代理站点操作封装类"""

    def __init__(self):
        self.proxy_obj = ProxyModel()

    def add_proxy_site(self, domains, proxy_pass, proxy_type='http', remark='', proxy_host='$http_host'):
        """
        创建反向代理站点

        参数:
            domains (str): 监听域名，格式为 域名:端口 或纯域名(默认80)，多域名用换行分隔
            proxy_pass (str): 代理目标地址，http类型必须以http://或https://开头
            proxy_type (str): 代理类型，'http' 或 'unix'
            remark (str): 站点备注
            proxy_host (str): 传递给后端的主机头，默认$http_host

        返回:
            dict: {'status': True/False, 'msg': '消息'}
        """
        params = {
            "domains": domains,
            "proxy_pass": proxy_pass,
            "proxy_type": proxy_type,
            "remark": remark,
            "proxy_host": proxy_host
        }

        return self.proxy_obj.create(public.to_dict_obj(params))

    def delete_proxy_site(self, site_id, site_name, remove_path=False):
        """
        删除反向代理站点

        参数:
            site_id (str/int): 站点ID（面板sites表主键）
            site_name (str): 站点名称，如 192.168.10.194_7321
            remove_path (bool): 是否同时删除网站目录

        返回:
            dict: {'status': True/False, 'msg': '消息'}
        """
        params = {
            "id": str(site_id),
            "site_name": site_name,
            "remove_path": 1 if remove_path else 0
        }

        return self.proxy_obj.delete(public.to_dict_obj(params))

    def list_sites(self, project_type=None):
        """
        查询宝塔面板所有站点列表（跨类型通用查询）

        参数:
            project_type (str): 过滤站点类型，可选 PHP/html/proxy/None(全部)

        返回:
            list[dict]: 站点列表，每项包含:
                id (int) — 站点ID，删除/后续操作必需
                name (str) — 站点在面板中的注册名（site_name），删除时必需
                project_type (str) — 站点类型（PHP/html/proxy），用于判断用哪个删除方法
                path (str) — 网站根目录路径，用于判断是否需要删除目录
                ps (str) — 站点备注说明
                project_config (str) — 站点配置JSON字符串，反代站点包含代理目标、域名等详细信息
        """
        db = public.M('sites')
        fields = 'id,name,project_type,path,ps,project_config'
        if project_type:
            rows = db.field(fields).where('project_type=?', (project_type,)).select()
        else:
            rows = db.field(fields).select()
        return rows


def main():
    parser = argparse.ArgumentParser(description='宝塔面板反向代理站点操作脚本')
    subparsers = parser.add_subparsers(dest='action', help='操作类型')

    add_parser = subparsers.add_parser('add', help='创建反向代理站点')
    add_parser.add_argument('--domains', required=True, help='监听域名 (如 192.168.10.194:7321 或 www.example.com)')
    add_parser.add_argument('--proxy_pass', required=True, help='代理目标地址 (如 http://www.baidu.com)')
    add_parser.add_argument('--proxy_type', default='http', choices=['http', 'unix'], help='代理类型')
    add_parser.add_argument('--remark', default='', help='站点备注')
    add_parser.add_argument('--proxy_host', default='$http_host', help='传递给后端的主机头')

    del_parser = subparsers.add_parser('delete', help='删除反向代理站点')
    del_parser.add_argument('--site_id', required=True, help='站点ID')
    del_parser.add_argument('--site_name', required=True, help='站点名称')
    del_parser.add_argument('--remove_path', default='0', choices=['0', '1'], help='是否删除网站目录 (1=删除,0=保留)')

    list_parser = subparsers.add_parser('list-sites', help='查询站点列表')
    list_parser.add_argument('--project_type', default=None, help='过滤站点类型 (PHP/html/proxy)，不传则返回全部')

    args = parser.parse_args()

    if not args.action:
        parser.print_help()
        sys.exit(1)

    site = BtPanelProxySite()

    if args.action == 'add':
        result = site.add_proxy_site(
            domains=args.domains,
            proxy_pass=args.proxy_pass,
            proxy_type=args.proxy_type,
            remark=args.remark,
            proxy_host=args.proxy_host
        )
    elif args.action == 'delete':
        result = site.delete_proxy_site(
            site_id=args.site_id,
            site_name=args.site_name,
            remove_path=(args.remove_path == '1')
        )
    elif args.action == 'list-sites':
        result = site.list_sites(project_type=args.project_type)

    is_success = isinstance(result, dict) and result.get('status', False)

    if is_success:
        print(f"SUCCESS: {json.dumps(result, ensure_ascii=False)}")
        sys.exit(0)
    elif args.action == 'list-sites':
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)
    else:
        error_msg = ''
        if isinstance(result, dict):
            error_msg = result.get('msg', str(result))
        print(f"ERROR: {error_msg}")
        sys.exit(1)


if __name__ == '__main__':
    main()