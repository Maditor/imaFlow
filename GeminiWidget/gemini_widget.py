"""
GeminiWidget - mo Gemini bang cua so Chrome/Edge that (app mode, khong thanh tab),
va tu dong ghim always-on-top bang Win32 API (SetWindowPos), khong can PowerToys.

Chi dung ctypes + thu vien chuan Python de tim/pin cua so, va pystray de co
1 icon nho o khay he thong (system tray) cho anh bat/tat pin hoac thoat.
"""

import atexit
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
CLICK_CONFIG_PATH = os.path.join(CONFIG_DIR, "click_config.json")


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

user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int
user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsIconic.restype = wintypes.BOOL
user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.BringWindowToTop.restype = wintypes.BOOL
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL

# Cua so trinh duyet nhan Chromium (Chrome/Edge/Brave/Coc Coc) deu co class nay.
CHROME_WINDOW_CLASS = "Chrome_WidgetWin_1"
BROWSER_EXE_NAMES = {"brave.exe", "browser.exe", "chrome.exe", "msedge.exe"}
STATE_PATH = os.path.join(CONFIG_DIR, "state.json")
WS_EX_TOPMOST = 0x00000008
GWL_EXSTYLE = -20


def get_class_name(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def get_process_exe_name(hwnd):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return ""
    h = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return os.path.basename(buf.value).lower()
    finally:
        kernel32.CloseHandle(h)
    return ""


def is_browser_window(hwnd):
    """Cua so top-level cua trinh duyet Chromium (KHONG BAO GIO la Photoshop, Explorer...)."""
    if not hwnd or not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd):
        return False
    if get_class_name(hwnd) != CHROME_WINDOW_CLASS:
        return False
    exe = get_process_exe_name(hwnd)
    return (exe in BROWSER_EXE_NAMES) if exe else True


def is_topmost(hwnd):
    return bool(user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOPMOST)


def save_state(hwnd):
    """Ban chinh ghi lai HWND cua so Gemini no dang quan ly, de cac lan goi
    --autopaste sau (tien trinh moi) tim DUNG cua so, khong phai do theo tieu de."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump({"hwnd": int(hwnd), "pid": os.getpid()}, f)
    except Exception:
        pass


def load_state_hwnd():
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        hwnd = int(data.get("hwnd") or 0)
    except Exception:
        return None
    # Chi tin HWND neu no van la cua so trinh duyet Gemini/dang ghim (HWND co the bi tai su dung)
    if not is_browser_window(hwnd):
        return None
    if "gemini" in get_window_title(hwnd).lower() or is_topmost(hwnd):
        return hwnd
    return None


def clear_state():
    try:
        os.remove(STATE_PATH)
    except Exception:
        pass


def find_running_gemini_hwnd():
    """Tim cua so Gemini cua ban widget dang chay: uu tien HWND da luu, roi moi do
    theo tieu de (chi trong cua so trinh duyet, uu tien cua so dang ghim topmost)."""
    hwnd = load_state_hwnd()
    if hwnd:
        return hwnd
    candidates = list(snapshot_gemini_windows())
    if not candidates:
        return None
    candidates.sort(key=lambda h: 0 if is_topmost(h) else 1)
    return candidates[0]


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

    # CHI xet cua so trinh duyet: truoc day do theo tieu de nen hay bat nham
    # Photoshop dang mo file "Gemini_Generated_Image_xxx.png" -> dan nguoc vao PS.
    @ENUM_WINDOWS_PROC
    def enum_handler(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            title = get_window_title(hwnd)
            if "gemini" in title.lower() and is_browser_window(hwnd):
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
        if get_class_name(hwnd) != CHROME_WINDOW_CLASS:
            return True  # khong phai cua so trinh duyet -> bo qua

        # Cach 1: khop PID
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == target_pid:
            result["value"] = hwnd
            return False

        # Cach 2: cua so moi, tieu de chua 'gemini', chua tung thay truoc do
        if "gemini" in title.lower() and hwnd not in existing_windows and is_browser_window(hwnd):
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
    cfg = dict(cfg)
    cfg["w"] = min(cfg["w"], max_window_width(hwnd))  # toi da 1/4 chieu ngang man hinh
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
    # SW_RESTORE chi khi dang thu nho (neu khong se lam mat trang thai maximize)
    user32.ShowWindow(hwnd, 9 if user32.IsIconic(hwnd) else 5)  # SW_RESTORE / SW_SHOW
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)


# ---------- Gioi han chieu ngang cua so toi da = 1/4 man hinh ----------
# De bo cuc trang Gemini on dinh (o nhap van ban luon o cung cho), cua so khong duoc
# rong qua 1/4 chieu ngang man hinh dang chua no.
class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]


user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
user32.MonitorFromWindow.restype = wintypes.HANDLE
user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MONITORINFO)]
user32.GetMonitorInfoW.restype = wintypes.BOOL
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int


def max_window_width(hwnd):
    width = 0
    try:
        mon = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if mon and user32.GetMonitorInfoW(mon, ctypes.byref(mi)):
            width = mi.rcMonitor.right - mi.rcMonitor.left
    except Exception:
        pass
    if width <= 0:
        width = user32.GetSystemMetrics(0)  # SM_CXSCREEN
    return max(200, width // 4)


# ---------- Gia lap click chuot vao o nhap van ban cua Gemini ----------
# Vi tri click luu dang TUONG DOI so voi cua so (ti le ngang + so pixel tinh tu day
# cua so len), nen dung duoc du cua so o dau. Mac dinh: giua ngang, cach day 70px.
# Co the hieu chinh bang menu khay he thong "Hieu chinh vi tri click o nhap".
DEFAULT_CLICK = {"rel_x": 0.5, "from_bottom": 70}

user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = wintypes.BOOL
user32.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                               wintypes.DWORD, ctypes.c_size_t]
user32.mouse_event.restype = None
user32.WindowFromPoint.argtypes = [wintypes.POINT]
user32.WindowFromPoint.restype = wintypes.HWND
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
VK_LBUTTON = 0x01


def load_click_config():
    cfg = dict(DEFAULT_CLICK)
    try:
        with open(CLICK_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        cfg["rel_x"] = min(0.98, max(0.02, float(data.get("rel_x", cfg["rel_x"]))))
        cfg["from_bottom"] = max(5, int(data.get("from_bottom", cfg["from_bottom"])))
    except Exception:
        pass
    return cfg


def save_click_config(cfg):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CLICK_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
    except Exception:
        pass


def click_input_box(hwnd, clicks=2):
    """Click chuot vao o nhap van ban cua Gemini de lay lai focus, roi tra con tro ve cho cu.
    Cach lam chac an hon: rung nhe con tro truoc (Chrome hay bo qua click neu chua thay chuot
    di chuyen vao cua so), roi click `clicks` lan cach nhau mot nhip. Chi bo qua khi diem do
    ro rang dang nam duoi MOT CUA SO KHAC (vd. cua so topmost khac che len)."""
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return False
    cfg = load_click_config()
    w = rect.right - rect.left
    x = int(rect.left + w * cfg["rel_x"])
    y = int(rect.bottom - cfg["from_bottom"])
    y = max(rect.top + 10, y)

    pt = wintypes.POINT(x, y)
    under = user32.WindowFromPoint(pt)
    if under:
        root = user32.GetAncestor(under, 2)  # GA_ROOT
        if root and root != hwnd:
            return False

    old = wintypes.POINT()
    have_old = user32.GetCursorPos(ctypes.byref(old))
    try:
        # rung nhe de Chrome nhan ra chuot dang o trong cua so
        user32.SetCursorPos(x - 6, y - 4)
        time.sleep(0.06)
        user32.SetCursorPos(x - 2, y - 1)
        time.sleep(0.06)
        user32.SetCursorPos(x, y)
        time.sleep(0.12)
        for i in range(max(1, clicks)):
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.35)  # khoang nghi du de khong thanh double-click chon chu
    finally:
        if have_old:
            user32.SetCursorPos(old.x, old.y)
    return True


def calibrate_click_position(hwnd, notify=None):
    """Cho nguoi dung click 1 lan vao o nhap cua Gemini, ghi lai vi tri do."""
    if notify:
        notify("Hay click 1 lan vao O NHAP van ban cua Gemini (co 15 giay).")
    # doi nha chuot ra het (lan bam menu khay vua roi co the van dang giu)
    t0 = time.time()
    while user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000 and time.time() - t0 < 3:
        time.sleep(0.02)

    deadline = time.time() + 15
    while time.time() < deadline:
        if user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000:
            pt = wintypes.POINT()
            rect = wintypes.RECT()
            if user32.GetCursorPos(ctypes.byref(pt)) and user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                if rect.left <= pt.x <= rect.right and rect.top <= pt.y <= rect.bottom:
                    w = max(1, rect.right - rect.left)
                    save_click_config({
                        "rel_x": round((pt.x - rect.left) / float(w), 4),
                        "from_bottom": int(rect.bottom - pt.y),
                    })
                    if notify:
                        notify("Da luu vi tri o nhap.")
                    return True
            # click ngoai cua so Gemini -> bo qua, doi click tiep
            while user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000:
                time.sleep(0.02)
        time.sleep(0.02)
    if notify:
        notify("Het gio, chua luu vi tri nao.")
    return False


# ---------- Tu dong dan anh + prompt vao Gemini ----------
# Luong: dua cua so Gemini ra truoc (kiem tra that su dang o tren cung) ->
# Ctrl+V dan anh (dang nam san trong clipboard do Photoshop vua copy) -> cho anh
# tai len -> dua prompt vao clipboard -> Ctrl+V dan prompt. KHONG tu bam Enter.
AUTOPASTE_LOAD_WAIT = 5.0     # giay cho Gemini tai xong khi vua MOI mo cua so
AUTOPASTE_FOCUS_DELAY = 0.4   # giay nghi sau khi cua so len truoc, truoc khi dan anh
AUTOPASTE_IMAGE_WAIT = 2.0    # giay cho Gemini tai anh len truoc khi dan prompt

VK_CONTROL = 0x11
VK_V = 0x56
KEYEVENTF_KEYUP = 0x0002
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

# Khai bao argtypes day du (bai hoc cu: thieu argtypes tren Windows 64-bit se lam
# HANDLE/con tro bi cat cut va ham am tham that bai)
user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wintypes.HWND
user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_size_t]
user32.keybd_event.restype = None
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.AttachThreadInput.restype = wintypes.BOOL
user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = wintypes.BOOL
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.SetClipboardData.restype = wintypes.HANDLE
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wintypes.HANDLE
kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
kernel32.GlobalUnlock.restype = wintypes.BOOL
kernel32.GlobalFree.argtypes = [wintypes.HANDLE]
kernel32.GlobalFree.restype = wintypes.HANDLE
kernel32.GetCurrentThreadId.argtypes = []
kernel32.GetCurrentThreadId.restype = wintypes.DWORD


def _msgbox(text, flags=0x30):
    stop_busy_cursor()  # co hop thoai thi tra con tro binh thuong truoc
    ctypes.windll.user32.MessageBoxW(0, text, "GeminiWidget", flags)


def read_prompt_file(path):
    """Doc prompt do panel imaFlow ghi ra file tam, doc xong thi xoa."""
    if not path:
        return ""
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            text = f.read()
    except Exception:
        return ""
    try:
        os.remove(path)
    except Exception:
        pass
    return text


def set_clipboard_text(text):
    data = text.replace("\r\n", "\n").replace("\n", "\r\n")
    raw = (data + "\0").encode("utf-16-le")

    hmem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(raw))
    if not hmem:
        return False
    ptr = kernel32.GlobalLock(hmem)
    if not ptr:
        kernel32.GlobalFree(hmem)
        return False
    ctypes.memmove(ptr, raw, len(raw))
    kernel32.GlobalUnlock(hmem)

    opened = False
    for _ in range(20):  # clipboard co the dang bi app khac giu, thu lai vai lan
        if user32.OpenClipboard(None):
            opened = True
            break
        time.sleep(0.05)
    if not opened:
        kernel32.GlobalFree(hmem)
        return False

    try:
        user32.EmptyClipboard()
        if not user32.SetClipboardData(CF_UNICODETEXT, hmem):
            kernel32.GlobalFree(hmem)
            return False
        return True  # clipboard da so huu hmem, khong duoc free nua
    finally:
        user32.CloseClipboard()


AUTOPASTE_SEND_DELAY = 1.0    # giay cho Gemini xu ly anh/prompt vua dan truoc khi bam Enter
VK_RETURN = 0x0D

# ---------- Con tro chuot "dang tai" trong luc tu dan ----------
OCR_NORMAL = 32512
OCR_IBEAM = 32513
IDC_WAIT = 32514
SPI_SETCURSORS = 0x0057

user32.LoadCursorW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
user32.LoadCursorW.restype = wintypes.HANDLE
user32.CopyImage.argtypes = [wintypes.HANDLE, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.CopyImage.restype = wintypes.HANDLE
user32.SetSystemCursor.argtypes = [wintypes.HANDLE, wintypes.DWORD]
user32.SetSystemCursor.restype = wintypes.BOOL
user32.SystemParametersInfoW.argtypes = [wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT]
user32.SystemParametersInfoW.restype = wintypes.BOOL

_busy_cursor_on = False


def start_busy_cursor():
    """Doi con tro he thong (mui ten + o go chu) thanh vong xoay 'dang tai'."""
    global _busy_cursor_on
    if _busy_cursor_on:
        return
    try:
        for target in (OCR_NORMAL, OCR_IBEAM):
            # SetSystemCursor huy handle nen phai copy ban moi cho moi lan
            wait = user32.LoadCursorW(None, IDC_WAIT)
            copy = user32.CopyImage(wait, 2, 0, 0, 0)  # IMAGE_CURSOR
            if copy:
                user32.SetSystemCursor(copy, target)
        _busy_cursor_on = True
    except Exception:
        pass


def stop_busy_cursor():
    """Tra con tro ve theme goc cua nguoi dung."""
    global _busy_cursor_on
    if not _busy_cursor_on:
        return
    try:
        user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)
    except Exception:
        pass
    _busy_cursor_on = False


atexit.register(stop_busy_cursor)


VK_SHIFT = 0x10
VK_MENU = 0x12
MOUSEEVENTF_MOVE = 0x0001
CF_BITMAP = 2
CF_DIB = 8
CF_DIBV5 = 17

user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
user32.MapVirtualKeyW.restype = wintypes.UINT
user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE
user32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
user32.RegisterClipboardFormatW.restype = wintypes.UINT
user32.AllowSetForegroundWindow.argtypes = [wintypes.DWORD]
user32.AllowSetForegroundWindow.restype = wintypes.BOOL
kernel32.GlobalSize.argtypes = [wintypes.HANDLE]
kernel32.GlobalSize.restype = ctypes.c_size_t

TIMING_CONFIG_PATH = os.path.join(CONFIG_DIR, "timing_config.json")


def load_timing():
    """Cho phep chinh moc thoi gian khong can build lai: tao file
    %APPDATA%\\GeminiWidget\\timing_config.json, vd {"image_wait": 3, "send_delay": 2}."""
    t = {
        "load_wait": AUTOPASTE_LOAD_WAIT,
        "focus_delay": AUTOPASTE_FOCUS_DELAY,
        "image_wait": AUTOPASTE_IMAGE_WAIT,
        "send_delay": AUTOPASTE_SEND_DELAY,
        "per_mb": 0.4,       # cong them moi MB anh (anh to upload lau hon)
        "max_extra": 6.0,    # cong them toi da
        "auto_enter": True,
        "wait_result": True,      # sau khi gui, cho anh duoc "Sao chep" trong Gemini roi tra ve Photoshop
        "result_timeout": 600.0,  # cho toi da 10 phut
    }
    try:
        with open(TIMING_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k in t:
            if k in data:
                t[k] = bool(data[k]) if k in ("auto_enter", "wait_result") else max(0.0, float(data[k]))
    except Exception:
        pass
    return t


def _key(vk, up=False):
    scan = user32.MapVirtualKeyW(vk, 0)  # MAPVK_VK_TO_VSC — Chrome on dinh hon khi co scan code
    user32.keybd_event(vk, scan & 0xFF, KEYEVENTF_KEYUP if up else 0, 0)


def release_stray_modifiers():
    """Neu Shift/Alt dang bi giu, Ctrl+V se thanh Ctrl+Shift+V (dan chu tron -> MAT ANH)."""
    for vk in (VK_SHIFT, VK_MENU):
        if user32.GetAsyncKeyState(vk) & 0x8000:
            _key(vk, up=True)


def press_enter():
    _key(VK_RETURN)
    time.sleep(0.03)
    _key(VK_RETURN, up=True)


def press_ctrl_v():
    release_stray_modifiers()
    _key(VK_CONTROL)
    time.sleep(0.04)
    _key(VK_V)
    time.sleep(0.04)
    _key(VK_V, up=True)
    time.sleep(0.04)
    _key(VK_CONTROL, up=True)


def clipboard_image_size(timeout=4.0):
    """Doi clipboard CO ANH (Photoshop copy xong) va tra ve kich thuoc byte (0 neu khong do duoc).
    Goi GetClipboardData cung buoc Photoshop 'render' anh ngay (Photoshop dung delayed
    rendering) -> luc Chrome dan se lay duoc anh tron ven, khong bi treo/cut giua chung.
    Tra ve None neu het gio ma clipboard van khong co anh."""
    png = user32.RegisterClipboardFormatW("PNG")
    deadline = time.time() + timeout
    while time.time() < deadline:
        has_img = any(user32.IsClipboardFormatAvailable(f) for f in (CF_DIB, CF_DIBV5, CF_BITMAP, png))
        if has_img:
            size = 0
            if user32.OpenClipboard(None):
                try:
                    for fmt in (CF_DIB, CF_DIBV5, png):
                        if user32.IsClipboardFormatAvailable(fmt):
                            h = user32.GetClipboardData(fmt)
                            if h:
                                size = kernel32.GlobalSize(h)
                                break
                finally:
                    user32.CloseClipboard()
            return size
        time.sleep(0.1)
    return None


def _nudge_input():
    """Gui 1 su kien chuot 'dung yen' -> tien trinh nay thanh noi nhan input cuoi cung,
    Windows se cho phep SetForegroundWindow (foreground lock)."""
    user32.mouse_event(MOUSEEVENTF_MOVE, 0, 0, 0, 0)


def focus_window_strict(hwnd, timeout=2.5):
    """Dua cua so ra truoc VA xac nhan that su dang la cua so tren cung.
    Tra ve False neu Windows khong cho -> de nguoi goi dung lai, tranh gui phim
    nham vao Photoshop (Ctrl+V trong Photoshop se tao layer la)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if user32.GetForegroundWindow() == hwnd:
            return True
        _nudge_input()
        user32.AllowSetForegroundWindow(0xFFFFFFFF)  # ASFW_ANY
        fg = user32.GetForegroundWindow()
        cur_tid = kernel32.GetCurrentThreadId()
        fg_tid = user32.GetWindowThreadProcessId(fg, None) if fg else 0
        attached = bool(fg_tid) and fg_tid != cur_tid and user32.AttachThreadInput(cur_tid, fg_tid, True)
        try:
            bring_to_front(hwnd)
        finally:
            if attached:
                user32.AttachThreadInput(cur_tid, fg_tid, False)
        time.sleep(0.15)
        if user32.GetForegroundWindow() == hwnd:
            return True
    return False


def ensure_gemini_foreground(hwnd, click=True, attempts=4):
    """Dam bao Gemini THAT SU la cua so dang nhan phim.
    - click=True: click vao o nhap (dat con tro go chu vao o chat) — dung truoc lan dan dau.
    - click=False: chi click khi bi mat focus va khong lay lai duoc bang cach thuong
      (click lai sau khi da dan anh co the trung thumbnail/nut X xoa anh -> mat anh).
    Tra ve False neu khong chac -> nguoi goi phai DUNG, khong gui phim."""
    if not user32.IsWindow(hwnd):
        return False
    for _ in range(attempts):
        if user32.GetForegroundWindow() != hwnd:
            focus_window_strict(hwnd, timeout=1.2)
        if click or user32.GetForegroundWindow() != hwnd:
            # Click chuot len cua so luon kich hoat duoc no, ke ca khi Windows chan SetForegroundWindow
            click_input_box(hwnd, clicks=1)
            time.sleep(0.25)
            click = False  # da click 1 lan la du, khong click lap lai
        if user32.GetForegroundWindow() == hwnd:
            return True
        time.sleep(0.2)
    return False


def _send_if_foreground(hwnd, action):
    """Kiem tra NGAY truoc khi gui phim (khong co khoang nghi o giua)."""
    if user32.GetForegroundWindow() != hwnd:
        return False
    action()
    return True


# Chi 1 tien trinh duoc tu dan tai 1 thoi diem (bam Copy & Mark 2 lan lien tiep
# truoc day se co 2 tien trinh cung gui phim, dan chen lan nhau).
AUTOPASTE_MUTEX_NAME = "Local\\GeminiWidget_Autopaste_Mutex_ImaFlow"
kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.WaitForSingleObject.restype = wintypes.DWORD
kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
kernel32.ReleaseMutex.restype = wintypes.BOOL


def autopaste_to_gemini(hwnd, prompt_text, initial_wait=0.0):
    """Dan anh (dang co san trong clipboard) roi dan prompt vao cua so Gemini.
    Truoc MOI lan gui phim (Ctrl+V, Enter) deu kiem tra Gemini dang la cua so tren cung;
    neu khong thi dung han, tuyet doi khong gui phim vao Photoshop."""
    mutex = kernel32.CreateMutexW(None, False, AUTOPASTE_MUTEX_NAME)
    got = mutex and kernel32.WaitForSingleObject(mutex, 30000) in (0, 0x80)  # OBJECT / ABANDONED
    start_busy_cursor()
    try:
        timing = load_timing()
        if initial_wait:
            time.sleep(initial_wait)

        # Lop bao ve cuoi: tuyet doi khong gui phim neu HWND khong phai cua so trinh duyet
        if not is_browser_window(hwnd):
            _msgbox("Khong tim thay dung cua so Gemini (trinh duyet) nen da DUNG, khong dan gi ca.")
            return False

        img_size = clipboard_image_size()
        if img_size is None:
            _msgbox("Clipboard khong co anh (Photoshop chua copy xong?) nen da DUNG.\n\n"
                    "Thu bam Copy & Mark lai nhe.")
            return False
        extra = min(timing["max_extra"], (img_size / 1048576.0) * timing["per_mb"])

        if not ensure_gemini_foreground(hwnd, click=True):
            _msgbox("Khong dua duoc / giu duoc focus o cua so Gemini nen da DUNG, khong dan gi ca "
                    "(de tranh dan nham vao Photoshop).\n\n"
                    "Bam vao o chat cua Gemini roi dan tay (Ctrl+V) nhe.")
            return False
        time.sleep(timing["focus_delay"])
        if not _send_if_foreground(hwnd, press_ctrl_v):  # dan anh
            if not (ensure_gemini_foreground(hwnd, click=True) and _send_if_foreground(hwnd, press_ctrl_v)):
                _msgbox("Gemini mat focus ngay truoc khi dan anh nen da DUNG. Dan tay (Ctrl+V) nhe.")
                return False

        if not prompt_text.strip():
            return True

        # Cho anh tai len (anh cang to cho cang lau)
        time.sleep(timing["image_wait"] + extra)

        if not set_clipboard_text(prompt_text):
            _msgbox("Khong dua duoc prompt vao clipboard. Anh da duoc dan, hay dan prompt tay nhe.")
            return False
        time.sleep(0.15)

        if not ensure_gemini_foreground(hwnd, click=False):
            _msgbox("Cua so Gemini khong con o tren cung nen da dung truoc buoc dan prompt "
                    "(anh da duoc dan). Prompt dang nam san trong clipboard, dan tay nhe.")
            return False
        if not _send_if_foreground(hwnd, press_ctrl_v):  # dan prompt
            return False

        if not timing["auto_enter"]:
            return True

        # Cho Gemini nhan anh + chu roi moi bam Enter de gui
        time.sleep(timing["send_delay"] + extra * 0.5)
        stop_busy_cursor()
        return _send_if_foreground(hwnd, press_enter)  # mat top -> khong gui Enter nham app khac
    except Exception:
        return False
    finally:
        stop_busy_cursor()
        if got:
            kernel32.ReleaseMutex(mutex)
        if mutex:
            kernel32.CloseHandle(mutex)


# ---------- Cho anh ket qua duoc "Sao chep" trong Gemini -> gui ve Photoshop ----------
# Sau khi gui (Enter), widget xoa clipboard roi theo doi: anh DAU TIEN duoc sao chep
# (khong phai do Photoshop copy) se duoc luu thanh file PNG trong RESULTS_DIR.
# Panel imaFlow theo doi thu muc nay va tu dan anh vao dung marker (ten file mang ID marker).
RESULTS_DIR = os.path.join(CONFIG_DIR, "results")
CURRENT_REQUEST_PATH = os.path.join(RESULTS_DIR, "current_request.txt")

user32.GetClipboardSequenceNumber.argtypes = []
user32.GetClipboardSequenceNumber.restype = wintypes.DWORD
user32.GetClipboardOwner.argtypes = []
user32.GetClipboardOwner.restype = wintypes.HWND


def begin_request():
    """Danh dau yeu cau moi nhat. Ban cu dang cho anh se tu dung lai (anh sao chep tiep theo
    thuoc ve lan Copy & Mark moi nhat)."""
    req = "{}_{}".format(int(time.time() * 1000), os.getpid())
    try:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        with open(CURRENT_REQUEST_PATH, "w", encoding="utf-8") as f:
            f.write(req)
    except Exception:
        pass
    return req


def is_current_request(req):
    try:
        with open(CURRENT_REQUEST_PATH, "r", encoding="utf-8") as f:
            return f.read().strip() == req
    except Exception:
        return True


def clear_clipboard():
    for _ in range(20):
        if user32.OpenClipboard(None):
            try:
                user32.EmptyClipboard()
            finally:
                user32.CloseClipboard()
            return True
        time.sleep(0.05)
    return False


def clipboard_has_image():
    png = user32.RegisterClipboardFormatW("PNG")
    return any(user32.IsClipboardFormatAvailable(f) for f in (CF_DIB, CF_DIBV5, CF_BITMAP, png))


def clipboard_owner_exe():
    owner = user32.GetClipboardOwner()
    return get_process_exe_name(owner) if owner else ""


def save_clipboard_image(path):
    """Luu anh trong clipboard ra PNG (ghi file tam roi doi ten -> panel khong doc file do dang)."""
    try:
        from PIL import Image, ImageGrab
        data = ImageGrab.grabclipboard()
        if isinstance(data, list):  # copy file anh (vd. tu Explorer)
            data = next((Image.open(p) for p in data
                         if p.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp"))), None)
        if data is None:
            return False
        if data.mode not in ("RGB", "RGBA"):
            data = data.convert("RGBA")
        tmp = path + ".tmp"
        data.save(tmp, "PNG")
        os.replace(tmp, path)
        return True
    except Exception:
        return False


def cleanup_old_results(max_age=24 * 3600):
    try:
        now = time.time()
        for name in os.listdir(RESULTS_DIR):
            p = os.path.join(RESULTS_DIR, name)
            if name.startswith("imaflow_result_") and now - os.path.getmtime(p) > max_age:
                os.remove(p)
    except Exception:
        pass


def wait_for_result_image(req, marker, timeout):
    """Xoa clipboard, cho anh DAU TIEN duoc sao chep, luu ra file cho panel. Chi nhan 1 anh."""
    cleanup_old_results()
    clear_clipboard()
    seq = user32.GetClipboardSequenceNumber()
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(0.3)
        if not is_current_request(req):
            return False  # da co lan Copy & Mark moi hon -> nhuong cho no
        cur = user32.GetClipboardSequenceNumber()
        if cur == seq:
            continue
        time.sleep(0.2)  # trinh duyet co the ghi nhieu dinh dang lien tiep, cho ghi xong
        seq = user32.GetClipboardSequenceNumber()
        if not clipboard_has_image():
            continue  # sao chep chu -> bo qua, cho tiep
        if clipboard_owner_exe() == "photoshop.exe" or \
                get_process_exe_name(user32.GetForegroundWindow()) == "photoshop.exe":
            continue  # anh do Photoshop copy (Copy & Mark) -> khong phai ket qua
        safe_marker = "".join(c if c.isdigit() else "_" for c in (marker or "0|0"))
        name = "imaflow_result_{}_{}.png".format(safe_marker, int(time.time() * 1000))
        if save_clipboard_image(os.path.join(RESULTS_DIR, name)):
            return True
    return False


def run_autopaste(hwnd, prompt_path, marker, initial_wait=0.0, before_wait=None):
    """Dan anh + prompt, gui, roi (neu bat) cho anh ket qua duoc sao chep."""
    req = begin_request()
    ok = autopaste_to_gemini(hwnd, read_prompt_file(prompt_path), initial_wait)
    timing = load_timing()
    if ok and timing["wait_result"]:
        if before_wait:
            before_wait()
        wait_for_result_image(req, marker, timing["result_timeout"])
    return ok


def parse_marker_arg(argv):
    if "--marker" in argv:
        i = argv.index("--marker")
        return argv[i + 1] if i + 1 < len(argv) else ""
    return ""


def parse_autopaste_arg(argv):
    """Tra ve (co_flag, duong_dan_file_prompt). Dung: GeminiWidget.exe --autopaste <file>"""
    if "--autopaste" in argv:
        i = argv.index("--autopaste")
        path = argv[i + 1] if i + 1 < len(argv) else ""
        return True, path
    return False, ""


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
            stop_busy_cursor()
            clear_state()
            os._exit(0)

        rect = get_window_rect(hwnd)
        if not rect or rect["w"] < 50 or rect["h"] < 50:
            continue

        max_w = max_window_width(hwnd)
        if rect["w"] > max_w + 2:
            # keo rong qua 1/4 man hinh -> thu nho lai (giu nguyen z-order/topmost)
            user32.SetWindowPos(hwnd, None, rect["x"], rect["y"], max_w, rect["h"],
                                0x0004 | 0x0010)  # SWP_NOZORDER | SWP_NOACTIVATE
            rect["w"] = max_w

        current = (rect["x"], rect["y"], rect["w"], rect["h"])
        if current != last_saved:
            save_window_config(rect)
            last_saved = current


class GeminiWidgetApp:
    def __init__(self, autopaste=False, prompt_path="", marker=""):
        self.hwnd = None
        self.pinned = True
        self.autopaste = autopaste
        self.prompt_path = prompt_path
        self.marker = marker

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

        save_state(self.hwnd)  # de cac lan --autopaste sau tim dung cua so nay
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

        if self.autopaste:
            # Cua so vua MOI mo nen cho Gemini tai xong roi moi dan; chay o thread
            # rieng de khong chan icon khay he thong.
            threading.Thread(
                target=lambda: run_autopaste(
                    self.hwnd, self.prompt_path, self.marker, AUTOPASTE_LOAD_WAIT),
                daemon=True,
            ).start()

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

    def calibrate_click(self, icon=None, item=None):
        if not self.hwnd:
            return

        def notify(msg):
            try:
                if icon:
                    icon.notify(msg, "GeminiWidget")
            except Exception:
                pass

        threading.Thread(target=calibrate_click_position, args=(self.hwnd, notify), daemon=True).start()

    def quit_app(self, icon=None, item=None):
        if self.hwnd:
            rect = get_window_rect(self.hwnd)
            if rect and rect["w"] > 50 and rect["h"] > 50:
                save_window_config(rect)
            user32.PostMessageW(self.hwnd, 0x0010, 0, 0)  # WM_CLOSE
        clear_state()
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
                pystray.MenuItem("Hieu chinh vi tri click o nhap", self.calibrate_click),
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
    _autopaste, _prompt_path = parse_autopaste_arg(sys.argv)
    _marker = parse_marker_arg(sys.argv)
    if _autopaste:
        start_busy_cursor()
    _mutex_handle, _already_running = acquire_single_instance_lock()

    if _already_running:
        # Da co ban khac dang chay: lay DUNG cua so Gemini ma ban do dang quan ly
        # (HWND luu trong state.json), khong do bua theo tieu de nua.
        _hwnd = find_running_gemini_hwnd()
        if _autopaste and not _hwnd:
            # Ban kia co the vua khoi dong, cua so chua kip hien -> doi toi 12 giay
            for _ in range(24):
                time.sleep(0.5)
                _hwnd = find_running_gemini_hwnd()
                if _hwnd:
                    break
        if _hwnd:
            set_topmost(_hwnd, True)
            if _autopaste:
                # Truoc khi ngoi cho anh ket qua (co the vai phut), tra lai khoa "1 ban duy nhat"
                # de khong lam lan mo sau tuong widget van con chay.
                run_autopaste(_hwnd, _prompt_path, _marker,
                              before_wait=lambda: kernel32.CloseHandle(_mutex_handle))
            else:
                bring_to_front(_hwnd)
        else:
            _msgbox("GeminiWidget dang chay roi.\n\n"
                    "Kiem tra icon o khay he thong (goc duoi phai man hinh, "
                    "canh dong ho) — cua so Gemini van dang mo o do.", 0x40)
        sys.exit(0)

    GeminiWidgetApp(_autopaste, _prompt_path, _marker).start()
