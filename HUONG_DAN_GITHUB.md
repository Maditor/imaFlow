# 🚀 Hướng dẫn đưa dự án lên GitHub

## Bước 1 — Tạo repo trên GitHub

1. Vào [github.com/new](https://github.com/new)
2. Đặt tên repo, ví dụ: `imaflow-photoshop-panel`
3. Chọn **Public** (để chia sẻ cho người khác dùng) hoặc **Private**
4. **Không** tick "Add a README file" (vì mình đã có sẵn README rồi)
5. Bấm **Create repository**

## Bước 2 — Đẩy code lên (lần đầu)

Mở Command Prompt hoặc PowerShell, `cd` vào thư mục dự án (`imaFlow-repo` hoặc tên anh đặt), rồi chạy lần lượt:

```bash
git init
git add .
git commit -m "Initial commit: imaFlow for Photoshop"
git branch -M main
git remote add origin https://github.com/<username>/<ten-repo>.git
git push -u origin main
```

Thay `<username>` và `<ten-repo>` bằng thông tin thật của anh. GitHub sẽ hỏi đăng nhập (dùng Personal Access Token thay vì mật khẩu nếu bị từ chối — GitHub tắt đăng nhập bằng password qua Git từ lâu rồi).

> Nếu chưa cài Git: tải tại [git-scm.com](https://git-scm.com/downloads)

## Bước 3 — Những lần cập nhật sau

Mỗi khi sửa code xong, chỉ cần:

```bash
git add .
git commit -m "Mô tả ngắn gọn thay đổi"
git push
```

## Gợi ý thêm (không bắt buộc)

- **Thêm ảnh chụp màn hình**: chụp panel đang chạy trong Photoshop, bỏ vào thư mục `screenshots/`, rồi chèn vào README bằng `![screenshot](screenshots/ten-anh.png)` để repo trông chuyên nghiệp hơn.
- **.gitignore**: nếu sau này có thêm file cấu hình cá nhân/API key, nhớ thêm vào `.gitignore` để không bị đẩy lên GitHub công khai.

## 📦 Share file GeminiWidget.exe đã build sẵn (qua GitHub Releases)

File `GeminiWidget.exe` sau khi build khá nặng (30–80MB, vì đóng gói cả Python bên trong) — **vượt quá giới hạn 25MB khi kéo-thả upload trực tiếp qua giao diện web GitHub**. Repo này đã cấu hình `.gitignore` để không commit file exe vào code, nhưng nếu anh muốn share sẵn bản build cho người khác dùng ngay (không cần tự build), dùng **GitHub Releases** — chỗ này cho phép file tới **2GB**, không bị giới hạn 25MB:

1. Vào trang repo trên GitHub → bấm **"Releases"** (cột phải, hoặc `github.com/<username>/<repo>/releases`).
2. Bấm **"Create a new release"**.
3. Đặt tag phiên bản, ví dụ `v1.0.0`, đặt tiêu đề (ví dụ "imaFlow v1.0 + GeminiWidget.exe").
4. Kéo thả file `GeminiWidget.exe` (và cả file `.zip` toàn bộ `imaFlow-repo` nếu muốn) vào ô **"Attach binaries"** ở cuối trang.
5. Bấm **"Publish release"**.

Từ giờ, ai vào repo cũng thấy link tải file exe ngay trong mục Releases, không cần tự build. Anh có thể dán link Release đó vào đầu README để người dùng thấy ngay.

