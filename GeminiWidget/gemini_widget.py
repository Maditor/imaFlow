"""
GeminiWidget - mo Gemini bang cua so Chrome/Edge that (app mode, khong thanh tab),
va tu dong ghim always-on-top bang Win32 API (SetWindowPos), khong can PowerToys.

Chi dung ctypes + thu vien chuan Python de tim/pin cua so, va pystray de co
1 icon nho o khay he thong (system tray) cho anh bat/tat pin hoac thoat.
"""

import ctypes
import ctypes.wintypes as wintypes
import json
import os
import subprocess
import sys
import threading
import time

GEMINI_URL = "https://gemini.google.com/"

# Kich thuoc/vi tri mac dinh — CHI dung cho lan dau tien chay (chua co file
# config nao duoc luu). Nhung lan sau, kich thuoc/vi tri thuc te cua cua so
# (anh tu keo/resize) se duoc nho lai va dung lai, xem CONFIG_PATH ben duoi.
DEFAULT_WINDOW = {"x": 1200, "y": 80, "w": 420, "h": 760}

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "GeminiWidget")
CONFIG_PATH = os.path.join(CONFIG_DIR, "window_config.json")


def load_window_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        cfg = dict(DEFAULT_WINDOW)
        cfg.update({k: int(v) for k, v in data.items() if k in ("x", "y", "w", "h")})
        return cfg
    except Exception:
        return dict(DEFAULT_WINDOW)


def save_window_config(cfg):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
    except Exception:
        pass  # khong lam gian doan ung dung neu ghi file that bai


# ---------- Single instance lock (Windows Named Mutex) ----------
# Neu bam mo GeminiWidget nhieu lan (hoac bam nut "Mo Gemini" trong panel
# nhieu lan lien tuc), khong cho tao them tien trinh moi -> tranh tinh
# trang nhieu icon tray + nhieu cua so Gemini chong chat nhau.
SINGLE_INSTANCE_MUTEX_NAME = "Local\\GeminiWidget_SingleInstance_Mutex_ImaFlow"
ERROR_ALREADY_EXISTS = 183


def acquire_single_instance_lock():
    kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.GetLastError.restype = wintypes.DWORD

    handle = kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX_NAME)
    already_running = kernel32.GetLastError() == ERROR_ALREADY_EXISTS
    return handle, already_running


# ---------- Win32 constants ----------
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Khai bao ro argtypes/restype cho tung ham Win32 dung den — bat buoc tren
# Windows 64-bit, neu khong HWND (con tro 64-bit) co the bi cat cut khi
# ctypes tu doan kieu du lieu mac dinh, khien SetWindowPos "gui nham dia chi"
# va am tham that bai (khong bao loi gi ca).
user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.UINT,
]
user32.SetWindowPos.restype = wintypes.BOOL

user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL

user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD

user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int

user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int

user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL

user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL

user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL

user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL

user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL

ENUM_WINDOWS_PROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [ENUM_WINDOWS_PROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL


def find_browser_path():
    """Tim Brave, Coc Coc, Chrome hoac Edge da cai tren may (uu tien Brave/Coc Coc truoc)."""
    pf = os.environ.get("ProgramFiles", "")
    pf86 = os.environ.get("ProgramFiles(x86)", "")
    local = os.environ.get("LocalAppData", "")

    candidates = [
        os.path.join(local, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
        os.path.join(pf, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
        os.path.join(pf86, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
        os.path.join(local, "CocCoc", "Browser", "Application", "browser.exe"),
        os.path.join(pf, "CocCoc", "Browser", "Application", "browser.exe"),
        os.path.join(pf86, "CocCoc", "Browser", "Application", "browser.exe"),
        os.path.join(pf, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(pf86, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(local, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(pf86, "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(pf, "Microsoft", "Edge", "Application", "msedge.exe"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def launch_browser_app_mode(browser_path, window_cfg):
    args = [
        browser_path,
        "--app=" + GEMINI_URL,
        "--window-size={},{}".format(window_cfg["w"], window_cfg["h"]),
        "--window-position={},{}".format(window_cfg["x"], window_cfg["y"]),
    ]
    proc = subprocess.Popen(args)
    return proc.pid


def snapshot_gemini_windows():
    """Chup lai danh sach cac cua so dang mo co tieu de chua 'gemini' (khong phan biet hoa/thuong),
    dung de sau nay phat hien cua so MOI xuat hien (khac voi cac cua so da co san)."""
    existing = set()

    @ENUM_WINDOWS_PROC
    def enum_handler(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            title = get_window_title(hwnd)
            if "gemini" in title.lower():
                existing.add(hwnd)
        return True

    user32.EnumWindows(enum_handler, 0)
    return existing


def get_window_title(hwnd):
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def find_gemini_hwnd(target_pid, existing_windows, timeout_sec=12):
    """
    Tim cua so Gemini vua mo bang 2 cach song song:
    1) Cua so thuoc dung PID vua launch (truong hop chua co tien trinh nao chay san)
    2) Cua so MOI xuat hien co tieu de chua 'gemini', khac voi snapshot ban dau
       (truong hop trinh duyet da chay san, tien trinh moi chi la "nhan tin" roi thoat)
    """
    result = {"value": None}

    @ENUM_WINDOWS_PROC
    def enum_handler(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True

        title = get_window_title(hwnd)
        if not title:
            return True

        # Cach 1: khop PID
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == target_pid:
            result["value"] = hwnd
            return False

        # Cach 2: cua so moi, tieu de chua 'gemini', chua tung thay truoc do
        if "gemini" in title.lower() and hwnd not in existing_windows:
            result["value"] = hwnd
            return False

        return True

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        result["value"] = None
        user32.EnumWindows(enum_handler, 0)
        if result["value"]:
            return result["value"]
        time.sleep(0.3)
    return None


def apply_geometry_and_topmost(hwnd, cfg):
    """
    Ep cua so vao dung vi tri/kich thuoc da luu, DONG THOI ghim topmost —
    bang Win32 API truc tiep, KHONG phu thuoc vao Chrome co nghe theo tham so
    dong lenh --window-size/--window-position hay khong (Chrome hay BO QUA
    2 tham so nay neu dang "gui yeu cau" toi 1 tien trinh dang chay san,
    thay vi tu khoi dong tien trinh moi).
    """
    ok = user32.SetWindowPos(
        hwnd, HWND_TOPMOST,
        cfg["x"], cfg["y"], cfg["w"], cfg["h"],
        SWP_SHOWWINDOW,
    )
    if not ok:
        time.sleep(0.2)
        ok = user32.SetWindowPos(
            hwnd, HWND_TOPMOST,
            cfg["x"], cfg["y"], cfg["w"], cfg["h"],
            SWP_SHOWWINDOW,
        )
    return bool(ok)


def set_topmost(hwnd, topmost=True):
    flag = HWND_TOPMOST if topmost else HWND_NOTOPMOST
    ok = user32.SetWindowPos(hwnd, flag, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    if not ok:
        # Thu lai 1 lan (doi khi lan goi dau bi Windows bo qua do cua so
        # chua "on dinh" ngay sau khi vua tao)
        time.sleep(0.2)
        ok = user32.SetWindowPos(hwnd, flag, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    return bool(ok)


def bring_to_front(hwnd):
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)


def get_window_rect(hwnd):
    rect = wintypes.RECT()
    if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return {
            "x": rect.left,
            "y": rect.top,
            "w": rect.right - rect.left,
            "h": rect.bottom - rect.top,
        }
    return None


def watch_and_remember_window(hwnd):
    """
    Chay o thread rieng: cu vai giay kiem tra kich thuoc/vi tri cua so hien
    tai, neu khac lan luu gan nhat thi ghi lai vao file config — de lan mo
    sau tai dung kich thuoc anh vua chinh. Neu cua so bi dong, tu thoat app.
    """
    last_saved = None
    while True:
        time.sleep(1.5)

        if not user32.IsWindow(hwnd):
            # Cua so da bi dong (anh bam X) -> thoat luon ung dung
            os._exit(0)

        rect = get_window_rect(hwnd)
        if not rect or rect["w"] < 50 or rect["h"] < 50:
            continue

        current = (rect["x"], rect["y"], rect["w"], rect["h"])
        if current != last_saved:
            save_window_config(rect)
            last_saved = current


class GeminiWidgetApp:
    def __init__(self):
        self.hwnd = None
        self.pinned = True

    def start(self):
        browser_path = find_browser_path()
        if not browser_path:
            self._fatal("Khong tim thay Chrome hoac Edge tren may.\n"
                        "Hay cai Chrome hoac Edge roi chay lai.")
            return

        # Chup snapshot cua so Gemini truoc khi mo, de sau do phat hien dung
        # cua so MOI (tranh truong hop trinh duyet da chay san lam PID vua
        # launch "chet" ngay lap tuc va khong tao cua so nao ca)
        existing_windows = snapshot_gemini_windows()

        window_cfg = load_window_config()
        pid = launch_browser_app_mode(browser_path, window_cfg)
        self.hwnd = find_gemini_hwnd(pid, existing_windows)

        if not self.hwnd:
            self._fatal(
                "Khong tim thay cua so Gemini vua mo.\n\n"
                "Co the do trinh duyet dang chay o che do khac (vi du dang "
                "mo san 1 tab Gemini thuong, khong phai app-mode). Hay dong "
                "het cua so Gemini dang mo roi chay lai ung dung nay."
            )
            return

        pinned_ok = apply_geometry_and_topmost(self.hwnd, window_cfg)
        if not pinned_ok:
            # Cua so co the van con dang "on dinh" layout ngay sau khi tao —
            # doi 1 chut roi ep lai kich thuoc lan nua cho chac.
            time.sleep(0.5)
            pinned_ok = apply_geometry_and_topmost(self.hwnd, window_cfg)
        else:
            # Du thanh cong ngay lan dau, Chrome doi khi tu resize lai ngay
            # sau do (animation mo cua so) -> ep lai 1 lan nua cho chac an.
            time.sleep(0.4)
            apply_geometry_and_topmost(self.hwnd, window_cfg)
        self.pinned = pinned_ok
        if not pinned_ok:
            # Khong fatal - van mo cua so + tray binh thuong, chi bao cho anh
            # biet de thu ghim lai bang menu tray (khac quyen Admin la
            # nguyen nhan pho bien nhat).
            ctypes.windll.user32.MessageBoxW(
                0,
                "Da mo cua so Gemini nhung ghim khong thanh cong ngay.\n\n"
                "Thu bam 'Ghim noi' trong menu khay he thong (goc duoi phai "
                "man hinh). Neu van khong duoc, co the do cua so trinh "
                "duyet dang chay voi quyen Administrator con GeminiWidget "
                "thi khong - hay chay ca hai cung quyen (deu binh thuong "
                "hoac deu Admin).",
                "GeminiWidget",
                0x30,
            )

        self._start_size_watcher()
        self._run_tray()

    def _start_size_watcher(self):
        t = threading.Thread(target=watch_and_remember_window, args=(self.hwnd,), daemon=True)
        t.start()

    def toggle_pin(self, icon=None, item=None):
        if not self.hwnd:
            return
        new_state = not self.pinned
        ok = set_topmost(self.hwnd, new_state)
        if ok:
            self.pinned = new_state

    def show_window(self, icon=None, item=None):
        if self.hwnd:
            bring_to_front(self.hwnd)

    def quit_app(self, icon=None, item=None):
        if self.hwnd:
            rect = get_window_rect(self.hwnd)
            if rect and rect["w"] > 50 and rect["h"] > 50:
                save_window_config(rect)
            user32.PostMessageW(self.hwnd, 0x0010, 0, 0)  # WM_CLOSE
        if icon:
            icon.stop()
        sys.exit(0)

    def _fatal(self, message):
        ctypes.windll.user32.MessageBoxW(0, message, "GeminiWidget", 0x10)
        sys.exit(1)

    def _run_tray(self):
        try:
            import pystray
            from PIL import Image, ImageDraw

            def make_icon_image():
                img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
                d = ImageDraw.Draw(img)
                d.rounded_rectangle([4, 4, 60, 60], radius=14, fill=(66, 133, 244, 255))
                d.ellipse([20, 20, 44, 44], fill=(255, 255, 255, 255))
                return img

            menu = pystray.Menu(
                pystray.MenuItem(
                    "Ghim noi (Always On Top)",
                    self.toggle_pin,
                    checked=lambda item: self.pinned,
                ),
                pystray.MenuItem("Hien cua so Gemini", self.show_window),
                pystray.MenuItem("Thoat", self.quit_app),
            )
            icon = pystray.Icon("GeminiWidget", make_icon_image(), "Gemini Widget", menu)
            icon.run()
        except Exception:
            # Neu pystray khong dung duoc, van giu app song don gian bang vong lap
            # (cua so van da duoc ghim topmost roi, chi thieu khay he thong).
            while True:
                time.sleep(1)


if __name__ == "__main__":
    _mutex_handle, _already_running = acquire_single_instance_lock()

    if _already_running:
        # Thu tim va dua cua so Gemini dang mo san ra truoc, thay vi chi
        # bao "da chay roi" suong khong lam gi ca.
        _existing = snapshot_gemini_windows()
        if _existing:
            _hwnd = next(iter(_existing))
            set_topmost(_hwnd, True)
            bring_to_front(_hwnd)
        else:
            ctypes.windll.user32.MessageBoxW(
                0,
                "GeminiWidget dang chay roi.\n\n"
                "Kiem tra icon o khay he thong (goc duoi phai man hinh, "
                "canh dong ho) — cua so Gemini van dang mo o do.",
                "GeminiWidget",
                0x40,
            )
        sys.exit(0)

    GeminiWidgetApp().start()
