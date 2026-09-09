#!/usr/bin/python
# coding: utf-8
import os
import re
import sys

os.chdir('/www/server/panel')
sys.path.append('class/')
import public

_title = 'CVE-2026-42945 Nginx重写引擎漏洞检测'
_version = 1.0
_ps = '检测Nginx版本是否存在CVE-2026-42945'
_level = 2
_date = '2026-05-15'
_ignore = os.path.exists("data/warning/ignore/sw_nginx_cve_2026_42945.pl")
_tips = [
    '查看当前版本：nginx -v',
    '解决方案：前往【软件商店】，将Nginx升级到1.30.1或更高版本',
    '升级后检查配置：nginx -t'
]
_help = ''
_remind = '该漏洞存在于Nginx重写引擎中，涉及rewrite捕获组、set字面问号以及继承重写上下文的链式if/rewrite交互。'

VULNERABLE_MIN_VERSION = (0, 6, 27)
FIXED_STABLE_VERSION = (1, 30, 1)
FIXED_MAINLINE_VERSION = (1, 31, 0)


def _parse_nginx_version(output):
    match = re.search(r'nginx/(\d+(?:\.\d+){1,3})', output or '')
    if not match:
        return None
    return _version_to_tuple(match.group(1))


def _version_to_tuple(version):
    parts = []
    for item in version.split('.'):
        try:
            parts.append(int(item))
        except:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:4])


def _is_vulnerable_version(version):
    if not version:
        return False
    if version < VULNERABLE_MIN_VERSION:
        return False
    if version >= FIXED_MAINLINE_VERSION:
        return False
    if version >= FIXED_STABLE_VERSION and version < FIXED_MAINLINE_VERSION:
        return False
    return True


def _get_nginx_version():
    nginx_bin = '/www/server/nginx/sbin/nginx'
    commands = []
    if os.path.exists(nginx_bin):
        commands.append('{} -v 2>&1'.format(nginx_bin))
    commands.append('nginx -v 2>&1')
    for command in commands:
        out, err = public.ExecShell(command)
        version = _parse_nginx_version('{}\n{}'.format(out or '', err or ''))
        if version:
            return version, '.'.join([str(i) for i in version[:3]])
    return None, ''


def _has_suspicious_rewrite_config():
    nginx_bin = '/www/server/nginx/sbin/nginx'
    if not os.path.exists(nginx_bin):
        return False
    try:
        out, err = public.ExecShell('{} -T 2>/dev/null'.format(nginx_bin))
        conf = out or ''
        if not conf:
            return False
        return bool(re.search(r'(?mi)(^|[;{\n]\s*)(?!#)\s*rewrite\s+[^;]*\$\d+', conf))
    except:
        return False


def check_run():
    try:
        version, version_text = _get_nginx_version()
        if not version:
            return True, '未检测到Nginx版本信息'
        if _is_vulnerable_version(version):
            msg = '当前Nginx版本【{}】受CVE-2026-42945影响，请升级到1.30.1或更高版本'.format(version_text)
            if _has_suspicious_rewrite_config():
                msg += '；检测到疑似rewrite捕获组配置，请优先处理'
            return False, msg
        return True, '当前Nginx版本【{}】无风险'.format(version_text)
    except:
        return True, '检测异常，默认无风险'
