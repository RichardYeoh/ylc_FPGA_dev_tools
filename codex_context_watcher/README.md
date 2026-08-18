# Codex Context Watcher

用于按 Codex thread 监控上下文窗口占用，并在达到阈值时弹出 Windows 提醒。当前项目是原全局 watcher 的工作区迁移版。

## 项目结构

- `src/codex_context_watcher.py`：watcher 主程序。
- `scripts/start.ps1`：启动 watcher。
- `scripts/stop.ps1`：停止 watcher。
- `scripts/status.ps1`：查看 watcher 状态。
- `scripts/resume_context.ps1`：按指定上下文窗口打开 Codex 会话选择器。
- `维护会话记录.md`：原开发会话、设计结论和迁移记录。

## 运行

```powershell
.\scripts\start.ps1
.\scripts\status.ps1
.\scripts\stop.ps1
```

全局快捷命令 `codexwatch`、`codexwatch-stop`、`codexwatch-status` 也已改为指向本项目源码。

## 恢复已有会话

先进入目标工程目录，再执行对应的全局快捷命令：

```powershell
codexr512
codexr1m
```

命令会以当前目录筛选 Codex 的会话 picker，并分别覆盖为 512K 或 1M 上下文窗口；不覆盖模型和推理档位。需要查看其他目录的会话时，可附加 `--all`，例如 `codexr512 --all`。

## 通知点击定位

CLI 会话按 WezTerm pane 的当前工作目录匹配。只有匹配到唯一 pane 时，点击通知才会直接激活该 pane 及其 tab；同一目录存在多个 pane、WezTerm CLI 不可用或匹配失败时，程序退回到激活 WezTerm 窗口。ChatGPT App 会话不在当前 watcher 的数据源范围内。

## 数据边界

watcher 继续读取用户级 Codex 状态和 rollout 文件：

- `%USERPROFILE%\.codex\state_5.sqlite`
- `%USERPROFILE%\.codex\sessions\...\rollout-*.jsonl`

当前只处理状态库中 `cli` 和 `vscode` source 的未归档 thread；CLI 的宿主定位优先使用 WezTerm。ChatGPT App 不写入当前 watcher 使用的 thread 数据源，因此暂不监控其会话。

这些运行时数据没有复制进项目，OAuth token、状态数据库和运行日志也不进入版本库。
