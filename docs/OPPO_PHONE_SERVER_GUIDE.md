# Hướng Dẫn Biến Điện Thoại OPPO Thành Server Chạy Web (Chỉ Tốn ~25MB RAM, Không Bao Giờ Tràn RAM)

Điện thoại OPPO (Android) khi chạy file gốc `backend/fastapi_app.py` sẽ bị văng (`Killed` / tràn RAM) vì mô hình AI `Wav2Vec2` + thư viện `PyTorch` ngốn từ **2.2 GB đến 3 GB RAM** ngay lúc khởi động, khiến hệ điều hành ColorOS của OPPO tự động tắt ứng dụng.

Để bạn lấy chính chiếc **điện thoại OPPO làm Server** chạy 24/7 mượt mà **không đụng vào bất kỳ dòng code gốc nào**, dự án đã được trang bị thêm **2 bộ khởi chạy siêu nhẹ (chỉ tốn ~20–25MB RAM)**:
1. `server.mjs` (Chạy bằng Node.js trên Termux — chỉ tốn **25MB RAM**).
2. `server_oppo_lite.py` (Chạy bằng Python trên Termux — chỉ tốn **20MB RAM**, hỗ trợ kết nối Hybrid AI).

---

## Cách 1: Chạy Bằng Termux Trên Điện Thoại OPPO (Khuyên Dùng - Nhẹ Nhất & Dễ Nhất)

### Bước 1: Cài đặt Termux trên điện thoại OPPO
1. Tải và cài ứng dụng **Termux** (từ F-Droid hoặc GitHub chính thức của Termux).
2. *(Mẹo cho máy OPPO ColorOS)*: Nhấn giữ biểu tượng **Termux** -> **Thông tin ứng dụng (App Info)** -> **Mức sử dụng pin (Battery usage)** -> Bật **Cho phép hoạt động dưới nền (Allow background activity)** để khi tắt màn hình điện thoại server vẫn chạy.

### Bước 2: Cài đặt gói siêu nhẹ (Chỉ tốn ~50MB bộ nhớ thay vì 4GB của PyTorch)
Mở Termux trên điện thoại OPPO và dán lệnh sau:
```bash
pkg update -y && pkg install nodejs git cloudflared -y
```

### Bước 3: Chạy Server ngay trên điện thoại OPPO
Di chuyển vào thư mục dự án của bạn trên điện thoại và chạy:
```bash
bash run_oppo_termux.sh
```
Hoặc chạy trực tiếp:
```bash
PORT=7864 node server.mjs
```
Ngay lập tức, điện thoại OPPO của bạn đã trở thành Server tại địa chỉ:
- Trên chính điện thoại đó: `http://127.0.0.1:7864`
- Trên các máy tính/điện thoại khác cùng mạng Wi-Fi: `http://<IP-WiFi-của-điện-thoại-OPPO>:7864`

---

## Cách 2: Phát Server Từ Điện Thoại OPPO Ra Toàn Thế Giới (Miễn Phí 100% Có HTTPS)

Sau khi server đã chạy ở Bước 3, bạn mở một tab mới trong Termux (vuốt từ mép trái màn hình Termux sang phải -> chọn **New Session**) và gõ:
```bash
cloudflared tunnel --url http://127.0.0.1:7864
```
Chỉ sau 3 giây, Cloudflare sẽ cấp miễn phí cho chiếc điện thoại OPPO của bạn một đường link công khai có dạng:
```text
https://xxxx-xxxx-xxxx.trycloudflare.com
```
Bạn có thể gửi link này cho bất kỳ ai truy cập từ 4G/Wi-Fi ở mọi nơi mà không tốn 1 đồng nào!

---

## Cách 3: Kết Hợp Điện Thoại OPPO (20MB RAM) + AI Wav2Vec2 Đám Mây Miễn Phí (Hybrid Mode)

Nếu bạn muốn chiếc điện thoại OPPO làm Server chính nhưng khi bấm nút **Auto Align** vẫn có sức mạnh của mô hình AI `Wav2Vec2` 1.2GB:
1. Chạy `server_oppo_lite.py` trên điện thoại OPPO kèm đường dẫn Space miễn phí của bạn:
   ```bash
   REMOTE_AI_URL="https://ten-ban-ten-space.hf.space" python3 server_oppo_lite.py
   ```
2. **Cách hoạt động**:
   - Điện thoại OPPO chỉ tốn **20MB RAM** để phục vụ giao diện Auto Karaoke, Player, lưu trữ nhạc và hiệu ứng.
   - Khi có người bấm **Auto Align**, điện thoại OPPO tự động gửi nhờ file nhạc lên đám mây 16GB RAM xử lý rồi nhận kết quả JSON về lại điện thoại!
   - Nếu đang offline không có mạng, điện thoại OPPO tự động chuyển về bộ căn chỉnh siêu nhẹ ngay trên máy mà không bao giờ bị treo hay văng ứng dụng.
