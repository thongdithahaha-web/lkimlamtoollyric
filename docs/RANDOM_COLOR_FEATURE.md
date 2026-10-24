# 🎨 Random Colors Feature

## Tính năng mới: Random màu sắc cho từng từ

### Mô tả
Thêm nút **"🎨 Random Colors"** trong chế độ EDIT để tự động random màu sắc cho tất cả các từ trong bài hát.

### Vị trí
- **Desktop**: Nút nằm ngay dưới bảng chọn màu (color swatches)
- **Mobile**: Nút nằm trong Mobile Word Panel, đầu tiên trong danh sách actions

### Cách sử dụng

#### Desktop:
1. Vào chế độ **EDIT** (từ menu chính)
2. Thêm các từ vào bài hát
3. Bấm nút **"🎨 Random Colors"** (màu tím, nằm dưới bảng màu)
4. Tất cả các từ sẽ được random màu ngẫu nhiên từ bảng màu

#### Mobile:
1. Vào chế độ **EDIT**
2. Thêm các từ vào bài hát
3. Tap vào bất kỳ từ nào để mở Mobile Word Panel
4. Bấm nút **"🎨 Random"** (màu tím, đầu tiên trong danh sách)
5. Tất cả các từ sẽ được random màu

### Tính năng
- ✅ Random màu cho tất cả các từ cùng lúc
- ✅ Sử dụng 12 màu có sẵn trong bảng màu
- ✅ Tự động lưu settings sau khi random (nếu có songId)
- ✅ Hiển thị toast notification với số lượng từ đã random
- ✅ Hoạt động trên cả Desktop và Mobile

### Màu sắc có sẵn
```javascript
const COLORS = [
  '#f5f5f8',  // Trắng
  '#ff5555',  // Đỏ
  '#55eb55',  // Xanh lá
  '#4ba5ff',  // Xanh dương
  '#ffff6e',  // Vàng
  '#ff87eb',  // Hồng
  '#a55fff',  // Tím
  '#ff9b4b',  // Cam
  '#00ffd2',  // Xanh ngọc
  '#ff4baf',  // Hồng đậm
  '#9bff41',  // Xanh lá nhạt
  '#d2d2e1'   // Xám
];
```

### Code thay đổi
- Thêm hàm `randomizeWordColors()` để random màu
- Thêm hàm `randomColorBtnRect()` để định vị nút
- Cập nhật `boxRect()` để điều chỉnh vị trí text box
- Thêm vẽ nút trong `drawInputStatePC()`
- Thêm xử lý click trong `handleInputStatePointer()`
- Thêm nút mobile trong HTML và event listener

### Demo
```
Trước random:
- Từ 1: Trắng
- Từ 2: Trắng
- Từ 3: Trắng
- Từ 4: Trắng

Sau random:
- Từ 1: Đỏ
- Từ 2: Xanh dương
- Từ 3: Vàng
- Từ 4: Tím
```

### Lợi ích
- ⚡ Tiết kiệm thời gian: Không cần chọn màu từng từ một
- 🎨 Đa dạng màu sắc: Tạo hiệu ứng karaoke sống động
- 🎯 Dễ sử dụng: Chỉ cần 1 click
- 💾 Tự động lưu: Settings được lưu ngay sau khi random

### Version
- Added in: **_lkimlamdevcode 7.6 BETA**
- Date: May 14, 2026
