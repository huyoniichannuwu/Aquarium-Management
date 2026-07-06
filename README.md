"# Aquarium-Management-Project" 
"# Aquarium-Management-Project" 
# QLThuyCung – Ứng dụng Quản lý Thủy Cung

## Cấu trúc file

```
QLThuyCung/
├── main.py              ← Chạy file này để khởi động
├── database.py          ← Kết nối SQL Server
├── tab_khach_hang.py    ← Tab Khách hàng
├── tab_quan_ly.py       ← Tab Nhân viên Quản lý
└── README.md
```

## Yêu cầu

- Python 3.8+
- SQL Server với database **QLThuyCung** đã tạo xong
- ODBC Driver 17 for SQL Server

```bash
pip install pyodbc
```

## Cách chạy

```bash
cd QLThuyCung
python main.py
```

## Đăng nhập demo

Vì mật khẩu trong DB có thể là plain-text (dữ liệu demo), app hỗ trợ
cả mật khẩu plain-text lẫn SHA-256 hashed. Khi tạo tài khoản mới qua
giao diện, mật khẩu sẽ tự động được hash.

---

## Tab KHÁCH HÀNG (4 chức năng)

| Sub-tab | Chức năng |
|---|---|
| 📅 Lịch tham quan | Xem ngày còn vé, màu đỏ = hết, vàng = gần hết |
| 🎫 Đặt vé | Chọn ngày, loại vé, số lượng → đặt vé |
| 📋 Đơn của tôi | Xem danh sách đơn đã đặt, hủy đơn nếu chưa xác nhận |
| 🧾 Hóa đơn | Xem hóa đơn của mình |

---

## Tab NHÂN VIÊN QUẢN LÝ (5 chức năng)

| Sub-tab | Chức năng |
|---|---|
| 👷 Nhân viên | Thêm/sửa/xóa nhân viên, đổi trạng thái Đang làm ↔ Nghỉ việc |
| 🧑‍💼 Khách hàng | Thêm/sửa/xóa khách hàng |
| 🔑 Tài khoản | Tạo/sửa/khóa/xóa tài khoản, đặt lại mật khẩu |
| 📋 Đơn đặt vé | Xem tất cả đơn, lọc theo trạng thái, xác nhận / hủy |
| 🧾 Hóa đơn / TT | Lập hóa đơn (tính thuế + giảm giá), ghi nhận thanh toán |

---

## Luồng nghiệp vụ cơ bản

```
Khách đặt vé
  → NV Quản lý xác nhận đơn (tab Đơn đặt vé)
  → NV Quản lý lập hóa đơn  (tab Hóa đơn / TT)
  → NV Quản lý ghi nhận TT  (cùng tab, phần dưới)
```

## Ghi chú kỹ thuật

- **Mã tự sinh**: DV001, VE001, HD001, TT001, NV001, KH001, TK001 …
- **Mật khẩu**: lưu SHA-256 khi tạo qua UI
- **Số vé còn lại** được cập nhật tự động vào `LICH_NGAY.soVeDaBan`
  mỗi khi đặt vé thành công hoặc hủy đơn
- **Xóa nhân viên/khách hàng** sẽ báo lỗi nếu còn FK liên kết
  (đây là hành vi đúng – bảo vệ toàn vẹn dữ liệu)
"# Aquarium-Management" 
