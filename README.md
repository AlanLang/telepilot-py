# telepilot-py

Telegram 用户端消息监听机器人，使用 MTProto 协议（非 Bot API）以普通用户账号登录，监听指定群组消息并自动执行规则。

## 功能

- **单汉字二连跟发**：在每小时整点 1 分钟内（CST 8:00–23:00），同一群组累计收到 2 条相同汉字后自动跟发，随后进入 1 小时冷却
- **启动/停止通知**：通过 Telegram Bot 发送服务状态通知
- **崩溃通知**：程序异常退出时自动发送通知

## 环境要求

- Python 3.11+
- Telegram App API（从 [my.telegram.org/apps](https://my.telegram.org/apps) 申请）

## 安装

```bash
git clone git@github.com:AlanLang/telepilot-py.git
cd telepilot-py
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

## 配置

复制 `.env.example` 为 `.env` 并填写：

```bash
cp .env.example .env
```

```env
TELEGRAM_API_ID=       # 从 my.telegram.org/apps 申请
TELEGRAM_API_HASH=
TELEGRAM_PHONE=        # 格式：+8613800138000
TELEGRAM_SESSION_FILE= # 默认 telepilot-py.session
NOTIFY_BOT_TOKEN=      # Telegram Bot Token，用于状态通知（可选）
NOTIFY_CHAT_ID=        # 接收通知的 chat_id（可选）
LOG_LEVEL=INFO         # 日志等级：DEBUG / INFO
```

## 首次登录

首次运行需要交互式登录（输入验证码）：

```bash
venv/bin/python main.py
```

登录成功后会生成 `*.session` 文件，后续启动无需再次登录。

## 运行

```bash
# 直接运行
venv/bin/python main.py

# 作为 systemd 服务运行（推荐）
sudo cp telepilot-py.service /etc/systemd/system/
sudo systemctl enable --now telepilot-py
```

systemd 服务文件示例：

```ini
[Unit]
Description=Telepilot-py Telegram MTProto Client
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=alan
WorkingDirectory=/path/to/telepilot-py
EnvironmentFile=/path/to/telepilot-py/.env
ExecStart=/path/to/telepilot-py/venv/bin/python main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## 项目结构

```
main.py          — 入口：初始化客户端、注册 handler、信号处理
char_tracker.py  — CharTracker：单汉字二连跟发规则
notifier.py      — Telegram Bot API 通知
.env.example     — 配置模板
requirements.txt — 依赖列表
```

## 依赖

- [pyrofork](https://github.com/KurimuzonAkuma/pyrogram) — Pyrogram 社区维护 fork，支持 Telegram 新版 Forum 群组
- [tgcrypto](https://github.com/pyrogram/tgcrypto) — MTProto 加密加速
- [python-dotenv](https://github.com/theskumar/python-dotenv) — `.env` 文件加载
