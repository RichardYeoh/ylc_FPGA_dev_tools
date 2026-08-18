import base64
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse


CODEX_HOME = Path.home() / ".codex"
STATE_DB = CODEX_HOME / "state_5.sqlite"
PID_FILE = CODEX_HOME / "tmp" / "codex_context_watcher.pid"
LOG_FILE = CODEX_HOME / "log" / "codex_context_watcher.log"
SCRIPT_PATH = Path(__file__).resolve()
POLL_INTERVAL_SECONDS = 5.0
RECENT_REGISTER_LOOKBACK_SECONDS = 120.0


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def log(message: str) -> None:
    ensure_parent(LOG_FILE)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(f"[{stamp}] {message}\n")


def parse_timestamp(ts: str) -> float:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()


def kfmt(value: int) -> str:
    return f"{int(round(value / 1000.0))}k"


def short_cwd(cwd: str | None) -> str:
    if not cwd:
        return "(unknown)"
    cleaned = cwd.replace("\\\\?\\", "")
    return cleaned


def normalize_cwd(cwd: str | None) -> str | None:
    if not cwd:
        return None
    value = cwd.strip()
    if value.startswith("file://"):
        parsed = urlparse(value)
        path = unquote(parsed.path)
        if parsed.netloc:
            value = f"\\\\{parsed.netloc}{path}"
        else:
            value = path.lstrip("/")
    value = value.replace("\\\\?\\", "").replace("/", "\\").rstrip("\\")
    return os.path.normcase(os.path.normpath(value))


def choose_tier(context_window: int) -> dict:
    if context_window <= 300000:
        return {
            "name": "258k",
            "soft_used": 185000,
            "hard_used": 210000,
            "action_soft": "codexr512",
            "action_hard": "codexr512",
        }
    if context_window <= 700000:
        return {
            "name": "512k",
            "soft_used": 370000,
            "hard_used": 415000,
            "action_soft": "codexr1m",
            "action_hard": "codexr1m",
        }
    return {
        "name": "1m",
        "soft_used": 720000,
        "hard_used": 810000,
        "action_soft": None,
        "action_hard": None,
    }


def show_notification(title: str, body: str, host_kind: str, cwd: str | None) -> None:
    payload = {
        "title": title,
        "body": body,
        "host_kind": host_kind,
        "cwd": cwd,
    }
    encoded = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode(
        "ascii"
    )
    subprocess.Popen(
        [
            detect_pythonw(),
            str(Path(__file__).resolve()),
            "popup",
            encoded,
        ],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        close_fds=True,
    )


def pid_is_running(pid: int) -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return False
    return str(pid) in result.stdout


def find_watcher_pids() -> list[int]:
    script_name = SCRIPT_PATH.name.replace("'", "''")
    ps_script = f"""
$items = Get-CimInstance Win32_Process |
    Where-Object {{
        $_.CommandLine -and
        $_.Name -in @('python.exe', 'pythonw.exe') -and
        $_.CommandLine -like '*{script_name}*' -and
        $_.CommandLine -like '* run*'
    }} |
    Select-Object -ExpandProperty ProcessId
if ($null -eq $items) {{
    '[]'
}} else {{
    $items | ConvertTo-Json -Compress
}}
"""
    try:
        result = subprocess.run(
            [
                "pwsh",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                ps_script,
            ],
            capture_output=True,
            text=True,
            timeout=8,
        )
    except Exception:
        return []
    if result.returncode != 0:
        return []
    text = result.stdout.strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(data, int):
        return [data]
    if isinstance(data, list):
        return [int(item) for item in data if str(item).isdigit()]
    return []


def read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def write_pid(pid: int) -> None:
    ensure_parent(PID_FILE)
    PID_FILE.write_text(str(pid), encoding="utf-8")


def remove_pid() -> None:
    try:
        PID_FILE.unlink()
    except FileNotFoundError:
        pass


def connect_state() -> sqlite3.Connection:
    uri = f"file:{STATE_DB.as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=5)


def fetch_threads() -> list[dict]:
    con = connect_state()
    try:
        cur = con.cursor()
        rows = cur.execute(
            """
            select id, source, rollout_path, cwd, title, model, updated_at_ms, updated_at
            from threads
            where archived = 0 and source in ('cli', 'vscode')
            """
        ).fetchall()
    finally:
        con.close()
    items = []
    for row in rows:
        items.append(
            {
                "id": row[0],
                "source": row[1],
                "rollout_path": row[2],
                "cwd": row[3],
                "title": row[4],
                "model": row[5],
                "updated_at_ms": row[6],
                "updated_at": row[7],
            }
        )
    return items


class ThreadState:
    def __init__(self, meta: dict, watcher_start_ts: float):
        self.id = meta["id"]
        self.source = meta["source"]
        self.rollout_path = meta["rollout_path"]
        self.cwd = meta["cwd"]
        self.title = meta["title"]
        self.model = meta["model"]
        self.last_alert_stage = 0
        self.last_context_window = None
        self.last_used = 0
        self.last_event_ts = 0.0
        self.offset = 0
        self.watcher_start_ts = watcher_start_ts
        self.register()

    def register(self) -> None:
        path = Path(self.rollout_path)
        if not path.exists():
            return
        text = path.read_text(encoding="utf-8", errors="replace")
        self.offset = len(text.encode("utf-8"))
        # Also inspect very recent token_count events so a currently active thread can be picked up.
        recent_lines = text.splitlines()[-200:]
        for line in recent_lines:
            self.process_line(line, only_recent=True)

    def sync_meta(self, meta: dict) -> None:
        self.source = meta["source"]
        self.rollout_path = meta["rollout_path"]
        self.cwd = meta["cwd"]
        self.title = meta["title"]
        self.model = meta["model"]

    def maybe_reset_alert_stage(self, used: int, context_window: int) -> None:
        tier = choose_tier(context_window)
        if self.last_context_window != context_window:
            self.last_alert_stage = 0
            self.last_context_window = context_window
            return
        if used < int(tier["soft_used"] * 0.7):
            self.last_alert_stage = 0

    def alert(self, stage: int, used: int, context_window: int) -> None:
        remain = max(context_window - used, 0)
        tier = choose_tier(context_window)
        source_label = "VS Code" if self.source == "vscode" else "WezTerm CLI"
        where = short_cwd(self.cwd)
        if tier["name"] == "1m":
            action = "建议阶段总结后新开线程"
        else:
            cmd = tier["action_hard"] if stage >= 2 else tier["action_soft"]
            if self.source == "vscode":
                action = f"如需更大上下文，建议转终端继续：{cmd}"
            else:
                prefix = "尽快切换" if stage >= 2 else "建议切换"
                action = f"{prefix}：{cmd}"
        title = f"Codex 上下文提醒 [{source_label}]"
        body = f"{where}\n已用 {kfmt(used)} / {kfmt(context_window)}，剩余 {kfmt(remain)}。\n{action}"
        show_notification(
            title,
            body,
            "vscode" if self.source == "vscode" else "wezterm",
            self.cwd,
        )
        log(
            f"notify thread={self.id} source={self.source} used={used} "
            f"context_window={context_window} stage={stage} cwd={where} action={action}"
        )

    def process_token_count(self, payload: dict, event_ts: float, only_recent: bool) -> None:
        info = payload.get("info") or {}
        last_usage = info.get("last_token_usage") or {}
        used = int(last_usage.get("input_tokens") or 0)
        context_window = int(info.get("model_context_window") or 0)
        if used <= 0 or context_window <= 0:
            return
        if only_recent and event_ts < self.watcher_start_ts - RECENT_REGISTER_LOOKBACK_SECONDS:
            return
        self.maybe_reset_alert_stage(used, context_window)
        tier = choose_tier(context_window)
        stage = 0
        if used >= tier["hard_used"]:
            stage = 2
        elif used >= tier["soft_used"]:
            stage = 1
        self.last_used = used
        self.last_context_window = context_window
        self.last_event_ts = event_ts
        if stage > self.last_alert_stage:
            self.alert(stage, used, context_window)
            self.last_alert_stage = stage

    def process_line(self, line: str, only_recent: bool = False) -> None:
        line = line.strip()
        if not line or '"type":"token_count"' not in line:
            return
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            return
        if item.get("type") != "event_msg":
            return
        payload = item.get("payload") or {}
        if payload.get("type") != "token_count":
            return
        try:
            event_ts = parse_timestamp(item["timestamp"])
        except Exception:
            event_ts = time.time()
        self.process_token_count(payload, event_ts, only_recent=only_recent)

    def poll(self) -> None:
        path = Path(self.rollout_path)
        if not path.exists():
            return
        try:
            size = path.stat().st_size
        except OSError:
            return
        if size < self.offset:
            self.offset = 0
            self.last_alert_stage = 0
        if size == self.offset:
            return
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            fh.seek(self.offset)
            data = fh.read()
            self.offset = fh.tell()
        for line in data.splitlines():
            self.process_line(line, only_recent=False)


def detect_pythonw() -> str:
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe":
        return str(exe)
    candidate = exe.with_name("pythonw.exe")
    if candidate.exists():
        return str(candidate)
    result = subprocess.run(
        ["where", "pythonw.exe"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    for line in result.stdout.splitlines():
        line = line.strip()
        if line:
            return line
    return str(exe)


def powershell_focus_script(host_kind: str) -> str:
    if host_kind == "vscode":
        titles = ["Visual Studio Code", "Code - Insiders"]
    elif host_kind == "wezterm":
        titles = ["WezTerm", "Windows Terminal", "PowerShell", "pwsh"]
    else:
        titles = ["Windows Terminal", "PowerShell", "Command Prompt", "pwsh", "cmd.exe"]
    attempts = "\n".join(
        [f'if ($wshell.AppActivate("{title}")) {{ return }}' for title in titles]
    )
    return f"""
$wshell = New-Object -ComObject WScript.Shell
{attempts}
"""


def activate_wezterm_pane(cwd: str | None) -> bool:
    target_cwd = normalize_cwd(cwd)
    wezterm = shutil.which("wezterm")
    if not target_cwd or not wezterm:
        return False
    try:
        result = subprocess.run(
            [wezterm, "cli", "list", "--format", "json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except Exception as exc:
        log(f"wezterm list failed cwd={short_cwd(cwd)} error={exc}")
        return False
    if result.returncode != 0:
        log(f"wezterm list failed cwd={short_cwd(cwd)} rc={result.returncode}")
        return False
    try:
        panes = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        log(f"wezterm list returned invalid json error={exc}")
        return False
    matches = [
        pane
        for pane in panes
        if normalize_cwd(pane.get("cwd")) == target_cwd and isinstance(pane.get("pane_id"), int)
    ]
    if len(matches) != 1:
        if len(matches) > 1:
            log(f"wezterm pane match ambiguous cwd={short_cwd(cwd)} matches={len(matches)}")
        return False
    pane_id = matches[0]["pane_id"]
    try:
        result = subprocess.run(
            [wezterm, "cli", "activate-pane", "--pane-id", str(pane_id)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except Exception as exc:
        log(f"wezterm activate failed pane_id={pane_id} error={exc}")
        return False
    if result.returncode != 0:
        log(f"wezterm activate failed pane_id={pane_id} rc={result.returncode}")
        return False
    log(f"wezterm pane activated pane_id={pane_id} cwd={short_cwd(cwd)}")
    return True


def focus_host(host_kind: str, cwd: str | None) -> None:
    if host_kind == "wezterm" and activate_wezterm_pane(cwd):
        return
    encoded = base64.b64encode(powershell_focus_script(host_kind).encode("utf-16le")).decode(
        "ascii"
    )
    subprocess.Popen(
        [
            "powershell",
            "-NoLogo",
            "-NoProfile",
            "-WindowStyle",
            "Hidden",
            "-EncodedCommand",
            encoded,
        ],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        close_fds=True,
    )


def run_popup(encoded_payload: str) -> int:
    import tkinter as tk

    try:
        payload = json.loads(base64.b64decode(encoded_payload).decode("utf-8"))
    except Exception:
        return 1

    title = payload.get("title", "Codex 上下文提醒")
    body = payload.get("body", "")
    host_kind = payload.get("host_kind", "")
    cwd = payload.get("cwd")

    root = tk.Tk()
    root.title(title)
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg="#1f2937")

    width = 430
    height = 124
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = max(screen_w - width - 24, 0)
    y = max(screen_h - height - 72, 0)
    root.geometry(f"{width}x{height}+{x}+{y}")

    frame = tk.Frame(root, bg="#1f2937", highlightbackground="#60a5fa", highlightthickness=1)
    frame.pack(fill="both", expand=True)

    title_label = tk.Label(
        frame,
        text=title,
        bg="#1f2937",
        fg="#f9fafb",
        font=("Segoe UI", 11, "bold"),
        anchor="w",
        justify="left",
    )
    title_label.pack(fill="x", padx=12, pady=(10, 4))

    body_label = tk.Label(
        frame,
        text=body,
        bg="#1f2937",
        fg="#d1d5db",
        font=("Segoe UI", 10),
        anchor="w",
        justify="left",
        wraplength=400,
    )
    body_label.pack(fill="both", expand=True, padx=12, pady=(0, 6))

    hint_label = tk.Label(
        frame,
        text=(
            "点击此通知可尝试激活对应 WezTerm pane"
            if host_kind == "wezterm"
            else "点击此通知可尝试切到对应宿主窗口"
        ),
        bg="#1f2937",
        fg="#93c5fd",
        font=("Segoe UI", 9),
        anchor="w",
        justify="left",
    )
    hint_label.pack(fill="x", padx=12, pady=(0, 10))

    def on_click(_event=None) -> None:
        if host_kind:
            focus_host(host_kind, cwd)
        root.destroy()

    for widget in (root, frame, title_label, body_label, hint_label):
        widget.bind("<Button-1>", on_click)

    root.after(15000, root.destroy)
    root.mainloop()
    return 0


def run_loop() -> int:
    existing_pid = read_pid()
    if existing_pid and existing_pid != os.getpid() and pid_is_running(existing_pid):
        log(f"duplicate watcher suppressed existing_pid={existing_pid} new_pid={os.getpid()}")
        return 0
    other_pids = [pid for pid in find_watcher_pids() if pid != os.getpid()]
    if other_pids:
        log(f"duplicate watcher suppressed running_pids={other_pids} new_pid={os.getpid()}")
        return 0
    write_pid(os.getpid())
    log("watcher started")
    watcher_start_ts = time.time()
    known: dict[str, ThreadState] = {}
    try:
        while True:
            try:
                threads = fetch_threads()
                current_ids = set()
                for meta in threads:
                    rollout = meta.get("rollout_path")
                    if not rollout:
                        continue
                    current_ids.add(meta["id"])
                    state = known.get(meta["id"])
                    if state is None:
                        known[meta["id"]] = ThreadState(meta, watcher_start_ts)
                    else:
                        state.sync_meta(meta)
                stale_ids = [tid for tid in known if tid not in current_ids]
                for tid in stale_ids:
                    known.pop(tid, None)
                for state in list(known.values()):
                    state.poll()
            except Exception as exc:
                log(f"loop error: {exc}")
            time.sleep(POLL_INTERVAL_SECONDS)
    finally:
        remove_pid()
        log("watcher stopped")
    return 0


def cmd_start() -> int:
    running_pids = find_watcher_pids()
    if running_pids:
        write_pid(running_pids[0])
        extra = f", extra={','.join(str(pid) for pid in running_pids[1:])}" if len(running_pids) > 1 else ""
        print(f"codex context watcher already running (pid={running_pids[0]}{extra})")
        return 0
    pid = read_pid()
    if pid and pid_is_running(pid):
        print(f"codex context watcher already running (pid={pid})")
        return 0
    remove_pid()
    pythonw = detect_pythonw()
    script = str(SCRIPT_PATH)
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
        subprocess, "CREATE_NEW_PROCESS_GROUP", 0
    )
    subprocess.Popen(
        [pythonw, script, "run"],
        cwd=str(Path(__file__).resolve().parent),
        close_fds=True,
        creationflags=flags,
    )
    deadline = time.time() + 3.0
    while time.time() < deadline:
        time.sleep(0.3)
        running_pids = find_watcher_pids()
        if running_pids:
            write_pid(running_pids[0])
            print(f"codex context watcher started (pid={running_pids[0]})")
            return 0
    print("failed to start codex context watcher")
    return 1


def cmd_stop() -> int:
    pid = read_pid()
    running_pids = sorted(set(find_watcher_pids() + ([pid] if pid else [])))
    if not running_pids:
        remove_pid()
        print("codex context watcher is not running")
        return 0
    for watcher_pid in running_pids:
        subprocess.run(
            ["taskkill", "/PID", str(watcher_pid), "/T", "/F"],
            capture_output=True,
            text=True,
        )
    time.sleep(0.5)
    remove_pid()
    joined = ",".join(str(watcher_pid) for watcher_pid in running_pids)
    print(f"codex context watcher stopped (pid={joined})")
    return 0


def cmd_status() -> int:
    running_pids = sorted(set(find_watcher_pids()))
    if running_pids:
        write_pid(running_pids[0])
        extra = f", extra={','.join(str(pid) for pid in running_pids[1:])}" if len(running_pids) > 1 else ""
        print(f"codex context watcher running (pid={running_pids[0]}{extra})")
        return 0
    remove_pid()
    print("codex context watcher is not running")
    return 1


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return cmd_start()
    cmd = argv[1].lower()
    if cmd == "popup" and len(argv) >= 3:
        return run_popup(argv[2])
    if cmd == "run":
        return run_loop()
    if cmd == "start":
        return cmd_start()
    if cmd == "stop":
        return cmd_stop()
    if cmd == "status":
        return cmd_status()
    print("usage: codex_context_watcher.py [start|stop|status|run]")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
