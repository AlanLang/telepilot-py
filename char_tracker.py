"""
CharTracker：单汉字二连跟发处理器

监听群组中的单个汉字消息，在以下条件下生效：
  - CST 白天 8:00–23:00（含 8 不含 23）
  - 每小时整点 1 分钟内（如 9:00–9:00:59）

在活跃窗口内同一局内累计收到 2 条相同汉字（不要求连续）后自动跟发，
随后该字进入 1 小时冷却期。每到新整点自动重置本局计数。
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

CST = timezone(timedelta(hours=8))
COOLDOWN_SECS = 3600

# Unicode 汉字范围
_CHINESE_RANGES = [
    (0x4E00, 0x9FFF),    # CJK 统一表意文字
    (0x3400, 0x4DBF),    # CJK 扩展 A
    (0x20000, 0x2A6DF),  # CJK 扩展 B
]


def _parse_cst_time(dt: datetime) -> tuple[int, int, int]:
    """将 datetime（任意时区）转换为 CST 的 (hour, minute, second)"""
    cst_dt = dt.astimezone(CST)
    return cst_dt.hour, cst_dt.minute, cst_dt.second


def _is_active_window(hour: int, minute: int) -> bool:
    """CST 8–23 时的整点 1 分钟内"""
    return 8 <= hour < 23 and minute == 0


def _single_chinese_char(text: str) -> Optional[str]:
    """如果 text（去除首尾空格后）恰好是单个汉字，返回该字符，否则返回 None"""
    s = text.strip()
    if len(s) != 1:
        return None
    cp = ord(s)
    for lo, hi in _CHINESE_RANGES:
        if lo <= cp <= hi:
            return s
    return None


class CharTracker:
    def __init__(self, notifier, hostname: str):
        self.notifier = notifier
        self.hostname = hostname
        self._lock = asyncio.Lock()
        self._counts: dict[str, int] = {}
        self._cooldowns: dict[str, datetime] = {}  # char -> 冷却到期时间（UTC）
        self._last_game_hour: Optional[int] = None

    def _is_cooling_down(self, ch: str) -> bool:
        until = self._cooldowns.get(ch)
        return until is not None and datetime.now(timezone.utc) < until

    def _set_cooldown(self, ch: str) -> None:
        self._cooldowns[ch] = datetime.now(timezone.utc) + timedelta(seconds=COOLDOWN_SECS)

    def _maybe_reset(self, hour: int) -> None:
        """如果是新一局（整点），重置本局计数"""
        if self._last_game_hour != hour:
            if self._last_game_hour is not None:
                logger.debug(f"[重置] 新一局开始（{hour}:00），清空本局计数")
            self._counts.clear()
            self._last_game_hour = hour

    async def handle(self, client, message) -> None:
        # Pyrogram 的 message.date 是 UTC timezone-aware datetime
        dt: datetime = message.date
        hour, minute, second = _parse_cst_time(dt)

        if not _is_active_window(hour, minute):
            logger.debug(f"[跳过] 不在活跃窗口（CST {hour}:{minute:02}:{second:02}）")
            return

        text = message.text or ""
        ch = _single_chinese_char(text)
        logger.debug(f"[解析] text={text!r} → single_chinese_char={ch!r}")

        if ch is None:
            logger.debug(f"[跳过] 非单个汉字，忽略: {text!r}")
            return

        chat = message.chat
        sender = message.from_user
        sender_name = getattr(sender, "first_name", "未知") or "未知"
        sender_id = getattr(sender, "id", 0) or 0
        chat_name = chat.title or getattr(chat, "first_name", "") or str(chat.id)
        logger.info(
            f"[消息] chat='{chat_name}' (id={chat.id}) | "
            f"sender='{sender_name}' (id={sender_id}) | text={text!r}"
        )

        should_send = False
        async with self._lock:
            self._maybe_reset(hour)

            if self._is_cooling_down(ch):
                until = self._cooldowns[ch]
                remaining = (until - datetime.now(timezone.utc)).total_seconds()
                logger.info(
                    f"[冷却] '{ch}' 冷却中，剩余 {int(remaining // 60)}分{int(remaining % 60)}秒，跳过"
                )
            else:
                self._counts[ch] = self._counts.get(ch, 0) + 1
                count = self._counts[ch]
                logger.info(f"[追踪] '{ch}' x{count} / 2（本局累计，不要求连续）")

                if count >= 2:
                    self._set_cooldown(ch)
                    del self._counts[ch]
                    should_send = True

        if should_send:
            logger.info(f"[触发] 本局累计 2 次，准备发送 '{ch}'")
            try:
                await client.send_message(chat.id, ch)
                logger.info(f"[发送] 成功发送 '{ch}'，已进入 1 小时冷却")
                await self.notifier.send(
                    f"✅ <b>已跟发</b>：{ch}\n"
                    f"🖥 主机：<code>{self.hostname}</code>\n"
                    f"💬 群组：{chat_name}"
                )
            except Exception as e:
                logger.warning(f"[发送] 发送 '{ch}' 失败: {e}")
