#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
宝塔面板防火墙管理脚本
封装防火墙启停、Ping开关、状态查看、端口规则管理等功能

使用方法:
    1. 命令行调用:
        python firewall_ops.py start
        python firewall_ops.py stop
        python firewall_ops.py ping_enable
        python firewall_ops.py ping_disable
        python firewall_ops.py status
        python firewall_ops.py port_list --chain INPUT
        python firewall_ops.py port_add --port 80 --protocol tcp --address all --strategy accept --brief "Web服务"
        python firewall_ops.py port_remove --port 80 --protocol tcp --address all --strategy accept

    2. Python代码导入:
        from firewall_ops import BtPanelFirewall
        fw = BtPanelFirewall()
        result = fw.start_firewall()
        result = fw.stop_firewall()
        result = fw.enable_ping()
        result = fw.disable_ping()
        info = fw.get_status()
        rules = fw.list_port_rules(chain='INPUT')
        result = fw.add_port_rule(port='80', protocol='tcp', address='all', strategy='accept', brief='Web服务')
        result = fw.remove_port_rule(port='80', protocol='tcp', address='all', strategy='accept')
"""

import os
import sys
import argparse
import json

os.chdir('/www/server/panel/')
sys.path.insert(0, 'class/')
sys.path.insert(0, '/www/server/panel/')

import public
from firewallModel.comModel import main as FirewallModel
from firewalls import firewalls


class BtPanelFirewall:

    def __init__(self):
        self.model = FirewallModel()
        self.fw = firewalls()

    def _clean_cache(self):
        get_obj = public.to_dict_obj({})
        self.model.clean_cache(get_obj)

    def start_firewall(self):
        """
        启动防火墙

        返回:
            dict: {'status': True/False, 'msg': '消息'}
        """
        get_obj = public.to_dict_obj({'status': '1', 'ports': ''})
        result = self.model.set_status(get_obj)
        if result.get('status'):
            self._clean_cache()
            return {'status': True, 'msg': 'SUCCESS'}
        return {'status': False, 'msg': result.get('msg', '启动失败')}

    def stop_firewall(self):
        """
        停止防火墙

        返回:
            dict: {'status': True/False, 'msg': '消息'}
        """
        get_obj = public.to_dict_obj({'status': '0'})
        result = self.model.set_status(get_obj)
        if result.get('status'):
            self._clean_cache()
            return {'status': True, 'msg': 'SUCCESS'}
        return {'status': False, 'msg': result.get('msg', '停止失败')}

    def enable_ping(self):
        """
        启用Ping协议（允许ICMP响应）

        返回:
            dict: {'status': True/False, 'msg': '消息'}
        """
        get_obj = public.to_dict_obj({'status': '1'})
        result = self.fw.SetPing(get_obj)
        if result.get('status'):
            self._clean_cache()
            return {'status': True, 'msg': 'SUCCESS'}
        return {'status': False, 'msg': result.get('msg', '设置失败')}

    def disable_ping(self):
        """
        禁用Ping协议（禁Ping）

        返回:
            dict: {'status': True/False, 'msg': '消息'}
        """
        get_obj = public.to_dict_obj({'status': '0'})
        result = self.fw.SetPing(get_obj)
        if result.get('status'):
            self._clean_cache()
            return {'status': True, 'msg': 'SUCCESS'}
        return {'status': False, 'msg': result.get('msg', '设置失败')}

    def get_status(self):
        """
        获取防火墙状态信息

        返回:
            dict: 包含 running, init_status, type, port_count, ping_enabled, status_text
        """
        get_obj = public.to_dict_obj({})
        info = self.model.get_firewall_info(get_obj)
        status = self.model.get_status(get_obj)

        firewall_running = status.get('status', False)
        init_status = status.get('init_status', True)
        firewall_type = info.get('type', 'iptables')
        port_count = info.get('port', 0)
        ping_enabled = info.get('ping', True)

        status_text_map = {True: '已启动', False: '已停止'}
        ping_text_map = {True: '已启用', False: '已禁用'}
        status_text = '防火墙状态：{}\n防火墙类型：{}\n端口规则条数：{}\nPing协议：{}'.format(
            status_text_map.get(firewall_running, '未知'),
            firewall_type,
            port_count,
            ping_text_map.get(ping_enabled, '未知')
        )

        return {
            'running': firewall_running,
            'init_status': init_status,
            'type': firewall_type,
            'port_count': port_count,
            'ping_enabled': ping_enabled,
            'status_text': status_text
        }

    def list_port_rules(self, chain='ALL', query='', page=1, page_size=20):
        """
        查看端口规则列表

        参数:
            chain (str): 链类型 INPUT/OUTPUT/ALL
            query (str): 搜索关键词
            page (int): 页码
            page_size (int): 每页条数

        返回:
            dict: 分页数据
        """
        get_obj = public.to_dict_obj({
            'chain': str(chain),
            'query': str(query),
            'p': str(page),
            'row': str(page_size),
            'export': '0'
        })
        return self.model.port_rules_list(get_obj)

    def add_port_rule(self, port, protocol='tcp', address='all', strategy='accept',
                       chain='INPUT', brief='', domain=''):
        """
        添加端口规则

        参数:
            port (str): 端口号，如 '80', '3306', '8080-8090'
            protocol (str): tcp / udp / tcp/udp
            address (str): 来源IP，'all' 或具体IP
            strategy (str): accept / drop
            chain (str): INPUT / OUTPUT
            brief (str): 备注说明
            domain (str): 域名

        返回:
            dict: {'status': True/False, 'msg': '消息'}
        """
        get_obj = public.to_dict_obj({
            'operation': 'add',
            'protocol': str(protocol),
            'address': str(address),
            'port': str(port),
            'strategy': str(strategy),
            'chain': str(chain),
            'reload': '1',
            'brief': str(brief),
            'domain': str(domain)
        })
        result = self.model.set_port_rule(get_obj)
        if result.get('status'):
            self._clean_cache()
            return {'status': True, 'msg': 'SUCCESS'}
        return {'status': False, 'msg': result.get('msg', '添加失败')}

    def remove_port_rule(self, port, protocol='tcp', address='all', strategy='accept',
                          chain='INPUT', brief='', domain=''):
        """
        删除端口规则

        参数:
            port (str): 端口号
            protocol (str): tcp / udp / tcp/udp
            address (str): 来源IP
            strategy (str): accept / drop
            chain (str): INPUT / OUTPUT
            brief (str): 备注
            domain (str): 域名

        返回:
            dict: {'status': True/False, 'msg': '消息'}
        """
        brief_val = str(brief) if brief else 'undefined'
        get_obj = public.to_dict_obj({
            'operation': 'remove',
            'protocol': str(protocol),
            'address': str(address),
            'port': str(port),
            'strategy': str(strategy),
            'chain': str(chain),
            'reload': '1',
            'brief': brief_val,
            'domain': str(domain)
        })
        result = self.model.set_port_rule(get_obj)
        if result.get('status'):
            self._clean_cache()
            return {'status': True, 'msg': 'SUCCESS'}
        return {'status': False, 'msg': result.get('msg', '删除失败')}


def main():
    parser = argparse.ArgumentParser(description='宝塔面板防火墙管理脚本')
    subparsers = parser.add_subparsers(dest='action', help='操作类型')

    subparsers.add_parser('start', help='启动防火墙')
    subparsers.add_parser('stop', help='停止防火墙')
    subparsers.add_parser('ping_enable', help='启用Ping协议')
    subparsers.add_parser('ping_disable', help='禁用Ping协议（禁Ping）')
    subparsers.add_parser('status', help='查看防火墙状态信息')

    list_parser = subparsers.add_parser('port_list', help='查看端口规则列表')
    list_parser.add_argument('--chain', default='ALL', help='链类型: INPUT/OUTPUT/ALL (默认ALL)')
    list_parser.add_argument('--query', default='', help='搜索关键词')
    list_parser.add_argument('--page', default=1, type=int, help='页码')
    list_parser.add_argument('--page_size', default=20, type=int, help='每页条数')

    add_parser = subparsers.add_parser('port_add', help='添加端口规则')
    add_parser.add_argument('--port', required=True, help='端口号 (如 80, 3306, 8080-8090)')
    add_parser.add_argument('--protocol', default='tcp', help='协议: tcp/udp/tcp-udp (默认tcp)')
    add_parser.add_argument('--address', default='all', help='来源IP (默认all)')
    add_parser.add_argument('--strategy', default='accept', help='策略: accept/drop (默认accept)')
    add_parser.add_argument('--chain', default='INPUT', help='链类型 (默认INPUT)')
    add_parser.add_argument('--brief', default='', help='备注说明')
    add_parser.add_argument('--domain', default='', help='域名')

    del_parser = subparsers.add_parser('port_remove', help='删除端口规则')
    del_parser.add_argument('--port', required=True, help='端口号')
    del_parser.add_argument('--protocol', default='tcp', help='协议: tcp/udp/tcp-udp (默认tcp)')
    del_parser.add_argument('--address', default='all', help='来源IP (默认all)')
    del_parser.add_argument('--strategy', default='accept', help='策略 (默认accept)')
    del_parser.add_argument('--chain', default='INPUT', help='链类型 (默认INPUT)')
    del_parser.add_argument('--brief', default='', help='备注')
    del_parser.add_argument('--domain', default='', help='域名')

    args = parser.parse_args()

    if not args.action:
        parser.print_help()
        sys.exit(1)

    fw_ops = BtPanelFirewall()

    if args.action == 'start':
        result = fw_ops.start_firewall()
    elif args.action == 'stop':
        result = fw_ops.stop_firewall()
    elif args.action == 'ping_enable':
        result = fw_ops.enable_ping()
    elif args.action == 'ping_disable':
        result = fw_ops.disable_ping()
    elif args.action == 'status':
        info = fw_ops.get_status()
        print(info['status_text'])
        sys.exit(0)
    elif args.action == 'port_list':
        rules = fw_ops.list_port_rules(
            chain=args.chain,
            query=args.query,
            page=args.page,
            page_size=args.page_size
        )
        print(json.dumps(rules, ensure_ascii=False, indent=2))
        sys.exit(0)
    elif args.action == 'port_add':
        result = fw_ops.add_port_rule(
            port=args.port,
            protocol=args.protocol,
            address=args.address,
            strategy=args.strategy,
            chain=args.chain,
            brief=args.brief,
            domain=args.domain
        )
    elif args.action == 'port_remove':
        result = fw_ops.remove_port_rule(
            port=args.port,
            protocol=args.protocol,
            address=args.address,
            strategy=args.strategy,
            chain=args.chain,
            brief=args.brief,
            domain=args.domain
        )
    else:
        parser.print_help()
        sys.exit(1)

    if result.get('status'):
        print('SUCCESS: ' + result.get('msg'))
        sys.exit(0)
    else:
        print('ERROR: ' + result.get('msg'))
        sys.exit(1)


if __name__ == '__main__':
    main()
