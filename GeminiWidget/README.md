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

## Tự dán ảnh + prompt (dùng cùng panel imaFlow)

Chạy với tham số `GeminiWidget.exe --autopaste <file-prompt.txt>` (panel imaFlow tự gọi sau mỗi lần Copy & Mark):
1. Đưa cửa sổ Gemini ra trước và kiểm tra nó thật sự đang ở trên cùng (nếu không thì dừng, không gửi phím).
2. `Ctrl+V` dán ảnh đang có trong clipboard.
3. Chờ ~2 giây cho ảnh tải lên, đưa prompt vào clipboard, `Ctrl+V` dán prompt. Không tự bấm Enter.

Các mốc thời gian chỉnh ở đầu `gemini_widget.py`: `AUTOPASTE_LOAD_WAIT`, `AUTOPASTE_FOCUS_DELAY`, `AUTOPASTE_IMAGE_WAIT`. Trong lúc tự dán, con trỏ chuột chuyển thành vòng xoay "đang tải"; dán xong prompt widget đợi ~1 giây (`AUTOPASTE_SEND_DELAY`) rồi tự nhấn **Enter** để gửi. Nếu cửa sổ Gemini không còn ở trên cùng thì không nhấn Enter.

Trước khi dán, widget tự **click chuột vào ô nhập** của Gemini để lấy lại focus (xong trả con trỏ chuột về chỗ cũ).

- Cửa sổ widget bị giới hạn **tối đa 1/4 chiều ngang màn hình** để vị trí ô nhập luôn ổn định.
- Mặc định click ở giữa ngang, cách đáy cửa sổ 70px. Nếu click lệch: chuột phải icon ở khay hệ thống → **Hieu chinh vi tri click o nhap** → click 1 lần vào ô nhập của Gemini (15 giây). Vị trí lưu ở `%APPDATA%\GeminiWidget\click_config.json`.

### Chống dán nhầm / dán thiếu (bản sửa lỗi focus)

- Widget chỉ nhận **cửa sổ trình duyệt** (class `Chrome_WidgetWin_1` của Brave/Cốc Cốc/Chrome/Edge) là Gemini — không bao giờ nhận nhầm Photoshop đang mở file `Gemini_Generated_Image_xxx.png`.
- Bản đang chạy lưu HWND cửa sổ Gemini vào `%APPDATA%\GeminiWidget\state.json`; các lần `--autopaste` sau dùng đúng cửa sổ đó.
- Trước khi dán, đợi clipboard **thật sự có ảnh** (Photoshop copy xong) và ép Photoshop render ảnh ngay, nên Chrome dán được ảnh trọn vẹn.
- Chỉ click ô nhập **trước lần dán ảnh**; bước dán prompt không click lại (tránh click trúng thumbnail/nút X làm mất ảnh).
- Ảnh càng nặng thì chờ upload càng lâu (+0.4 giây/MB, tối đa +6 giây) trước khi dán prompt và nhấn Enter.
- Bấm Copy & Mark liên tục: các lần tự dán xếp hàng chạy lần lượt, không chen nhau.

Chỉnh thời gian không cần build lại — tạo file `%APPDATA%\GeminiWidget\timing_config.json`:
```json
{ "image_wait": 2.0, "send_delay": 1.0, "per_mb": 0.4, "max_extra": 6, "auto_enter": true,
  "wait_result": true, "result_timeout": 600 }
```
`wait_result`: sau khi gửi, chờ ảnh được "Sao chép" trong Gemini để panel imaFlow tự dán về Photoshop (`result_timeout` = số giây chờ tối đa).
