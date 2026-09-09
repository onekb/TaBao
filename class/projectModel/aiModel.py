# coding: utf-8
# -------------------------------------------------------------------
# 宝塔Linux面板 - AI网站项目管理模块
# -------------------------------------------------------------------
# Copyright (c) 2015-2099 宝塔软件(http://bt.cn) All rights reserved.
# -------------------------------------------------------------------

import os
import sys
import re
import json
import psutil
import time
from projectModel.base import projectBase
import public

try:
    from BTPanel import cache
except:
    pass


class main(projectBase):
    _panel_path = public.get_panel_path()
    _ai_path = '/www/server/ai_project'
    _log_name = 'AI项目管理'
    _ai_logs_path = "/www/wwwlogs/ai"
    _vhost_path = '{}/vhost'.format(_panel_path)
    _pids = None

    def __init__(self):
        if not os.path.exists(self._ai_path):
            os.makedirs(self._ai_path, 493)

        if not os.path.exists(self._ai_logs_path):
            os.makedirs(self._ai_logs_path, 493)

    def _get_port_numbers(self, ports):
        '''
            @name 从ports列表中提取纯端口号
            @param ports<list> ports列表，每项为 {"port": int, "label": string}
            @return list<int>
        '''
        if not ports:
            return []
        return [int(p["port"]) for p in ports]

    def _get_project_path(self, project_name):
        '''
            @name 获取AI项目根目录路径（核心函数，直接查询数据库）
            @author <2024-01-01>
            @param project_name<string> 项目名称
            @return string|None 项目根目录路径
        '''
        project_find = public.M('sites').where('project_type=? AND name=?', ('AI', project_name)).find()
        if isinstance(project_find, str) or not project_find:
            return None
        return project_find['path']

    def get_aiproject_dir(self, project_name):
        '''
            @name 获取AI项目.aiproject目录路径
            @author <2024-01-01>
            @param project_name<string> 项目名称
            @return string|None .aiproject目录路径
        '''
        path = self._get_project_path(project_name)
        if not path:
            return None
        return "{}/.aiproject".format(path)

    def get_ai_config_path(self, project_name):
        '''
            @name 获取AI项目配置文件路径
            @author <2024-01-01>
            @param project_name<string> 项目名称
            @return string 配置文件完整路径
        '''
        path = self._get_project_path(project_name)
        if not path:
            return "{}/ai_config.json".format(self._ai_path)
        return "{}/.aiproject/ai_config.json".format(path)

    def get_ai_pid_path(self, project_name):
        '''
            @name 获取AI项目PID文件路径
            @author <2024-01-01>
            @param project_name<string> 项目名称
            @return string PID文件完整路径
        '''
        path = self._get_project_path(project_name)
        if not path:
            return "/var/tmp/ai_project/{}.pid".format(project_name)
        return "{}/.aiproject/{}.pid".format(path, project_name)

    def ensure_aiproject_dir(self, project_name):
        '''
            @name 确保.aiproject目录存在
            @author <2024-01-01>
            @param project_name<string> 项目名称
            @return bool
        '''
        path = self._get_project_path(project_name)
        if not path:
            return False
        aiproject_dir = "{}/.aiproject".format(path)
        if not os.path.exists(aiproject_dir):
            os.makedirs(aiproject_dir, 493)
        return True

    def read_ai_config(self, project_name, project_path=None):
        '''
            @name 读取AI项目配置文件
            @author <2024-01-01>
            @param project_name<string> 项目名称
            @param project_path<string> 项目目录路径，传入后可跳过DB查询直接读配置
            @return dict|bool
                成功: dict<配置信息>
                失败: False
        '''
        if project_path:
            config_path = "{}/.aiproject/ai_config.json".format(project_path)
        else:
            path = self._get_project_path(project_name)
            if not path:
                config_path = "{}/ai_config.json".format(self._ai_path)
            else:
                config_path = "{}/.aiproject/ai_config.json".format(path)
        if not os.path.exists(config_path):
            return False
        try:
            config_body = public.readFile(config_path)
            return json.loads(config_body)
        except:
            return False

    def write_ai_config(self, project_name, config, project_path=None):
        '''
            @name 写入AI项目配置文件
            @author <2024-01-01>
            @param project_name<string> 项目名称
            @param config<dict> 配置信息
            @param project_path<string> 项目目录路径，传入后可跳过DB查询直接写配置
            @return bool
                True: 写入成功
                False: 写入失败
        '''
        if project_path:
            config_path = "{}/.aiproject/ai_config.json".format(project_path)
        else:
            path = self._get_project_path(project_name)
            if not path:
                config_path = "{}/ai_config.json".format(self._ai_path)
            else:
                config_path = "{}/.aiproject/ai_config.json".format(path)
        print(config_path)
        config_dir = os.path.dirname(config_path)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, 493)
        try:
            public.writeFile(config_path, json.dumps(config, indent=4))
            return True
        except:
            return False

    def get_project_find(self, project_name):
        '''
            @name 获取指定项目配置
            @author <2024-01-01>
            @param project_name<string> 项目名称
            @return dict|bool
                成功: {
                    id: int<项目ID>,
                    name: string<项目名称>,
                    path: string<项目路径>,
                    ps: string<项目备注>,
                    status: int<项目状态 1:运行中 0:已停止>,
                    project_type: string<项目类型 AI>,
                    project_config: dict<项目配置信息>,
                    addtime: string<添加时间>
                }
                失败: False
        '''
        project_info = public.M('sites').where('project_type=? AND name=?', ('AI', project_name)).find()
        print(project_info)
        if isinstance(project_info, str):
            raise public.PanelError('数据库查询错误：' + project_info)
        if not project_info:
            return False

        config_path = "{}/.aiproject/ai_config.json".format(project_info['path'])
        if os.path.exists(config_path):
            try:
                project_info['project_config'] = json.loads(public.readFile(config_path))
            except:
                project_info['project_config'] = json.loads(project_info['project_config'])
        else:
            project_info['project_config'] = json.loads(project_info['project_config'])

        return project_info

    def get_project_run_state(self, get=None, project_name=None):
        '''
            @name 获取项目运行状态
            @author <2024-01-01>
            @param get<dict_obj>{
                project_name: string<项目名称>
            }
            @param project_name<string> 项目名称
            @return bool
                True: 项目运行中
                False: 项目已停止
        '''
        if get:
            project_name = get.project_name.strip()
        project_find = self.get_project_find(project_name)
        if not project_find:
            return False

        project_mode = project_find['project_config'].get('project_mode', 'dynamic')

        if project_mode == 'static':
            config_file = "{}/nginx/ai_{}.conf".format(self._vhost_path, project_name)
            if not os.path.exists(config_file):
                return False
            config_body = public.readFile(config_file)
            if not config_body:
                return False
            if 'bt-stop.html' in config_body:
                return False
            return True
        else:
            pid_file = self.get_ai_pid_path(project_name)
            if not os.path.exists(pid_file):
                return False
            try:
                pid = int(public.readFile(pid_file))
            except:
                return False
            if not os.path.exists('/proc/{}'.format(pid)):
                return False
            try:
                p = psutil.Process(pid)
                if p.status() == psutil.STATUS_ZOMBIE:
                    return False
                return True
            except:
                return False

    def get_ssl_end_date(self, project_name):
        '''
            @name 获取SSL信息
            @author <2024-01-01>
            @param project_name <string> 项目名称
            @return dict
        '''
        import data
        return data.data().get_site_ssl_info('ai_{}'.format(project_name))

    def get_project_stat(self, project_info):
        '''
            @name 获取项目状态信息
            @author <2024-01-01>
            @param project_info<dict> 项目信息，包含以下字段:
                id: int<项目ID>
                name: string<项目名称>
                path: string<项目路径>
                ps: string<项目备注>
                status: int<项目状态>
                project_config: dict|str<项目配置>
                addtime: string<添加时间>
            @return dict
                返回增强后的项目信息，新增以下字段:
                run: bool<项目运行状态 True:运行中 False:已停止>
                listen: list<监听的端口列表>
                listen_ok: bool<端口监听是否正常>
                ssl: dict|int<SSL证书信息>
        '''
        ai_config = self.read_ai_config(project_info['name'])
        if ai_config:
            project_info['project_config'] = ai_config
        elif isinstance(project_info['project_config'], str):
            project_info['project_config'] = json.loads(project_info['project_config'])

        #外网映射 1:开启 0:关闭
        project_info['project_config']['bind_extranet'] = 1

        project_info['run'] = self.get_project_run_state(project_name=project_info['name'])
        project_info['ssl'] = self.get_ssl_end_date(project_name=project_info['name'])
        project_info['listen'] = []
        project_info['listen_ok'] = True

        if project_info['project_config'].get('project_mode') == 'dynamic':
            pid_file = self.get_ai_pid_path(project_info['name'])
            if os.path.exists(pid_file):
                try:
                    pid = int(public.readFile(pid_file))
                    if os.path.exists('/proc/{}'.format(pid)):
                        p = psutil.Process(pid)
                        for conn in p.connections():
                            if conn.status == 'LISTEN':
                                project_info['listen'].append(conn.laddr.port)
                except:
                    pass

            ports = self._get_port_numbers(project_info['project_config'].get('ports', []))
            if ports and project_info['listen']:
                project_info['listen_ok'] = any(p in project_info['listen'] for p in ports)

        return project_info

    def start_project(self, get):
        '''
            @name 启动项目
            @author <2024-01-01>
            @param get<dict_obj>{
                project_name: string<项目名称>
            }
            @return dict
                成功: {
                    status: True,
                    msg: string<成功提示信息>,
                    data: null
                }
                失败: {
                    status: False,
                    msg: string<错误信息>,
                    data: null
                }
        '''
        project_find = self.get_project_find(get.project_name)
        if not project_find:
            return public.return_error('指定项目不存在: {}'.format(get.project_name))

        project_config = project_find['project_config']
        project_mode = project_config.get('project_mode', 'dynamic')

        if project_mode == 'static':
            config_file = "{}/nginx/ai_{}.conf".format(self._vhost_path, get.project_name)
            if os.path.exists(config_file):
                config_body = public.readFile(config_file)
                if config_body and 'bt-stop.html' in config_body:
                    stop_path = '/www/server/stop'
                    site_path = project_find.get('path', '')
                    config_body = config_body.replace(stop_path, site_path)
                    config_body = re.sub(
                        r'\s*rewrite\s+.*bt-stop\\\.html\S*\s+/bt-stop\.html\s+last;\s*'
                        r'location\s*=\s*/bt-stop\.html\s*\{[^}]+\}[^\n]*\n',
                        '',
                        config_body
                    )
                    public.writeFile(config_file, config_body)
                    public.serviceReload()

            public.M('sites').where('name=?', (get.project_name,)).setField('status', 1)
            public.WriteLog(self._log_name, '启动AI静态项目{}'.format(get.project_name))
            return public.returnMsg(True, '项目启动成功')

        start_cmd = project_config.get('start_cmd')
        if not start_cmd:
            return public.returnMsg(False,'项目未配置启动命令')

        run_user = project_config.get('run_user', 'www')
        pid_file = self.get_ai_pid_path(get.project_name)
        self.ensure_aiproject_dir(get.project_name)

        cmd = 'nohup {} > /dev/null 2>&1 & echo $! > {}'.format(start_cmd, pid_file)

        if run_user != 'root':
            cmd = 'sudo -u {} {}'.format(run_user, cmd)

        public.ExecShell(cmd)
        time.sleep(1)

        if os.path.exists(pid_file):
            public.M('sites').where('name=?', (get.project_name,)).setField('status', 1)
            public.WriteLog(self._log_name, '启动AI动态项目{}'.format(get.project_name))
            return public.returnMsg(True, '项目启动成功')
        else:
            return public.returnMsg(False,'项目启动失败')

    def stop_project(self, get):
        '''
            @name 停止项目
            @author <2024-01-01>
            @param get<dict_obj>{
                project_name: string<项目名称>
            }
            @return dict
                成功: {
                    status: True,
                    msg: string<成功提示信息>,
                    data: null
                }
                失败: {
                    status: False,
                    msg: string<错误信息>,
                    data: null
                }
        '''
        project_find = self.get_project_find(get.project_name)
        if not project_find:
            return public.return_error('指定项目不存在: {}'.format(get.project_name))

        project_config = project_find['project_config']
        project_mode = project_config.get('project_mode', 'dynamic')

        if project_mode == 'static':
            config_file = "{}/nginx/ai_{}.conf".format(self._vhost_path, get.project_name)
            if os.path.exists(config_file):
                config_body = public.readFile(config_file)
                if config_body and 'bt-stop.html' not in config_body:
                    stop_path = '/www/server/stop'
                    site_path_match = re.search(r'root\s+(.+?)\s*;', config_body)
                    if site_path_match:
                        site_path = site_path_match.group(1)
                        stop_rule = "root " + stop_path + ";\n\n"
                        stop_rule += "    rewrite ^/(?!bt-stop\\.html$).* /bt-stop.html last;\n"
                        stop_rule += "    location = /bt-stop.html {\n"
                        stop_rule += "        root " + stop_path + ";\n"
                        stop_rule += "        internal;\n"
                        stop_rule += "    }"
                        config_body = re.sub(r'root\s+' + re.escape(site_path) + r'\s*;', stop_rule, config_body, 1)
                    else:
                        stop_rule = '''
    rewrite ^/(?!bt-stop\\.html$).* /bt-stop.html last;
    location = /bt-stop.html {
        root /www/server/stop;
        internal;
    }
'''
                        config_body = config_body.replace('access_log', stop_rule + '\n    access_log', 1)
                    public.writeFile(config_file, config_body)
                    public.serviceReload()

            public.M('sites').where('name=?', (get.project_name,)).setField('status', 0)
            public.WriteLog(self._log_name, '停止AI静态项目{}'.format(get.project_name))
            return public.returnMsg(True, '项目已停止')

        stop_cmd = project_config.get('stop_cmd')
        pid_file = self.get_ai_pid_path(get.project_name)

        if stop_cmd:
            public.ExecShell(stop_cmd)
        elif os.path.exists(pid_file):
            try:
                pid = int(public.readFile(pid_file))
                os.kill(pid, 9)
            except:
                pass

        if os.path.exists(pid_file):
            os.remove(pid_file)

        public.M('sites').where('name=?', (get.project_name,)).setField('status', 0)
        public.WriteLog(self._log_name, '停止AI动态项目{}'.format(get.project_name))
        return public.returnMsg(True, '项目已停止')

    def restart_project(self, get):
        '''
            @name 重启项目
            @author <2024-01-01>
            @param get<dict_obj>{
                project_name: string<项目名称>
            }
            @return dict
                成功: {
                    status: True,
                    msg: string<成功提示信息>,
                    data: null
                }
                失败: {
                    status: False,
                    msg: string<错误信息>,
                    data: null
                }
        '''
        self.stop_project(get)
        time.sleep(1)
        return self.start_project(get)

    def create_project(self, get):
        '''
            @name 创建新的AI项目
            @author <2024-01-01>
            @param get<dict_obj>{
                project_name: string<项目名称>
                project_path: string<项目目录>
                project_ps: string<项目备注信息> 可选
                project_mode: string<项目模式> dynamic:动态项目 static:静态项目 默认dynamic
                ports: list|str<项目端口列表> 动态项目必填，格式: [{"port":3000,"label":"前端服务"}] 或 JSON字符串
                start_cmd: string<启动命令> 动态项目必填
                stop_cmd: string<停止命令> 动态项目必填
                domains: list<域名列表> 可选 ["domain1:80","domain2:443"]
                is_power_on: int<是否开机启动> 1:是 0:否 默认0
                run_user: string<运行用户> 默认www
                environment: string<环境变量> 可选
                logs: dict<日志配置> 可选，由AI自定义日志分类和路径
                      格式: {"后端日志": "/path/to/backend.log", "前端日志": "/path/to/frontend.log"}
            }
            @return dict
                成功: {
                    status: True,
                    msg: string<成功提示信息>,
                    data: int<项目ID>
                }
                失败: {
                    status: False,
                    msg: string<错误信息>,
                    data: null
                }
        '''
        project_name = get.project_name.strip()
        if not re.match("^\w+$", project_name):
            return public.return_error('项目名称格式不正确，支持字母、数字、下划线，表达式: ^[0-9A-Za-z_]$')

        if public.M('sites').where('name=?', (get.project_name,)).count():
            return public.return_error('指定项目名称已存在: {}'.format(get.project_name))

        if not os.path.exists(get.project_path):
            return public.return_error('项目目录不存在: {}'.format(get.project_path))

        project_mode = get.get('project_mode', 'dynamic')
        if project_mode not in ['dynamic', 'static']:
            return public.return_error('项目模式必须为 dynamic 或 static')

        if project_mode == 'dynamic':
            if not hasattr(get, 'start_cmd') or not get.start_cmd:
                return public.return_error('动态项目必须提供启动命令')
            if not hasattr(get, 'stop_cmd') or not get.stop_cmd:
                return public.return_error('动态项目必须提供停止命令')
            if not hasattr(get, 'ports') or not get.ports:
                return public.return_error('动态项目必须配置端口')

            ports = get.ports
            if isinstance(ports, str):
                ports = json.loads(ports)

            for entry in ports:
                port_num = int(entry["port"])
                if self.check_port_is_used(port_num):
                    return public.return_error('指定端口已被其它应用占用，请修改您的项目配置使用其它端口, 端口: {}'.format(port_num))

        domains = []
        if hasattr(get, 'domains') and get.domains:
            if isinstance(get.domains, str):
                domains = json.loads(get.domains)
            else:
                domains = get.domains

        for domain in domains:
            if "[" in domain and "]" in domain:
                if "]:" in domain:
                    domain_arr = domain.rsplit(":", 1)
                else:
                    domain_arr = [domain]
            else:
                domain_arr = domain.split(':')

            domain_arr[0] = self.check_domain(domain_arr[0])
            if domain_arr[0] is False:
                return public.return_error('域名格式错误: {}'.format(domain))

            if len(domain_arr) == 1:
                domain_arr.append("")
            if domain_arr[1] == "":
                domain_arr[1] = 80
                domain += ':80'

            if public.M('domain').where('name=? and port=?', (domain_arr[0], domain_arr[1])).count():
                return public.return_error('指定域名已存在: {}'.format(domain))

        ports = []
        if hasattr(get, 'ports') and get.ports:
            if isinstance(get.ports, str):
                ports = json.loads(get.ports)
            else:
                ports = get.ports

        if not ports:
            domain_ports = set()
            for domain in domains:
                if "[" in domain and "]" in domain:
                    if "]:" in domain:
                        _, port_part = domain.rsplit(":", 1)
                        try:
                            domain_ports.add(int(port_part))
                        except ValueError:
                            pass
                else:
                    parts = domain.rsplit(':', 1)
                    if len(parts) == 2:
                        try:
                            domain_ports.add(int(parts[1]))
                        except ValueError:
                            pass
            sorted_ports = sorted(domain_ports) if domain_ports else [80]
            ports = [{"port": p, "label": ""} for p in sorted_ports]

        primary_port = ports[0]["port"] if ports else 80
        ssl_path = '/www/wwwroot/ai_ssl/{}'.format(get.project_name)

        # 基础日志配置（Nginx访问/错误日志）
        base_logs = {
        }

        # 合并AI自定义的日志配置
        if hasattr(get, 'logs') and get.logs:
            custom_logs = get.logs
            if isinstance(custom_logs, str):
                custom_logs = json.loads(custom_logs)
            base_logs.update(custom_logs)

        ai_config = {
            'ssl_path': ssl_path,
            'project_name': get.project_name,
            'project_path': get.project_path,
            'ports': ports,
            'primary_port': primary_port,
            'start_cmd': get.get('start_cmd', ''),
            'stop_cmd': get.get('stop_cmd', ''),
            'is_power_on': get.get('is_power_on', 0),
            'run_user': get.get('run_user', 'www'),
            'project_mode': project_mode,
            'domains': domains,
            'environment': get.get('environment', ''),
            'logs': base_logs
        }
        self.write_ai_config(get.project_name, ai_config, get.project_path)

        pdata = {
            'name': get.project_name,
            'path': get.project_path,
            'ps': get.get('project_ps', ''),
            'status': 1,
            'type_id': 0,
            'project_type': 'AI',
            'project_config': json.dumps({
                'ssl_path': ssl_path
            }),
            'addtime': public.getDate()
        }

        project_id = public.M('sites').insert(pdata)
        pdata['id'] = project_id

        if domains:
            format_domains = []
            for domain in domains:
                if "[" in domain and "]" in domain:
                    if "]:" not in domain:
                        domain += ':80'
                else:
                    if domain.find(':') == -1:
                        domain += ':80'
                format_domains.append(domain)

            for domain in format_domains:
                domain_arr = domain.rsplit(':', 1)
                public.M('domain').insert({
                    'name': domain_arr[0],
                    'pid': str(project_id),
                    'port': domain_arr[1],
                    'addtime': public.getDate()
                })

        if not self.set_config(project_find=pdata):
            return public.return_error('生成Nginx配置文件失败')

        aiproject_dir = "{}/.aiproject".format(get.project_path)
        if not os.path.exists(aiproject_dir):
            os.makedirs(aiproject_dir, 493)

        if not os.path.exists(self._ai_logs_path):
            os.makedirs(self._ai_logs_path, 493)

        public.WriteLog(self._log_name, '添加AI项目{}'.format(get.project_name))

        if project_mode == 'dynamic':
            self.start_project(get)
            
        try:
            from firewallModel.comModel import main as comModel
            firewall_com = comModel()
            for port_info in ports:
                port_num = port_info["port"]
                f_get = public.dict_obj()
                f_get.port = str(port_num)
                f_get.protocol = 'tcp'
                f_get.address = 'all'
                f_get.operation = 'add'
                f_get.strategy = 'accept'
                f_get.chain = 'INPUT'
                f_get.reload = '1'
                f_get.brief = 'AI项目{}端口'.format(get.project_name)
                
                result = firewall_com.set_port_rule(f_get)
                if result.get('status'):
                    public.WriteLog(self._log_name, '放行AI项目{}端口: {}'.format(get.project_name, port_num))
        except Exception as e:
            public.WriteLog(self._log_name, '放行AI项目端口失败: {}'.format(str(e)))

        return public.return_data(True, '添加AI项目成功', project_id)

    def modify_project(self, get):
        '''
            @name 修改指定AI项目
            @author <2024-01-01>
            @param get<dict_obj>{
                project_name: string<项目名称> 必填，不可修改
                project_path: string<项目执行目录> 可选
                project_ps: string<项目备注信息> 可选
                ports: list|str<项目端口列表> 可选，格式: [{"port":3000,"label":"前端服务"}]
                start_cmd: string<启动命令> 可选，动态项目可修改
                stop_cmd: string<停止命令> 可选，动态项目可修改
                is_power_on: int<是否开机启动> 1:是 0:否 可选
                run_user: string<运行用户> 可选
                environment: string<环境变量> 可选
            }
            @return dict
                成功: {
                    status: True,
                    msg: string<成功提示信息，修改成功后重启项目>,
                    data: null
                }
                失败: {
                    status: False,
                    msg: string<错误信息>,
                    data: null
                }
        '''
        project_find = self.get_project_find(get.project_name)
        if not project_find:
            return public.return_error('指定项目不存在: {}'.format(get.project_name))

        ai_config = project_find['project_config']

        if hasattr(get, 'project_path'):
            if not os.path.exists(get.project_path):
                return public.return_error('项目目录不存在: {}'.format(get.project_path))
            ai_config['project_path'] = get.project_path.strip()
            project_find['path'] = get.project_path.strip()
            public.M('sites').where('name=?', (get.project_name,)).setField('path', get.project_path)

        if hasattr(get, 'ports'):
            ports = get.ports
            if isinstance(ports, str):
                ports = json.loads(ports)
            ai_config['ports'] = ports
            if ports:
                ai_config['primary_port'] = ports[0]["port"]

        if hasattr(get, 'start_cmd'):
            ai_config['start_cmd'] = get.start_cmd.strip()

        if hasattr(get, 'stop_cmd'):
            ai_config['stop_cmd'] = get.stop_cmd.strip()

        if hasattr(get, 'is_power_on'):
            ai_config['is_power_on'] = get.is_power_on

        if hasattr(get, 'run_user'):
            ai_config['run_user'] = get.run_user.strip()

        if hasattr(get, 'environment'):
            ai_config['environment'] = get.environment

        self.write_ai_config(get.project_name, ai_config)

        if hasattr(get, 'project_ps'):
            public.M('sites').where('name=?', (get.project_name,)).setField('ps', get.project_ps)

        public.WriteLog(self._log_name, '修改AI项目{}'.format(get.project_name))

        if not self.set_config(project_find=project_find):
            return public.return_error('更新Nginx配置失败')

        if ai_config.get('project_mode') == 'dynamic':
            self.stop_project(get)
            time.sleep(1)
            self.start_project(get)
        else:
            public.serviceReload()

        return public.return_data(True, '修改项目成功')

    def remove_project(self, get):
        '''
            @name 删除指定AI项目
            @author <2024-01-01>
            @param get<dict_obj>{
                project_name: string<项目名称>
                delete_path: bool<是否删除项目目录> 默认False
            }
            @return dict
                成功: {
                    status: True,
                    msg: string<成功提示信息>,
                    data: null
                }
                失败: {
                    status: False,
                    msg: string<错误信息>,
                    data: null
                }
        '''
        project_find = self.get_project_find(get.project_name)
        if not project_find:
            return public.return_error('指定项目不存在: {}'.format(get.project_name))

        project_path = project_find['path']

        if project_find['project_config'].get('project_mode') == 'dynamic':
            self.stop_project(get)

        self.clear_config(get.project_name)

        public.M('domain').where('pid=?', (project_find['id'],)).delete()
        public.M('sites').where('name=?', (get.project_name,)).delete()

        pid_file = "{}/.aiproject/{}.pid".format(project_path, get.project_name)
        if os.path.exists(pid_file):
            os.remove(pid_file)

        config_path = "{}/.aiproject/ai_config.json".format(project_path)
        if os.path.exists(config_path):
            os.remove(config_path)

        aiproject_dir = "{}/.aiproject".format(project_path)
        if os.path.exists(aiproject_dir) and not os.listdir(aiproject_dir):
            os.rmdir(aiproject_dir)

        delete_path = get.get('delete_path', False)
        if delete_path and os.path.exists(project_path) and project_path.strip() != '/':
            import shutil
            shutil.rmtree(project_path)

        public.WriteLog(self._log_name, '删除AI项目{}'.format(get.project_name))
        return public.return_data(True, '删除项目成功')

    def set_config(self, project_find):
        '''
            @name 设置项目Nginx配置（增量更新域名和端口，保留用户自定义配置）
            @author <2024-01-01>
            @param project_find<dict> 项目信息，包含以下字段:
                id: int<项目ID>
                name: string<项目名称>
                path: string<项目路径>
                project_config: dict|str<项目配置>
            @return bool
                True: 配置成功
                False: 配置失败
        '''
        project_id = project_find['id']
        project_name = project_find['name']
        config_file = "{}/nginx/ai_{}.conf".format(self._vhost_path, project_name)

        all_domains_data = public.M('domain').where('pid=?', (project_id,)).select()
        if not isinstance(all_domains_data, list):
            return False

        domains, ports = set(), set()
        for i in all_domains_data:
            domains.add(i["name"])
            ports.add(str(i["port"]))

        conf = public.readFile(config_file)
        if not conf:
            ai_config = self.read_ai_config(project_name, project_find['path'])
            if ai_config:
                project_config = ai_config
            elif isinstance(project_find['project_config'], str):
                project_config = json.loads(project_find['project_config'])
            else:
                project_config = project_find['project_config']

            project_mode = project_config.get('project_mode', 'dynamic')
            primary_port = project_config.get('primary_port', 80)
            project_path = project_config.get('project_path', project_find['path'])

            if not domains:
                domains = {project_name}

            listen_ipv6 = public.listen_ipv6()
            listen_ports = []
            for port in sorted(ports):
                listen_ports.append("    listen {};".format(port))
                if listen_ipv6:
                    listen_ports.append("    listen [::]:{};".format(port))

            ssl_config = ''
            log_path = self._ai_logs_path
            url = 'http://127.0.0.1:{}'.format(primary_port)
            host = '$host'

            template_file = "{}/template/nginx/ai_http.conf".format(self._vhost_path)
            if not os.path.exists(template_file):
                return False

            config_body = public.readFile(template_file)
            if not config_body:
                return False

            mut_config = {
                "listen_ports": "\n".join(listen_ports),
                "domains": " ".join(domains),
                "site_path": project_path,
                "project_name": project_name,
                "panel_path": self._panel_path,
                "ssl_config": ssl_config,
                "log_path": log_path,
                "url": url,
                "host": host
            }

            config_body = config_body.format(**mut_config)
            public.writeFile(config_file, config_body)

            well_known_file = "/www/server/panel/vhost/nginx/well-known/{}.conf".format(project_name)
            if not os.path.exists(os.path.dirname(well_known_file)):
                os.makedirs(os.path.dirname(well_known_file), 493)
            public.writeFile(well_known_file, '')

            public.serviceReload()
            return True

        rep_server_name = re.compile(r"\s*server_name\s*(.*);", re.M)
        new_conf = rep_server_name.sub("\n    server_name {};".format(" ".join(domains)), conf, 1)

        rep_port = re.compile(r"\s*listen\s+[\[\]:]*(?P<port>[0-9]+).*;[^\n]*\n", re.M)
        listen_ipv6 = public.listen_ipv6()
        last_port_idx = None
        need_remove_port_idx = []
        had_ports = set()
        for tmp_res in rep_port.finditer(new_conf):
            last_port_idx = tmp_res.end()
            if tmp_res.group("port") in ports:
                had_ports.add(tmp_res.group("port"))
            elif tmp_res.group("port") != "443":
                need_remove_port_idx.append((tmp_res.start(), tmp_res.end()))

        if not last_port_idx:
            return False

        ports = ports - had_ports
        if ports:
            listen_add_list = []
            for p in ports:
                tmp = "    listen {};\n".format(p)
                if listen_ipv6:
                    tmp += "    listen [::]:{};\n".format(p)
                listen_add_list.append(tmp)

            new_conf = new_conf[:last_port_idx] + "".join(listen_add_list) + new_conf[last_port_idx:]

        if need_remove_port_idx:
            conf_list = []
            idx = 0
            for start, end in need_remove_port_idx:
                conf_list.append(new_conf[idx:start])
                idx = end
            conf_list.append(new_conf[idx:])
            new_conf = "".join(conf_list)

        public.writeFile(config_file, new_conf)
        public.serviceReload()
        return True

    def clear_config(self, project_name):
        '''
            @name 清理项目Nginx配置
            @author <2024-01-01>
            @param project_name<string> 项目名称
            @return bool
                True: 清理成功
        '''
        config_file = "{}/nginx/ai_{}.conf".format(self._vhost_path, project_name)
        if os.path.exists(config_file):
            os.remove(config_file)

        well_known_file = "/www/server/panel/vhost/nginx/well-known/{}.conf".format(project_name)
        if os.path.exists(well_known_file):
            os.remove(well_known_file)

        public.serviceReload()
        return True

    def project_add_domain(self, get):
        '''
            @name 为AI项目添加域名
            @author <2024-01-01>
            @param get<dict_obj>{
                project_name: string<项目名称>
                domains: list<域名列表>
            }
            @return dict
                成功: {
                    domains: [
                        {
                            name: string<域名>,
                            status: bool<添加状态>,
                            msg: string<提示信息>
                        }
                    ]
                }
                失败: {
                    status: False,
                    msg: string<错误信息>,
                    data: null
                }
        '''
        try:
            if isinstance(get.domains, str):
                domains = json.loads(get.domains)
            else:
                domains = get.domains
        except json.JSONDecodeError:
            return public.return_error('参数错误')
        if not isinstance(domains, list):
            return public.return_error('参数错误')
        project_find = self.get_project_find(get.project_name)
        if not project_find:
            return public.return_error('指定项目不存在')
        project_id = project_find['id']
        check_cloud = False
        flag = False
        res_domains = []
        for domain in domains:
            domain = domain.strip()
            if not domain: continue
            if "[" in domain and "]" in domain:  # IPv6格式特殊处理
                if "]:" in domain:
                    domain_arr = domain.rsplit(":", 1)
                else:
                    domain_arr = [domain]
            else:
                domain_arr = domain.split(':')
            domain_arr[0] = self.check_domain(domain_arr[0])
            if domain_arr[0] is False:
                res_domains.append({"name": domain, "status": False, "msg": '域名格式错误'})
                continue
            if len(domain_arr) == 1:
                domain_arr.append("")
            if domain_arr[1] == "":
                domain_arr[1] = 80
                domain += ':80'
            try:
                if not (0 < int(domain_arr[1]) < 65535):
                    res_domains.append({"name": domain, "status": False, "msg": '域名格式错误'})
                    continue
            except ValueError:
                res_domains.append({"name": domain, "status": False, "msg": '域名格式错误'})
                continue
            if not public.M('domain').where('name=? AND port=? ', (domain_arr[0], domain_arr[1])).count():
                public.M('domain').add('name,pid,port,addtime',
                                       (domain_arr[0], project_id, domain_arr[1], public.getDate()))
                real_d = "{}:{}".format(domain_arr[0], domain_arr[1])
                
                ai_config = self.read_ai_config(get.project_name)
                if ai_config:
                    ai_domains = ai_config.get('domains', [])
                    if not real_d in ai_domains:
                        ai_domains.append(real_d)
                        ai_config['domains'] = ai_domains
                        self.write_ai_config(get.project_name, ai_config)
                
                public.WriteLog(self._log_name, '成功添加域名{}到AI项目{}'.format(domain, get.project_name))
                res_domains.append({"name": domain_arr[0], "status": True, "msg": '添加成功'})
                if not check_cloud:
                    check_cloud = True
                    public.check_domain_cloud(domain_arr[0])
                flag = True
            else:
                public.WriteLog(self._log_name, '添加域名错误，域名{}已存在'.format(domain))
                res_domains.append({"name": domain_arr[0], "status": False, "msg": '添加失败，域名{}已存在'.format(domain)})
        if flag:
            if not self.set_config(project_find=project_find):
                return public.return_error('更新Nginx配置失败')

        return self._ckeck_add_domain(get.project_name, res_domains)

    def project_del_domain(self, get):
        '''
            @name 删除AI项目的域名
            @author <2024-01-01>
            @param get<dict_obj>{
                project_name: string<项目名称>
                domain: string<域名>
            }
            @return dict
                成功: {
                    status: True,
                    msg: string<成功提示信息>,
                    data: null
                }
                失败: {
                    status: False,
                    msg: string<错误信息>,
                    data: null
                }
        '''
        project_find = self.get_project_find(get.project_name)
        if not project_find:
            return public.return_error('指定项目不存在')
        
        if "[" in get.domain and "]" in get.domain:
            if "]:" in get.domain:
                domain_arr = get.domain.rsplit(":", 1)
            else:
                domain_arr = [get.domain, 80]
        else:
            domain_arr = get.domain.rsplit(':', 1)
            if len(domain_arr) == 1:
                domain_arr.append(80)

        project_id = public.M('sites').where('name=?', (get.project_name,)).getField('id')
        
        ai_config = self.read_ai_config(get.project_name)
        if not ai_config:
            return public.return_error('读取项目配置失败')
        
        ai_domains = ai_config.get('domains', [])
        if len(ai_domains) == 1:
            return public.return_error('项目至少需要一个域名')
        
        domain_id = public.M('domain').where('name=? AND port=? AND pid=?', (domain_arr[0], domain_arr[1], project_id)).getField('id')
        if domain_id:
            public.M('domain').where('id=?', (domain_id,)).delete()

        if get.domain in ai_domains:
            ai_domains.remove(get.domain)
        if get.domain + ":80" in ai_domains:
            ai_domains.remove(get.domain + ":80")
        
        ai_config['domains'] = ai_domains
        self.write_ai_config(get.project_name, ai_config)

        if not self.set_config(project_find=project_find):
            return public.return_error('更新Nginx配置失败')

        public.WriteLog(self._log_name, 'AI项目{}删除域名{}'.format(get.project_name, get.domain))
        return public.return_data(True, '删除域名成功')

    def project_remove_domain(self, get):
        '''
            @name 为指定项目删除域名
            @author hwliang<2021-08-09>
            @param get<dict_obj>{
                project_name: string<项目名称>
                domain: string<域名>
            }
            @return dict
        '''
        project_find = self.get_project_find(get.project_name)
        if not project_find:
            return public.return_error('指定项目不存在')
        last_domain = get.domain
        if "[" in get.domain and "]" in get.domain:
            if "]:" in get.domain:
                domain_arr = get.domain.rsplit(":", 1)
            else:
                domain_arr = [get.domain, 80]
        else:
            domain_arr = get.domain.rsplit(':', 1)
            if len(domain_arr) == 1:
                domain_arr.append(80)

        project_id = public.M('sites').where('name=?', (get.project_name,)).getField('id')

        ai_config = self.read_ai_config(get.project_name)
        if not ai_config:
            return public.return_error('读取项目配置失败')

        ai_domains = ai_config.get('domains', [])
        if len(ai_domains) == 1:
            return public.return_error('项目至少需要一个域名')

        domain_id = public.M('domain').where('name=? AND port=? AND pid=?', (domain_arr[0], domain_arr[1], project_id)).getField('id')
        if not domain_id:
            return public.return_error('指定域名不存在')
        public.M('domain').where('id=?', (domain_id,)).delete()

        if get.domain in ai_domains:
            ai_domains.remove(get.domain)
        if get.domain + ":80" in ai_domains:
            ai_domains.remove(get.domain + ":80")

        ai_config['domains'] = ai_domains
        self.write_ai_config(get.project_name, ai_config)

        public.WriteLog(self._log_name, '从项目：{}，删除域名{}'.format(get.project_name, get.domain))
        self.set_config(project_find=project_find)
        return public.return_data(True, '删除域名成功')

    def project_get_domain(self, get):
        '''
            @name 获取指定AI项目的域名列表
            @author <2024-01-01>
            @param get<dict_obj>{
                project_name: string<项目名称>
            }
            @return list
                成功: [
                    {
                        id: int<域名ID>,
                        name: string<域名>,
                        pid: int<项目ID>,
                        port: int<端口>,
                        addtime: string<添加时间>,
                        cn_name: string<中文域名(解码后)>
                    }
                ]
                失败: []
        '''
        project_id = public.M('sites').where('name=?', (get.project_name,)).getField('id')
        if not project_id:
            return public.return_data(False, '站点查询失败')
        domains = public.M('domain').where('pid=?', (project_id,)).order('id desc').select()
        for d in domains:
            d["cn_name"] = self.try_unpunycode(d["name"]) or d["name"]
        return domains

    def get_log_list(self, get):
        '''
            @name 获取AI项目日志文件列表
            @author <2024-01-01>
            @param get<dict_obj>{
                project_name: string<项目名称>
            }
            @return dict|list
                成功: [
                    {
                        name: string<日志分类名称，如"后端服务">,
                        path: string<日志文件完整路径>
                    }
                ]
                失败: {
                    status: False,
                    msg: string<错误信息>,
                    data: null
                }
        '''
        project_find = self.get_project_find(get.project_name)
        if not project_find:
            return public.return_error('指定项目不存在')

        ai_config = self.read_ai_config(get.project_name)
        if not ai_config:
            return public.return_error('读取项目配置失败')

        logs = ai_config.get('logs', {})

        # 动态读取AI配置的所有日志分类
        # logs 可以是一个字典，key为日志分类名称，value为日志文件路径
        # 例如: {"后端日志": "/path/to/backend.log", "前端日志": "/path/to/frontend.log"}
        # 或者是 {"nginx": {"access": "/path/to/access.log", "error": "/path/to/error.log"}}

        result = []

        # 兼容旧格式 (如果还是 access_log/error_log 结构)
        if 'access_log' in logs:
            result.append({
                'name': 'Nginx访问日志',
                'path': logs['access_log']
            })
        if 'error_log' in logs:
            result.append({
                'name': 'Nginx错误日志',
                'path': logs['error_log']
            })

        # 读取新格式 - AI自定义的日志分类
        for log_name, log_path in logs.items():
            # 跳过旧格式的key，避免重复
            if log_name in ['access_log', 'error_log']:
                continue
            
            # 如果value是字典（包含access/error子分类），则展开
            if isinstance(log_path, dict):
                for sub_name, sub_path in log_path.items():
                    result.append({
                        'name': '{}{}'.format(log_name, sub_name),
                        'path': sub_path
                    })
            else:
                # 简单的 key: path 格式
                result.append({
                    'name': log_name,
                    'path': log_path
                })

        return result

    def update_log_config(self, get):
        '''
            @name 更新AI项目日志配置
            @author <2024-01-01>
            @param get<dict_obj>{
                project_name: string<项目名称>
                log_name: string<日志分类名称>
                log_path: string<日志文件路径>
            }
            @return dict
                成功: {
                    status: True,
                    msg: string<成功提示信息>,
                    data: null
                }
                失败: {
                    status: False,
                    msg: string<错误信息>,
                    data: null
                }
        '''
        project_find = self.get_project_find(get.project_name)
        if not project_find:
            return public.return_error('指定项目不存在')

        ai_config = self.read_ai_config(get.project_name)
        if not ai_config:
            return public.return_error('读取项目配置失败')

        if 'logs' not in ai_config:
            ai_config['logs'] = {}

        # AI添加或修改日志配置
        ai_config['logs'][get.log_name] = get.log_path

        if not self.write_ai_config(get.project_name, ai_config):
            return public.return_error('写入配置失败')

        public.WriteLog(self._log_name, 'AI项目{}添加日志配置{}'.format(get.project_name, get.log_name))
        return public.return_data(True, '日志配置添加成功')

    def remove_log_config(self, get):
        '''
            @name 删除AI项目日志配置
            @author <2024-01-01>
            @param get<dict_obj>{
                project_name: string<项目名称>
                log_name: string<日志分类名称>
            }
            @return dict
                成功: {
                    status: True,
                    msg: string<成功提示信息>,
                    data: null
                }
                失败: {
                    status: False,
                    msg: string<错误信息>,
                    data: null
                }
        '''
        project_find = self.get_project_find(get.project_name)
        if not project_find:
            return public.return_error('指定项目不存在')

        ai_config = self.read_ai_config(get.project_name)
        if not ai_config:
            return public.return_error('读取项目配置失败')

        if 'logs' in ai_config and get.log_name in ai_config['logs']:
            del ai_config['logs'][get.log_name]
            if not self.write_ai_config(get.project_name, ai_config):
                return public.return_error('写入配置失败')

            public.WriteLog(self._log_name, 'AI项目{}删除日志配置{}'.format(get.project_name, get.log_name))
            return public.return_data(True, '日志配置删除成功')
        else:
            return public.return_error('日志配置不存在')

    def get_log_content(self, get):
        '''
            @name 获取AI项目日志内容
            @author <2024-01-01>
            @param get<dict_obj>{
                project_name: string<项目名称>
                log_path: string<日志文件路径>
                lines: int<获取最后多少行> 默认100
            }
            @return dict|string
                成功: string<日志内容>
                失败: {
                    status: False,
                    msg: string<错误信息>,
                    data: null
                }
        '''
        project_find = self.get_project_find(get.project_name)
        if not project_find:
            return public.return_error('指定项目不存在')

        log_path = get.get('log_path', '')
        if not log_path:
            return public.return_error('请指定日志路径')

        if not os.path.exists(log_path):
            return public.return_error('日志文件不存在')

        lines = int(get.get('lines', 100))
        content = public.GetNumLines(log_path, lines)

        return content

    def check_port_is_used(self, port):
        '''
            @name 检查端口是否被占用
            @author <2024-01-01>
            @param port: int<端口号>
            @return bool
                True: 端口已被占用
                False: 端口可用
        '''
        if not isinstance(port, int):
            port = int(port)
        if port == 0:
            return False

        project_list = public.M('sites').where('status=? AND project_type=?', (1, 'AI')).field(
            'name,path').select()

        for project_find in project_list:
            ai_config = self.read_ai_config(project_find['name'])
            if not ai_config or 'ports' not in ai_config:
                continue
            try:
                if port in self._get_port_numbers(ai_config['ports']):
                    return True
            except:
                continue

        return public.check_tcp('127.0.0.1', port)

    def get_project_list(self, get):
        '''
            @name 获取AI项目列表
            @author <2024-01-01>
            @param get<dict_obj>{
                p: int<当前页码> 默认1
                limit: int<每页条数> 默认20
                callback: string<回调函数名>
                order: string<排序方式> 默认"id desc"
                search: string<搜索关键词> 可选
                type_id: int<分类ID> 可选
            }
            @return dict
                成功: {
                    page: int<当前页码>,
                    size: int<每页条数>,        
                    count: int<总条数>,
                    data: [
                        {
                            id: int<项目ID>,
                            name: string<项目名称>,
                            path: string<项目路径>,
                            ps: string<项目备注>,
                            status: int<项目状态 1:启用 0:停用>,
                            project_config: dict<项目配置信息>,
                            addtime: string<添加时间>,
                            run: bool<运行状态 True:运行中 False:已停止>
                        }
                    ]
                }
        '''

        if not 'p' in get:
            get.p = 1
        if not 'limit' in get:
            get.limit = 20
        if not 'callback' in get:
            get.callback = ''
        if not 'order' in get:
            get.order = 'id desc'

        type_id = None
        if "type_id" in get:
            try:
                type_id = int(get.type_id)
            except:
                type_id = None

        if 'search' in get:
            get.project_name = get.search.strip()
            search = "%{}%".format(get.project_name)
            if type_id is None:
                count = public.M('sites').where('project_type=? AND (name LIKE ? OR ps LIKE ?)',('AI', search, search)).count()
                data = public.get_page(count, int(get.p), int(get.limit), get.callback)
                data['data'] = public.M('sites').where('project_type=? AND (name LIKE ? OR ps LIKE ?)',('AI', search, search)).limit(data['shift'] + ',' + data['row']).order(get.order).select()
            else:
                count = public.M('sites').where('project_type=? AND (name LIKE ? OR ps LIKE ?) AND type_id = ?',('AI', search, search, type_id)).count()
                data = public.get_page(count, int(get.p), int(get.limit), get.callback)
                data['data'] = public.M('sites').where('project_type=? AND (name LIKE ? OR ps LIKE ?) AND type_id = ?',('AI', search, search, type_id)).limit(data['shift'] + ',' + data['row']).order(get.order).select()
        else:
            if type_id is None:
                count = public.M('sites').where('project_type=?', 'AI').count()
                data = public.get_page(count, int(get.p), int(get.limit), get.callback)
                data['data'] = public.M('sites').where('project_type=?', 'AI').limit(data['shift'] + ',' + data['row']).order(get.order).select()
            else:
                count = public.M('sites').where('project_type=? AND type_id = ?',('AI', type_id)).count()
                data = public.get_page(count, int(get.p), int(get.limit), get.callback)
                data['data'] = public.M('sites').where('project_type=? AND type_id = ?',('AI', type_id)).limit(data['shift'] + ',' + data['row']).order(get.order).select()

        if isinstance(data["data"], str) and data["data"].startswith("error"):
            raise public.PanelError("数据库查询错误：" + data["data"])

        for i in range(len(data['data'])):
            data['data'][i] = self.get_project_stat(data['data'][i])

        names = [d['name'] for d in data['data']]
        waf = self.get_waf_status_all(names)
        site_netinfo = self.new_get_site_netinfo(names)
        net = {i: self.get_site_net(site_netinfo, i) for i in names}
        for i in range(len(data['data'])):
            name = data['data'][i]['name']
            data['data'][i]['waf'] = waf.get(name, {})
            data['data'][i]['net'] = net.get(name, {})
        return data

    @staticmethod
    def free_get_site_netinfo(names=None):
        from mod.base.free_site_total import SiteTotalData
        return SiteTotalData().get_total_day_data(names)

    def get_waf_status_all(self, names):
        """
        @name 获取waf状态
        """
        data = {}
        try:
            path = '/www/server/btwaf/site.json'
            res = json.loads(public.readFile(path))
            config_path = '/www/server/btwaf/config.json'
            open_status = json.loads(public.readFile(config_path))["open"]
            if not open_status:
                return data
            for site in res:
                data[site] = {}
                data[site]['status'] = True
                if 'open' in res[site]:
                    data[site]['status'] = res[site]['open']
        except:
            return data
        data = {i: data[i] if i in data else {} for i in names}
        return data

    def get_site_net(self, info, siteName):
        """
        @name 获取网站流量
        @param siteName<string> 网站名称
        @return dict
        """
        try:
            if info['status']: info = info['data']

            if siteName in info:
                return info[siteName]
        except:
            pass
        return {}

    def get_site_netinfo(self):
        """
        @name 获取网站流量
        """
        try:
            import PluginLoader
            args = public.dict_obj()
            args.model_index = 'panel'
            res = PluginLoader.module_run("total", "get_site_traffic", args)

            return res
        except:
            pass
        return {}

    def new_get_site_netinfo(self, names=None):
        """
        @name 获取重构版监控报表网站流量
        @param names<list> 获取的网站列表
        """
        if names is None:
            names = []
        try:
            import PluginLoader
            args = public.dict_obj()
            args.names = names
            args.model_index = 'panel'
            res = PluginLoader.module_run("total", "new_get_site_traffic", args)
            if res and res.get('data', {}) and any(i["one_day_total_flow"] for i in res['data'].values()):
                return  res
            return self.free_get_site_netinfo(names)
        except:
            # public.print_error()
            pass
        return self.free_get_site_netinfo(names)

    def get_ai_config(self, get):
        '''
            @name 获取AI项目配置文件
            @author <2024-01-01>
            @param get<dict_obj>{
                project_name: string<项目名称>
            }
            @return dict
                成功: {
                    status: True,
                    msg: string<成功提示信息>,
                    data: {
                        id: int<项目ID>,
                        name: string<项目名称>,
                        path: string<项目路径>,
                        ps: string<项目备注>,
                        status: int<项目状态 1:运行中 0:已停止>,
                        project_type: string<项目类型 AI>,
                        project_config: dict<项目配置信息>,
                        addtime: string<添加时间>,
                        run: bool<项目运行状态 True:运行中 False:已停止>,
                        listen: list<监听的端口列表>,
                        listen_ok: bool<端口监听是否正常>,
                        ssl: dict|int<SSL证书信息>,
                        ai_config: dict<AI项目完整配置信息>,
                        nginx_config_file: string<Nginx配置文件路径>,
                        nginx_config: string<Nginx配置文件内容>
                    }
                }
                失败: {
                    status: False,
                    msg: string<错误信息>,
                    data: null
                }
        '''
        project_find = self.get_project_find(get.project_name)
        if not project_find:
            return public.return_error('指定项目不存在: {}'.format(get.project_name))

        ai_config = self.read_ai_config(get.project_name)
        if not ai_config:
            return public.return_error('读取项目配置失败')

        project_stat = self.get_project_stat(project_find)

        nginx_config_file = "{}/nginx/ai_{}.conf".format(self._vhost_path, get.project_name)
        if os.path.exists(nginx_config_file):
            nginx_config = public.readFile(nginx_config_file)
        else:
            nginx_config = ''

        return public.return_data(True, data={
            'id': project_stat.get('id'),
            'name': project_stat.get('name'),
            'path': project_stat.get('path'),
            'ps': project_stat.get('ps'),
            'status': project_stat.get('status'),
            'project_type': project_stat.get('project_type'),
            'project_config': project_stat.get('project_config'),
            'addtime': project_stat.get('addtime'),
            'run': project_stat.get('run'),
            'listen': project_stat.get('listen'),
            'listen_ok': project_stat.get('listen_ok'),
            'ssl': project_stat.get('ssl'),
            'ai_config': ai_config,
            'nginx_config_file': nginx_config_file,
            'nginx_config': nginx_config
        })

    def update_ai_config(self, get):
        '''
            @name 更新AI项目配置文件（直接修改文件，无需重启）
            @author <2024-01-01>
            @param get<dict_obj>{
                project_name: string<项目名称>
                config: dict|str<新的配置信息，支持JSON字符串或字典>
            }
            @return dict
                成功: {
                    status: True,
                    msg: string<成功提示信息>,
                    data: null
                }
                失败: {
                    status: False,
                    msg: string<错误信息>,
                    data: null
                }
        '''
        project_find = self.get_project_find(get.project_name)
        if not project_find:
            return public.return_error('指定项目不存在: {}'.format(get.project_name))

        config = get.config
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except:
                return public.return_error('配置格式错误，请提供有效的JSON')

        if not isinstance(config, dict):
            return public.return_error('配置格式错误，请提供有效的JSON对象')

        if not self.write_ai_config(get.project_name, config):
            return public.return_error('写入配置文件失败')

        public.WriteLog(self._log_name, '更新AI项目配置{}'.format(get.project_name))
        return public.return_data(True, '配置更新成功')

    def _ckeck_add_domain(self, site_name, domains):
        '''
            @name 检查添加的域名是否在SSL证书范围内
            @author <2024-01-01>
            @param site_name<string> 项目名称
            @param domains<list> 域名添加结果列表
            @return dict
        '''
        from panelSite import panelSite
        ssl_data = panelSite().GetSSL(type("get", tuple(), {"siteName": site_name})())
        if not ssl_data["status"] or not ssl_data.get("cert_data", {}).get("dns", None):
            return {"domains": domains}
        domain_rep = []
        for i in ssl_data["cert_data"]["dns"]:
            if i.startswith("*"):
                _rep = "^[^\.]+\." + i[2:].replace(".", "\.")
            else:
                _rep = "^" + i.replace(".", "\.")
            domain_rep.append(_rep)
        no_ssl = []
        for domain in domains:
            if not domain["status"]: continue
            for _rep in domain_rep:
                if re.search(_rep, domain["name"]):
                    break
            else:
                no_ssl.append(domain["name"])
        if no_ssl:
            return {
                "domains": domains,
                "not_ssl": no_ssl,
                "tip": "本站点已启用SSL证书,但本次添加的域名：{}，无法匹配当前证书，如有需求，请重新申请证书。".format(str(no_ssl))
            }
        return {"domains": domains}
