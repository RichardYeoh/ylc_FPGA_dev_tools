from __future__ import annotations

from codex_quota_provider import load_snapshot
from codex_quota_taskbar import project_root


def main() -> int:
    # Validate provider and compact formatting path / 验证配额读取和紧凑格式化路径
    snapshot = load_snapshot(project_root())
    assert snapshot.five_hour.key == "5h"
    assert snapshot.weekly.key == "weekly"
    print("snapshot_ok", snapshot.source, snapshot.five_hour.remaining_text, snapshot.weekly.remaining_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
