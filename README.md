# 🪄 imaFlow

Panel Photoshop giúp redraw ảnh bằng Gemini: khoanh vùng → AI vẽ lại → ảnh tự dán về đúng chỗ.

**Yêu cầu:** Windows 10/11 · Photoshop 2018 trở lên · Brave / Cốc Cốc / Chrome / Edge

## 🖼️ Cách dùng

1. Khoanh vùng chọn (Khuyên dùng 512 x 512 px hoặc 768 x 768 px) → bấm **Copy & Mark**.
2. GeminiWidget tự dán ảnh + prompt vào Gemini và gửi đi.
3. Ảnh tạo xong → bấm **Sao chép ảnh** trong Gemini → ảnh tự dán vào đúng vị trí trong Photoshop.

> Dán tay: copy ảnh → chọn layer marker → bấm **Paste & Align**.

## 📦 Cài đặt

1. Chạy **`install.bat`** → mở lại Photoshop → **Window > Extensions > imaFlow**.
2. Vào thư mục `GeminiWidget`, chạy **`build.bat`** để tạo `GeminiWidget.exe`.
3. Trong panel: **Cài đặt** → **Chọn file...** → trỏ tới `GeminiWidget.exe`, soạn sẵn prompt.

Gỡ cài đặt: chạy `uninstall.bat`.

## ⚠️ Lưu ý

- Windows SmartScreen có thể cảnh báo `GeminiWidget.exe` lần đầu → **More info** → **Run anyway**.
- Ảnh dán chưa khớp hoàn toàn thì chỉnh tay bằng `Ctrl+T`.
- Debug panel: mở `http://localhost:8088` bằng Chrome.

## 📄 License

MIT
