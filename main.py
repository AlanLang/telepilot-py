"""
telepilot-py — Telegram 用户端消息监听（Pyrogram 实现）

数据流：Pyrogram 实时推送 → filters.chat 路由 → CharTracker 处理
"""
import asyncio
import logging
import os
import signal
import socket
import sys

from dotenv import load_dotenv
from pyrogram import Client, filters

from char_tracker import CharTracker
from notifier import Notifier

load_dotenv()

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# 屏蔽 Pyrogram 自身的 INFO 日志噪音，只保留 WARNING+
logging.getLogger("pyrogram").setLevel(logging.WARNING)

logger = logging.getLogger("telepilot")

# 监听的群组/对话 chat_id（Pyrogram 格式）
MONITORED_CHATS = [-1002304161402, 8512706023]


async def main() -> None:
    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    phone = os.environ.get("TELEGRAM_PHONE", "") or None
    session_file = os.environ.get("TELEGRAM_SESSION_FILE", "telepilot-py.session")
    notify_token = os.environ.get("NOTIFY_BOT_TOKEN", "")
    notify_chat = os.environ.get("NOTIFY_CHAT_ID", "")

    hostname = socket.gethostname()
    notifier = Notifier(notify_token, notify_chat)

    # Pyrogram 用 name 作为 session 文件名（自动加 .session 后缀）
    session_name = session_file.removesuffix(".session")

    app = Client(
        name=session_name,
        api_id=api_id,
        api_hash=api_hash,
        phone_number=phone,
    )

    tracker = CharTracker(notifier, hostname)

    @app.on_message(filters.chat(MONITORED_CHATS) & ~filters.outgoing)
    async def on_message(client, message):
        try:
            await tracker.handle(client, message)
        except Exception as e:
            logger.error(f"处理消息异常: {e}", exc_info=True)

    stop_event = asyncio.Event()

    def _on_signal():
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _on_signal)

    async with app:
        logger.info("已连接到 Telegram，开始监听消息...")
        await notifier.send(
            f"🚀 <b>telepilot 已启动</b>\n🖥 主机：<code>{hostname}</code>"
        )
        await stop_event.wait()
        await notifier.send(
            f"🛑 <b>telepilot 已停止</b>\n🖥 主机：<code>{hostname}</code>"
        )


if __name__ == "__main__":
    _notify_token = os.environ.get("NOTIFY_BOT_TOKEN", "")
    _notify_chat = os.environ.get("NOTIFY_CHAT_ID", "")
    _hostname = socket.gethostname()

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        # 同步发送崩溃通知（asyncio 已退出，无法用 await）
        Notifier(_notify_token, _notify_chat).send_sync(
            f"💥 <b>telepilot 崩溃</b>\n"
            f"🖥 主机：<code>{_hostname}</code>\n"
            f"❌ 原因：<code>{type(e).__name__}: {e}</code>"
        )
        sys.exit(1)
