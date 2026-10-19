# GeminiWidget — cửa sổ Gemini ghim always-on-top, không cần PowerToys

Ứng dụng nhỏ mở Gemini bằng **Chrome/Edge thật** (chế độ app-mode, không thanh tab) và **tự động ghim always-on-top** bằng Win32 API — không cần cài thêm công cụ nào khác.

## Vì sao không nhúng Gemini vào 1 trình duyệt tự viết?

Vì Google **chủ động chặn đăng nhập** trong các trình duyệt nhúng/tự dựng (Electron, CEF, WebView...) — kể cả khi tự build exe. Nên cách chắc ăn nhất là điều khiển đúng **Chrome/Edge thật đã cài trên máy anh** (đã đăng nhập sẵn), chỉ thêm 2 việc: mở nó ở chế độ gọn (app mode) và ghim nó bằng Win32 API — hoàn toàn không đụng tới cơ chế bảo mật của Google.

## Build file .exe (chỉ cần làm 1 lần)

1. Cài **Python** nếu máy chưa có: <https://www.python.org/downloads/> (nhớ tick "Add python.exe to PATH" lúc cài).
2. Double-click **`build.bat`** trong thư mục này.
3. Đợi 1–2 phút, xong sẽ có file `dist\GeminiWidget.exe`.
4. Copy `GeminiWidget.exe` ra Desktop hoặc ghim vào Taskbar để dùng nhanh lần sau — **không cần build lại nữa**.

## Cách dùng

- Double-click `GeminiWidget.exe` → tự mở Gemini dạng cửa sổ nhỏ, **tự ghim always-on-top ngay lập tức**.
- Có icon nhỏ ở khay hệ thống (system tray, góc dưới phải màn hình) với 3 lựa chọn:
  - **Ghim nổi (Always On Top)** — bật/tắt ghim.
  - **Hiện cửa sổ Gemini** — đưa cửa sổ ra trước nếu bị che.
  - **Thoát** — đóng cả cửa sổ Gemini lẫn ứng dụng.

## Ghi nhớ kích thước / vị trí cửa sổ

App tự động lưu lại kích thước và vị trí cửa sổ Gemini mỗi khi anh kéo-resize hoặc di chuyển nó, vào file:
```
%APPDATA%\GeminiWidget\window_config.json
```
Lần mở tiếp theo sẽ tự tái tạo lại đúng kích thước/vị trí đó — không cần chỉnh lại từ đầu mỗi lần.

## Chỉnh vị trí / kích thước mặc định

Mở `gemini_widget.py`, sửa dòng `DEFAULT_WINDOW` ở đầu file — chỉ áp dụng cho **lần chạy đầu tiên** (chưa có file `window_config.json`):
```python
DEFAULT_WINDOW = {"x": 1200, "y": 80, "w": 420, "h": 760}
```
Sau khi sửa, chạy lại `build.bat` để build bản exe mới.

## Yêu cầu

- Windows
- Đã cài **Brave**, **Cốc Cốc**, Chrome, hoặc Edge (ứng dụng tự dò tìm theo thứ tự ưu tiên đó, dùng trình duyệt nào tìm thấy trước)

File `GeminiWidget.exe` sau khi build sẽ có icon riêng (hình ghim + lấp lánh, file `icon.ico` đi kèm) — không cần làm gì thêm, `build.bat` tự gắn icon vào.
