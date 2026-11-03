"""离线测试的网络护栏：除本机回环地址外，任何 DNS 查询与连接都会抛 NetworkBlocked。

install() 由 tests/test_offline.py 在导入时调用（其他测试模块都先导入它），并通过 CHILD_ENV 的 PYTHONPATH
（tests/childguard/sitecustomize.py）装进测试启动的子进程。NetworkBlocked 继承 BaseException：脚本里
"单个请求失败不影响其他请求" 的 except Exception 拦不住它，HTTP 客户端也不会把它当作网络错误重试，测试会直接报错。
设置 NP_LIVE=1 时不安装（只用于 tests/test_live_contract.py 这类明确要联网的测试）。
"""
import ipaddress
import os
import socket

PROXY_VARS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")
_LOCAL_NAMES = {"localhost", "localhost.localdomain", "ip6-localhost"}


class NetworkBlocked(BaseException):
    """离线测试试图访问网络。"""


def live():
    return os.environ.get("NP_LIVE") == "1"


def _is_local(host):
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    if not isinstance(host, str):
        return False
    host = host.strip("[]").split("%")[0]
    if host.lower() in _LOCAL_NAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _blocked(what):
    return NetworkBlocked(f"offline tests may not use the network: {what!r} (live tests need NP_LIVE=1)")


def install():
    """装上护栏（重复调用无害）。返回是否装上。"""
    if live() or getattr(socket, "_np_netguard", False):
        return False
    for var in PROXY_VARS:          # 不经代理：否则连向本机代理的连接会被放行，再由代理转发到外网
        os.environ.pop(var, None)
    os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost"
    real_connect, real_connect_ex, real_getaddrinfo = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo
    unix = getattr(socket, "AF_UNIX", None)

    def check(sock, address):
        if unix is not None and sock.family == unix:
            return
        host = address[0] if isinstance(address, tuple) else address
        if not _is_local(host):
            raise _blocked(address)

    def connect(self, address):
        check(self, address)
        return real_connect(self, address)

    def connect_ex(self, address):
        check(self, address)
        return real_connect_ex(self, address)

    def getaddrinfo(host, *args, **kwargs):
        if host is not None and not _is_local(host):
            raise _blocked(host)
        return real_getaddrinfo(host, *args, **kwargs)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
    socket.getaddrinfo = getaddrinfo
    socket._np_netguard = True
    return True
