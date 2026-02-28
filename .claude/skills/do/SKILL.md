---
name: do
description: 在 telepilot-py 项目中按描述执行代码修改任务。完成改动后自动检查 README.md/CLAUDE.md 是否需要更新，提交并 push 代码，安装新依赖（如有），重启 telepilot-py systemd 服务，最后通过 Telegram 发送简洁的修改报告。当用户调用 /do 并跟随任务描述时触发，例如 "/do 增加对频道消息的支持"。
---

# do

根据 `$ARGUMENTS` 描述完成代码修改、提交、重启服务、发送报告。

## 基本信息

- **项目路径**: `/home/alan/code/telepilot-py`
- **服务名**: `telepilot-py`
- **发送脚本**: `.claude/skills/do/scripts/send-tg.py`

## 执行步骤

### 0. 发送输入状态

任务开始时**立即**执行，让用户感知到已收到指令：

```bash
python3 /home/alan/code/telepilot-py/.claude/skills/do/scripts/send-tg.py --typing
```

### 1. 理解任务

读取 `$ARGUMENTS`，阅读相关源文件（`main.py`、`char_tracker.py`、`notifier.py` 等）理解上下文后再动手。

### 2. 修改代码

按任务描述完成代码改动，遵守 `CLAUDE.md` 中的架构约定。

### 3. 检查文档

改动完成后评估是否需要更新：
- `README.md`：功能说明、使用方式、配置项有变化时更新
- `CLAUDE.md`：架构描述、关键文件列表、群组表格有变化时更新

### 4. 提交并 Push

```bash
cd /home/alan/code/telepilot-py
git add <仅本次修改的文件，不用 -A>
git commit -m "<简短中文描述>"
git push
```

记录 commit hash（`git rev-parse --short HEAD`）用于报告。

### 5. 安装依赖（仅 requirements.txt 有变化时）

```bash
cd /home/alan/code/telepilot-py
venv/bin/pip install -r requirements.txt -q
```

### 6. 重启服务

```bash
sudo systemctl restart telepilot-py
sleep 2
sudo systemctl is-active telepilot-py
```

记录返回状态（`active` / `failed`）。

### 7. 发送 Telegram 报告

报告控制在 **1500 字符以内**，格式如下：

```
✅ telepilot-py 更新完成

📋 任务：{$ARGUMENTS 的简短摘要，≤50字}

📝 变更：
  • {文件名}：{一句话说明}
  • {文件名}：{一句话说明}
  （如有文档更新也列出）

📦 依赖：{无变化 | 已安装：包名}
🔄 服务：{active ✓ | failed ✗}
🔖 Commit：{7位hash}
```

发送命令：

```bash
python3 /home/alan/code/telepilot-py/.claude/skills/do/scripts/send-tg.py "报告内容"
```

## 错误处理

**git push 失败**：检查远端状态后报告原因，发送失败通知。

**服务重启失败**：执行以下命令获取日志，附在报告末尾（截取最后 5 行）：
```bash
sudo journalctl -u telepilot-py -n 5 --no-pager
```

**任何步骤失败**：先发 TG 通知（前缀 `❌`），再终止。
