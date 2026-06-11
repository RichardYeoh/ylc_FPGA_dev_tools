from __future__ import annotations

import csv
import ctypes
import io
import subprocess
import sys
import time
from pathlib import Path

from codex_quota_provider import load_config


CREATE_NO_WINDOW = 0x08000000
ERROR_ALREADY_EXISTS = 183


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def acquire_single_instance(name: str) -> object | None:
    # Named mutex prevents duplicate watchers / 命名互斥量防止重复监听器
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, name)
    if not handle or ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        return None
    return handle


def find_pythonw() -> str:
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    if candidate.exists():
        return str(candidate)
    return str(exe)


def query_processes() -> list[tuple[str, str]]:
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        "Get-CimInstance Win32_Process | Select-Object Name,CommandLine | ConvertTo-Csv -NoTypeInformation",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            check=True,
            creationflags=CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    rows = csv.DictReader(io.StringIO(result.stdout))
    return [(row.get("Name") or "", row.get("CommandLine") or "") for row in rows]


def contains_any(text: str, patterns: list[str]) -> bool:
    text_l = text.lower()
    return any(pattern.lower() in text_l for pattern in patterns)


def is_own_tool_process(cmd: str, root: Path) -> bool:
    # Do not classify this utility as Codex just because its path contains "codex" / 不因本工具路径包含 codex 而误判为 Codex
    cmd_l = cmd.lower()
    root_l = str(root).lower()
    return root_l in cmd_l and (
        "codex_quota_taskbar.py" in cmd_l
        or "codex_quota_watcher.py" in cmd_l
        or "scripts\\run_watcher.ps1" in cmd_l
        or "scripts\\run_app.ps1" in cmd_l
    )


def app_is_running(processes: list[tuple[str, str]], root: Path) -> bool:
    # Detect this UI script by command line / 通过命令行检测本 UI 脚本是否已运行
    root_l = str(root).lower()
    return any("codex_quota_taskbar.py" in cmd.lower() and root_l in cmd.lower() for _name, cmd in processes)


def codex_is_running(processes: list[tuple[str, str]], watcher_cfg: dict, root: Path) -> bool:
    process_patterns = watcher_cfg.get("process_patterns", [])
    vscode_patterns = watcher_cfg.get("vscode_patterns", [])
    desktop_patterns = watcher_cfg.get("desktop_patterns", [])
    for name, cmd in processes:
        if is_own_tool_process(cmd, root):
            continue
        text = f"{name} {cmd}"
        if contains_any(text, process_patterns):
            return True
        if contains_any(name, vscode_patterns) and contains_any(cmd, ["openai", "codex", "chatgpt"]):
            return True
        if contains_any(text, desktop_patterns) and contains_any(text, ["codex", "openai", "chatgpt"]):
            return True
    return False


def launch_app(root: Path) -> None:
    pythonw = find_pythonw()
    app_path = root / "src" / "codex_quota_taskbar.py"
    subprocess.Popen(
        [pythonw, str(app_path)],
        cwd=str(root),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )


def stop_app(processes: list[tuple[str, str]], root: Path) -> None:
    # Conservative cleanup by script command line / 按脚本命令行进行保守清理
    root_s = str(root)
    for _name, cmd in processes:
        cmd_l = cmd.lower()
        if "codex_quota_taskbar.py" not in cmd_l or root_s.lower() not in cmd_l:
            continue
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                "$root = '"
                + root_s.replace("'", "''")
                + "'; "
                "$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*codex_quota_taskbar.py*' -and $_.CommandLine -like \"*$root*\" }; "
                "$p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        break


def main() -> int:
    mutex = acquire_single_instance("Local\\CodexQuotaTaskbarWatcher")
    if mutex is None:
        return 0
    root = project_root()
    config = load_config(root)
    watcher_cfg = config.get("watcher", {})
    poll_seconds = max(2, int(watcher_cfg.get("poll_seconds", 5)))
    close_when_codex_exits = bool(watcher_cfg.get("close_when_codex_exits", False))
    while True:
        processes = query_processes()
        codex_seen = codex_is_running(processes, watcher_cfg, root)
        app_seen = app_is_running(processes, root)
        if codex_seen and not app_seen:
            launch_app(root)
        if close_when_codex_exits and app_seen and not codex_seen:
            stop_app(processes, root)
        time.sleep(poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
