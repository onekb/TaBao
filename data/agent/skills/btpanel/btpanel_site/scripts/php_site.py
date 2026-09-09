#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
宝塔面板PHP站点操作脚本
封装 AddSite、DeleteSite、ListSites、GetPHPVersions 四个核心功能

使用方法:
    1. 命令行调用:
        btpython scripts/php_site.py add --domain www.example.com --site_path /www/wwwroot/www.example.com --php_version 00
        btpython scripts/php_site.py add --domain 192.168.10.194_9321 --site_path /www/wwwroot/192.168.10.194_9321 --php_version 80
        btpython scripts/php_site.py delete --site_id 126 --domain 192.168.10.194_9321 --delete_path 1 --ftp 0 --database 0
        btpython scripts/php_site.py list-sites --project_type PHP
        btpython scripts/php_site.py php-versions

    2. Python代码导入:
        from php_site import BtPanelPhpSite
        site = BtPanelPhpSite()
        result = site.add_site(domain='www.example.com', site_path='/www/wwwroot/www.example.com', php_version='00')
        result = site.delete_site(site_id='126', domain='192.168.10.194_9321', delete_path=True, ftp=False, database=False)
        result = site.list_sites()
        result = site.get_php_versions()
"""

import os
import sys
import json
import argparse

os.chdir('/www/server/panel/')
sys.path.insert(0, 'class/')
sys.path.insert(0, '/www/server/panel/')

import public
from panelSite import panelSite


class BtPanelPhpSite:
    """宝塔面板PHP站点操作封装类"""

    def __init__(self):
        self.site_obj = panelSite()

    def add_site(self, domain, site_path, php_version='00', ps='来自AI助手', ftp=False, sql=False):
        """
        创建PHP站点

        参数:
            domain (str): 网站域名或IP端口组合，如 www.example.com 或 192.168.10.194_9321
            site_path (str): 网站根目录绝对路径
            php_version (str): PHP版本编号，如 '80'(PHP8.0)/'74'(PHP7.4)/'00'(纯静态)
            ps (str): 网站备注
            ftp (bool): 是否创建FTP
            sql (bool/str): 是否创建数据库，False或'false'不创建，'MySQL'创建MySQL数据库

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
            clean_domain = domain

        webname_json = json.dumps({
            "domain": clean_domain,
            "domainlist": [],
            "count": 0
        }, ensure_ascii=False)

        params = {
            "path": site_path,
            "ftp": "true" if ftp else "false",
            "type": "PHP",
            "type_id": "0",
            "ps": ps,
            "port": port,
            "version": php_version,
            "need_index": "0",
            "need_404": "0",
            "sql": sql if isinstance(sql, str) and sql == 'MySQL' else "false",
            "codeing": "utf8mb4",
            "webname": webname_json,
            "add_dns_record": "false"
        }

        return self.site_obj.AddSite(public.to_dict_obj(params))

    def delete_site(self, site_id, domain, delete_path=True, ftp=False, database=False):
        """
        删除PHP站点

        参数:
            site_id (str/int): 站点ID（面板sites表主键）
            domain (str): 站点名称（webname），如 192.168.10.194_9321
            delete_path (bool): 是否同时删除网站目录
            ftp (bool): 是否同时删除FTP账户
            database (bool): 是否同时删除数据库

        返回:
            dict: {'status': True/False, 'msg': '消息'}
        """
        params = {
            "id": str(site_id),
            "webname": domain,
            "path": "1" if delete_path else "0",
            "ftp": "1" if ftp else "0",
            "sql": "1" if database else "0"
        }
        return self.site_obj.DeleteSite(public.to_dict_obj(params))

    def list_sites(self, project_type=None):
        """
        查询宝塔面板所有站点列表（跨类型通用查询）

        参数:
            project_type (str): 过滤站点类型，可选 PHP/html/proxy/None(全部)

        返回:
            list[dict]: 站点列表，每项包含:
                id (int) — 站点ID，删除/后续操作必需
                name (str) — 站点在面板中的注册名（webname），删除时必需
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

    def get_php_versions(self):
        """
        查询面板当前可用的PHP版本列表

        调用 panelSite().GetPHPVersion() 获取已安装的PHP版本信息。

        返回:
            list[dict]: 版本列表，每项包含:
                version (str) — 版本编号，如 '80'/'74'/'00'，用于 add_site 的 php_version 参数
                name (str) — 版本显示名，如 'PHP-80'/'纯静态'
                status (bool) — True=已安装可用，False=未安装不可用
        """
        return self.site_obj.GetPHPVersion(public.to_dict_obj({}))


def main():
    parser = argparse.ArgumentParser(description='宝塔面板PHP站点操作脚本')
    subparsers = parser.add_subparsers(dest='action', help='操作类型')

    add_parser = subparsers.add_parser('add', help='创建PHP站点')
    add_parser.add_argument('--domain', required=True, help='网站域名或IP端口 (如 www.example.com 或 192.168.10.194_9321)')
    add_parser.add_argument('--site_path', required=True, help='网站根目录绝对路径')
    add_parser.add_argument('--php_version', default='00', help='PHP版本编号 (如 80=PHP8.0, 74=PHP7.4, 00=纯静态)')
    add_parser.add_argument('--ps', default='来自AI助手', help='网站备注')
    add_parser.add_argument('--ftp', default='false', choices=['true', 'false'], help='是否创建FTP')
    add_parser.add_argument('--sql', default='false', choices=['false', 'MySQL'], help='是否创建数据库')

    del_parser = subparsers.add_parser('delete', help='删除PHP站点')
    del_parser.add_argument('--site_id', required=True, help='站点ID')
    del_parser.add_argument('--domain', required=True, help='站点名称(webname)')
    del_parser.add_argument('--delete_path', default='1', choices=['0', '1'], help='是否删除网站目录 (1=删除,0=保留)')
    del_parser.add_argument('--ftp', default='0', choices=['0', '1'], help='是否删除FTP (1=删除,0=保留)')
    del_parser.add_argument('--database', default='0', choices=['0', '1'], help='是否删除数据库 (1=删除,0=保留)')

    list_parser = subparsers.add_parser('list-sites', help='查询站点列表')
    list_parser.add_argument('--project_type', default=None, help='过滤站点类型 (PHP/html/proxy)，不传则返回全部')

    subparsers.add_parser('php-versions', help='查询可用PHP版本列表')

    args = parser.parse_args()

    if not args.action:
        parser.print_help()
        sys.exit(1)

    site = BtPanelPhpSite()

    if args.action == 'add':
        result = site.add_site(
            domain=args.domain,
            site_path=args.site_path,
            php_version=args.php_version,
            ps=args.ps,
            ftp=(args.ftp == 'true'),
            sql=args.sql
        )
    elif args.action == 'delete':
        result = site.delete_site(
            site_id=args.site_id,
            domain=args.domain,
            delete_path=(args.delete_path == '1'),
            ftp=(args.ftp == '1'),
            database=(args.database == '1')
        )
    elif args.action == 'list-sites':
        result = site.list_sites(project_type=args.project_type)
    elif args.action == 'php-versions':
        result = site.get_php_versions()

    is_add_success = (args.action == 'add' and isinstance(result, dict) and result.get('siteStatus', False))
    is_del_success = (args.action == 'delete' and isinstance(result, dict) and result.get('status', False))

    if is_add_success or is_del_success:
        print(f"SUCCESS: {json.dumps(result, ensure_ascii=False)}")
        sys.exit(0)
    elif args.action in ('list-sites', 'php-versions'):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)
    else:
        error_msg = ''
        if isinstance(result, dict):
            error_msg = result.get('msg', result.get('status', '未知错误'))
        print(f"ERROR: {error_msg}")
        sys.exit(1)


if __name__ == '__main__':
    main()