"""
连接看门狗：监控 Pyrogram 连接超时，长时间断连时自动重启，重启后仍失败则发告警。

工作流程：
1. 监听 pyrogram.connection.connection 的 WARNING 日志（Connection timed out / Connection failed）
2. 连续超时超过 TIMEOUT_THRESHOLD 秒（默认 5 分钟）时触发
3. 若无历史重启记录 → 发"正在重启"通知 → sys.exit(1)（systemd 自动重启）
4. 若已重启过（标记文件存在）→ 发"持续故障"告警，不再重启
5. 连接恢复（RECOVERY_WINDOW 秒内无新超时）→ 清理标记文件，重置状态
"""
import asyncio
import logging
import os
import sys
import time

logger = logging.getLogger("telepilot.watchdog")

RESTART_FLAG = "/tmp/telepilot-watchdog-restarted"
TIMEOUT_THRESHOLD = 300   # 持续超时 5 分钟后触发
RECOVERY_WINDOW = 60      # 60 秒内无超时则认为连接已恢复
CHECK_INTERVAL = 30       # 每 30 秒检查一次


class ConnectionWatchdog:
    def __init__(self, notifier, hostname: str):
        self.notifier = notifier
        self.hostname = hostname
        self._first_timeout_at: float | None = None
        self._last_timeout_at: float | None = None
        self._triggered = False
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        """安装日志 handler 并启动后台监控任务。须在 asyncio 事件循环中调用。"""
        logging.getLogger("pyrogram.connection.connection").addHandler(
            self._make_log_handler()
        )
        self._task = asyncio.get_running_loop().create_task(self._monitor_loop())
        logger.info("连接看门狗已启动（阈值 %d 秒）", TIMEOUT_THRESHOLD)

    def stop(self) -> None:
        if self._task:
            self._task.cancel()

    # ------------------------------------------------------------------

    def _make_log_handler(self) -> logging.Handler:
        watchdog = self

        class _Handler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                msg = record.getMessage()
                if "Connection timed out" in msg or "Connection failed" in msg:
                    now = time.monotonic()
                    if watchdog._first_timeout_at is None:
                        watchdog._first_timeout_at = now
                        logger.debug("连接超时开始计时")
                    watchdog._last_timeout_at = now

        h = _Handler()
        h.setLevel(logging.WARNING)
        return h

    async def _monitor_loop(self) -> None:
        while True:
            await asyncio.sleep(CHECK_INTERVAL)
            await self._check()

    async def _check(self) -> None:
        if self._first_timeout_at is None:
            return

        now = time.monotonic()

        # 连接已恢复：超过 RECOVERY_WINDOW 秒没有新的超时
        if self._last_timeout_at is not None and now - self._last_timeout_at > RECOVERY_WINDOW:
            self._reset()
            return

        # 达到触发阈值
        elapsed = now - self._first_timeout_at
        if elapsed >= TIMEOUT_THRESHOLD and not self._triggered:
            self._triggered = True
            await self._handle_failure(elapsed)

    def _reset(self) -> None:
        logger.info("连接已恢复，重置看门狗状态")
        self._first_timeout_at = None
        self._last_timeout_at = None
        self._triggered = False
        if os.path.exists(RESTART_FLAG):
            try:
                os.remove(RESTART_FLAG)
                logger.info("已清理重启标记文件")
            except OSError:
                pass

    async def _handle_failure(self, elapsed: float) -> None:
        minutes = round(elapsed / 60)
        if os.path.exists(RESTART_FLAG):
            logger.error("连接持续超时 %d 分钟，重启后仍未恢复，发送告警", minutes)
            await self.notifier.send(
                f"🔴 <b>telepilot 网络持续故障</b>\n"
                f"🖥 主机：<code>{self.hostname}</code>\n"
                f"⏱ 已中断约 {minutes} 分钟，重启后仍未恢复，请手动检查"
            )
        else:
            logger.warning("连接持续超时 %d 分钟，准备重启...", minutes)
            try:
                with open(RESTART_FLAG, "w") as f:
                    f.write(str(time.time()))
            except OSError:
                pass
            await self.notifier.send(
                f"⚠️ <b>telepilot 连接超时，正在重启</b>\n"
                f"🖥 主机：<code>{self.hostname}</code>\n"
                f"⏱ 已中断约 {minutes} 分钟"
            )
            sys.exit(1)  # systemd Restart=on-failure 会自动重启
