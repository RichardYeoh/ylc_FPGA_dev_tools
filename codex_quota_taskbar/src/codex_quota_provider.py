from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
USAGE_URLS = [
    "https://chatgpt.com/backend-api/codex/usage",
]
TOKEN_URL = "https://auth.openai.com/oauth/token"
REQUEST_TIMEOUT_SECONDS = 6


@dataclass(frozen=True)
class QuotaWindow:
    key: str
    label: str
    remaining_fraction: float | None
    remaining_text: str
    reset_at: datetime | None


@dataclass(frozen=True)
class QuotaSnapshot:
    source: str
    updated_at: datetime | None
    five_hour: QuotaWindow
    weekly: QuotaWindow


def load_json(path: Path) -> dict[str, Any]:
    # Read UTF-8 JSON state / 读取 UTF-8 JSON 状态文件
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def write_json(path: Path, data: dict[str, Any]) -> None:
    # Cache normalized quota data in the project / 在项目内缓存标准化后的配额数据
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_config(project_root: Path) -> dict[str, Any]:
    # Keep configuration local to the project / 配置固定保存在项目目录内
    return load_json(project_root / "config.json")


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def datetime_to_iso(value: Any) -> str | None:
    if value is None:
        return None
    try:
        timestamp = float(value)
    except (TypeError, ValueError):
        return None
    if timestamp <= 0:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def normalize_fraction(value: Any) -> float | None:
    if value is None:
        return None
    try:
        fraction = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, fraction))


def normalize_remaining_text(fraction: float | None, value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if fraction is None:
        return "--%"
    return f"{fraction * 100:02.0f}%"


def build_window(key: str, label: str, raw: dict[str, Any] | None) -> QuotaWindow:
    raw = raw or {}
    fraction = normalize_fraction(raw.get("remaining_fraction"))
    return QuotaWindow(
        key=key,
        label=label,
        remaining_fraction=fraction,
        remaining_text=normalize_remaining_text(fraction, raw.get("remaining_text")),
        reset_at=parse_datetime(raw.get("reset_at")),
    )


def run_provider_command(project_root: Path, command: list[str]) -> dict[str, Any] | None:
    if not command:
        return None
    try:
        result = subprocess.run(
            command,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def find_codex_auth_file() -> Path:
    # Respect CODEX_HOME when present / 优先使用 CODEX_HOME 指定的 Codex 主目录
    import os

    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home) / "auth.json"
    return Path.home() / ".codex" / "auth.json"


def read_codex_auth() -> dict[str, Any]:
    auth_path = find_codex_auth_file()
    return load_json(auth_path)


def refresh_access_token(auth: dict[str, Any]) -> str:
    tokens = auth.get("tokens", {})
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise RuntimeError("Codex auth.json has no refresh token")
    payload = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": CLIENT_ID,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        data = json.loads(response.read().decode("utf-8"))
    return str(data["access_token"])


def fetch_usage_with_token(url: str, access_token: str, account_id: str) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "User-Agent": "CodexQuotaTaskbar/0.1",
    }
    if account_id:
        headers["chatgpt-account-id"] = account_id
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_live_usage() -> dict[str, Any]:
    auth = read_codex_auth()
    tokens = auth.get("tokens", {})
    access_token = tokens.get("access_token")
    if not access_token:
        raise RuntimeError("Codex auth.json has no access token")
    account_id = str(tokens.get("account_id", ""))
    last_error: Exception | None = None
    for url in USAGE_URLS:
        token = access_token
        for attempt in range(3):
            try:
                return fetch_usage_with_token(url, token, account_id)
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code in (401, 403) and attempt == 0:
                    token = refresh_access_token(auth)
                    continue
                break
            except Exception as exc:
                last_error = exc
                continue
    if last_error:
        raise last_error
    raise RuntimeError("No Codex usage endpoint was tried")


def normalize_api_window(raw: dict[str, Any] | None) -> dict[str, Any]:
    raw = raw or {}
    used_percent = raw.get("used_percent")
    try:
        used = float(used_percent)
    except (TypeError, ValueError):
        used = None
    remaining_fraction = None if used is None else max(0.0, min(1.0, (100.0 - used) / 100.0))
    remaining_text = "--%" if remaining_fraction is None else f"{remaining_fraction * 100:.0f}%"
    return {
        "remaining_fraction": remaining_fraction,
        "remaining_text": remaining_text,
        "reset_at": datetime_to_iso(raw.get("reset_at")),
    }


def normalize_api_usage(api_data: dict[str, Any]) -> dict[str, Any]:
    rate_limit = api_data.get("rate_limit") or {}
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "chatgpt-codex-usage-api",
        "plan": api_data.get("plan_type", "unknown"),
        "windows": {
            "5h": normalize_api_window(rate_limit.get("primary_window")),
            "weekly": normalize_api_window(rate_limit.get("secondary_window")),
        },
    }


def load_cached_or_live(project_root: Path, quota_cfg: dict[str, Any]) -> dict[str, Any] | None:
    if not quota_cfg.get("use_live_api", True):
        return None
    cache_path = project_root / quota_cfg.get("cache_file", "quota_cache.json")
    max_age = max(30, int(quota_cfg.get("api_refresh_seconds", 300)))
    try:
        cached = load_json(cache_path)
        updated_at = parse_datetime(cached.get("updated_at"))
        now = datetime.now(updated_at.tzinfo) if updated_at and updated_at.tzinfo else datetime.now()
        if updated_at and (now - updated_at).total_seconds() < max_age:
            return cached
    except Exception:
        pass
    for _attempt in range(3):
        try:
            normalized = normalize_api_usage(fetch_live_usage())
            write_json(cache_path, normalized)
            return normalized
        except Exception:
            continue
    try:
        return load_json(cache_path)
    except Exception:
        return None


def load_snapshot(project_root: Path) -> QuotaSnapshot:
    config = load_config(project_root)
    quota_cfg = config.get("quota", {})
    provider_data = run_provider_command(project_root, quota_cfg.get("provider_command", []))
    if provider_data is None:
        provider_data = load_cached_or_live(project_root, quota_cfg)
    state_path = project_root / quota_cfg.get("state_file", "quota_state.json")
    data = provider_data if provider_data is not None else load_json(state_path)
    windows = data.get("windows", {})
    return QuotaSnapshot(
        source=str(data.get("source", "unknown")),
        updated_at=parse_datetime(data.get("updated_at")),
        five_hour=build_window("5h", "5h", windows.get("5h")),
        weekly=build_window("weekly", "W", windows.get("weekly")),
    )
