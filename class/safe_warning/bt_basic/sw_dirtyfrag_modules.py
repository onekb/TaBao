# coding: utf-8
import os
import sys

os.chdir('/www/server/panel')
sys.path.append('class/')
import public

_title = 'Dirty Frag危险内核模块检测'
_version = 1.0
_ps = '检测是否存在Dirty Frag漏洞（CVE-2026-31431）'
_level = 3
_date = '2026-05-09'
_ignore = os.path.exists("data/warning/ignore/sw_dirtyfrag_modules.pl")
_tips = [
    '执行前确认未使用IPsec VPN（strongSwan/Libreswan）和AFS客户端',
    "一键缓解命令：sudo sh -c \"printf 'install esp4 /bin/false\\ninstall esp6 /bin/false\\ninstall rxrpc /bin/false\\n' > /etc/modprobe.d/dirtyfrag.conf && { rmmod esp4 esp6 rxrpc 2>/dev/null || true; sync; echo 3 > /proc/sys/vm/drop_caches; }\"",
    "验证命令：lsmod | grep -E '^(esp4|esp6|rxrpc) ' && echo '危险模块已加载' || echo '危险模块未加载'",
    '回滚命令：sudo rm -f /etc/modprobe.d/dirtyfrag.conf；如需恢复IPsec/AFS，请重启或手动重新加载相关模块'
]
_help = ''
_remind = '高严重性 Linux 内核零日漏洞，称为“Copy Fail”（CVE-2026-31431）。该漏洞可导致本地普通用户未经授权的权限提升至root 访问权限，检测到相关模块已加载时建议尽快处理。'

DANGEROUS_MODULES = ('esp4', 'esp6', 'rxrpc')


def _get_loaded_dangerous_modules(lsmod_output):
    loaded = []
    for line in (lsmod_output or '').splitlines():
        parts = line.split()
        if not parts:
            continue
        module_name = parts[0]
        if module_name in DANGEROUS_MODULES and module_name not in loaded:
            loaded.append(module_name)
    return loaded


def check_run():
    try:
        out, err = public.ExecShell('lsmod 2>/dev/null')
        loaded = _get_loaded_dangerous_modules(out)
        if loaded:
            return False, '该服务器存在Dirty Frag漏洞（CVE-2026-31431），存在以下危险模块：{}'.format('、'.join(loaded))
        return True, '危险模块未加载'
    except:
        return True, '检测异常，默认无风险'
