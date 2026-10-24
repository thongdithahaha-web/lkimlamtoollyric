# Hướng Dẫn Deploy Miễn Phí 100% (0đ) Chạy Full AI Wav2Vec2 Trên Hugging Face Spaces

Tài liệu này hướng dẫn bạn cách đưa toàn bộ dự án **Tool Lyric by lekimlamcode** (bao gồm **FastAPI Backend**, **FFmpeg** và mô hình AI **Wav2Vec2 `nguyenvulebinh/lyric-alignment` nặng 1.2GB**) lên mạng hoàn toàn **miễn phí 0 đồng vĩnh viễn**, **không cần thẻ tín dụng/thẻ ngân hàng**, và **giữ nguyên 100% code gốc của bạn**.

---

## Tại sao nên dùng Hugging Face Spaces?

| Tiêu chí | Hugging Face Spaces (Free) | Render / Fly.io (Free) | Google Cloud Run / Railway |
| :--- | :--- | :--- | :--- |
| **Chi phí** | **0đ vĩnh viễn** | 0đ (giới hạn) | Yêu cầu thẻ Visa / Tính phí |
| **Yêu cầu thẻ ngân hàng** | **Không cần thẻ** | Có thể yêu cầu xác minh | Bắt buộc thẻ quốc tế |
| **Bộ nhớ RAM miễn phí** | **16 GB RAM** | Chỉ 512 MB RAM (Bị sập khi nạp AI) | Tính phí theo GB/giờ |
| **CPU & Ổ cứng** | **2 vCPU · 50 GB Disk** | 0.1 CPU · Bộ nhớ rất nhỏ | Tính phí theo mức dùng |
| **Chạy Full AI Wav2Vec2** | **Chạy mượt 100%** | Không đủ RAM để nạp model 1.2GB | Chạy được nhưng tốn tiền |

---

## Các Bước Triển Khai Chỉ Trong 3 Phút

### Bước 1: Tạo tài khoản và tạo Space miễn phí trên Hugging Face

1. Truy cập [https://huggingface.co/join](https://huggingface.co/join) và đăng ký một tài khoản miễn phí (chỉ cần email).
2. Sau khi đăng nhập, truy cập [https://huggingface.co/new-space](https://huggingface.co/new-space) để tạo Space mới:
   - **Space name**: Đặt tên tùy ý (ví dụ: `tool-lyric-lekimlamcode`).
   - **Select the Space SDK**: Chọn **Docker** -> chọn mục **Blank**.
   - **Space Hardware**: Để mặc định là **CPU basic · 2 vCPU · 16 GB · FREE**.
   - **Visibility**: Chọn **Public** (hoặc **Private** tùy ý).
3. Nhấn **Create Space**.

---

### Bước 2: Lấy Access Token (Quyền Write) để đẩy code

1. Vào trang cài đặt Token: [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Nhấn **Create new token**:
   - Chọn loại **Write** (hoặc tại tab Fine-grained, tích chọn quyền *Write access to contents of all repos under your personal namespace*).
   - Đặt tên token (ví dụ: `deploy-lyric`) rồi nhấn **Create token**.
3. Sao chép (Copy) mã token vừa tạo (bắt đầu bằng `hf_...`).

---

### Bước 3: Đẩy nguyên trạng dự án lên Hugging Face Spaces

Bạn có thể sử dụng công cụ tự động đã được chuẩn bị sẵn mà **không cần sửa bất kỳ dòng code nào**:

#### Cách A: Chạy file tự động trên Windows (Khuyên dùng)
Nhấp đúp vào file `deploy_free_hf.bat` ở thư mục gốc của dự án (hoặc mở Terminal tại thư mục dự án):
```bat
deploy_free_hf.bat
```
- Nhập **Username Hugging Face** của bạn.
- Nhập **Tên Space** bạn vừa tạo ở Bước 1.
- Khi được hỏi mật khẩu hoặc token, dán **Access Token (`hf_...`)** ở Bước 2 vào.

#### Cách B: Chạy trên Linux / macOS / Git Bash
```bash
chmod +x deploy_free_hf.sh
./deploy_free_hf.sh
```

#### Cách C: Đẩy thủ công bằng lệnh Git
```bash
git remote add hf https://huggingface.co/spaces/<USERNAME_CUA_BAN>/<TEN_SPACE>
git push hf main --force
```

---

### Bước 4: Lưu ý nhỏ về cổng kết nối (`app_port`) trong `README.md`

Trong dự án hiện tại của bạn:
- `Dockerfile` đang đặt cổng mặc định là `ENV PORT=8080`.
- Phần đầu file `README.md` (dòng `app_port: 7860`) báo cho Hugging Face biết container lắng nghe ở cổng nào.

Để Hugging Face nối thẳng vào container mà không cần sửa code Python hay Dockerfile, bạn chỉ cần đảm bảo dòng `app_port` ở đầu file `README.md` khớp với `PORT` trong `Dockerfile`:
```yaml
---
title: Tool Lyric by lekimlamcode
emoji: 🎤
colorFrom: indigo
colorTo: pink
sdk: docker
app_port: 8080
pinned: false
license: mit
---
```
*(Script `deploy_free_hf` cũng sẽ nhắc bạn kiểm tra thông số này trước khi đẩy).*

---

## Cách Lấy Link Web Trực Tiếp (Không Có Khung Viền Hugging Face)

Sau khi Hugging Face báo trạng thái **Running** (lần đầu build Docker mất khoảng 3–5 phút vì hệ thống tự tải sẵn model `nguyenvulebinh/lyric-alignment` 1.2GB vào trong container):

- **Link giao diện đầy đủ (Direct URL)**:
  ```text
  https://<username-cua-ban>-<ten-space>.hf.space
  ```
- **Các đường dẫn hoạt động nguyên bản 100%**:
  - Trang Auto Karaoke chính: `https://<username>-<ten-space>.hf.space/` hoặc `/auto`
  - Trang Player: `https://<username>-<ten-space>.hf.space/player`
  - Giao diện căn chỉnh nhanh: `https://<username>-<ten-space>.hf.space/static/index.html`
  - API AI Wav2Vec2 Alignment: `POST https://<username>-<ten-space>.hf.space/api/align`
