# 🪄 AI Redraw Panel — CEP Extension cho Photoshop

Panel tiện ích trong Photoshop hỗ trợ workflow **redraw ảnh bằng AI** (Gemini "Nano Banana"): copy vùng chọn, dán ảnh AI trả về, tự canh chỉnh vị trí — không cần copy-paste thủ công từng bước. Tương thích **Photoshop CC 2018 (v19.0) trở lên**, cả Windows lẫn macOS.

## ✨ Tính năng

| Nút | Chức năng |
|---|---|
| 📋 **Copy & Mark** | Copy vùng chọn hiện tại (merged) vào clipboard + tạo layer marker (màu neon) đánh dấu toạ độ |
| 🎯 **Paste & Align** | Dán ảnh AI từ clipboard, tự động resize + canh đúng vị trí marker, tạo mask |
| ↗ **Mở Gemini** | Mở [gemini.google.com](https://gemini.google.com) bằng trình duyệt mặc định của máy |
| 📝 **Prompt** | Mở khung soạn/lưu prompt, có nút copy nhanh — prompt được lưu lại giữa các lần dùng |

## 🖼️ Workflow

1. Trong Photoshop, khoanh **vùng chọn** cần redraw.
2. Bấm **📋 Copy & Mark** — vùng chọn được copy vào clipboard, một layer marker được tạo để đánh dấu vị trí.
3. Bấm **↗ Mở Gemini**, dán ảnh (`Ctrl+V` / `Cmd+V`) và prompt (dùng khung **📝 Prompt** để lưu sẵn prompt hay dùng), generate ảnh.
4. Copy ảnh kết quả từ Gemini.
5. Quay lại Photoshop, **chọn đúng layer marker** vừa tạo ở bước 2.
6. Bấm **🎯 Paste & Align** — ảnh AI được dán vào, tự resize và canh đúng vị trí, kèm mask sẵn.
7. Chỉnh màu/blend layer cho khớp nếu cần.

## 📦 Cài đặt

### Windows — cài tự động
1. Tải hoặc clone repo này về máy.
2. Chạy file **`install.bat`** (double-click). Script sẽ tự bật chế độ debug cho CEP và copy extension vào đúng thư mục.
3. Khởi động lại Photoshop → **Window > Extensions > AI Redraw Panel**.

> Muốn gỡ cài đặt: chạy `uninstall.bat`.

### macOS — cài tự động
1. Tải hoặc clone repo này về máy.
2. Mở Terminal, `cd` vào thư mục repo, chạy:
   ```bash
   bash install.sh
   ```
3. Khởi động lại Photoshop → **Window > Extensions > AI Redraw Panel**.

### Cài thủ công (mọi hệ điều hành)
1. Bật chế độ debug cho CEP (để Photoshop chấp nhận extension chưa ký số):
   - **Windows**: mở Registry Editor → tạo `HKEY_CURRENT_USER\Software\Adobe\CSXS.<version>\PlayerDebugMode` = `1` (kiểu String). Thử các version `8`–`12` tuỳ bản Photoshop.
   - **macOS**: Terminal → `defaults write com.adobe.CSXS.<version> PlayerDebugMode 1`
2. Copy thư mục `AIRedrawPanel/` vào:
   - **Windows**: `%APPDATA%\Adobe\CEP\extensions\`
   - **macOS**: `~/Library/Application Support/Adobe/CEP/extensions/`
3. Mở Photoshop → **Window > Extensions > AI Redraw Panel**.

## ⚠️ Giới hạn cần biết

- Extension **không nhúng được giao diện Gemini web** trực tiếp trong panel — Google chủ động chặn đăng nhập từ trình duyệt nhúng (bảo mật chống phishing). Vì vậy panel chỉ mở Gemini bằng trình duyệt ngoài.
- Nếu bước **Paste & Align** không tự resize/canh đúng 100% (một số phiên bản Photoshop báo lỗi nhỏ ở bước Smart Object), ảnh vẫn được dán vào — anh chỉ cần chỉnh tay bằng `Ctrl+T` (Free Transform).
- Extension chưa ký số (unsigned) nên bắt buộc phải bật `PlayerDebugMode` mới chạy được.

## 🗂️ Cấu trúc dự án

```
AIRedrawPanel/
├── CSXS/manifest.xml       # Khai báo extension, host app, phiên bản hỗ trợ
├── icons/                  # Icon mono cho theme sáng/tối của Photoshop
├── client/                 # Giao diện panel (HTML/CSS/JS)
├── host/index.jsx          # ExtendScript xử lý Copy & Mark / Paste & Align
└── .debug                  # Cấu hình debug qua Chrome DevTools (port 8088)
install.bat / install.sh    # Script cài đặt tự động
uninstall.bat                # Script gỡ cài đặt (Windows)
```

## 🛠️ Debug / Phát triển thêm

Panel bật sẵn debug qua Chrome DevTools ở cổng `8088`. Sau khi cài, mở Chrome, gõ `http://localhost:8088` để xem console, chỉnh lỗi trực tiếp.

## 📄 License

MIT — tự do sử dụng, chỉnh sửa, chia sẻ.

## 🙏 Ghi công

Ý tưởng workflow Copy & Mark / Paste & Align dựa trên kỹ thuật redraw phổ biến trong cộng đồng edit/typeset (kết hợp Photoshop + AI image model qua clipboard).
