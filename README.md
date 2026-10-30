# imaFlow — CEP Extension cho Photoshop

Panel tiện ích trong Photoshop hỗ trợ workflow **redraw ảnh bằng AI** (Gemini "Nano Banana"): copy vùng chọn, dán ảnh AI trả về, tự canh chỉnh vị trí — không cần copy-paste thủ công từng bước. Tương thích **Photoshop CC 2018 (v19.0) trở lên**

## ✨ Tính năng

| Nút | Chức năng |
|---|---|
| **Copy & Mark** | Copy vùng chọn hiện tại (merged) vào clipboard + tạo layer marker (màu neon) đánh dấu toạ độ |
| **Paste & Align** | Dán ảnh AI từ clipboard, tự động resize + canh đúng vị trí marker, tạo mask |
| **Cài đặt** | Mở submenu để: (1) chọn đường dẫn `GeminiWidget.exe`, (2) soạn/lưu nội dung prompt, (3) ẩn dòng trạng thái. Sau mỗi lần **Copy & Mark**, panel luôn tự mở GeminiWidget và dán ảnh + prompt đã lưu, |

Icon các nút dùng SVG line-art đơn sắc, đồng bộ với các CEP extension khác trong series (TypoVision, TypoCore...).

## 🖼️ Workflow

1. Trong Photoshop, khoanh **vùng chọn** cần redraw.
2. Bấm **Copy & Mark** — vùng chọn được copy vào clipboard, một layer marker được tạo để đánh dấu vị trí.
3. Bấm **Mở Gemini** (đã cài đặt sẵn đường dẫn `GeminiWidget.exe` trong Cài đặt để tự ghim nổi), dán ảnh (`Ctrl+V`) và bấm **Prompt** để copy nhanh prompt đã soạn sẵn, generate ảnh.
4. Copy ảnh kết quả từ Gemini.
5. Quay lại Photoshop, **chọn đúng layer marker** vừa tạo ở bước 2.
6. Bấm **Paste & Align** — ảnh AI được dán vào, tự resize và canh đúng vị trí, kèm mask sẵn.
7. Chỉnh màu/blend layer cho khớp nếu cần.

## 📦 Cài đặt panel imaFlow

### Windows — cài tự động
1. Tải hoặc clone repo này về máy.
2. Chạy file **`install.bat`** (double-click). Script tự bật chế độ debug cho CEP và copy extension vào đúng thư mục.
3. Khởi động lại Photoshop → **Window > Extensions > imaFlow**.

> Muốn gỡ cài đặt: chạy `uninstall.bat`.

### macOS — cài tự động
> ⚠️ Script này chưa được test trực tiếp trên máy macOS thật. Nếu chạy lỗi (ví dụ do Gatekeeper chặn), dùng mục **"Cài thủ công"** bên dưới.

1. Tải hoặc clone repo này về máy.
2. Mở Terminal, `cd` vào thư mục repo, chạy:
   ```bash
   bash install.sh
   ```
   Nếu bị Gatekeeper chặn, chạy thêm trước đó: `xattr -cr .`
3. Khởi động lại Photoshop → **Window > Extensions > imaFlow**.

### Cài thủ công (mọi hệ điều hành)
1. Bật chế độ debug cho CEP (để Photoshop chấp nhận extension chưa ký số):
   - **Windows**: mở Registry Editor → tạo `HKEY_CURRENT_USER\Software\Adobe\CSXS.<version>\PlayerDebugMode` = `1` (kiểu String). Thử các version `8`–`12` tuỳ bản Photoshop.
   - **macOS**: Terminal → `defaults write com.adobe.CSXS.<version> PlayerDebugMode 1`
2. Copy thư mục `imaFlow/` vào:
   - **Windows**: `%APPDATA%\Adobe\CEP\extensions\`
   - **macOS**: `~/Library/Application Support/Adobe/CEP/extensions/`
3. Mở Photoshop → **Window > Extensions > imaFlow**.

## 📌 GeminiWidget — ghim cửa sổ Gemini luôn nổi phía trước (Windows)

`GeminiWidget` là app nhỏ đi kèm, mở Gemini bằng Chrome/Brave/Cốc Cốc/Edge thật (app-mode, không thanh tab) và tự ghim **always-on-top** bằng Win32 API — không cần cài PowerToys hay công cụ ngoài nào khác.

- Tự nhớ kích thước & vị trí cửa sổ giữa các lần mở.
- Tự dán: sau khi **Copy & Mark** widget đưa Gemini ra trước, dán ảnh rồi dán prompt (không tự bấm Enter). Nếu không đưa được Gemini ra trước, nó dừng lại thay vì dán nhầm vào Photoshop.
- Chỉ chạy 1 bản duy nhất — bấm mở lần nữa sẽ tự đưa cửa sổ cũ ra trước thay vì mở trùng.
- Icon riêng (hình ghim), có icon khay hệ thống để bật/tắt ghim hoặc thoát.

**Cài đặt:**
1. Build ra file `.exe` theo hướng dẫn trong [`GeminiWidget/`](./GeminiWidget) (file exe không có sẵn trong repo vì khá nặng — build 1 lần là dùng mãi, xem thêm mục Releases trong [`HUONG_DAN_GITHUB.md`](./HUONG_DAN_GITHUB.md) nếu muốn tải bản dựng sẵn).
2. Trong panel imaFlow, mở **Cài đặt** → **"Chọn file..."** → trỏ tới file `GeminiWidget.exe` vừa build.
3. Từ giờ, mỗi lần bấm **Mở Gemini**, panel sẽ chạy đúng file đó — cửa sổ Gemini tự mở và tự ghim always-on-top ngay lập tức.

**Cách thay thế (không dùng GeminiWidget):** cài [Microsoft PowerToys](https://learn.microsoft.com/windows/powertoys/install) → bật module "Always On Top" → click cửa sổ Gemini → `Win + Ctrl + T` để ghim.

## ⚠️ Giới hạn cần biết

- Extension **không nhúng được giao diện Gemini web** trực tiếp trong panel — Google chủ động chặn đăng nhập từ trình duyệt nhúng (bảo mật chống phishing). Vì vậy panel mở Gemini bằng cửa sổ trình duyệt riêng (xem mục GeminiWidget bên trên).
- Tính năng mở Gemini dạng cửa sổ nhỏ hỗ trợ **Brave, Cốc Cốc, Chrome, Edge** trên **Windows**; nếu không tìm thấy trình duyệt nào trong 4 loại đó sẽ tự fallback về mở bằng trình duyệt mặc định.
- Nếu bước **Paste & Align** không tự resize/canh đúng 100% (một số phiên bản Photoshop báo lỗi nhỏ ở bước Smart Object), ảnh vẫn được dán vào — chỉnh tay bằng `Ctrl+T` (Free Transform).
- Extension chưa ký số (unsigned) nên bắt buộc phải bật `PlayerDebugMode` mới chạy được.
- `GeminiWidget.exe` chưa ký số nên Windows SmartScreen có thể cảnh báo lần chạy đầu — bấm "More info" → "Run anyway".

## 🗂️ Cấu trúc dự án

```
imaFlow-repo/
├── imaFlow/                  # CEP extension chính
│   ├── CSXS/manifest.xml     # Khai báo extension, host app, phiên bản hỗ trợ
│   ├── icons/                 # Icon extension cho theme sáng/tối của Photoshop
│   ├── client/                # Giao diện panel (HTML/CSS/JS)
│   ├── host/index.jsx          # ExtendScript xử lý Copy & Mark / Paste & Align
│   └── .debug                  # Cấu hình debug qua Chrome DevTools (port 8088)
├── GeminiWidget/               # App pin cửa sổ Gemini (Python -> .exe)
├── install.bat / install.sh    # Script cài đặt panel tự động
├── uninstall.bat                 # Script gỡ cài đặt (Windows)
└── HUONG_DAN_GITHUB.md            # Hướng dẫn đưa repo lên GitHub + Releases
```

## 🛠️ Debug / Phát triển thêm

Panel bật sẵn debug qua Chrome DevTools ở cổng `8088`. Sau khi cài, mở Chrome, gõ `http://localhost:8088` để xem console, chỉnh lỗi trực tiếp.

## 📄 License

MIT — tự do sử dụng, chỉnh sửa, chia sẻ.

## 🙏 Ghi công

Ý tưởng workflow Copy & Mark / Paste & Align dựa trên kỹ thuật redraw phổ biến trong cộng đồng edit/typeset (kết hợp Photoshop + AI image model qua clipboard).
