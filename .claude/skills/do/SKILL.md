---
name: do
description: 在 telepilot-py 项目中按描述执行任务。若为编码任务：完成改动后自动检查 README.md/CLAUDE.md 是否需要更新，提交并 push 代码，安装新依赖（如有），重启 telepilot-py systemd 服务，最后通过 Telegram 发送简洁的修改报告。若为非编码任务（如查询、配置、分析等）：按描述执行操作，通过 Telegram 发送执行结果说明，不提交代码、不重启服务。当用户调用 /do 并跟随任务描述时触发，例如 "/do 增加对频道消息的支持" 或 "/do 查看当前服务运行状态"。
---

# do

根据 `$ARGUMENTS` 描述执行任务，并通过 Telegram 发送结果报告。

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

### 1. 理解任务并判断类型

读取 `$ARGUMENTS`，判断是否为**编码任务**：

**编码任务**（需要修改源代码文件）：
- 添加新功能、修复 bug、重构代码
- 修改 `.py` 文件中的逻辑
- 更新配置模板或依赖

**非编码任务**（不需要修改源代码）：
- 查询信息（日志、状态、配置）
- 系统操作（查看进程、磁盘空间等）
- 分析、解释说明类请求
- 修改 skill/文档/配置文件等非项目源码
- 其他不涉及 `main.py`、`char_tracker.py`、`notifier.py` 等核心文件的操作

根据判断结果，走对应分支：

---

## 分支 A：编码任务

### A1. 阅读源文件

阅读相关源文件（`main.py`、`char_tracker.py`、`notifier.py` 等）理解上下文后再动手。

### A2. 修改代码

按任务描述完成代码改动，遵守 `CLAUDE.md` 中的架构约定。

### A3. 检查文档

改动完成后评估是否需要更新：
- `README.md`：功能说明、使用方式、配置项有变化时更新
- `CLAUDE.md`：架构描述、关键文件列表、群组表格有变化时更新

### A4. 提交并 Push

```bash
cd /home/alan/code/telepilot-py
git add <仅本次修改的文件，不用 -A>
git commit -m "<简短中文描述>"
git push
```

记录 commit hash 和 GitHub 链接用于报告：

```bash
COMMIT_HASH=$(git rev-parse --short HEAD)
REMOTE_URL=$(git remote get-url origin)
# 将 git@github.com:user/repo.git 转换为 https://github.com/user/repo
GITHUB_URL=$(echo "$REMOTE_URL" | sed 's|git@github.com:|https://github.com/|;s|\.git$||')
COMMIT_URL="${GITHUB_URL}/commit/${COMMIT_HASH}"
```

### A5. 安装依赖（仅 requirements.txt 有变化时）

```bash
cd /home/alan/code/telepilot-py
venv/bin/pip install -r requirements.txt -q
```

### A6. 重启服务

```bash
sudo systemctl restart telepilot-py
sleep 2
sudo systemctl is-active telepilot-py
```

记录返回状态（`active` / `failed`）。

### A7. 发送 Telegram 报告（编码任务）

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
🔗 {GitHub commit URL}
```

---

## 分支 B：非编码任务

### B1. 执行操作

按照任务描述执行对应操作，例如：
- 查询日志、状态 → 运行相关命令收集信息
- 修改 skill/文档文件 → 直接编辑对应文件
- 分析说明 → 读取相关文件并整理结论

**不修改项目源代码（`main.py`、`char_tracker.py`、`notifier.py` 等），不执行 git commit/push，不重启服务。**

### B2. 发送 Telegram 报告（非编码任务）

报告控制在 **1500 字符以内**，格式如下：

```
✅ 操作完成

📋 任务：{$ARGUMENTS 的简短摘要，≤50字}

📄 结果：
  {操作结果的简要说明，分条列出关键信息}

ℹ️ 说明：{补充说明，如有必要}
```

如果操作结果有具体数据（如日志片段、状态值），可适当截取关键内容附在报告中。

---

## 发送报告命令

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
