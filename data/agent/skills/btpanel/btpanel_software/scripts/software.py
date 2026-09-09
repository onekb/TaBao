#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
宝塔面板软件商店安装脚本

封装软件商店查询、版本解析、安装任务创建、任务状态和安装日志查看。

使用方法:
    btpython scripts/software.py list --query nginx
    btpython scripts/software.py find --name nginx
    btpython scripts/software.py install --name nginx --version 1.28
    btpython scripts/software.py install --name nginx
    btpython scripts/software.py status --msg-id <消息ID>
    btpython scripts/software.py status --task-id <任务ID>
    btpython scripts/software.py log --msg-id <消息ID> --lines 100
    btpython scripts/software.py log --task-id <任务ID> --lines 100
"""

import argparse
import json
import os
import re
import sys
import traceback


PANEL_PATH = '/www/server/panel'


def setup_import_path():
    if os.path.exists(PANEL_PATH):
        os.chdir(PANEL_PATH)
    if 'class/' not in sys.path:
        sys.path.insert(0, 'class/')
    if PANEL_PATH not in sys.path:
        sys.path.insert(0, PANEL_PATH)


setup_import_path()

import public  # noqa: E402


RUNTIME_ENV_NAMES = {
    'php', 'php5', 'php7', 'php8',
    'java', 'jdk',
    'node', 'node.js',
    'go', 'golang',
    'python', 'py',
    'net', '.net', 'dotnet'
}

RUNTIME_MANAGER_NAMES = {
    'nodejs',
    'pythonmamager',
    'python_manager',
    'java_manager',
    'golangmanager',
    'go_manager',
    'dotnet',
    'dotnet_manager'
}


def to_json(data):
    return json.dumps(data, ensure_ascii=False, indent=2)


def normalize_name(name):
    return str(name or '').strip()


def is_runtime_environment_name(name):
    normalized = normalize_name(name).lower()
    if normalized in RUNTIME_MANAGER_NAMES:
        return False
    if normalized in RUNTIME_ENV_NAMES:
        return True
    if re.match(r'^(php|python|node|go|jdk|java|dotnet|net)[-_]?\d', normalized):
        return True
    return False


def assert_software_install_allowed(name):
    if is_runtime_environment_name(name):
        raise ValueError(
            '软件商店技能不能安装具体运行环境 [{}]，请使用 btpanel_runtime 运行环境管理技能。'
            '软件商店技能只允许安装运行环境管理器插件，例如 nodejs 版本管理器。'.format(name)
        )


def version_display(version_info):
    m_version = str(version_info.get('m_version', '')).strip()
    sub_version = str(version_info.get('version', '')).strip()
    if m_version and sub_version:
        return '{}.{}'.format(m_version, sub_version)
    return m_version or sub_version


def version_candidates(version_info):
    m_version = str(version_info.get('m_version', '')).strip()
    sub_version = str(version_info.get('version', '')).strip()
    display = version_display(version_info)
    candidates = set()
    for item in (m_version, sub_version, display):
        if item:
            candidates.add(item.lower())
    return candidates


def numeric_version_key(value):
    value = str(value or '').strip()
    if not re.match(r'^\d+(\.\d+)*$', value):
        return None
    return tuple(int(x) for x in value.split('.'))


def resolve_version(soft_info, requested_version=None):
    versions = soft_info.get('versions') or []
    if not versions:
        raise ValueError('软件 [{}] 没有可安装版本'.format(soft_info.get('name', '')))

    if requested_version:
        requested = str(requested_version).strip().lower()
        for item in versions:
            if requested in version_candidates(item):
                return item, 'specified'
        available = [version_display(x) for x in versions]
        raise ValueError('指定版本 [{}] 不存在，可用版本：{}'.format(requested_version, ', '.join(available)))

    numeric_versions = []
    for item in versions:
        display = version_display(item)
        key = numeric_version_key(display)
        if key is None:
            key = numeric_version_key(item.get('m_version', ''))
        if key is not None:
            numeric_versions.append((key, item))

    if numeric_versions:
        numeric_versions.sort(key=lambda x: x[0], reverse=True)
        return numeric_versions[0][1], 'latest'

    return versions[0], 'store-default'


class BtPanelContext:
    """创建面板方法需要的最小 Flask request context。"""

    def __init__(self, path='/plugin?action=install_plugin', method='POST'):
        self.path = path
        self.method = method
        self.ctx = None

    def __enter__(self):
        from BTPanel import app, session
        from common import panelAdmin

        self.ctx = app.test_request_context(self.path, method=self.method)
        self.ctx.push()

        session['uid'] = 1
        session['login'] = True
        session['download_url'] = public.GetConfigValue('download') or public.get_url()
        session['rootPath'] = '/www'
        session['setupPath'] = '/www/server'
        session['logsPath'] = '/www/wwwlogs'

        admin = panelAdmin()
        admin.setSession()
        admin.checkWebType()
        admin.checkConfig()
        admin.GetOS()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if self.ctx is not None:
            self.ctx.pop()


class BtPanelSoftware:
    """宝塔面板软件商店操作封装。"""

    def __init__(self):
        import panelPlugin

        self.plugin = panelPlugin.panelPlugin()

    def trigger_task_scheduler(self):
        from files import files as Files
        try:
            Files().GetTaskSpeed(public.to_dict_obj({}))
        except Exception:
            return {'status': False, 'msg': '触发任务调度器失败'}

    def list_soft(self, query=None):
        args = public.to_dict_obj({
            'p': '1',
            'rows': '10000',
            'type': '-3',
            'query': query or ''
        })
        result = self.plugin.get_soft_list(args)
        return result

    def find_soft(self, name):
        name = normalize_name(name)
        result = self.plugin.get_soft_find(name)
        if result:
            return result

        soft_list = self.list_soft(query=name)
        data = []
        try:
            data = soft_list.get('list', {}).get('data', [])
        except Exception:
            data = []

        for item in data:
            if str(item.get('name', '')).lower() == name.lower():
                result = self.plugin.get_soft_find(item.get('name'))
                return result or item

        return False

    def install(self, name, version=None, install_type='1', force='false'):
        assert_software_install_allowed(name)
        soft_info = self.find_soft(name)
        if not soft_info:
            raise ValueError('指定软件 [{}] 不存在，请先使用 list --query 查询软件内部名称'.format(name))

        version_info, source = resolve_version(soft_info, version)
        m_version = str(version_info.get('m_version', '')).strip()
        sub_version = str(version_info.get('version', '')).strip()

        if not m_version:
            raise ValueError('软件 [{}] 版本信息缺少 m_version，无法调用面板安装方法'.format(name))
        args = {
            'sName': soft_info.get('name') or normalize_name(name),
            'version': m_version,
            'min_version': sub_version,
            'type': '1',
            # 'force': str(force).lower()
        }
        print(args)
        result = self.plugin.install_plugin(public.to_dict_obj(args))

        if result.get('tmp_path'):
            args = public.dict_obj()
            args.tmp_path = result['tmp_path']
            args.plugin_name = soft_info.get('name') or name
            args.install_opt = result['install_opt']
            pkg_result = self.plugin.input_package(args)
            self.trigger_task_scheduler()
            return pkg_result

        msg_id = result.get('msg_id')
        install_result = self.wait_install_task(msg_id) if msg_id else {
            'status': False, 'msg': '安装任务未返回 msg_id'
        }

        self.trigger_task_scheduler()
        return {
            'selected': {
                'name': args['sName'],
                'version': version_display(version_info),
                'm_version': m_version,
                'min_version': sub_version,
                'source': source
            },
            'install_args': args,
            'result': result,
            'install_result': install_result
        }

    def wait_install_task(self, msg_id):
        import time
        from panel_msg.msg_file import Message

        if not msg_id:
            return {'status': False, 'msg': '缺少 msg_id，无法等待安装任务'}

        print('安装任务已创建，msg_id: {}'.format(msg_id))
        print('开始等待安装任务完成...')

        max_wait = 1000
        interval = 3
        waited = 0
        last_status = None

        while waited < max_wait:
            msg = Message.form_file(msg_id)
            if msg:
                sub = msg.sub or {}
                sub_status = sub.get('status')
                install_status = sub.get('install_status', '')

                if sub_status != last_status:
                    last_status = sub_status
                    print('')
                    print('=== 安装任务状态更新 ===')
                    print('msg_id: {}'.format(msg.id))
                    print('task_id: {}'.format(sub.get('task_id', '')))
                    print('软件: {}'.format(sub.get('soft_name', '')))
                    print('状态: {}'.format(install_status))
                    print('日志文件: {}'.format(sub.get('file_name', '')))
                    print('========================')
                    print('')

                if sub_status == 2:
                    return {
                        'status': True,
                        'msg': msg.title or '安装完成',
                        'soft_name': sub.get('soft_name', ''),
                        'install_status': install_status,
                        'file_name': sub.get('file_name', ''),
                        'task_id': sub.get('task_id')
                    }
            time.sleep(interval)
            waited += interval

        return {'status': False, 'msg': '等待安装任务超时 ({} 秒)'.format(max_wait)}

    def get_install_status(self, msg_id=None, task_id=None):
        from panel_msg.msg_file import Message, message_mgr

        if msg_id:
            msg = Message.form_file(msg_id)
            if not msg:
                return {'status': False, 'msg': '消息文件不存在: {}'.format(msg_id)}
            return self._format_msg_status(msg)

        if task_id:
            for mid in message_mgr.message_id_list():
                msg = Message.form_file(mid)
                if msg and msg.sub.get('task_id') == int(task_id):
                    return self._format_msg_status(msg)
            return {'status': False, 'msg': '未找到 task_id={} 对应的安装消息'.format(task_id)}

        return {'status': False, 'msg': '请提供 --msg-id 或 --task-id 参数'}

    def get_install_log(self, msg_id=None, task_id=None, lines=100):
        from panel_msg.msg_file import Message, message_mgr

        if msg_id:
            msg = Message.form_file(msg_id)
            if not msg:
                return {'status': False, 'msg': '消息文件不存在: {}'.format(msg_id)}
            file_name = msg.sub.get('file_name', '')
            return self._read_log_file(file_name, lines)

        if task_id:
            for mid in message_mgr.message_id_list():
                msg = Message.form_file(mid)
                if msg and msg.sub.get('task_id') == int(task_id):
                    file_name = msg.sub.get('file_name', '')
                    return self._read_log_file(file_name, lines)
            return {'status': False, 'msg': '未找到 task_id={} 对应的安装消息'.format(task_id)}

        return {'status': False, 'msg': '请提供 --msg-id 或 --task-id 参数'}

    def _format_msg_status(self, msg):
        sub = msg.sub or {}
        sub_status = sub.get('status', 0)
        status_map = {0: '等待中', 1: '进行中', 2: '已完成'}
        return {
            'msg_id': msg.id,
            'title': msg.title,
            'soft_name': sub.get('soft_name', ''),
            'install_status': sub.get('install_status', ''),
            'status_code': sub_status,
            'status_desc': status_map.get(sub_status, '未知'),
            'file_name': sub.get('file_name', ''),
            'task_id': sub.get('task_id')
        }

    def _read_log_file(self, file_name, lines=100):
        import os
        if not file_name:
            return {'status': False, 'msg': '日志文件路径为空'}
        if not os.path.exists(file_name):
            return {'status': False, 'msg': '日志文件不存在: {}'.format(file_name)}
        try:
            with open(file_name, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
            log_lines = all_lines[-int(lines):] if len(all_lines) > int(lines) else all_lines
            return {
                'status': True,
                'file_name': file_name,
                'total_lines': len(all_lines),
                'lines': len(log_lines),
                'log': ''.join(log_lines)
            }
        except Exception as e:
            return {'status': False, 'msg': '读取日志文件失败: {}'.format(str(e))}


def main():
    parser = argparse.ArgumentParser(description='宝塔面板软件商店安装脚本')
    subparsers = parser.add_subparsers(dest='action', help='操作类型')

    list_parser = subparsers.add_parser('list', help='查询软件列表')
    list_parser.add_argument('--query', default='', help='搜索关键词')

    find_parser = subparsers.add_parser('find', help='查询指定软件')
    find_parser.add_argument('--name', required=True, help='软件内部名称，如 nginx/mysql/php')

    install_parser = subparsers.add_parser('install', help='安装指定软件')
    install_parser.add_argument('--name', required=True, help='软件内部名称，如 nginx/mysql/php')
    install_parser.add_argument('--version', default=None, help='指定版本，不传则安装最新版')
    install_parser.add_argument('--type', default='1', help='安装方式，默认 1')
    install_parser.add_argument('--force', default='false', choices=['true', 'false'], help='是否强制安装')

    status_parser = subparsers.add_parser('status', help='查询安装任务状态')
    status_parser.add_argument('--msg-id', default=None, help='消息 ID')
    status_parser.add_argument('--task-id', default=None, help='任务 ID')

    log_parser = subparsers.add_parser('log', help='查看安装日志')
    log_parser.add_argument('--msg-id', default=None, help='消息 ID')
    log_parser.add_argument('--task-id', default=None, help='任务 ID')
    log_parser.add_argument('--lines', default=100, type=int, help='日志行数')

    args = parser.parse_args()
    if not args.action:
        parser.print_help()
        sys.exit(1)

    try:
        with BtPanelContext():
            software = BtPanelSoftware()
            if args.action == 'list':
                result = software.list_soft(query=args.query)
            elif args.action == 'find':
                result = software.find_soft(args.name)
                if not result:
                    raise ValueError('未找到软件 [{}]'.format(args.name))
            elif args.action == 'install':
                result = software.install(
                    name=args.name,
                    version=args.version,
                    install_type=args.type,
                    force=args.force
                )
            elif args.action == 'status':
                result = software.get_install_status(
                    msg_id=args.msg_id,
                    task_id=args.task_id
                )
            elif args.action == 'log':
                result = software.get_install_log(
                    msg_id=args.msg_id,
                    task_id=args.task_id,
                    lines=args.lines
                )
            else:
                raise ValueError('未知操作：{}'.format(args.action))

        print(to_json({
            'status': True,
            'data': result
        }))
        sys.exit(0)
    except Exception as exc:
        print(to_json({
            'status': False,
            'msg': str(exc),
            'traceback': traceback.format_exc()
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
