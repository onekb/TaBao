#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
宝塔面板运行环境安装脚本。

本脚本只负责安装具体运行环境版本，例如 PHP、JDK、Python、Go、Node.js、.NET。
运行环境管理器插件（如 nodejs、dotnet）缺失时，会先通过宝塔软件商店原生方法安装管理器。

重要约束：
1. 只调用宝塔面板已经提供的方法，不手写安装命令，不直接写 tasks 表。
2. 所有面板方法都在 Flask request context 内执行，并使用 BTPanel.session。
3. PHP、Java/JDK、Python、Go 安装后，通过版本列表每 5 秒轮询确认目标版本已安装。
4. Node.js 和 .NET 的版本安装接口本身完成后才返回，不额外通过版本列表判断完成。
"""

import argparse
import json
import os
import sys
import time
import traceback


PANEL_PATH = '/www/server/panel'
DEFAULT_WAIT_TIMEOUT = 7200
DEFAULT_POLL_INTERVAL = 5.0

# 只有这些运行环境需要先安装软件商店里的“管理器插件”。
MANAGER_PLUGIN = {
    'node': 'nodejs',
    'nodejs': 'nodejs',
    'dotnet': 'dotnet',
    'net': 'dotnet'
}

MANAGER_PATH = {
    'nodejs': '/www/server/panel/plugin/nodejs',
    'dotnet': '/www/server/panel/plugin/dotnet'
}


def setup_import_path():
    """让脚本在技能目录中执行时，也能导入面板 class/ 与项目模块。"""
    if os.path.exists(PANEL_PATH):
        os.chdir(PANEL_PATH)
    if 'class/' not in sys.path:
        sys.path.insert(0, 'class/')
    if PANEL_PATH not in sys.path:
        sys.path.insert(0, PANEL_PATH)


setup_import_path()

import public


def to_json(data):
    return json.dumps(data, ensure_ascii=False, indent=2)


def normalize_runtime(runtime):
    """统一用户可能输入的运行环境别名。"""
    runtime = str(runtime or '').strip().lower()
    aliases = {
        'jdk': 'java',
        'node.js': 'node',
        'nodejs': 'node',
        '.net': 'dotnet',
        'net': 'dotnet',
        'golang': 'go',
        'py': 'python'
    }
    return aliases.get(runtime, runtime)


class BtPanelContext:
    """
    为宝塔面板内部方法创建最小 Flask 上下文。

    注意：session 必须从 BTPanel 引入。不要直接 from flask import session，
    否则脚本环境下容易出现缺失 session 或 request context 的问题。
    """

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

        # 面板很多方法依赖 panelAdmin 初始化后的 session/config/os 信息。
        admin = panelAdmin()
        admin.setSession()
        admin.checkWebType()
        admin.checkConfig()
        admin.GetOS()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if self.ctx is not None:
            self.ctx.pop()


class RuntimeManager:
    """封装运行环境查询、安装、等待完成与诊断能力。"""

    def list_versions(self, runtime):
        """调用宝塔已有列表接口，返回对应运行环境的版本信息。"""
        runtime = normalize_runtime(runtime)
        if runtime == 'php':
            import panelSite
            return panelSite.panelSite().GetPHPVersion(public.to_dict_obj({}))
        if runtime == 'java':
            from projectModel.javaModel import main
            return main().get_local_jdk_version(public.to_dict_obj({}))
        if runtime == 'python':
            from projectModel.pythonModel import main
            return main().list_py_version(public.to_dict_obj({}))
        if runtime == 'go':
            from projectModel.goModel import main
            data = main().list_go_sdk(public.to_dict_obj({}))
            if data.get('status',False):
                del data.get('sdk')['all']
            return data
        if runtime == 'node':
            self.check_manager_installed('node')
            result = self.run_plugin_action('nodejs', 'get_online_version_list',params={'force': '1'})
            versions = result.get('result', [])
            re_versions = []
            if isinstance(versions, list):
                for v in versions[:30]:
                    version_item = {'version': v.get('version', ''), 'setup': v.get('setup', 0)}
                    if v.get('setup', 0) == 1:
                        version_item['path'] = '/www/server/nodejs/' + v.get('version', '')
                    re_versions.append(version_item)
                    
            return re_versions
        if runtime == 'dotnet':
            self.check_manager_installed('dotnet')
            result = self.run_plugin_action('dotnet', 'get_dotnet_version', {})
            return result['result']
        raise ValueError('不支持的运行环境: {}'.format(runtime))

    def ensure_manager(self, runtime, wait_timeout=DEFAULT_WAIT_TIMEOUT, poll_interval=DEFAULT_POLL_INTERVAL):
        """
        确保 Node.js/.NET 管理器插件存在。

        PHP、Java、Python、Go 使用面板内置项目模型，不需要额外管理器插件。
        管理器插件安装仍然通过软件商店的 install_plugin 方法完成。
        """
        runtime = normalize_runtime(runtime)
        manager = MANAGER_PLUGIN.get(runtime)
        if not manager:
            return {
                'status': True,
                'manager_required': False,
                'msg': '该运行环境无需额外管理器插件'
            }

        manager_path = MANAGER_PATH[manager]
        if os.path.exists(manager_path):
            return {
                'status': True,
                'manager_required': True,
                'installed': True,
                'manager': manager
            }

        result = self.install_manager_plugin(manager)
        self.trigger_task_scheduler()
        wait_result = self.wait_for_manager(manager, wait_timeout, poll_interval)
        return {
            'status': True,
            'manager_required': True,
            'installed': True,
            'manager': manager,
            'install_result': result,
            'wait_result': wait_result
        }

    def install_manager_plugin(self, manager):
        """通过软件商店安装运行环境管理器插件，不直接写任务表。"""
        import panelPlugin

        plugin = panelPlugin.panelPlugin()
        soft_info = plugin.get_soft_find(manager)
        if not soft_info:
            raise ValueError('未找到运行环境管理器插件: {}'.format(manager))

        versions = soft_info.get('versions') or []
        if not versions:
            raise ValueError('管理器插件 [{}] 没有可安装版本'.format(manager))

        version_info = versions[0]
        args = public.to_dict_obj({
            'sName': soft_info.get('name') or manager,
            'version': str(version_info.get('m_version', '')).strip(),
            'min_version': str(version_info.get('version', '')).strip(),
            "action": "install_plugin",
            "data": [],
        })

        info = plugin.install_plugin(args)
        if not info.get('tmp_path'):
            raise ValueError(info.get('msg', '插件安装失败'))

        args = public.dict_obj()
        args.tmp_path = info['tmp_path']
        args.plugin_name = soft_info.get('name') or manager
        args.install_opt = info['install_opt']
        return plugin.input_package(args)

    def install(self, runtime, version, install_type='0',
                wait_timeout=DEFAULT_WAIT_TIMEOUT, poll_interval=DEFAULT_POLL_INTERVAL):
        """
        安装指定运行环境版本。

        PHP、Java、Python、Go 会在提交安装后按版本列表轮询确认完成。
        Node.js、.NET 的插件安装动作返回即表示版本安装动作完成。
        """
        runtime = normalize_runtime(runtime)
        if not version:
            raise ValueError('安装运行环境必须指定版本')

        manager_state = self.ensure_manager(runtime, wait_timeout, poll_interval)
        if manager_state.get('manager_required') and not manager_state.get('installed'):
            return manager_state

        if runtime == 'php':
            return self.install_php(version, install_type, wait_timeout, poll_interval)
        if runtime == 'java':
            return self.install_java(version, wait_timeout, poll_interval)
        if runtime == 'python':
            return self.install_python(version, wait_timeout, poll_interval)
        if runtime == 'go':
            return self.install_go(version, wait_timeout, poll_interval)
        if runtime == 'node':
            return self.install_node(version, wait_timeout, poll_interval)
        if runtime == 'dotnet':
            return self.install_dotnet(version, wait_timeout, poll_interval)
        raise ValueError('不支持的运行环境: {}'.format(runtime))

    def install_php(self, version, install_type='1',
                    wait_timeout=DEFAULT_WAIT_TIMEOUT, poll_interval=DEFAULT_POLL_INTERVAL):
        """PHP 环境安装必须走 panelPlugin.panelPlugin().install_plugin。"""
        import panelPlugin
        if '.' not in version:
            version = '.'.join(version)
        plugin = panelPlugin.panelPlugin()

        result = plugin.install_plugin(public.to_dict_obj({
            'sName': 'php-{}'.format(version),
            'version': str(version),
            'min_version': '',
            'type': str(install_type)
        }))
        if not result.get('status'):
            raise ValueError('PHP 插件安装失败: {}'.format(result.get('msg')))
        ret = {
            'runtime': 'php',
            'version': version,
            'method': 'panelPlugin.panelPlugin().install_plugin',
            'result': result,
        }
        self.trigger_task_scheduler()
        ret['wait_result'] = self.wait_for_runtime('php', version, wait_timeout, poll_interval)
        return ret

    def install_java(self, version, wait_timeout=DEFAULT_WAIT_TIMEOUT, poll_interval=DEFAULT_POLL_INTERVAL):
        """JDK 安装使用 Java 项目模型提供的安装方法。"""
        from projectModel.javaModel import main

        result = main().install_jdk_new(public.to_dict_obj({'version': str(version)}))
        if not result.get('status'):
            raise ValueError('JDK 安装失败: {}'.format(result.get('msg')))
        ret = {
            'runtime': 'java',
            'version': version,
            'method': 'projectModel.javaModel.main().install_jdk_new',
            'result': result,
        }
        self.trigger_task_scheduler()
        ret['wait_result'] = self.wait_for_runtime('java', version, wait_timeout, poll_interval)
        return ret

    def install_python(self, version, wait_timeout=DEFAULT_WAIT_TIMEOUT, poll_interval=DEFAULT_POLL_INTERVAL):
        """Python 版本安装使用 Python 项目模型的异步安装入口。"""
        from projectModel.pythonModel import main

        result = main().async_install_py_version(public.to_dict_obj({'version': str(version)}))
        ret = {
            'runtime': 'python',
            'version': version,
            'method': 'projectModel.pythonModel.main().async_install_py_version',
            'result': result,
        }
        self.trigger_task_scheduler()
        ret['wait_result'] = self.wait_for_runtime('python', version, wait_timeout, poll_interval)
        return ret

    def install_go(self, version, wait_timeout=DEFAULT_WAIT_TIMEOUT, poll_interval=DEFAULT_POLL_INTERVAL):
        """Go SDK 安装使用 Go 项目模型的异步安装入口。"""
        from projectModel.goModel import main

        result = main().install_go_sdk_async(public.to_dict_obj({'version': str(version)}))
        ret = {
            'runtime': 'go',
            'version': version,
            'method': 'projectModel.goModel.main().install_go_sdk_async',
            'result': result,
        }
        self.trigger_task_scheduler()
        ret['wait_result'] = self.wait_for_runtime('go', version, wait_timeout, poll_interval)
        return ret

    def check_manager_installed(self, runtime):
        """校验管理器插件是否已安装，未安装则抛出错误引导执行 ensure-manager。"""
        runtime = normalize_runtime(runtime)
        manager = MANAGER_PLUGIN.get(runtime)
        if not manager:
            return
        manager_path = MANAGER_PATH[manager]
        if not os.path.exists(manager_path):
            raise ValueError(
                '{}管理器未安装，请先执行 ensure-manager --runtime {} 安装管理器'.format(
                    manager, runtime
                )
            )

    def install_node(self, version, wait_timeout=DEFAULT_WAIT_TIMEOUT, poll_interval=DEFAULT_POLL_INTERVAL):
        """
        安装 Node.js 版本，并为该版本安装 PM2 与 yarn。

        Node.js 版本安装必须走：
        /plugin?action=a&s=install_nodejs&name=nodejs

        该接口返回时代表版本安装动作已经完成，因此不再轮询 Node.js 版本列表。
        PM2/yarn 是后续模块安装动作，安装后按文件存在情况等待完成。
        """
        self.check_manager_installed('node')
        version = str(version)
        install_result = self.run_plugin_action(
            'nodejs',
            'install_nodejs',
            {'version': version}
        )

        module_results = []
        for module_name in ('pm2', 'yarn'):
            module_result = self.run_plugin_action(
                'nodejs',
                'install_module',
                {
                    'version': version,
                    'module': module_name
                }
            )
            module_result['module'] = module_name
            module_result['wait_result'] = self.wait_for_node_module(version, module_name, wait_timeout, poll_interval)
            module_results.append(module_result)

        self.trigger_task_scheduler()
        post_install_version = self.run_plugin_action(
            'nodejs',
            'get_online_version_list',
            {'force': '1'}
        )
        return {
            'runtime': 'node',
            'version': version,
            'method': install_result['method'],
            'result': install_result['result'],
            'post_install_modules': module_results,
            'post_install_version': post_install_version['result'],
        }

    def install_dotnet(self, version, wait_timeout=DEFAULT_WAIT_TIMEOUT, poll_interval=DEFAULT_POLL_INTERVAL):
        """
        安装 .NET 版本。

        .NET 版本安装必须走：
        /plugin?action=a&name=dotnet&s=install_dotnet

        该接口返回时代表版本安装动作已经完成，因此不再轮询 .NET 版本列表。
        """
        self.check_manager_installed('dotnet')
        version = str(version)
        install_result = self.run_plugin_action(
            'dotnet',
            'install_dotnet',
            {'version': version}
        )

        self.trigger_task_scheduler()
        post_install_version = self.run_plugin_action(
            'dotnet',
            'get_dotnet_version',
            {}
        )
        print("test2222")
        return {
            'runtime': 'dotnet',
            'version': version,
            'method': install_result['method'],
            'result': install_result['result'],
            'post_install_version': post_install_version['result'],
        }

    def run_plugin_action(self, plugin_name, action, params=None):
        """模拟 /plugin?action=a 的分发入口，保持与面板插件路由一致。"""
        import panelPlugin

        payload = {
            'name': plugin_name,
            's': action
        }
        if params:
            payload.update(params)
        result = panelPlugin.panelPlugin().a(public.to_dict_obj(payload))
        print(result)
        return {
            'method': '/plugin?action=a&s={}&name={}'.format(action, plugin_name),
            'result': result
        }

    def normalize_php_version(self, version):
        """面板 PHP 列表使用 83/82 这类版本号，用户可能输入 8.3/8.2。"""
        return str(version).strip().replace('.', '')

    def normalize_go_version(self, version):
        """Go 已安装列表里通常是 go1.22.5，用户可能只传 1.22.5。"""
        version = str(version).strip()
        return version if version.startswith('go') else 'go{}'.format(version)

    def runtime_installed(self, runtime, version):
        """
        判断 PHP、Java、Python、Go 是否已经安装完成。

        该方法只通过宝塔提供的版本列表判断，不使用任务队列状态。
        Node.js 和 .NET 不走这里，因为它们的版本安装插件接口本身完成后才返回。
        """
        runtime = normalize_runtime(runtime)
        version = str(version).strip()

        if runtime == 'php':
            php_version = self.normalize_php_version(version)
            for item in self.list_versions('php'):
                if item.get('version') == php_version and item.get('status'):
                    return True
            return False

        if runtime == 'java':
            for item in self.list_versions('java'):
                if item.get('name') == version and item.get('operation') in (1, 2):
                    return True
            return False

        if runtime == 'python':
            data = self.list_versions('python')
            for group in (data.get('sdk', {}).get('all', []), data.get('sdk', {}).get('streamline', [])):
                for item in group:
                    if item.get('version') == version and item.get('installed'):
                        return True
            return False

        if runtime == 'go':
            data = self.list_versions('go')
            return self.normalize_go_version(version) in data.get('installed', [])

        raise ValueError('{} 不使用版本列表轮询判断安装完成'.format(runtime))

    def wait_until(self, check_func, timeout=DEFAULT_WAIT_TIMEOUT, poll_interval=DEFAULT_POLL_INTERVAL):
        """
        通用等待器。

        每 poll_interval 秒执行一次 check_func；返回 True 即认为完成。
        默认轮询间隔是 5 秒，超时后返回 completed=False，由上层决定是否抛错。
        """
        timeout = float(timeout)
        poll_interval = max(float(poll_interval), 1.0)
        started_at = time.time()
        last_error = None

        while True:
            try:
                if check_func():
                    return {
                        'completed': True,
                        'elapsed': round(time.time() - started_at, 2)
                    }
            except Exception as exc:
                last_error = str(exc)

            if timeout > 0 and time.time() - started_at >= timeout:
                result = {
                    'completed': False,
                    'timeout': timeout,
                    'elapsed': round(time.time() - started_at, 2)
                }
                if last_error:
                    result['last_error'] = last_error
                return result

            time.sleep(poll_interval)

    def wait_for_manager(self, manager, timeout=DEFAULT_WAIT_TIMEOUT, poll_interval=DEFAULT_POLL_INTERVAL):
        """等待管理器插件目录出现。管理器不是具体运行环境版本，因此这里不查版本列表。"""
        manager_path = MANAGER_PATH[manager]
        result = self.wait_until(lambda: os.path.exists(manager_path), timeout, poll_interval)
        if not result.get('completed'):
            raise TimeoutError('管理器插件安装超时: {}'.format(manager))
        return result

    def wait_for_runtime(self, runtime, version, timeout=DEFAULT_WAIT_TIMEOUT, poll_interval=DEFAULT_POLL_INTERVAL):
        """等待 PHP、Java、Python、Go 目标版本出现在宝塔版本列表中。"""
        result = self.wait_until(lambda: self.runtime_installed(runtime, version), timeout, poll_interval)
        if not result.get('completed'):
            raise TimeoutError('运行环境安装超时: {} {}'.format(runtime, version))
        return result

    def node_module_installed(self, version, module_name):
        """判断指定 Node.js 版本下的全局模块是否安装完成。"""
        if module_name == 'pm2':
            return (
                os.path.exists('/www/server/nodejs/{}/bin/pm2'.format(version)) or
                os.path.exists('/www/server/nodejs/{}/lib/node_modules/pm2'.format(version))
            )
        if module_name == 'yarn':
            return os.path.exists('/www/server/nodejs/{}/bin/yarn'.format(version))
        return os.path.exists('/www/server/nodejs/{}/lib/node_modules/{}'.format(version, module_name))

    def wait_for_node_module(self, version, module_name,
                             timeout=DEFAULT_WAIT_TIMEOUT, poll_interval=DEFAULT_POLL_INTERVAL):
        """等待 Node.js 版本下的 PM2/yarn 安装完成。"""
        result = self.wait_until(lambda: self.node_module_installed(version, module_name), timeout, poll_interval)
        if not result.get('completed'):
            raise TimeoutError('Node.js 模块安装超时: {} {}'.format(version, module_name))
        return result

    def task_status(self, silent=False):
        """
        仅用于手动诊断当前面板任务状态。

        安装完成判断不得依赖此方法，也不得依赖 tasks 表是否为空。
        """
        from files import files as Files

        try:
            return Files().GetTaskSpeed(public.to_dict_obj({}))
        except Exception as exc:
            if silent:
                return {
                    'status': False,
                    'msg': str(exc)
                }
            raise

    def task_log(self, lines=100):
        """读取面板安装日志，仅用于安装失败或超时时排查。"""
        from files import files as Files

        return Files().GetLastLine('/tmp/panelExec.log', int(lines))

    def trigger_task_scheduler(self):
        from files import files as Files
        try:
            Files().GetTaskSpeed(public.to_dict_obj({}))
        except Exception:
            return {'status': False, 'msg': '触发任务调度器失败'}


def main():
    parser = argparse.ArgumentParser(description='宝塔面板运行环境安装脚本')
    subparsers = parser.add_subparsers(dest='action', help='操作类型')

    list_parser = subparsers.add_parser('list', help='查询运行环境版本')
    list_parser.add_argument('--runtime', required=True, help='php/java/node/go/python/dotnet')

    ensure_parser = subparsers.add_parser('ensure-manager', help='检查并安装必要管理器')
    ensure_parser.add_argument('--runtime', required=True, help='php/java/node/go/python/dotnet')
    ensure_parser.add_argument('--wait-timeout', default=DEFAULT_WAIT_TIMEOUT, type=float, help='等待超时时间，默认 7200 秒')
    ensure_parser.add_argument('--poll-interval', default=DEFAULT_POLL_INTERVAL, type=float, help='轮询间隔，默认 5 秒')

    install_parser = subparsers.add_parser('install', help='安装具体运行环境版本')
    install_parser.add_argument('--runtime', required=True, help='php/java/node/go/python/dotnet')
    install_parser.add_argument('--version', required=True, help='运行环境版本')
    install_parser.add_argument('--type', default='0', help='PHP 安装方式，默认 0')
    install_parser.add_argument('--wait-timeout', default=DEFAULT_WAIT_TIMEOUT, type=float, help='等待超时时间，默认 7200 秒')
    install_parser.add_argument('--poll-interval', default=DEFAULT_POLL_INTERVAL, type=float, help='轮询间隔，默认 5 秒')

    subparsers.add_parser('status', help='诊断当前面板任务状态')

    log_parser = subparsers.add_parser('log', help='查看安装日志')
    log_parser.add_argument('--lines', default=100, type=int, help='日志行数')

    args = parser.parse_args()
    if not args.action:
        parser.print_help()
        sys.exit(1)

    try:
        with BtPanelContext():
            manager = RuntimeManager()
            if args.action == 'list':
                result = manager.list_versions(args.runtime)
            elif args.action == 'ensure-manager':
                result = manager.ensure_manager(args.runtime, args.wait_timeout, args.poll_interval)
            elif args.action == 'install':
                result = manager.install(
                    args.runtime,
                    args.version,
                    install_type=args.type,
                    wait_timeout=args.wait_timeout,
                    poll_interval=args.poll_interval
                )
            elif args.action == 'status':
                result = manager.task_status()
            elif args.action == 'log':
                result = {'log': manager.task_log(args.lines)}
            else:
                raise ValueError('未知操作: {}'.format(args.action))

        print(to_json({'status': True, 'data': result}))
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
