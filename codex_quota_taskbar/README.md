# Codex Quota Taskbar

这是一个 Windows 本地小工具，用于在底部任务栏区域显示 Codex 的 `5h` 余量、周余量和各自复位时间。当前实现使用 Python 标准库，核心界面为透明背景的无边框紧凑窗，默认贴靠到 Windows 任务栏系统托盘左侧，宽度约等于两个普通任务栏图标。

## 当前边界

OpenAI 官方帮助文档说明可在 Codex usage page 或 limit banner 查看 Codex 限额；Codex CLI 当前没有公开的 `codex usage --json` 命令。开源社区已有可裁剪方案，例如 `codex-cli-usage` 说明其通过 `~/.codex/auth.json` 调用 `https://chatgpt.com/backend-api/codex/usage` 获取 `primary_window` 和 `secondary_window`。

本工具默认采用同类思路：优先通过本地 Codex OAuth 状态实时读取接口，接口失败时回退到项目内 `quota_cache.json`，再失败才回退到 `quota_state.json`。不会把本地 token 统计伪装成官方余量。

接口返回的复位时间按原始 UTC 时间缓存，显示层统一换算为香港时间 `UTC+08:00`；因此当天判断、跨日日期和 `5h`/weekly 复位时间都按香港时间显示。

```json
{
  "windows": {
    "5h": {
      "remaining_fraction": 0.72,
      "remaining_text": "72%",
      "reset_at": "2026-06-04T21:00:00+08:00"
    },
    "weekly": {
      "remaining_fraction": 0.63,
      "remaining_text": "63%",
      "reset_at": "2026-06-08T09:00:00+08:00"
    }
  }
}
```

## 运行

```powershell
cd E:\proj\ylc_FPGA_dev_tools\codex_quota_taskbar
python .\src\codex_quota_taskbar.py
```

默认配置启用鼠标穿透，因此提示文字不会拦截任务栏点击，也不会影响系统托盘、音量、网络、时钟等区域的交互。需要关闭显示窗时运行：

```powershell
.\scripts\stop_app.ps1
```

如果需要恢复窗口右键退出或双击切换位置，可先在 `config.json` 中将 `window.click_through` 改为 `false` 后重新启动。

如果显示窗被任务栏或“显示桌面”等操作隐藏，直接重新运行启动脚本；脚本会先清理旧显示窗再启动：

```powershell
.\scripts\run_app.ps1
```

## Codex 联动启动

监听器默认每 15 秒扫描一次 `codex.exe`、`@openai\codex`、VS Code OpenAI/Codex/ChatGPT 扩展宿主、Codex/ChatGPT 桌面相关进程。发现后启动显示窗，默认不会在 Codex 退出时关闭显示窗。

```powershell
.\scripts\run_watcher.ps1
```

只关闭显示窗、不关闭监听器：

```powershell
.\scripts\stop_app.ps1
```

如果要开机登录后自动监听，可运行：

```powershell
.\scripts\install_autostart.ps1
```

卸载自启动任务：

```powershell
.\scripts\uninstall_autostart.ps1
```

## 适配其他配额源

`config.json` 的 `quota.provider_command` 可以填写一个外部命令。该命令输出与 `quota_state.json` 相同结构的 JSON 时，程序会优先使用命令输出。这样后续如果 Codex CLI 增加稳定的 `usage --json` 输出，只需新增一个采集脚本，不需要改 UI。

## 参考

- OpenAI Help Center: Using Codex with your ChatGPT plan
- PyPI: `codex-cli-usage`，https://pypi.org/project/codex-cli-usage/
- GitHub issue: `openai/codex-plugin-cc#102`，https://github.com/openai/codex-plugin-cc/issues/102
- CodexControl，https://codexcontrol.app/
- Codex Quota Monitor，https://codexquotamonitor.github.io/
