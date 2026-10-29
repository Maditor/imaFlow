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
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
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


def click_input_box(hwnd):
    """Click chuot vao o nhap van ban cua Gemini de lay lai focus, roi tra con tro ve cho cu.
    Chi click khi diem do thuc su thuoc cua so Gemini (khong click mu vao app khac)."""
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
    if not under or user32.GetAncestor(under, 2) != hwnd:  # GA_ROOT
        return False

    old = wintypes.POINT()
    have_old = user32.GetCursorPos(ctypes.byref(old))
    user32.SetCursorPos(x, y)
    time.sleep(0.05)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.04)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.15)
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


def press_ctrl_v():
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    time.sleep(0.03)
    user32.keybd_event(VK_V, 0, 0, 0)
    time.sleep(0.03)
    user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.03)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


def focus_window_strict(hwnd, timeout=2.5):
    """Dua cua so ra truoc VA xac nhan that su dang la cua so tren cung.
    Tra ve False neu Windows khong cho -> de nguoi goi dung lai, tranh gui phim
    nham vao Photoshop (Ctrl+V trong Photoshop se tao layer la)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        fg = user32.GetForegroundWindow()
        cur_tid = kernel32.GetCurrentThreadId()
        fg_tid = user32.GetWindowThreadProcessId(fg, None) if fg else 0
        attached = bool(fg_tid) and fg_tid != cur_tid and user32.AttachThreadInput(cur_tid, fg_tid, True)
        try:
            bring_to_front(hwnd)
        finally:
            if attached:
                user32.AttachThreadInput(cur_tid, fg_tid, False)
        time.sleep(0.2)
        if user32.GetForegroundWindow() == hwnd:
            return True
    return False


def autopaste_to_gemini(hwnd, prompt_text, initial_wait=0.0):
    """Dan anh (dang co san trong clipboard) roi dan prompt vao cua so Gemini."""
    try:
        if initial_wait:
            time.sleep(initial_wait)

        if not focus_window_strict(hwnd):
            _msgbox("Khong dua duoc cua so Gemini ra truoc nen da DUNG, khong dan gi ca "
                    "(de tranh dan nham vao Photoshop).\n\n"
                    "Bam vao cua so Gemini roi dan tay (Ctrl+V) nhe.")
            return False

        time.sleep(AUTOPASTE_FOCUS_DELAY)
        # Focus o nhap van ban hay bi mat -> click vao o nhap truoc khi dan
        # (neu diem click khong nam trong cua so Gemini thi bo qua, van dan binh thuong)
        if click_input_box(hwnd):
            time.sleep(0.25)
        press_ctrl_v()  # dan anh

        if not prompt_text.strip():
            return True

        time.sleep(AUTOPASTE_IMAGE_WAIT)

        if user32.GetForegroundWindow() != hwnd:
            _msgbox("Cua so Gemini khong con o tren cung nen da dung truoc buoc dan prompt "
                    "(anh da duoc dan). Dan prompt tay nhe.")
            return False
        if not set_clipboard_text(prompt_text):
            _msgbox("Khong dua duoc prompt vao clipboard. Anh da duoc dan, hay dan prompt tay nhe.")
            return False

        time.sleep(0.15)
        press_ctrl_v()  # dan prompt
        return True
    except Exception:
        return False


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
    def __init__(self, autopaste=False, prompt_path=""):
        self.hwnd = None
        self.pinned = True
        self.autopaste = autopaste
        self.prompt_path = prompt_path

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

        if self.autopaste:
            # Cua so vua MOI mo nen cho Gemini tai xong roi moi dan; chay o thread
            # rieng de khong chan icon khay he thong.
            threading.Thread(
                target=lambda: autopaste_to_gemini(
                    self.hwnd, read_prompt_file(self.prompt_path), AUTOPASTE_LOAD_WAIT),
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
    _mutex_handle, _already_running = acquire_single_instance_lock()

    if _already_running:
        # Da co ban khac dang chay: tim cua so Gemini dang mo san.
        _existing = snapshot_gemini_windows()
        if _autopaste and not _existing:
            # Ban kia co the vua khoi dong, cua so chua kip hien -> doi toi 10 giay
            for _ in range(20):
                time.sleep(0.5)
                _existing = snapshot_gemini_windows()
                if _existing:
                    break
        if _existing:
            _hwnd = next(iter(_existing))
            set_topmost(_hwnd, True)
            if _autopaste:
                autopaste_to_gemini(_hwnd, read_prompt_file(_prompt_path))
            else:
                bring_to_front(_hwnd)
        else:
            _msgbox("GeminiWidget dang chay roi.\n\n"
                    "Kiem tra icon o khay he thong (goc duoi phai man hinh, "
                    "canh dong ho) — cua so Gemini van dang mo o do.", 0x40)
        sys.exit(0)

    GeminiWidgetApp(_autopaste, _prompt_path).start()
