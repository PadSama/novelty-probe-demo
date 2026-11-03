"""HTTP 响应缓存与录制件（标准库）。

两者共用一种条目格式，所以录制件可以直接由缓存条目拼成：
  {"v": 1, "key": "<sha256>",
   "request": {"method": "GET", "url": "<规范化、去密钥>", "accept": "application/json", "body_sha256": null},
   "response": {"status": 200, "final_url": "...", "chain": [[302, "..."]], "headers": {...白名单...},
                "body": "<utf-8 文本>" 或 null, "body_b64": "<非 UTF-8 时>" 或 null},
   "meta": {"fetched_at": "...", "elapsed_s": 0.8, "attempts": 1, "ttl_s": 604800, "expires_at": "..."}}

- ResponseStore：内容寻址的目录缓存 <dir>/<host>/<key 前两位>/<key>.json，按 TTL 过期；
- Cassette：单个 JSON 文件，按录制顺序回放（同一请求多次出现时依次给出，可复现 429 → 200 的序列）。
缓存键 = sha256(method, 规范化 URL, Accept, 请求体哈希)。规范化：小写 scheme 与主机、去掉 api_key / mailto 参数、
参数按名称排序、去掉片段。密钥只在请求头里，从不写入磁盘。
"""
import base64
import hashlib
import json
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

ENTRY_VERSION = 1
SECRET_PARAMS = {"api_key", "mailto", "key", "token_secret"}
HEADER_ALLOWLIST = ("content-type", "content-length", "date", "vary", "retry-after", "location",
                    "x-api-pool", "x-amzn-errortype")
HEADER_PREFIXES = ("x-ratelimit-", "x-rate-limit-", "x-concurrency-")


def normalize_url(url):
    """缓存键用的 URL：小写 scheme/主机，去片段，去密钥参数，参数按名排序（保留空值）。"""
    s = urllib.parse.urlsplit(url)
    pairs = [(k, v) for k, v in urllib.parse.parse_qsl(s.query, keep_blank_values=True) if k not in SECRET_PARAMS]
    query = urllib.parse.urlencode(sorted(pairs), doseq=False)
    netloc = s.netloc.lower()
    for port, scheme in ((":443", "https"), (":80", "http")):
        if netloc.endswith(port) and s.scheme.lower() == scheme:
            netloc = netloc[: -len(port)]
    return urllib.parse.urlunsplit((s.scheme.lower(), netloc, s.path, query, ""))


def redact_url(url):
    """去掉密钥类参数，其余原样保留（用于记录 final_url 与跳转链）。"""
    s = urllib.parse.urlsplit(url or "")
    pairs = [(k, v) for k, v in urllib.parse.parse_qsl(s.query, keep_blank_values=True) if k not in SECRET_PARAMS]
    return urllib.parse.urlunsplit((s.scheme, s.netloc, s.path, urllib.parse.urlencode(pairs), s.fragment))


def cache_key(method, url, accept="", body=None):
    body_hash = hashlib.sha256(body).hexdigest() if body else ""
    raw = "\n".join([method.upper(), normalize_url(url), accept or "", body_hash])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def filtered_headers(headers):
    out = {}
    for k, v in (headers or {}).items():
        lk = k.lower()
        if lk in HEADER_ALLOWLIST or lk.startswith(HEADER_PREFIXES):
            out[lk] = v
    return out


def encode_body(body):
    """bytes → (text | None, base64 | None)。"""
    if body is None:
        return None, None
    try:
        return body.decode("utf-8"), None
    except UnicodeDecodeError:
        return None, base64.b64encode(body).decode("ascii")


def decode_body(entry):
    r = entry["response"]
    if r.get("body") is not None:
        return r["body"].encode("utf-8")
    if r.get("body_b64"):
        return base64.b64decode(r["body_b64"])
    return b""


def make_entry(key, method, url, accept, body_hash, status, final_url, chain, headers, body, *,
               elapsed_s, attempts, ttl_s, upgraded=()):
    text, b64 = encode_body(body)
    now = datetime.now(timezone.utc)
    return {
        "v": ENTRY_VERSION, "key": key,
        "request": {"method": method.upper(), "url": normalize_url(url), "accept": accept or "", "body_sha256": body_hash},
        "response": {"status": status, "final_url": redact_url(final_url), "chain": [[c, redact_url(u)] for c, u in chain],
                     "upgraded": [redact_url(u) for u in upgraded], "headers": filtered_headers(headers), "body": text,
                     "body_b64": b64},
        "meta": {"fetched_at": now.isoformat(timespec="seconds"), "elapsed_s": round(elapsed_s, 3), "attempts": attempts,
                 "ttl_s": ttl_s, "expires_at": (now + timedelta(seconds=ttl_s)).isoformat(timespec="seconds") if ttl_s else None},
    }


class ResponseStore:
    """目录缓存。"""

    def __init__(self, directory):
        self.dir = Path(directory)

    def path_for(self, key, host):
        return self.dir / (host or "unknown") / key[:2] / f"{key}.json"

    def get(self, key, host, now=None):
        p = self.path_for(key, host)
        if not p.is_file():
            return None
        try:
            entry = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        exp = (entry.get("meta") or {}).get("expires_at")
        if exp:
            now = now or datetime.now(timezone.utc)
            if datetime.fromisoformat(exp) < now:
                entry["_stale"] = True
        return entry

    def put(self, key, host, entry):
        p = self.path_for(key, host)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8", newline="\n") as f:   # Path.write_text 的 newline 参数要 3.10+
            f.write(json.dumps(entry, ensure_ascii=False))
        tmp.replace(p)


class Cassette:
    """录制件：单文件，顺序回放。"""

    def __init__(self, path):
        self.path = Path(path)
        self.interactions = []
        self._queues = {}
        if self.path.is_file():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.interactions = list(data.get("interactions") or [])
        self.reset()

    def reset(self):
        self._queues = {}
        for e in self.interactions:
            self._queues.setdefault(e["key"], []).append(e)

    def play(self, key):
        q = self._queues.get(key)
        return q.pop(0) if q else None

    def nearest(self, url):
        """回放未命中时给出最接近的已录 URL（按公共前缀长度），便于排错。"""
        target = normalize_url(url)
        best, best_len = None, -1
        for e in self.interactions:
            u = e["request"]["url"]
            n = len(_common_prefix(u, target))
            if n > best_len:
                best, best_len = u, n
        return best

    def record(self, entry):
        self.interactions.append(entry)
        self._queues.setdefault(entry["key"], []).append(entry)
        self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"version": ENTRY_VERSION, "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "redactions": sorted(SECRET_PARAMS), "interactions": self.interactions}
        tmp = self.path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=1))
        tmp.replace(self.path)


def _common_prefix(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return a[:n]


def monotonic():
    return time.monotonic()
