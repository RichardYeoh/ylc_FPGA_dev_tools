from __future__ import annotations

from datetime import datetime, timezone

from codex_quota_provider import load_snapshot
from codex_quota_taskbar import project_root, to_hong_kong_time
from codex_quota_watcher import app_is_running, codex_is_running


def main() -> int:
    # Validate provider and compact formatting path / 验证配额读取和紧凑格式化路径
    snapshot = load_snapshot(project_root())
    assert snapshot.five_hour.key == "5h"
    assert snapshot.weekly.key == "weekly"
    assert to_hong_kong_time(datetime(2026, 6, 5, 13, 0, tzinfo=timezone.utc)).strftime("%Y-%m-%d %H:%M") == "2026-06-05 21:00"
    assert to_hong_kong_time(datetime(2026, 6, 11, 3, 0, tzinfo=timezone.utc)).strftime("%Y-%m-%d %H:%M") == "2026-06-11 11:00"
    root = project_root()
    fake_self = [("pythonw.exe", str(root / "src" / "codex_quota_taskbar.py"))]
    watcher_cfg = {"process_patterns": ["codex.exe", "codex"]}
    assert app_is_running(fake_self, root)
    assert not codex_is_running(fake_self, watcher_cfg, root)
    print("snapshot_ok", snapshot.source, snapshot.five_hour.remaining_text, snapshot.weekly.remaining_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
