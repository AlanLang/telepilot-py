"""
Telegram Bot API 通知模块

通过 urllib 发送 HTML 通知，best-effort 设计：发送失败时静默忽略。
send() 为 async 包装，避免阻塞 asyncio 事件循环。
"""
import asyncio
import json
import logging
import urllib.request

logger = logging.getLogger(__name__)


class Notifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send_sync(self, text: str) -> None:
        if not self.bot_token or not self.chat_id:
            return
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = json.dumps({
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
        }).encode()
        try:
            req = urllib.request.Request(
                url, data=payload, headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            logger.warning(f"[notifier] 发送通知失败: {e}")

    async def send(self, text: str) -> None:
        await asyncio.to_thread(self.send_sync, text)
