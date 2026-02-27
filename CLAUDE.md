# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Commands

```bash
venv/bin/python main.py                    # 直接运行
LOG_LEVEL=DEBUG venv/bin/python main.py    # Debug 日志
sudo systemctl restart telepilot-py        # 重启 systemd 服务
sudo journalctl -u telepilot-py -f         # 查看实时日志
```

## Architecture

单进程 Telegram 用户端，使用 MTProto 协议（pyrofork）以普通用户账号监听群组消息。

**数据流**：Pyrogram 服务器实时推送 → `filters.chat` 路由 → `CharTracker.handle()` 处理

### 关键文件

```
main.py          — 入口：Client 初始化、handler 注册、SIGINT/SIGTERM 处理、崩溃通知
char_tracker.py  — CharTracker：全部业务逻辑
notifier.py      — Notifier：通过 Bot API 发送 HTML 通知（asyncio.to_thread 包装）
```

### 配置

通过 `.env` 文件管理（不提交 git）：

```
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_PHONE=         # 格式：+8613800138000，仅首次登录需要
TELEGRAM_SESSION_FILE=  # 默认 telepilot-py.session
NOTIFY_BOT_TOKEN=       # 可选，Bot Token 用于状态通知
NOTIFY_CHAT_ID=         # 可选，接收通知的 chat_id
LOG_LEVEL=INFO          # DEBUG / INFO
```

`.env.example` 是可提交的模板。`*.session` 保存登录态，被 `.gitignore` 排除。

### 依赖说明

- 使用 `pyrofork`（非官方 `pyrogram`）：官方 pyrogram 2.0.106 已停止维护，不支持 Telegram Forum 群组（`-1003` 前缀 ID），会导致 update 循环崩溃。pyrofork 是社区维护的活跃 fork。
- `tgcrypto`：MTProto 加密 C 扩展，需要编译（依赖 `python3-dev` 和 `gcc`）。

---

## 扩展指南：如何为群组添加新规则

### 第一步：实现新规则

在项目根目录新建文件，例如 `keyword_reply.py`：

```python
class KeywordReply:
    def __init__(self, notifier, hostname: str):
        self.notifier = notifier
        self.hostname = hostname

    async def handle(self, client, message) -> None:
        text = message.text or ""
        # 在这里写业务逻辑
```

### 第二步：在 main.py 注册

```python
from keyword_reply import KeywordReply

# 在 MONITORED_CHATS 中添加新群组 ID（Pyrogram 格式，超级群组为负数）
MONITORED_CHATS = [-1002304161402, 8512706023, 新群组ID]

# 实例化 handler
keyword_reply = KeywordReply(notifier, hostname)

# 注册（可与已有 handler 共用同一群组）
@app.on_message(filters.chat([新群组ID]) & ~filters.outgoing)
async def on_keyword(client, message):
    await keyword_reply.handle(client, message)
```

同一群组可注册多个 handler，互不干扰。

### 现有规则说明

**`CharTracker`**（`char_tracker.py`）

监听单个汉字消息，在活跃窗口内同一局累计 2 条相同汉字后自动跟发。

- 活跃窗口：CST 8:00–23:00 的整点 1 分钟内（`minute == 0`）
- 每到新整点重置本局计数（`_last_game_hour` 变更时清空 `_counts`）
- 跟发后该字进入 1 小时冷却（`_cooldowns` 记录到期时间）
- 使用 `asyncio.Lock` 保护共享状态，锁内只做判断和状态更新，网络 IO 在锁外执行

当前已注册的群组：

| chat_id          | Handler      |
|------------------|--------------|
| -1002304161402   | CharTracker  |
| 8512706023       | CharTracker  |

### chat_id 格式说明

Pyrogram 使用完整 Telegram ID：
- 超级群组 / 频道：`-100XXXXXXXXXX`（负数）
- 普通用户 / 私聊：正数

可通过 `message.chat.id` 在日志中查看实际 ID。
