from __future__ import annotations

import ctypes
import os
import sys
import tkinter as tk
from datetime import datetime, timedelta, timezone
from pathlib import Path
from ctypes import wintypes

from codex_quota_provider import QuotaSnapshot, load_config, load_snapshot


SPI_GETWORKAREA = 0x0030
GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CHILD = 0x40000000
WS_POPUP = 0x80000000
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
HWND_TOPMOST = -1
SW_SHOWNOACTIVATE = 4
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SM_CXSCREEN = 0
SM_CYSCREEN = 1
ERROR_ALREADY_EXISTS = 183
HONG_KONG_TZ = timezone(timedelta(hours=8), "HKT")


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def setup_user32_api() -> None:
    user32 = ctypes.windll.user32
    user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    user32.FindWindowW.restype = wintypes.HWND
    user32.EnumWindows.restype = wintypes.BOOL
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]
    user32.SetParent.restype = wintypes.HWND
    user32.EnumChildWindows.restype = wintypes.BOOL
    user32.MoveWindow.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.BOOL]
    user32.MoveWindow.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.SetWindowPos.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.restype = ctypes.c_int


setup_user32_api()


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def acquire_single_instance(name: str) -> object | None:
    # Named mutex prevents duplicate compact windows / 命名互斥量防止重复显示窗口
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, name)
    if not handle or ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        return None
    return handle


def get_work_area() -> tuple[RECT, int, int]:
    rect = RECT()
    # Query Windows work area excluding the taskbar / 查询排除任务栏后的 Windows 工作区
    ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
    screen_w = ctypes.windll.user32.GetSystemMetrics(SM_CXSCREEN)
    screen_h = ctypes.windll.user32.GetSystemMetrics(SM_CYSCREEN)
    return rect, screen_w, screen_h


def get_window_rect(hwnd: int) -> RECT | None:
    rect = RECT()
    if not hwnd or not ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return rect


def rect_width(rect: RECT) -> int:
    return int(rect.right - rect.left)


def rect_height(rect: RECT) -> int:
    return int(rect.bottom - rect.top)


def find_child_window(parent_hwnd: int, class_name: str) -> int:
    result = ctypes.c_void_p(0)
    enum_proc_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @enum_proc_type
    def enum_proc(hwnd: int, _lparam: int) -> bool:
        buffer = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetClassNameW(hwnd, buffer, len(buffer))
        if buffer.value == class_name:
            result.value = hwnd
            return False
        return True

    ctypes.windll.user32.EnumChildWindows(parent_hwnd, enum_proc, 0)
    return int(result.value or 0)


def find_process_window(class_name: str) -> int:
    result = ctypes.c_void_p(0)
    current_pid = os.getpid()
    enum_proc_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @enum_proc_type
    def enum_proc(hwnd: int, _lparam: int) -> bool:
        window_pid = wintypes.DWORD(0)
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
        if int(window_pid.value) != current_pid:
            return True
        buffer = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetClassNameW(hwnd, buffer, len(buffer))
        if buffer.value == class_name:
            result.value = hwnd
            return False
        return True

    ctypes.windll.user32.EnumWindows(enum_proc, 0)
    return int(result.value or 0)


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def parse_hwnd(value: object) -> int:
    text = str(value).strip()
    if not text:
        return 0
    try:
        return int(text, 0)
    except ValueError:
        return 0


def to_hong_kong_time(dt: datetime) -> datetime:
    # Display all reset windows in Hong Kong time / 所有复位窗口统一按香港时间显示
    return dt.astimezone(HONG_KONG_TZ) if dt.tzinfo else dt.replace(tzinfo=HONG_KONG_TZ)


def format_reset_time(dt: datetime | None) -> str:
    if dt is None:
        return "--:--"
    display_dt = to_hong_kong_time(dt)
    now = datetime.now(HONG_KONG_TZ)
    if display_dt.date() == now.date():
        return display_dt.strftime("%H:%M")
    return display_dt.strftime("%m/%d %H")


def quota_value_color(snapshot: QuotaSnapshot, window_cfg: dict) -> str:
    fractions = [
        value
        for value in (snapshot.five_hour.remaining_fraction, snapshot.weekly.remaining_fraction)
        if value is not None
    ]
    if not fractions:
        return str(window_cfg.get("unknown_color", "#374151"))
    lowest = min(fractions)
    if lowest <= 0.10:
        return str(window_cfg.get("critical_color", "#b91c1c"))
    if lowest <= 0.25:
        return str(window_cfg.get("warning_color", "#b45309"))
    return str(window_cfg.get("text_color", "#111827"))


class QuotaTaskbarWindow:
    def __init__(self) -> None:
        self.root_dir = project_root()
        self.config = load_config(self.root_dir)
        self.window_cfg = self.config.get("window", {})
        self.quota_cfg = self.config.get("quota", {})
        self.position_mode = self.window_cfg.get("position", "taskbar_docked")
        self.taskbar_hwnd = 0
        self.is_taskbar_child = False
        self.transparent_color = str(self.window_cfg.get("transparent_color", "#ff00ff"))
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", float(self.window_cfg.get("opacity", 0.92)))
        if self.window_cfg.get("transparent_background", True):
            self.root.attributes("-transparentcolor", self.transparent_color)
            background = self.transparent_color
        else:
            background = str(self.window_cfg.get("background", "#101418"))
        self.root.configure(bg=background)
        font_family = self.window_cfg.get("font_family", "Consolas")
        font_size = int(self.window_cfg.get("font_size", 10))
        self.cells: dict[str, tk.Label] = {}
        self.root.grid_columnconfigure(0, weight=0)
        self.root.grid_columnconfigure(1, weight=0)
        self.root.grid_columnconfigure(2, weight=1)
        for row, key in enumerate(("five", "week")):
            self.cells[f"{key}_label"] = self.make_cell(row, 0, "5h" if key == "five" else "W", background, font_family, font_size)
            self.cells[f"{key}_value"] = self.make_cell(row, 1, "--%", background, font_family, font_size)
            self.cells[f"{key}_time"] = self.make_cell(row, 2, "--:--", background, font_family, font_size)
        if not self.window_cfg.get("click_through", True):
            self.root.bind("<Button-3>", self.exit_app)
            self.root.bind("<Double-Button-1>", self.toggle_position)
            for cell in self.cells.values():
                cell.bind("<Button-3>", self.exit_app)
                cell.bind("<Double-Button-1>", self.toggle_position)
        self.root.after(50, self.apply_window_style)
        self.root.after(100, self.refresh)

    def make_cell(
        self,
        row: int,
        column: int,
        text: str,
        background: str,
        font_family: str,
        font_size: int,
    ) -> tk.Label:
        cell = tk.Label(
            self.root,
            text=text,
            justify="left",
            anchor="w",
            padx=int(self.window_cfg.get("pad_x", 1)),
            pady=int(self.window_cfg.get("pad_y", 0)),
            bg=background,
            fg=str(self.window_cfg.get("text_color", "#0f3d4c")),
            font=(font_family, font_size, "bold"),
        )
        cell.grid(row=row, column=column, sticky="w", padx=(0, int(self.window_cfg.get("column_gap", 2))))
        return cell

    def hwnd(self) -> int:
        # Tk on Windows has an outer frame HWND and an inner child HWND / Windows 下 Tk 同时有外层 frame 窗口和内层 child 窗口
        self.root.update_idletasks()
        toplevel_hwnd = find_process_window("TkTopLevel")
        frame_hwnd = parse_hwnd(self.root.frame())
        return toplevel_hwnd or frame_hwnd or int(self.root.winfo_id())

    def apply_window_style(self) -> None:
        hwnd = self.hwnd()
        user32 = ctypes.windll.user32
        # Hide from Alt-Tab and avoid taking focus / 从 Alt-Tab 隐藏并避免抢焦点
        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ex_style |= WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        if self.window_cfg.get("transparent_background", True):
            ex_style |= WS_EX_LAYERED
        if self.window_cfg.get("click_through", True):
            ex_style |= WS_EX_TRANSPARENT
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
        self.taskbar_hwnd = int(user32.FindWindowW("Shell_TrayWnd", None) or 0)
        self.place_window()

    def attach_to_taskbar(self, hwnd: int) -> None:
        user32 = ctypes.windll.user32
        taskbar_hwnd = int(user32.FindWindowW("Shell_TrayWnd", None) or 0)
        if not taskbar_hwnd:
            return
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        user32.SetWindowLongW(hwnd, GWL_STYLE, (style | WS_CHILD) & ~WS_POPUP)
        user32.SetParent(hwnd, taskbar_hwnd)
        self.taskbar_hwnd = taskbar_hwnd
        self.is_taskbar_child = True

    def place_window(self) -> None:
        hwnd = self.hwnd()
        if self.position_mode != "taskbar_docked" and self.is_taskbar_child:
            self.detach_from_taskbar(hwnd)

        rect, screen_w, screen_h = get_work_area()
        width = int(self.window_cfg.get("width", 116))
        height = int(self.window_cfg.get("height", 40))
        if self.window_cfg.get("auto_size", True):
            self.root.update_idletasks()
            width = max(1, int(self.root.winfo_reqwidth()))
            height = max(1, int(self.root.winfo_reqheight()))
        margin_x = int(self.window_cfg.get("margin_x", 96))
        margin_y = int(self.window_cfg.get("margin_y", 4))
        dock_gap = int(self.window_cfg.get("dock_gap", 8))
        dock_offset_x = int(self.window_cfg.get("dock_offset_x", 0))
        bottom_taskbar = rect.bottom < screen_h
        right_taskbar = rect.right < screen_w
        left_taskbar = rect.left > 0
        top_taskbar = rect.top > 0

        if self.position_mode == "taskbar_docked" and self.taskbar_hwnd:
            if self.place_docked_window(width, height, dock_gap, dock_offset_x):
                self.ensure_visible()
                return

        if self.position_mode == "above_taskbar" or (self.position_mode == "taskbar_docked" and not bottom_taskbar):
            x = max(rect.left, rect.right - width - margin_x)
            y = max(rect.top, rect.bottom - height - margin_y)
        elif bottom_taskbar:
            taskbar_h = screen_h - rect.bottom
            x = max(rect.left, rect.right - width - margin_x)
            y = rect.bottom + max(0, (taskbar_h - height) // 2)
        elif right_taskbar:
            taskbar_w = screen_w - rect.right
            x = rect.right + max(0, (taskbar_w - width) // 2)
            y = max(rect.top, rect.bottom - height - margin_y)
        elif left_taskbar:
            x = max(0, (rect.left - width) // 2)
            y = max(rect.top, rect.bottom - height - margin_y)
        elif top_taskbar:
            x = max(rect.left, rect.right - width - margin_x)
            y = max(0, (rect.top - height) // 2)
        else:
            x = screen_w - width - margin_x
            y = screen_h - height - margin_y
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.ensure_visible()

    def ensure_visible(self) -> None:
        hwnd = self.hwnd()
        if not hwnd:
            return
        user32 = ctypes.windll.user32
        # Restore after Show Desktop or taskbar status interactions / 在显示桌面或任务栏状态交互后恢复显示
        user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
        user32.SetWindowPos(
            hwnd,
            HWND_TOPMOST,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )

    def detach_from_taskbar(self, hwnd: int) -> None:
        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        user32.SetParent(hwnd, 0)
        user32.SetWindowLongW(hwnd, GWL_STYLE, (style | WS_POPUP) & ~WS_CHILD)
        self.is_taskbar_child = False

    def place_docked_window(self, width: int, height: int, dock_gap: int, dock_offset_x: int) -> bool:
        taskbar_rect = get_window_rect(self.taskbar_hwnd)
        if taskbar_rect is None:
            return False
        tray_hwnd = find_child_window(self.taskbar_hwnd, "TrayNotifyWnd")
        tray_rect = get_window_rect(tray_hwnd) if tray_hwnd else None
        taskbar_w = rect_width(taskbar_rect)
        taskbar_h = rect_height(taskbar_rect)
        screen_x = (tray_rect.left - width - dock_gap) if tray_rect else (taskbar_rect.right - width - dock_gap)
        screen_x += dock_offset_x
        screen_y = taskbar_rect.top + max(0, (taskbar_h - height) // 2)
        if taskbar_h > taskbar_w:
            screen_x = taskbar_rect.left + max(0, (taskbar_w - width) // 2)
            screen_y = (tray_rect.top - height - dock_gap) if tray_rect else (taskbar_rect.bottom - height - dock_gap)
        x = clamp(int(screen_x), taskbar_rect.left, max(taskbar_rect.left, taskbar_rect.right - width))
        y = clamp(int(screen_y), taskbar_rect.top, max(taskbar_rect.top, taskbar_rect.bottom - height))
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        return True

    def toggle_position(self, _event: object | None = None) -> None:
        # Double-click swaps docked and above-taskbar modes / 双击在任务栏停靠和贴近任务栏上方之间切换
        self.position_mode = "above_taskbar" if self.position_mode == "taskbar_docked" else "taskbar_docked"
        self.place_window()

    def render_snapshot(self, snapshot: QuotaSnapshot) -> None:
        text_color = quota_value_color(snapshot, self.window_cfg)
        rows = (("five", snapshot.five_hour), ("week", snapshot.weekly))
        for key, window in rows:
            self.cells[f"{key}_label"].configure(text=window.label, fg=text_color)
            self.cells[f"{key}_value"].configure(text=window.remaining_text, fg=text_color)
            self.cells[f"{key}_time"].configure(text=format_reset_time(window.reset_at), fg=text_color)

    def refresh(self) -> None:
        try:
            snapshot = load_snapshot(self.root_dir)
            self.render_snapshot(snapshot)
        except Exception:
            self.cells["five_label"].configure(text="5h")
            self.cells["five_value"].configure(text="ERR", fg=str(self.window_cfg.get("critical_color", "#b91c1c")))
            self.cells["five_time"].configure(text="--:--")
            self.cells["week_label"].configure(text="W")
            self.cells["week_value"].configure(text="ERR", fg=str(self.window_cfg.get("critical_color", "#b91c1c")))
            self.cells["week_time"].configure(text="--:--")
        self.place_window()
        interval_ms = max(1, int(self.quota_cfg.get("refresh_seconds", 2))) * 1000
        self.root.after(interval_ms, self.refresh)

    def exit_app(self, _event: object | None = None) -> None:
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    mutex = acquire_single_instance("Local\\CodexQuotaTaskbarWindow")
    if mutex is None:
        return 0
    QuotaTaskbarWindow().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
