#!/usr/bin/env python3
"""
发送消息到 Telegram。
TOKEN/CHAT_ID 从项目根目录 .env 读取（NOTIFY_BOT_TOKEN / NOTIFY_CHAT_ID）。

用法: python3 send-tg.py "消息内容"        # 发送文本消息
     python3 send-tg.py --typing           # 发送一次正在输入状态
     python3 send-tg.py --typing-loop      # 每 4 秒持续发送，直到被 kill
     echo "消息内容" | python3 send-tg.py  # 从 stdin 读取
"""
import json
import os
import sys
import time
import urllib.request
from pathlib import Path


def _load_env() -> tuple[str, str]:
    env_file = Path(__file__).resolve().parent.parent.parent.parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
    token = os.environ.get("NOTIFY_BOT_TOKEN", "")
    chat_id = os.environ.get("NOTIFY_CHAT_ID", "")
    if not token or not chat_id:
        print("错误: .env 中未配置 NOTIFY_BOT_TOKEN / NOTIFY_CHAT_ID", file=sys.stderr)
        sys.exit(1)
    return token, chat_id


MAX_LEN = 4000


def _post(endpoint: str, payload: dict) -> None:
    token, _ = _load_env()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{endpoint}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=10)


def typing() -> None:
    _, chat_id = _load_env()
    try:
        _post("sendChatAction", {"chat_id": chat_id, "action": "typing"})
        print("TG typing 发送成功")
    except Exception as e:
        print(f"TG typing 发送失败: {e}", file=sys.stderr)


def typing_loop(interval: int = 4) -> None:
    """每隔 interval 秒持续发送 typing，直到进程被 kill。"""
    _, chat_id = _load_env()
    while True:
        try:
            _post("sendChatAction", {"chat_id": chat_id, "action": "typing"})
        except Exception:
            pass
        time.sleep(interval)


def send(text: str) -> None:
    _, chat_id = _load_env()
    try:
        _post("sendMessage", {"chat_id": chat_id, "text": text[:MAX_LEN]})
        print("TG 发送成功")
    except Exception as e:
        print(f"TG 发送失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if "--typing-loop" in sys.argv:
        typing_loop()
    elif "--typing" in sys.argv:
        typing()
    else:
        if len(sys.argv) > 1:
            msg = " ".join(a for a in sys.argv[1:] if a != "--typing")
        else:
            msg = sys.stdin.read().strip()

        if not msg:
            print("错误: 消息内容为空", file=sys.stderr)
            sys.exit(1)

        send(msg)
