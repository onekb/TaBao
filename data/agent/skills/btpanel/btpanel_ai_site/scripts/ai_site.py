#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
宝塔面板AI项目管理脚本
封装 AI 项目（如Python/Node/Go等后端服务）的创建、修改、启停等核心功能

使用方法:
    1. 命令行调用:
        btpython scripts/ai_site.py create --project_name my_project --project_path /www/wwwroot/my_project --ports '[{"port":8080,"label":"Web服务"}]' --start_cmd "python app.py"
        btpython scripts/ai_site.py modify --project_name my_project --ports '[{"port":8081,"label":"API服务"}]'
        btpython scripts/ai_site.py remove --project_name my_project
        btpython scripts/ai_site.py start --project_name my_project
        btpython scripts/ai_site.py stop --project_name my_project
        btpython scripts/ai_site.py restart --project_name my_project
        btpython scripts/ai_site.py list --p 1 --limit 10
        btpython scripts/ai_site.py stat --project_name my_project
        btpython scripts/ai_site.py add-domain --project_name my_project --domain example.com:8080
        btpython scripts/ai_site.py del-domain --project_name my_project --domain example.com:8080
        btpython scripts/ai_site.py get-domain --project_name my_project
        btpython scripts/ai_site.py log-list --project_name my_project
        btpython scripts/ai_site.py log-content --project_name my_project --log_path /path/to/log --lines 200

    2. Python代码导入:
        from ai_site import BtPanelAiSite
        site = BtPanelAiSite()
        result = site.create_project(project_name='my_project', project_path='/www/wwwroot/my_project', ports='8080', start_cmd='python app.py')
        result = site.get_project_list(p=1, limit=10)
        result = site.get_domain(project_name='my_project')
"""

import os
import sys
import json
import argparse

os.chdir('/www/server/panel/')
sys.path.insert(0, 'class/')
sys.path.insert(0, '/www/server/panel/')

import public
from projectModel.aiModel import main as AiModel


class BtPanelAiSite:
    """宝塔面板AI项目管理封装类"""

    def __init__(self):
        self.ai_obj = AiModel()

    def create_project(self, project_name, project_path, project_mode='dynamic', project_ps='', ports=None, start_cmd='', stop_cmd='', domains=None, is_power_on=0, run_user='www', environment='', logs=None):
        """
        创建AI项目

        参数:
            project_name (str): 项目名称
            project_path (str): 项目路径
            project_mode (str): 项目模式，'dynamic' 或 'static'
            project_ps (str): 项目描述
            ports (list/str): 端口列表
            start_cmd (str): 启动命令
            stop_cmd (str): 停止命令
            domains (list/str): 域名列表
            is_power_on (int): 是否开机启动，0或1
            run_user (str): 运行用户
            environment (str): 运行环境
            logs (dict): 日志配置，如 {"后端日志": "/path/to/backend.log"}

        返回:
            dict: {'status': True/False, 'msg': '消息'}
        """
        params = {
            "project_name": project_name,
            "project_path": project_path,
            "project_mode": project_mode,
            "project_ps": project_ps,
            "start_cmd": start_cmd,
            "stop_cmd": stop_cmd,
            "is_power_on": is_power_on,
            "run_user": run_user,
            "environment": environment,
        }
        if ports is not None:
            params["ports"] = ports
        if domains is not None:
            params["domains"] = domains
        if logs is not None:
            params["logs"] = logs

        return self.ai_obj.create_project(public.to_dict_obj(params))

    def modify_project(self, project_name, project_path=None, project_ps=None, ports=None, start_cmd=None, stop_cmd=None, is_power_on=None, run_user=None, environment=None):
        """
        修改AI项目

        参数:
            project_name (str): 项目名称
            project_path (str): 项目路径（可选）
            project_ps (str): 项目描述（可选）
            ports (list/str): 端口列表（可选）
            start_cmd (str): 启动命令（可选）
            stop_cmd (str): 停止命令（可选）
            is_power_on (int): 是否开机启动（可选）
            run_user (str): 运行用户（可选）
            environment (str): 运行环境（可选）

        返回:
            dict: {'status': True/False, 'msg': '消息'}
        """
        params = {"project_name": project_name}
        optional_params = {
            "project_path": project_path,
            "project_ps": project_ps,
            "ports": ports,
            "start_cmd": start_cmd,
            "stop_cmd": stop_cmd,
            "is_power_on": is_power_on,
            "run_user": run_user,
            "environment": environment
        }
        for key, value in optional_params.items():
            if value is not None:
                params[key] = value

        return self.ai_obj.modify_project(public.to_dict_obj(params))

    def remove_project(self, project_name):
        """
        删除AI项目

        参数:
            project_name (str): 项目名称

        返回:
            dict: {'status': True/False, 'msg': '消息'}
        """
        return self.ai_obj.remove_project(public.to_dict_obj({"project_name": project_name}))

    def start_project(self, project_name):
        """
        启动AI项目

        参数:
            project_name (str): 项目名称

        返回:
            dict: {'status': True/False, 'msg': '消息'}
        """
        return self.ai_obj.start_project(public.to_dict_obj({"project_name": project_name}))

    def stop_project(self, project_name):
        """
        停止AI项目

        参数:
            project_name (str): 项目名称

        返回:
            dict: {'status': True/False, 'msg': '消息'}
        """
        return self.ai_obj.stop_project(public.to_dict_obj({"project_name": project_name}))

    def restart_project(self, project_name):
        """
        重启AI项目

        参数:
            project_name (str): 项目名称

        返回:
            dict: {'status': True/False, 'msg': '消息'}
        """
        return self.ai_obj.restart_project(public.to_dict_obj({"project_name": project_name}))

    def get_project_list(self, p=1, limit=20, search=None, order='id desc'):
        """
        获取AI项目列表

        参数:
            p (int): 页码，默认1
            limit (int): 每页数量，默认20
            search (str): 搜索关键词（可选）
            order (str): 排序方式，默认'id desc'

        返回:
            dict: {'page': int, 'size': int, 'count': int, 'data': list}
        """
        params = {
            "p": p,
            "limit": limit,
            "order": order
        }
        if search is not None:
            params["search"] = search

        return self.ai_obj.get_project_list(public.to_dict_obj(params))

    def get_project_stat(self, project_name):
        """
        获取AI项目运行状态

        参数:
            project_name (str): 项目名称

        返回:
            dict: 项目运行状态信息
        """
        project_info = public.M('sites').where('name=?', (project_name,)).find()
        return self.ai_obj.get_project_stat(project_info)

    def add_domain(self, project_name, domain):
        """
        添加域名到AI项目

        参数:
            project_name (str): 项目名称
            domain (str): 域名

        返回:
            dict: {'status': True/False, 'msg': '消息'}
        """
        domains = [domain] if isinstance(domain, str) else domain
        return self.ai_obj.project_add_domain(public.to_dict_obj({"project_name": project_name, "domains": domains}))

    def get_domain(self, project_name):
        """
        获取AI项目的域名列表

        参数:
            project_name (str): 项目名称

        返回:
            list: 域名列表，每项包含 id/name/pid/port/addtime/cn_name
        """
        return self.ai_obj.project_get_domain(public.to_dict_obj({"project_name": project_name}))

    def del_domain(self, project_name, domain):
        """
        从AI项目删除域名

        参数:
            project_name (str): 项目名称
            domain (str): 域名

        返回:
            dict: {'status': True/False, 'msg': '消息'}
        """
        return self.ai_obj.project_del_domain(public.to_dict_obj({"project_name": project_name, "domain": domain}))

    def get_log_list(self, project_name):
        """
        获取AI项目日志文件列表

        参数:
            project_name (str): 项目名称

        返回:
            list: 日志文件列表
        """
        return self.ai_obj.get_log_list(public.to_dict_obj({"project_name": project_name}))

    def get_log_content(self, project_name, log_path, lines=100):
        """
        获取AI项目日志内容

        参数:
            project_name (str): 项目名称
            log_path (str): 日志文件路径
            lines (int): 读取行数，默认100

        返回:
            str: 日志内容
        """
        return self.ai_obj.get_log_content(public.to_dict_obj({"project_name": project_name, "log_path": log_path, "lines": lines}))


def main():
    parser = argparse.ArgumentParser(description='宝塔面板AI项目管理脚本')
    subparsers = parser.add_subparsers(dest='action', help='操作类型')

    parser_create = subparsers.add_parser('create', help='创建AI项目')
    parser_create.add_argument('--project_name', required=True, help='项目名称')
    parser_create.add_argument('--project_path', required=True, help='项目路径')
    parser_create.add_argument('--project_mode', default='dynamic', help='项目模式，默认dynamic')
    parser_create.add_argument('--project_ps', default='', help='项目描述')
    parser_create.add_argument('--ports', default=None, help='端口列表JSON，格式: \'[{"port":3000,"label":"前端服务"}]\'')
    parser_create.add_argument('--start_cmd', default='', help='启动命令')
    parser_create.add_argument('--stop_cmd', default='', help='停止命令')
    parser_create.add_argument('--domains', default=None, help='域名（支持逗号分隔）')
    parser_create.add_argument('--is_power_on', type=int, default=0, help='是否开机启动，0或1')
    parser_create.add_argument('--run_user', default='www', help='运行用户')
    parser_create.add_argument('--environment', default='', help='运行环境')
    parser_create.add_argument('--logs', default=None, help='日志配置JSON，如 {"后端日志":"/path/to/log"}')

    parser_modify = subparsers.add_parser('modify', help='修改AI项目')
    parser_modify.add_argument('--project_name', required=True, help='项目名称')
    parser_modify.add_argument('--project_path', default=None, help='项目路径')
    parser_modify.add_argument('--project_ps', default=None, help='项目描述')
    parser_modify.add_argument('--ports', default=None, help='端口列表JSON，格式: \'[{"port":3000,"label":"前端服务"}]\'')
    parser_modify.add_argument('--start_cmd', default=None, help='启动命令')
    parser_modify.add_argument('--stop_cmd', default=None, help='停止命令')
    parser_modify.add_argument('--is_power_on', type=int, default=None, help='是否开机启动，0或1')
    parser_modify.add_argument('--run_user', default=None, help='运行用户')
    parser_modify.add_argument('--environment', default=None, help='运行环境')

    parser_remove = subparsers.add_parser('remove', help='删除AI项目')
    parser_remove.add_argument('--project_name', required=True, help='项目名称')

    parser_start = subparsers.add_parser('start', help='启动AI项目')
    parser_start.add_argument('--project_name', required=True, help='项目名称')

    parser_stop = subparsers.add_parser('stop', help='停止AI项目')
    parser_stop.add_argument('--project_name', required=True, help='项目名称')

    parser_restart = subparsers.add_parser('restart', help='重启AI项目')
    parser_restart.add_argument('--project_name', required=True, help='项目名称')

    parser_list = subparsers.add_parser('list', help='获取AI项目列表')
    parser_list.add_argument('--p', type=int, default=1, help='页码，默认1')
    parser_list.add_argument('--limit', type=int, default=20, help='每页数量，默认20')
    parser_list.add_argument('--search', default=None, help='搜索关键词')
    parser_list.add_argument('--order', default='id desc', help='排序方式，默认id desc')

    parser_stat = subparsers.add_parser('stat', help='获取AI项目运行状态')
    parser_stat.add_argument('--project_name', required=True, help='项目名称')

    parser_add_domain = subparsers.add_parser('add-domain', help='添加域名到AI项目')
    parser_add_domain.add_argument('--project_name', required=True, help='项目名称')
    parser_add_domain.add_argument('--domain', required=True, help='域名')

    parser_del_domain = subparsers.add_parser('del-domain', help='从AI项目删除域名')
    parser_del_domain.add_argument('--project_name', required=True, help='项目名称')
    parser_del_domain.add_argument('--domain', required=True, help='域名')

    parser_get_domain = subparsers.add_parser('get-domain', help='获取AI项目的域名列表')
    parser_get_domain.add_argument('--project_name', required=True, help='项目名称')

    parser_log_list = subparsers.add_parser('log-list', help='获取AI项目日志文件列表')
    parser_log_list.add_argument('--project_name', required=True, help='项目名称')

    parser_log_content = subparsers.add_parser('log-content', help='获取AI项目日志内容')
    parser_log_content.add_argument('--project_name', required=True, help='项目名称')
    parser_log_content.add_argument('--log_path', required=True, help='日志文件路径')
    parser_log_content.add_argument('--lines', type=int, default=100, help='读取行数，默认100')

    args = parser.parse_args()

    if not args.action:
        parser.print_help()
        sys.exit(1)

    site = BtPanelAiSite()

    def _parse_list(val):
        if val is None:
            return None
        val = val.strip()
        if val.startswith('['):
            return json.loads(val)
        return val.split(',')

    try:
        if args.action == 'create':
            ports = _parse_list(args.ports)
            domains = _parse_list(args.domains)
            logs = None
            if args.logs:
                logs = json.loads(args.logs)
            result = site.create_project(
                project_name=args.project_name,
                project_path=args.project_path,
                project_mode=args.project_mode,
                project_ps=args.project_ps,
                ports=ports,
                start_cmd=args.start_cmd,
                stop_cmd=args.stop_cmd,
                domains=domains,
                is_power_on=args.is_power_on,
                run_user=args.run_user,
                environment=args.environment,
                logs=logs
            )
        elif args.action == 'modify':
            ports = _parse_list(args.ports)
            result = site.modify_project(
                project_name=args.project_name,
                project_path=args.project_path,
                project_ps=args.project_ps,
                ports=ports,
                start_cmd=args.start_cmd,
                stop_cmd=args.stop_cmd,
                is_power_on=args.is_power_on,
                run_user=args.run_user,
                environment=args.environment
            )
        elif args.action == 'remove':
            result = site.remove_project(project_name=args.project_name)
        elif args.action == 'start':
            result = site.start_project(project_name=args.project_name)
        elif args.action == 'stop':
            result = site.stop_project(project_name=args.project_name)
        elif args.action == 'restart':
            result = site.restart_project(project_name=args.project_name)
        elif args.action == 'list':
            result = site.get_project_list(p=args.p, limit=args.limit, search=args.search, order=args.order)
        elif args.action == 'stat':
            result = site.get_project_stat(project_name=args.project_name)
        elif args.action == 'add-domain':
            result = site.add_domain(project_name=args.project_name, domain=args.domain)
        elif args.action == 'del-domain':
            result = site.del_domain(project_name=args.project_name, domain=args.domain)
        elif args.action == 'get-domain':
            result = site.get_domain(project_name=args.project_name)
        elif args.action == 'log-list':
            result = site.get_log_list(project_name=args.project_name)
        elif args.action == 'log-content':
            result = site.get_log_content(project_name=args.project_name, log_path=args.log_path, lines=args.lines)
        else:
            parser.print_help()
            sys.exit(1)

        if args.action == 'log-content':
            print(result)
        elif args.action in ('list', 'log-list', 'get-domain'):
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif isinstance(result, dict):
            if result.get('status'):
                print("SUCCESS: " + json.dumps(result, ensure_ascii=False))
            else:
                msg = result.get('msg', str(result))
                print("ERROR: " + msg)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        print("ERROR: " + str(e))
        sys.exit(1)


if __name__ == '__main__':
    main()
