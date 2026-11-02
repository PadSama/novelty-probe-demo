"""统一的 HTTP 客户端（标准库 urllib）。search / authors / enrich / snowball / verify 都经由这里访问网络。

- 模式（环境变量 NP_HTTP_MODE 或构造参数）：
    live    每次都请求网络，不读缓存；成功响应仍写入缓存目录（供 cache 模式与录制件使用）
    cache   先查缓存（按 TTL），未命中或过期再请求；网络失败时若有过期条目则返回它并标记 stale
    record  请求网络并把每次交互追加到录制件（供测试回放）
    replay  只从录制件取，禁网；没有对应条目则抛 ReplayMiss
- 按主机限速（相邻请求的最小间隔，每次重试也算一次），读 Retry-After；退避 = 基数 × 2^(n+1)，上限封顶，
  等抖动（一半固定 + 一半随机，避免紧挨着重试又避免 0 秒）；Retry-After 超过上限或 OpenAlex 报 "Insufficient budget"
  时不重试（BudgetExhausted）；连续 429 达到阈值时熔断（CircuitOpen）。
- 跟随跳转时记录每一跳；https → http 的跳转改用 https（Emerald、IEEE 的 DOI 登记的是 http:// 地址）。
- 错误分类：ClientError（4xx，不重试；404 为 NotFound）、RateLimited / BudgetExhausted、ServerError（5xx，重试）、
  NetworkError（超时、连接重置，重试）、BlockedByPolicy（代理拒绝 CONNECT：网络策略，不重试）、ContentError（2xx 但不是 JSON）。
  str(e) 以 "HTTP <状态码>: <摘要>" 开头，摘要取 JSON 的 message / error 字段，HTML 正文只取去标签后的前 200 字。
- 记录 OpenAlex 的额度头（X-Ratelimit-*）与 Crossref 的限速头，stats() 汇总到各脚本输出的 meta.http。
- 密钥只放请求头（OPENALEX_API_KEY → Authorization: Bearer；S2_API_KEY → x-api-key），不写入缓存或日志。
"""
import hashlib
import html
import json
import os
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from . import __version__
from .cache import Cassette, ResponseStore, cache_key, decode_body, make_entry
from .paths import PACKAGE_ROOT

MODES = ("live", "cache", "record", "replay")
DEFAULT_USER_AGENT = f"novelty-probe/{__version__} (+https://github.com/PadSama/novelty-probe-demo)"
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


# ---------- 错误 ----------

class HttpError(RuntimeError):
    def __init__(self, detail, *, status=None, url=None, attempts=1, retry_after=None, chain=None):
        self.detail, self.status, self.url, self.attempts, self.retry_after = detail, status, url, attempts, retry_after
        self.chain = list(chain or [])   # 出错前已跟随的跳转
        super().__init__(f"HTTP {status}: {detail}" if status else detail)


class ClientError(HttpError):
    """4xx（除 429）：请求本身的问题，不重试。"""


class NotFound(ClientError):
    pass


class RateLimited(HttpError):
    pass


class BudgetExhausted(RateLimited):
    """服务端要求等待超过上限，或 OpenAlex 当日额度用完：不重试。"""


class CircuitOpen(RateLimited):
    """连续 429 过多，熔断。"""


class ServerError(HttpError):
    pass


class NetworkError(HttpError):
    pass


class BlockedByPolicy(NetworkError):
    """代理拒绝建立连接（本环境的网络策略不允许该域名）。"""


class ContentError(HttpError):
    """2xx 但正文不是预期的格式。"""


class ReplayMiss(HttpError):
    pass


# ---------- 策略 ----------

@dataclass
class HostPolicy:
    min_interval_s: float = 0.0        # 相邻两次请求（含重试）的最小间隔
    max_attempts: int = 6
    backoff_base_s: float = 1.0        # 第 n 次重试前等待 base × 2^(n+1)（n 从 0 起）→ 2, 4, 8 …
    backoff_cap_s: float = 60.0
    retry_after_cap_s: float = 60.0    # Retry-After 超过它 → BudgetExhausted
    breaker_consecutive: int = 10      # 连续这么多次 429 → CircuitOpen
    ttl_s: int = 7 * 86400
    auth_env: str = ""                 # 存放密钥的环境变量名
    auth_header: str = ""              # 密钥放进哪个请求头
    auth_format: str = "{key}"
    budget_substrings: tuple = ("Insufficient budget",)


POLICIES = {
    "api.openalex.org": HostPolicy(min_interval_s=0.2, auth_env="OPENALEX_API_KEY", auth_header="Authorization",
                                   auth_format="Bearer {key}"),
    "api.semanticscholar.org": HostPolicy(min_interval_s=1.1, max_attempts=8, backoff_base_s=1.0, backoff_cap_s=20.0,
                                          breaker_consecutive=12, auth_env="S2_API_KEY", auth_header="x-api-key"),
    "api.crossref.org": HostPolicy(min_interval_s=0.35, ttl_s=30 * 86400),
    "doi.org": HostPolicy(min_interval_s=1.0, ttl_s=86400),
}
DEFAULT_POLICY = HostPolicy()


# ---------- 响应 ----------

@dataclass
class Response:
    status: int
    headers: dict
    body: bytes
    url: str
    final_url: str
    chain: list = field(default_factory=list)      # [(状态码, 目标地址), …] 跟随的跳转
    upgraded: list = field(default_factory=list)   # 由 http:// 改为 https:// 的目标地址
    from_cache: object = False                     # False | True | "stale"
    attempts: int = 1
    elapsed_s: float = 0.0
    warnings: list = field(default_factory=list)

    def text(self, limit=None, charset=None):
        enc = charset or content_charset(self.headers) or "utf-8"
        t = self.body.decode(enc, errors="replace")
        return t if limit is None else t[:limit]

    def json(self):
        ctype = (self.headers.get("content-type") or "").lower()
        try:
            return json.loads(self.body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise ContentError(f"响应不是 JSON（Content-Type: {ctype or '?'}）：{summarize_body(self.body, ctype)}",
                               status=self.status, url=self.final_url) from None


def content_charset(headers):
    m = re.search(r"charset=([\w-]+)", headers.get("content-type") or "", re.I)
    return m.group(1) if m else None


def summarize_body(body, ctype="", limit=200):
    """错误体摘要：JSON 取 message / error / detail 字段；HTML 去标签；其余取前 limit 字。"""
    text = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else (body or "")
    stripped = text.strip()
    if "json" in ctype or stripped.startswith(("{", "[")):
        try:
            d = json.loads(stripped)
            if isinstance(d, dict):
                for k in ("message", "error", "detail", "msg"):
                    if d.get(k):
                        return str(d[k])[:limit]
        except ValueError:
            pass
    return _WS_RE.sub(" ", html.unescape(_TAG_RE.sub(" ", text))).strip()[:limit]


# ---------- 传输层 ----------

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def urllib_transport(method, url, headers, body, timeout):
    """一次请求，不跟随跳转。返回 (status, headers(小写键), body, final_url)。3xx 也作为结果返回。"""
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=timeout) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read(), resp.geturl()
    except urllib.error.HTTPError as e:
        try:
            data = e.read()
        except Exception:  # noqa: BLE001
            data = b""
        return e.code, {k.lower(): v for k, v in e.headers.items()}, data, e.geturl() or url
    except urllib.error.URLError as e:
        reason = str(e.reason)
        if "Tunnel connection failed: 403" in reason:
            raise BlockedByPolicy(f"BLOCKED at {host_of(url)} (network policy, proxy 403)", url=url) from None
        if isinstance(e.reason, (TimeoutError, ConnectionResetError)) or "timed out" in reason.lower():
            raise NetworkError(f"{type(e.reason).__name__ if not isinstance(e.reason, str) else 'timeout'}: {reason}", url=url) from None
        raise NetworkError(f"network error: {reason}", url=url) from None
    except (TimeoutError, ConnectionResetError) as e:
        raise NetworkError(f"{type(e).__name__}: {e}", url=url) from None


def host_of(url):
    return urllib.parse.urlsplit(url or "").hostname or "?"


# ---------- 客户端 ----------

class Client:
    def __init__(self, mode=None, *, cache_dir=None, cassette=None, policies=None, user_agent=None, env=None,
                 clock=None, sleep=None, rng=None, transport=urllib_transport, timeout=60):
        self.env = os.environ if env is None else env
        self.mode = mode or self.env.get("NP_HTTP_MODE", "live")
        if self.mode not in MODES:
            raise ValueError(f"NP_HTTP_MODE 应为 {'/'.join(MODES)} 之一，不是 {self.mode!r}")
        cache_dir = cache_dir or self.env.get("NP_HTTP_CACHE") or (PACKAGE_ROOT / ".cache" / "http")
        self.store = ResponseStore(cache_dir)
        cassette = cassette or self.env.get("NP_HTTP_CASSETTE")
        self.cassette = Cassette(cassette) if cassette else None
        if self.mode == "replay" and self.cassette is None:
            raise ValueError("replay 模式需要指定录制件（NP_HTTP_CASSETTE 或 cassette=）")
        self.policies = dict(POLICIES, **(policies or {}))
        self.user_agent = user_agent or self.env.get("NP_USER_AGENT") or DEFAULT_USER_AGENT
        self.clock = clock or (lambda: time.monotonic())        # 延迟绑定，测试可以 patch time.sleep / time.monotonic
        self.sleep = sleep or (lambda s: time.sleep(s))
        self.rng, self.transport, self.timeout = rng or random.Random(), transport, timeout
        self.refresh = False
        self._last = {}          # host -> 上次请求时刻
        self._consecutive_429 = {}
        self.stats = {}

    # -- 统计 --
    def _stat(self, host):
        return self.stats.setdefault(host, {"requests": 0, "cache_hits": 0, "retries": 0, "status": {}, "sleep_s": 0.0,
                                            "credits_used": 0, "remaining": None, "warnings": 0})

    def stats_summary(self):
        return {"mode": self.mode, "hosts": {h: dict(s) for h, s in self.stats.items()}}

    # -- 限速与退避 --
    def policy(self, host):
        return self.policies.get(host, DEFAULT_POLICY)

    def _throttle(self, host):
        pol = self.policy(host)
        last = self._last.get(host)
        if last is not None and pol.min_interval_s:
            wait = last + pol.min_interval_s - self.clock()
            if wait > 0:
                self.sleep(wait)
                self._stat(host)["sleep_s"] += wait
        self._last[host] = self.clock()

    def _backoff(self, pol, attempt, retry_after):
        if retry_after is not None:
            return max(float(retry_after), pol.min_interval_s)
        full = min(pol.backoff_cap_s, pol.backoff_base_s * 2 ** (attempt + 1))
        return max(full / 2 + self.rng.random() * full / 2, pol.min_interval_s)

    def _auth_headers(self, host):
        pol = self.policy(host)
        key = self.env.get(pol.auth_env) if pol.auth_env else None
        return {pol.auth_header: pol.auth_format.format(key=key)} if key and pol.auth_header else {}

    # -- 主请求 --
    def request(self, url, *, method="GET", params=None, headers=None, accept="application/json", body=None,
                follow=True, max_hops=10, upgrade_http=True, errors_as_result=False, ttl=None, refresh=False):
        """发起请求。errors_as_result=True 时 4xx/5xx 不抛异常而作为结果返回（核验落地页时用）。"""
        if params:
            url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params, doseq=True)
        host = host_of(url)
        pol = self.policy(host)
        key = cache_key(method, url, accept, body)
        st = self._stat(host)

        if self.mode == "replay":
            entry = self.cassette.play(key)
            if entry is None:
                near = self.cassette.nearest(url)
                raise ReplayMiss(f"录制件中没有这个请求：{method} {url}" + (f"（最接近的已录 URL：{near}）" if near else ""), url=url)
            st["cache_hits"] += 1
            return self._from_entry(entry, url, cached=True, errors_as_result=errors_as_result)
        if self.mode == "cache" and not (refresh or self.refresh):
            entry = self.store.get(key, host)
            if entry and not entry.get("_stale"):
                st["cache_hits"] += 1
                return self._from_entry(entry, url, cached=True, errors_as_result=errors_as_result)
        else:
            entry = None

        try:
            resp = self._fetch(url, method, headers or {}, accept, body, follow, max_hops, upgrade_http, pol, host)
        except (RateLimited, ServerError, NetworkError) as e:
            if self.mode == "cache" and entry is not None:   # 有过期缓存：网络失败时先用它
                st["cache_hits"] += 1
                r = self._from_entry(entry, url, cached="stale", errors_as_result=errors_as_result)
                r.warnings.append(f"served stale cache after error: {e}")
                return r
            raise
        if resp.status < 400 or errors_as_result:
            if self.mode in ("live", "cache", "record") and resp.status < 500:
                ent = make_entry(key, method, url, accept, None if body is None else hashlib.sha256(body).hexdigest(),
                                 resp.status, resp.final_url, resp.chain, resp.headers, resp.body,
                                 elapsed_s=resp.elapsed_s, attempts=resp.attempts,
                                 ttl_s=ttl if ttl is not None else (86400 if resp.status >= 400 else pol.ttl_s),
                                 upgraded=resp.upgraded)
                if resp.status < 400 or resp.status == 404:
                    self.store.put(key, host, ent)
                if self.mode == "record" and self.cassette is not None:
                    self.cassette.record(ent)
            return resp
        raise self._error_for(resp, url)

    def _from_entry(self, entry, url, cached, errors_as_result):
        r = entry["response"]
        resp = Response(status=r["status"], headers=dict(r.get("headers") or {}), body=decode_body(entry), url=url,
                        final_url=r.get("final_url") or url, chain=[tuple(h) for h in r.get("chain") or []],
                        upgraded=list(r.get("upgraded") or []), from_cache=cached,
                        attempts=(entry.get("meta") or {}).get("attempts", 1))
        if resp.status >= 400 and not errors_as_result:
            raise self._error_for(resp, url)
        return resp

    def _fetch(self, url, method, headers, accept, body, follow, max_hops, upgrade_http, pol, host):
        """发请求，必要时重试；跟随跳转时每一跳都按目标主机限速、重试，并记录跳转链。"""
        first_url, chain, upgraded = url, [], []
        attempt = 0
        started = self.clock()
        while True:
            st = self._stat(host)
            hdrs = {"User-Agent": self.user_agent, "Accept": accept, **self._auth_headers(host), **headers}
            if self._consecutive_429.get(host, 0) >= pol.breaker_consecutive:
                raise CircuitOpen(f"{host} 连续 {self._consecutive_429[host]} 次 429，熔断；稍后再试", status=429, url=url,
                                  attempts=attempt)
            self._throttle(host)
            st["requests"] += 1
            try:
                status, rhdrs, data, final = self.transport(method, url, hdrs, body, self.timeout)
            except BlockedByPolicy as e:
                e.chain = chain
                raise
            except NetworkError as e:
                if attempt + 1 < pol.max_attempts:
                    attempt += 1
                    st["retries"] += 1
                    self._wait(host, self._backoff(pol, attempt - 1, None))
                    continue
                e.attempts, e.chain = attempt + 1, chain
                raise
            st["status"][str(status)] = st["status"].get(str(status), 0) + 1
            self._note_rate_headers(host, rhdrs)
            self._consecutive_429[host] = self._consecutive_429.get(host, 0) + 1 if status == 429 else 0
            if status in RETRY_STATUSES:
                detail = summarize_body(data, rhdrs.get("content-type", ""))
                ra = rhdrs.get("retry-after", "")
                ra = float(ra) if ra.replace(".", "", 1).isdigit() else None
                if any(s in detail for s in pol.budget_substrings) or (ra is not None and ra > pol.retry_after_cap_s):
                    raise BudgetExhausted(detail, status=status, url=url, attempts=attempt + 1, retry_after=ra, chain=chain)
                if attempt + 1 < pol.max_attempts:
                    attempt += 1
                    st["retries"] += 1
                    self._wait(host, self._backoff(pol, attempt - 1, ra))
                    continue
                cls = RateLimited if status == 429 else ServerError
                raise cls(detail, status=status, url=url, attempts=attempt + 1, retry_after=ra, chain=chain)
            if follow and 300 <= status < 400 and rhdrs.get("location") and len(chain) < max_hops:
                new = urllib.parse.urljoin(url, rhdrs["location"])
                if upgrade_http and url.lower().startswith("https://") and new.lower().startswith("http://"):
                    new = "https://" + new[len("http://"):]
                    upgraded.append(new)
                chain.append((status, new))
                url, host, pol, attempt = new, host_of(new), self.policy(host_of(new)), 0   # 换主机：换策略，重试计数归零
                continue
            return Response(status=status, headers=rhdrs, body=data, url=first_url, final_url=final or url, chain=chain,
                            upgraded=upgraded, attempts=attempt + 1, elapsed_s=self.clock() - started)

    def _wait(self, host, seconds):
        self.sleep(seconds)
        self._stat(host)["sleep_s"] += seconds

    def _note_rate_headers(self, host, headers):
        """OpenAlex：X-Ratelimit-Credits-Used / -Remaining（当日额度）；Crossref：x-rate-limit-limit / -interval（限速）。"""
        st = self._stat(host)
        used = headers.get("x-ratelimit-credits-used")
        if used and used.isdigit():
            st["credits_used"] += int(used)
        if headers.get("x-ratelimit-remaining") is not None:
            st["remaining"] = headers["x-ratelimit-remaining"]
        if headers.get("x-rate-limit-limit"):
            st["rate_limit"] = f"{headers['x-rate-limit-limit']}/{headers.get('x-rate-limit-interval', '?')}"

    def _error_for(self, resp, url):
        detail = summarize_body(resp.body, resp.headers.get("content-type", ""))
        if resp.status == 404:
            return NotFound(detail or "not found", status=404, url=url, attempts=resp.attempts)
        if resp.status == 429:
            return RateLimited(detail, status=429, url=url, attempts=resp.attempts)
        if resp.status >= 500:
            return ServerError(detail, status=resp.status, url=url, attempts=resp.attempts)
        return ClientError(detail, status=resp.status, url=url, attempts=resp.attempts)

    # -- 便捷方法 --
    def get(self, url, **kw):
        return self.request(url, **kw)

    def get_json(self, url, *, headers=None, params=None, validate=None, **kw):
        """GET 并解析 JSON；validate(obj) 可返回警告列表，记入 Response.warnings 与 stats，不中断。"""
        resp = self.request(url, params=params, headers=headers, accept="application/json", **kw)
        obj = resp.json()
        if validate is not None:
            warnings = list(validate(obj) or [])
            if warnings:
                resp.warnings.extend(warnings)
                self._stat(host_of(url))["warnings"] += len(warnings)
        resp.data = obj
        return obj

    def post_json(self, url, payload, *, headers=None, params=None, **kw):
        body = json.dumps(payload).encode("utf-8")
        hdrs = {"Content-Type": "application/json", **(headers or {})}
        resp = self.request(url, method="POST", params=params, headers=hdrs, body=body, **kw)
        return resp.json()

    def paginate(self, url, params, *, scheme, max_items=None, checkpoint=None, fetch=None):
        """按游标 / 续页令牌 / 偏移量翻页，逐页产出 (页 JSON, 该页的条目列表)。
        checkpoint 为路径时，每页后写入 {url, next, pages, items}，下次运行从中断处继续：先验证续页参数仍有效
        （再取一页成功）才产出已保存的条目；令牌失效（如 S2 的 "Invalid bulk token"）则丢弃断点、从头开始。
        fetch(url, params) 可替换取页函数（默认 self.get_json），便于脚本保留自己的 get_json 封装。"""
        from .io import load_json_lenient, write_json
        resumed = None
        if checkpoint and Path(checkpoint).is_file():
            try:
                saved = load_json_lenient(checkpoint)
                if saved.get("url") == url and saved.get("next") is not None:
                    resumed = {"next": saved["next"], "pages": saved["pages"], "items": list(saved["items"])}
            except (ValueError, KeyError, TypeError):
                resumed = None
        state = resumed or {"next": _FIRST, "pages": 0, "items": []}
        yielded = 0
        while state["next"] is not None and (max_items is None or yielded + len(state["items"]) * (resumed is not None) < max_items):
            p = dict(params)
            if state["next"] is not _FIRST:
                p[scheme.param] = state["next"]
            elif scheme.start is not None:
                p[scheme.param] = scheme.start
            try:
                page = fetch(url, p) if fetch else self.get_json(url, params=p)
            except ClientError as e:
                if resumed is not None and scheme.stale_detail and scheme.stale_detail in str(e):
                    resumed, state = None, {"next": _FIRST, "pages": 0, "items": []}   # 断点里的令牌已失效：从头再来
                    continue
                raise
            if resumed is not None:                    # 续页参数仍有效：先交出已保存的条目
                yield {"_resumed": True, "pages": resumed["pages"]}, list(resumed["items"])
                yielded += len(resumed["items"])
                resumed = None
            items = scheme.items_of(page)
            state["pages"] += 1
            state["items"].extend(items)
            yielded += len(items)
            state["next"] = scheme.next_of(page, state, len(items))
            if checkpoint and state["next"] is not None:
                write_json(checkpoint, {"url": url, **state})
            yield page, items
        if checkpoint and Path(checkpoint).is_file():
            Path(checkpoint).unlink()


_FIRST = object()   # 翻页的起点（尚未发出第一页请求）


@dataclass
class Cursor:
    """OpenAlex 式：参数 cursor=*，响应 meta.next_cursor。"""
    param: str = "cursor"
    start: object = "*"
    stale_detail: str = ""

    def items_of(self, page):
        return page.get("results") or []

    def next_of(self, page, state, n):
        nxt = (page.get("meta") or {}).get("next_cursor")
        return nxt if (nxt and n) else None


@dataclass
class Token:
    """S2 bulk 式：参数 token，响应 token。"""
    param: str = "token"
    start: object = None
    stale_detail: str = "Invalid bulk token"

    def items_of(self, page):
        return page.get("data") or []

    def next_of(self, page, state, n):
        return page.get("token") or None


@dataclass
class Offset:
    """S2 citations 式：参数 offset，响应 next。"""
    param: str = "offset"
    start: object = 0
    stale_detail: str = ""

    def items_of(self, page):
        return page.get("data") or []

    def next_of(self, page, state, n):
        return page.get("next") if page.get("next") is not None and n else None


# ---------- 默认客户端 ----------

_default = None


def default_client():
    """各脚本共用的客户端；模式与缓存目录由环境变量决定。"""
    global _default
    if _default is None:
        _default = Client()
    return _default


def set_default_client(client):
    global _default
    _default = client


def add_http_args(ap):
    """各联网脚本共用的命令行参数。"""
    g = ap.add_argument_group("HTTP")
    g.add_argument("--http-mode", choices=MODES, default=None,
                   help="live（默认）每次请求网络；cache 先查缓存；record 边请求边录制；replay 只从录制件回放、不联网。也可用环境变量 NP_HTTP_MODE")
    g.add_argument("--cache-dir", default=None, help="缓存目录（默认 .cache/http，或环境变量 NP_HTTP_CACHE）")
    g.add_argument("--cassette", default=None, help="录制件路径（record / replay 模式；或环境变量 NP_HTTP_CASSETTE）")
    g.add_argument("--refresh", action="store_true", help="cache 模式下忽略已有缓存，重新请求")
    return g


def configure_from_args(args):
    """按命令行参数建立默认客户端；返回它。"""
    client = Client(getattr(args, "http_mode", None), cache_dir=getattr(args, "cache_dir", None),
                    cassette=getattr(args, "cassette", None))
    client.refresh = bool(getattr(args, "refresh", False))
    set_default_client(client)
    return client
