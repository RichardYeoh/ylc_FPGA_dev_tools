from __future__ import annotations

from datetime import datetime, timezone

from codex_quota_provider import load_snapshot, normalize_api_usage
from codex_quota_taskbar import bitmap_lines_size, display_remaining_text, format_weekly_display_lines, project_root, quota_value_color, to_hong_kong_time
from codex_quota_watcher import app_is_running, codex_is_running


def main() -> int:
    # Validate provider and compact formatting path / 验证配额读取和紧凑格式化路径
    snapshot = load_snapshot(project_root())
    assert snapshot.five_hour.key == "5h"
    assert snapshot.weekly.key == "weekly"
    assert snapshot.weekly.remaining_fraction is not None
    assert display_remaining_text("92%") == "92"
    assert display_remaining_text("--%") == "--"
    assert format_weekly_display_lines("7%", None) == ["W   7", "   --:--"]
    assert format_weekly_display_lines("59%", None) == ["W  59", "   --:--"]
    single_window = normalize_api_usage({"rate_limit": {"primary_window": {"used_percent": 2, "reset_at": 1_784_000_000}}})
    assert single_window["windows"]["5h"]["remaining_text"] == "--%"
    assert single_window["windows"]["weekly"]["remaining_text"] == "98%"
    dual_window = normalize_api_usage({"rate_limit": {"primary_window": {"used_percent": 10, "reset_at": 1_784_000_000}, "secondary_window": {"used_percent": 20, "reset_at": 1_784_100_000}}})
    assert dual_window["windows"]["5h"]["remaining_text"] == "90%"
    assert dual_window["windows"]["weekly"]["remaining_text"] == "80%"
    assert quota_value_color(snapshot, {"text_color": "normal", "warning_color": "warning", "critical_color": "critical", "unknown_color": "unknown"}) in {"normal", "warning", "critical", "unknown"}
    assert to_hong_kong_time(datetime(2026, 6, 5, 13, 0, tzinfo=timezone.utc)).strftime("%Y-%m-%d %H:%M") == "2026-06-05 21:00"
    assert to_hong_kong_time(datetime(2026, 6, 11, 3, 0, tzinfo=timezone.utc)).strftime("%Y-%m-%d %H:%M") == "2026-06-11 11:00"
    root = project_root()
    fake_self = [("pythonw.exe", str(root / "src" / "codex_quota_taskbar.py"))]
    watcher_cfg = {"process_patterns": ["codex.exe", "codex"]}
    assert app_is_running(fake_self, root)
    assert not codex_is_running(fake_self, watcher_cfg, root)
    width, height = bitmap_lines_size(["W  92", "06/11 03"], 2, 1, 3)
    assert width == 71 and height == 27
    print("snapshot_ok", snapshot.source, snapshot.weekly.remaining_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
