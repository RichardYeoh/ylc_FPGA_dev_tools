# Codex Resume 快捷入口迁移计划

## 摘要

将旧的“启动新 Codex 并扩窗”命令替换为“以指定窗口恢复旧会话”的 picker 命令。当前官方文档与本机 CLI 均确认：`codex resume` 默认打开按当前 CWD 筛选的 picker，支持全局 `-c` 覆盖和可选 `--all`。

不实现 `--last` 快捷入口、thread ID 数据库、弹窗按钮或自动退出当前 TUI。

## 实现变更

- 在项目内增加一个共享 PowerShell 入口，接受 `512k` 或 `1m` 档位并透传额外 resume 参数：
  - `512k`：`codex -c model_context_window=512000 -c model_auto_compact_token_limit=430000 resume`
  - `1m`：`codex -c model_context_window=1000000 -c model_auto_compact_token_limit=820000 resume`
- 不传 `-m` 或 `model_reasoning_effort`；模型选择交给 Codex 原生 resume 行为。
- 在 `C:\Users\liche\AppData\Roaming\npm` 创建 `codexr512.cmd` 和 `codexr1m.cmd`。
- 两个 CMD 调用项目内共享脚本、保持调用者当前目录，并支持 `codexr512 --all` 等参数透传。
- 删除旧的 `codex512k.cmd`、`codex1m.cmd`，不保留兼容别名。
- watcher 的 258K/512K 提醒分别改为 `codexr512`、`codexr1m`，仍只通知和聚焦宿主窗口。
- 删除硬编码旧会话 ID 的 `scripts/resume_original_session.ps1`；README 移除旧恢复入口。
- 更新项目维护记录和全局 `AGENTS.md` 中的有效命令说明；历史记录保留原事实并标注已废弃。

## 验证

- PowerShell 语法检查及 Python `compileall` 通过。
- 使用临时 mock `codex` 验证两档参数、调用 CWD、额外参数和退出码透传。
- 确认参数中不存在 `-m`、推理档位或 `--last`。
- 运行 `codexr512 --help`、`codexr1m --help`，确认全局命令可解析且不会进入交互 TUI。
- 确认 `Get-Command codex512k/codex1m` 均失效，新命令均指向项目脚本。
- 静态检查 watcher 阈值映射和活动文档中不存在旧命令的操作性引用。

## 假设与记录

- 默认 picker 只显示当前项目会话；需要跨目录时由用户显式追加 `--all`。
- “不指定模型”表示快捷入口不覆盖模型；是否沿用会话保存模型由当前 Codex 原生 resume 机制决定。
- 本次授权覆盖新旧全局 CMD、全局 `AGENTS.md` 的命令名同步以及项目内相关脚本/文档。
- 在项目维护记录中记录迁移结论，并按 Memory/Automation 自检要求追加一条简洁的全局流程执行证据；不创建经验卡片或额外项目文档。
