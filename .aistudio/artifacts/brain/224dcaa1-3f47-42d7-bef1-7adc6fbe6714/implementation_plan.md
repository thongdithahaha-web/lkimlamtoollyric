# Kế Hoạch Deploy Miễn Phí 100% (0đ) Chạy Full AI Wav2Vec2 Trên Hugging Face Spaces

Tài liệu này cung cấp giải pháp triển khai (deploy) dự án **Tool Lyric by lekimlamcode** hoàn toàn **miễn phí 0 đồng vĩnh viễn (không cần thẻ ngân hàng/thẻ tín dụng)** trên **Hugging Face Spaces (gói CPU Basic: 16GB RAM, 2 vCPU, 50GB ổ cứng)** để chạy đầy đủ mô hình AI `nguyenvulebinh/lyric-alignment` (Wav2Vec2 1.2GB), đồng thời **không đụng chạm vào bất kỳ dòng code logic hay giao diện nào của bạn**.

## User Review & Critical Decisions

> [!IMPORTANT]
> - **Tại sao chọn Hugging Face Spaces (Docker SDK)?**
>   Các nền tảng miễn phí thông thường (Render Free, Fly.io, Railway dùng thử) chỉ cấp **512MB RAM**, nên khi nạp mô hình AI Wav2Vec2 (~1.2GB) sẽ bị sập ngay lập tức do tràn bộ nhớ (`Out of Memory`). Ngược lại, **Hugging Face Spaces cấp miễn phí 16GB RAM và 50GB bộ nhớ** mà không cần thẻ thanh toán.
> - **Phát hiện điểm lệch nhỏ khi chạy trên Hugging Face Spaces**:
>   Trong `README.md` hiện tại đang khai báo `app_port: 7860`, nhưng `Dockerfile` lại đặt `ENV PORT=8080`. Khi deploy lên Hugging Face Spaces, hai cổng này cần trùng nhau (cùng là `7860` hoặc cùng là `8080`) để Hugging Face kết nối được vào container.
> - **Cam kết bảo toàn code**: Không chỉnh sửa bất kỳ tệp Python (`fastapi_app.py`, `predict.py`, `utils.py`, `model_handling.py`) hay giao diện (`auto_karaoke.html`, `player.html`, `index.html`) nào.

- **Confirmed Decision 1**: Triển khai miễn phí 100% trên **Hugging Face Spaces (16GB RAM)** chạy đầy đủ mô hình AI Wav2Vec2 tự động căn chỉnh lời.
- **Confirmed Decision 2**: Tạo bộ tài liệu hướng dẫn từng bước (`docs/FREE_DEPLOY_GUIDE.md`) và kịch bản đẩy code tự động (`deploy_free_hf.bat` / `deploy_free_hf.sh`) để bạn có thể đưa web lên mạng với 1 lệnh duy nhất mà không tốn 1 đồng nào.

---

## 1. Overview & Core Concept

- **What It Does**: Cung cấp quy trình và công cụ tự động đưa toàn bộ ứng dụng `Tool Lyric by lekimlamcode` (bao gồm FastAPI Backend, FFmpeg, PyTorch CPU và mô hình `nguyenvulebinh/lyric-alignment`) lên máy chủ đám mây miễn phí 16GB RAM của Hugging Face Spaces.
- **Target Audience / Persona**: Tác giả dự án muốn xuất bản ứng dụng công khai có tên miền HTTPS riêng (`https://<username>-<space-name>.hf.space`) để sử dụng và chia sẻ cho mọi người mà không tốn chi phí thuê VPS/Cloud.
- **Key Value**:
  - **Chi phí 0đ trọn đời**, không yêu cầu thẻ Visa/Mastercard.
  - **16GB RAM miễn phí** — dư sức tải và chạy mô hình Wav2Vec2 1.2GB mượt mà.
  - **Giữ nguyên 100% mã nguồn** mà bạn đã dày công xây dựng.

---

## 2. User Experience & Visual Design

- **Key User Flows**:
  1. Bạn tạo một tài khoản miễn phí tại `huggingface.co` và bấm **New Space** -> chọn **Docker** -> chọn phần cứng **CPU Basic (Free - 2 vCPU · 16GB RAM)**.
  2. Chạy file script tự động (`deploy_free_hf.bat` trên Windows hoặc `deploy_free_hf.sh` trên Linux/Mac) để đẩy nguyên trạng dự án lên Space.
  3. Hugging Face tự động đóng gói Docker, tải sẵn trọng số mô hình `nguyenvulebinh/lyric-alignment` vào ổ cứng container và mở cổng web công khai.
  4. Bạn truy cập đường dẫn trực tiếp `https://<ten-ban>-tool-lyric.hf.space` để sử dụng đầy đủ giao diện Auto Karaoke, Player và tính năng AI Auto Align.
- **Visual Identity & Theme**:
  - Giữ nguyên tuyệt đối 100% giao diện hiện có (`auto_karaoke.html`, `player.html`, `index.html`).

---

## 3. Key Product Decisions & Trade-Offs

- **Decision 1: Sử dụng Hugging Face Spaces (Docker SDK - 16GB RAM Free)**
  - *Chosen Approach*: Tận dụng cấu hình Docker sẵn có của dự án kết hợp kịch bản đẩy Git tự động lên Hugging Face Spaces.
  - *Why*: Đây là nền tảng duy nhất hiện nay cung cấp **16GB RAM miễn phí không cần thẻ tín dụng**, tương thích hoàn hảo với PyTorch + Torchaudio + Wav2Vec2.
  - *Alternatives Considered*:
    - *Google Cloud Run / Railway*: Yêu cầu liên kết thẻ thanh toán quốc tế và tính phí theo dung lượng RAM/CPU khi vượt hạn mức.
    - *Render.com Free*: Chỉ có 512MB RAM, không thể nạp được mô hình Wav2Vec2 1.2GB.
- **Decision 2: Không can thiệp vào mã nguồn ứng dụng**
  - *Chosen Approach*: Bổ sung tệp hướng dẫn chi tiết bằng tiếng Việt và script hỗ trợ deploy độc lập ở thư mục gốc/docs.
  - *Why*: Đảm bảo tuân thủ tuyệt đối yêu cầu không làm ảnh hưởng tới bất kỳ logic hay giao diện nào đã hoàn thiện.

---

## 4. Technical Architecture & Data Strategy *(Technical Reference)*

- **Architecture & Component Diagram**:

```
┌─────────────────────────────────────────────────────────────────┐
│             Máy tính của bạn / Kho mã nguồn hiện tại            │
│  • Giữ nguyên 100% code Python & HTML/CSS/JS                    │
│  • Chạy lệnh deploy_free_hf.bat / deploy_free_hf.sh             │
└───────────────────────────────┬─────────────────────────────────┘
                                │ git push (Miễn phí 100%)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│      Hugging Face Spaces Cloud (Free Tier: 2 vCPU, 16GB RAM)    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Docker Container (Python 3.10 + FFmpeg + libsndfile1)     │  │
│  │ • Cài đặt PyTorch CPU & gói phụ thuộc                     │  │
│  │ • Tải sẵn model nguyenvulebinh/lyric-alignment (~1.2GB)   │  │
│  │ • Chạy backend/fastapi_app.py                             │  │
│  └─────────────────────────────┬─────────────────────────────┘  │
└────────────────────────────────┼────────────────────────────────┘
                                 │ HTTPS Public URL (.hf.space)
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│        Người dùng truy cập Web & Sử dụng AI Auto Align          │
└─────────────────────────────────────────────────────────────────┘
```

- **Data Model & State**:
  - Mô hình `nguyenvulebinh/lyric-alignment` được tải sẵn ngay trong bước build Docker nên khi mở web không tốn thời gian tải lại.
  - Toàn bộ cấu hình bài hát lưu trên `localStorage` hoặc xuất/nhập file `.vtbt` / `.json` hoạt động nguyên bản 100%.
- **Interactive Component & State Mapping**:
  - Kịch bản hỗ trợ deploy sẽ tự động kiểm tra Git, hướng dẫn nhập đường dẫn Space của bạn và đẩy toàn bộ mã nguồn lên đám mây miễn phí mà không sửa đổi code gốc.
