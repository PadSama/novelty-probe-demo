"""文件读写与控制台编码（标准库）。

- load_json_lenient()：读 JSON 时容忍 UTF-8 BOM（Windows 记事本的默认）和 Markdown 代码块围栏（AI 助手常把 JSON 包进 ```json … ```）；
- read_text() / write_text()：统一 utf-8（读时 utf-8-sig），写入固定 "\\n" 换行，避免 Windows 上写出 CRLF；
- atomic_write_text() / write_json()：先写临时文件再 os.replace，中途失败不会留下半个文件；
- configure_console()：把 stdout / stderr 切到 UTF-8（errors="replace"），避免 cp936 / cp1252 控制台打印中文或 "→" 时抛 UnicodeEncodeError。
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

_FENCE_RE = re.compile(r"^\s*```[A-Za-z0-9_-]*\s*\n(.*?)\n\s*```\s*$", re.S)


def read_text(path):
    """读文本：utf-8，去掉开头的 BOM。"""
    return Path(path).read_text(encoding="utf-8-sig")


def strip_fences(text):
    """去掉把整段内容包起来的 Markdown 代码块围栏（```json … ```）。"""
    m = _FENCE_RE.match(text)
    return m.group(1) if m else text


def load_json_lenient(path):
    """读 JSON 文件；容忍 BOM 与代码块围栏。解析失败时抛 ValueError，带文件名与行号。"""
    text = strip_fences(read_text(path))
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"{path} 不是合法的 JSON（第 {e.lineno} 行）：{e.msg}") from None


def write_text(path, text):
    """写文本：utf-8，换行固定为 \\n（不随操作系统变化）。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def append_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(text)


def atomic_write_text(path, text, encoding="utf-8"):
    """先写同目录下的临时文件，再原子替换到目标路径。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def dump_json(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def write_json(path, obj):
    """原子写 JSON（ensure_ascii=False，indent=2，末尾换行）。"""
    atomic_write_text(path, dump_json(obj))


def configure_console():
    """stdout / stderr 改为 UTF-8 输出，编码不了的字符用替代符，不抛异常。重复调用无害。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):  # 已关闭的流、不支持的平台
            pass
