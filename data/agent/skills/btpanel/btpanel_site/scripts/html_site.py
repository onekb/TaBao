#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
宝塔面板HTML静态站点操作脚本
封装 AddHtmlSite、DeleteHtmlSite、ListSites 三个核心功能

使用方法:
    1. 命令行调用:
        btpython scripts/html_site.py add --domain www.example.com --site_path /www/wwwroot/www.example.com
        btpython scripts/html_site.py add --domain 192.168.10.194_9321 --site_path /www/wwwroot/192.168.10.194_9321
        btpython scripts/html_site.py delete --project_name www.example.com
        btpython scripts/html_site.py list-sites --project_type html

    2. Python代码导入:
        from html_site import BtPanelHtmlSite
        site = BtPanelHtmlSite()
        result = site.add_html_site(domain='www.example.com', site_path='/www/wwwroot/www.example.com')
        result = site.delete_html_site(project_name='www.example.com')
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
from projectModel.htmlModel import main as HtmlModel


class BtPanelHtmlSite:
    """宝塔面板HTML静态站点操作封装类"""

    def __init__(self):
        self.html_obj = HtmlModel()

    def add_html_site(self, domain, site_path, ps='', ftp=False):
        """
        创建HTML静态站点

        参数:
            domain (str): 网站域名或IP端口组合，如 www.example.com 或 192.168.10.194_9321
            site_path (str): 网站根目录绝对路径
            ps (str): 网站备注
            ftp (bool): 是否创建FTP

        返回:
            dict: 成功返回 {'siteStatus': True, 'siteId': <int>, ...}
                  失败返回 {'status': False, 'msg': '错误信息'}
        """
        if '_' in domain:
            port = domain.split('_')[-1]
            clean_domain = domain.replace('_', ':', 1)
        elif ':' in domain:
            port = domain.split(':')[-1]
            clean_domain = domain
        else:
            port = '80'
            clean_domain = domain + ':80'

        webname_json = json.dumps({
            "domain": clean_domain,
            "domainlist": [],
            "count": 0
        }, ensure_ascii=False)

        params = {
            "path": site_path,
            "webname": webname_json,
            "ps": ps,
            "ftp": "true" if ftp else "false",
            "type_id": "0",
            "project_type": "html"
        }

        return self.html_obj.create_project(public.to_dict_obj(params))

    def delete_html_site(self, project_name):
        """
        删除HTML静态站点

        参数:
            project_name (str): 站点名称（面板sites表中的name字段）

        返回:
            dict: {'status': True/False, 'msg': '消息'}
        """
        params = {
            "project_name": project_name
        }
        return self.html_obj.remove_project(public.to_dict_obj(params))

    def list_sites(self, project_type=None):
        """
        查询宝塔面板所有站点列表（跨类型通用查询）

        参数:
            project_type (str): 过滤站点类型，可选 PHP/html/proxy/None(全部)

        返回:
            list[dict]: 站点列表，每项包含:
                id (int) — 站点ID，删除/后续操作必需
                name (str) — 站点在面板中的注册名，删除时必需
                project_type (str) — 站点类型（PHP/html/proxy），用于判断用哪个删除方法
                path (str) — 网站根目录路径，用于判断是否需要删除目录
                ps (str) — 站点备注说明
                project_config (str) — 站点配置JSON字符串
        """
        db = public.M('sites')
        fields = 'id,name,project_type,path,ps,project_config'
        if project_type:
            rows = db.field(fields).where('project_type=?', (project_type,)).select()
        else:
            rows = db.field(fields).select()
        return rows


def main():
    parser = argparse.ArgumentParser(description='宝塔面板HTML静态站点操作脚本')
    subparsers = parser.add_subparsers(dest='action', help='操作类型')

    add_parser = subparsers.add_parser('add', help='创建HTML静态站点')
    add_parser.add_argument('--domain', required=True, help='网站域名或IP端口 (如 www.example.com 或 192.168.10.194_9321)')
    add_parser.add_argument('--site_path', required=True, help='网站根目录绝对路径')
    add_parser.add_argument('--ps', default='', help='网站备注')
    add_parser.add_argument('--ftp', default='false', choices=['true', 'false'], help='是否创建FTP')

    del_parser = subparsers.add_parser('delete', help='删除HTML静态站点')
    del_parser.add_argument('--project_name', required=True, help='站点名称')

    list_parser = subparsers.add_parser('list-sites', help='查询站点列表')
    list_parser.add_argument('--project_type', default=None, help='过滤站点类型 (PHP/html/proxy)，不传则返回全部')

    args = parser.parse_args()

    if not args.action:
        parser.print_help()
        sys.exit(1)

    site = BtPanelHtmlSite()

    if args.action == 'add':
        result = site.add_html_site(
            domain=args.domain,
            site_path=args.site_path,
            ps=args.ps,
            ftp=(args.ftp == 'true')
        )
    elif args.action == 'delete':
        result = site.delete_html_site(project_name=args.project_name)
    elif args.action == 'list-sites':
        result = site.list_sites(project_type=args.project_type)

    is_add_success = (args.action == 'add' and isinstance(result, dict) and result.get('siteStatus', False))
    is_del_success = (args.action == 'delete' and isinstance(result, dict) and result.get('status', False))

    if is_add_success or is_del_success:
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