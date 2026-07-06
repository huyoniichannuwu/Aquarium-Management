"""
Tab NHÂN VIÊN QUẢN LÝ
Chức năng:
  1. Quản lý Nhân viên  (thêm, sửa, đổi trạng thái, xóa)
  2. Quản lý Khách hàng (thêm, sửa, xóa)  → gọi proc themKhachHang / xoaKhachHang
  3. Quản lý Tài khoản  (thêm, khóa/mở, đổi mật khẩu, xóa)
  4. Xác nhận / hủy đơn đặt vé            → gọi proc xacNhanDon / HuyDon
  5. Danh sách Hóa đơn                    → view danhsachHoaDon (riêng)
  6. Danh sách & xác nhận Thanh toán      → view danhsachThanhToan + proc ThanhToan (riêng)
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
import hashlib

# ─────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────
def _lbl(parent, text, row, col, sticky="e", padx=6, pady=4):
    tk.Label(parent, text=text).grid(row=row, column=col,
                                     sticky=sticky, padx=padx, pady=pady)

def _entry(parent, var, row, col, width=28, state="normal"):
    e = tk.Entry(parent, textvariable=var, width=width, state=state)
    e.grid(row=row, column=col, sticky="w", padx=6, pady=4)
    return e

def hash_pass(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def tao_ma_moi(conn, table, col_ma, prefix):
    cur = conn.cursor()
    cur.execute(f"SELECT MAX({col_ma}) FROM {table} WHERE {col_ma} LIKE ?",
                f"{prefix}%")
    row = cur.fetchone()
    if row[0] is None:
        return f"{prefix}001"
    so = int(row[0][len(prefix):]) + 1
    return f"{prefix}{so:03d}"


# ─────────────────────────────────────────────────────────
#  QUẢN LÝ NHÂN VIÊN  (raw SQL – chưa có proc)
# ─────────────────────────────────────────────────────────
class PanelNhanVien(ttk.Frame):
    CHUC_VU = [
        "Nhân viên quản lý",
        "Nhân viên kiểm bán vé",
        "Nhân viên kỹ thuật",
        "Nhân viên chăm sóc sinh vật",
    ]
    TRANG_THAI = ["Đang làm", "Nghỉ việc"]

    def __init__(self, parent, conn):
        super().__init__(parent)
        self.conn = conn
        self._build()

    def _build(self):
        cols = ("Mã NV", "Họ tên", "Chức vụ", "Điện thoại",
                "Email", "Lương", "Ngày vào làm", "Trạng thái", "Mã quản lý")
        self.tv = ttk.Treeview(self, columns=cols, show="headings", height=12)
        widths = [80, 160, 180, 110, 180, 100, 120, 100, 100]
        for c, w in zip(cols, widths):
            self.tv.heading(c, text=c)
            self.tv.column(c, width=w, anchor="center")
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.tv.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=6, pady=6)
        sb.grid(row=0, column=4, sticky="ns", pady=6)
        self.tv.bind("<<TreeviewSelect>>", self._on_select)

        frm = ttk.LabelFrame(self, text="Thông tin nhân viên")
        frm.grid(row=1, column=0, columnspan=4, sticky="ew", padx=6, pady=6)

        self.v = {k: tk.StringVar() for k in
                  ["ma", "ten", "chucVu", "sdt", "email",
                   "diaChi", "luong", "trangThai", "maQL"]}

        fields = [
            ("Mã NV (tự sinh):", "ma",     0, "readonly"),
            ("Họ tên:",          "ten",    1, "normal"),
            ("Điện thoại:",      "sdt",    2, "normal"),
            ("Email:",           "email",  3, "normal"),
            ("Địa chỉ:",        "diaChi", 4, "normal"),
            ("Lương:",           "luong",  5, "normal"),
            ("Mã quản lý:",      "maQL",   6, "normal"),
        ]
        for lbl_txt, key, r, st in fields:
            _lbl(frm, lbl_txt, r, 0)
            _entry(frm, self.v[key], r, 1, state=st)

        _lbl(frm, "Chức vụ:", 0, 2)
        ttk.Combobox(frm, textvariable=self.v["chucVu"],
                     values=self.CHUC_VU, state="readonly",
                     width=26).grid(row=0, column=3, sticky="w", padx=6, pady=4)

        _lbl(frm, "Trạng thái:", 1, 2)
        ttk.Combobox(frm, textvariable=self.v["trangThai"],
                     values=self.TRANG_THAI, state="readonly",
                     width=14).grid(row=1, column=3, sticky="w", padx=6, pady=4)

        self.v["chucVu"].set(self.CHUC_VU[0])
        self.v["trangThai"].set(self.TRANG_THAI[0])

        btn_f = ttk.Frame(self)
        btn_f.grid(row=2, column=0, columnspan=4, pady=8)
        for txt, cmd in [
            ("➕ Thêm",    self._them),
            ("✏️ Sửa",    self._sua),
            ("🚫 Đổi TT", self._doi_trang_thai),
            ("🗑 Xóa",    self._xoa),
            ("🔄 Làm mới", self._load),
        ]:
            ttk.Button(btn_f, text=txt, command=cmd).pack(side="left", padx=6)

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self._load()

    def _load(self):
        self.tv.delete(*self.tv.get_children())
        cur = self.conn.cursor()
        cur.execute("""
            SELECT maNhanVien, hoTenNhanVien, chucVu, soDienThoai,
                   email, luong, ngayVaoLam, trangThai, maQuanLy
            FROM NHAN_VIEN ORDER BY maNhanVien
        """)
        for r in cur.fetchall():
            ma, ten, cv, sdt, email, luong, ngay, tt, maql = r
            luong_str = f"{luong:,}" if luong is not None else ""
            ngay_str  = str(ngay)[:10] if ngay else ""
            tag = "nghi" if tt == "Nghỉ việc" else ""
            self.tv.insert("", "end",
                           values=(ma, ten, cv, sdt, email,
                                   luong_str, ngay_str, tt, maql or ""),
                           tags=(tag,))
        self.tv.tag_configure("nghi", foreground="#999999")

    def _on_select(self, _=None):
        sel = self.tv.selection()
        if not sel:
            return
        vals = self.tv.item(sel[0])["values"]
        mapping = {
            "ma": vals[0], "ten": vals[1], "chucVu": vals[2],
            "sdt": vals[3], "email": vals[4], "luong": str(vals[5]),
            "trangThai": vals[7], "maQL": vals[8]
        }
        for k, v in mapping.items():
            self.v[k].set(str(v) if v is not None else "")
        # Fix số 0 đầu
        self.v["sdt"].set(str(vals[3]).zfill(10) if vals[3] else "")

    def _validate(self):
        ten   = self.v["ten"].get().strip()
        sdt   = self.v["sdt"].get().strip()
        email = self.v["email"].get().strip()
        cv    = self.v["chucVu"].get()
        if not ten:
            messagebox.showerror("Lỗi", "Họ tên không được để trống."); return False
        if not sdt or len(sdt) != 10 or not sdt.isdigit():
            messagebox.showerror("Lỗi", "Số điện thoại phải đúng 10 chữ số."); return False
        if "@" not in email:
            messagebox.showerror("Lỗi", "Email không hợp lệ."); return False
        if not cv:
            messagebox.showerror("Lỗi", "Vui lòng chọn chức vụ."); return False
        luong = self.v["luong"].get().replace(",", "")
        if luong and not luong.isdigit():
            messagebox.showerror("Lỗi", "Lương phải là số."); return False
        return True

    def _them(self):
        if not self._validate():
            return
        ma         = tao_ma_moi(self.conn, "NHAN_VIEN", "maNhanVien", "NV")
        luong_raw  = self.v["luong"].get().replace(",", "")
        luong      = int(luong_raw) if luong_raw else None
        maql       = self.v["maQL"].get().strip() or None
        cur = self.conn.cursor()
        try:
            cur.execute("""
                INSERT INTO NHAN_VIEN
                  (maNhanVien, hoTenNhanVien, chucVu, soDienThoai,
                   email, diaChi, luong, trangThai, maQuanLy)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, ma,
                self.v["ten"].get().strip(),
                self.v["chucVu"].get(),
                self.v["sdt"].get().strip(),
                self.v["email"].get().strip(),
                self.v["diaChi"].get().strip() or None,
                luong,
                self.v["trangThai"].get(),
                maql)
            self.conn.commit()
            messagebox.showinfo("Thành công", f"Đã thêm nhân viên {ma}.")
            self._load()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi DB", str(e))

    def _sua(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Vui lòng chọn nhân viên cần sửa.")
            return
        if not self._validate():
            return
        ma        = self.tv.item(sel[0])["values"][0]
        luong_raw = self.v["luong"].get().replace(",", "")
        luong     = int(luong_raw) if luong_raw else None
        maql      = self.v["maQL"].get().strip() or None
        cur = self.conn.cursor()
        try:
            cur.execute("""
                UPDATE NHAN_VIEN SET
                  hoTenNhanVien = ?, chucVu = ?, soDienThoai = ?,
                  email = ?, diaChi = ?, luong = ?,
                  trangThai = ?, maQuanLy = ?
                WHERE maNhanVien = ?
            """,
                self.v["ten"].get().strip(),
                self.v["chucVu"].get(),
                self.v["sdt"].get().strip(),
                self.v["email"].get().strip(),
                self.v["diaChi"].get().strip() or None,
                luong,
                self.v["trangThai"].get(),
                maql,
                ma)
            self.conn.commit()
            messagebox.showinfo("Thành công", f"Đã cập nhật nhân viên {ma}.")
            self._load()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi DB", str(e))

    def _doi_trang_thai(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Vui lòng chọn nhân viên.")
            return
        vals     = self.tv.item(sel[0])["values"]
        ma, tt   = vals[0], vals[7]
        tt_moi   = "Nghỉ việc" if tt == "Đang làm" else "Đang làm"
        if not messagebox.askyesno("Xác nhận",
                                   f"Đổi trạng thái {ma} → '{tt_moi}'?"):
            return
        cur = self.conn.cursor()
        cur.execute("UPDATE NHAN_VIEN SET trangThai = ? WHERE maNhanVien = ?",
                    tt_moi, ma)
        self.conn.commit()
        self._load()

    def _xoa(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Vui lòng chọn nhân viên cần xóa.")
            return
        ma = self.tv.item(sel[0])["values"][0]
        if not messagebox.askyesno("Xác nhận",
                                   f"Xóa nhân viên {ma}? Hành động này không thể hoàn tác!"):
            return
        cur = self.conn.cursor()
        try:
            cur.execute("DELETE FROM NHAN_VIEN WHERE maNhanVien = ?", ma)
            self.conn.commit()
            messagebox.showinfo("Thành công", f"Đã xóa nhân viên {ma}.")
            self._load()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror(
                "Lỗi",
                f"Không thể xóa. Có thể nhân viên đang liên kết dữ liệu khác.\n{e}")


# ─────────────────────────────────────────────────────────
#  QUẢN LÝ KHÁCH HÀNG  → EXEC themKhachHang / xoaKhachHang
# ─────────────────────────────────────────────────────────
class PanelKhachHang(ttk.Frame):
    GIOI_TINH = ["Nam", "Nữ", "Khác"]

    def __init__(self, parent, conn):
        super().__init__(parent)
        self.conn = conn
        self._build()

    def _build(self):
        # View danhsachKH_Public: maKhachHang, hoTenKhachHang, gioiTinh,
        #                          soCCCD, soDienThoai, email, diaChi
        cols = ("Mã KH", "Họ tên", "Giới tính", "CCCD",
                "Điện thoại", "Email", "Địa chỉ")
        self.tv = ttk.Treeview(self, columns=cols, show="headings", height=12)
        widths  = [80, 160, 80, 130, 110, 180, 200]
        for c, w in zip(cols, widths):
            self.tv.heading(c, text=c)
            self.tv.column(c, width=w, anchor="center")
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.tv.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=6, pady=6)
        sb.grid(row=0, column=4, sticky="ns", pady=6)
        self.tv.bind("<<TreeviewSelect>>", self._on_select)

        frm = ttk.LabelFrame(self, text="Thông tin khách hàng")
        frm.grid(row=1, column=0, columnspan=4, sticky="ew", padx=6, pady=6)

        self.v = {k: tk.StringVar() for k in
                  ["ma", "ten", "cccd", "sdt", "email", "diaChi", "gioiTinh"]}

        fields = [
            ("Mã KH (tự sinh):", "ma",     0, "readonly"),
            ("Họ tên:",          "ten",    1, "normal"),
            ("CCCD:",            "cccd",   2, "normal"),
            ("Điện thoại:",      "sdt",    3, "normal"),
            ("Email:",           "email",  4, "normal"),
            ("Địa chỉ:",        "diaChi", 5, "normal"),
        ]
        for lbl_txt, key, r, st in fields:
            _lbl(frm, lbl_txt, r, 0)
            _entry(frm, self.v[key], r, 1, state=st)

        _lbl(frm, "Giới tính:", 0, 2)
        ttk.Combobox(frm, textvariable=self.v["gioiTinh"],
                     values=self.GIOI_TINH, state="readonly",
                     width=14).grid(row=0, column=3, sticky="w", padx=6, pady=4)
        self.v["gioiTinh"].set("Nam")

        btn_f = ttk.Frame(self)
        btn_f.grid(row=2, column=0, columnspan=4, pady=8)
        for txt, cmd in [
            ("➕ Thêm",    self._them),
            ("✏️ Sửa",    self._sua),
            ("🗑 Xóa",    self._xoa),
            ("🔄 Làm mới", self._load),
        ]:
            ttk.Button(btn_f, text=txt, command=cmd).pack(side="left", padx=6)

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self._load()

    def _load(self):
        self.tv.delete(*self.tv.get_children())
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM danhsachKH_Public ORDER BY maKhachHang")
        for r in cur.fetchall():
            # self.tv.insert("", "end",
            #                values=tuple(str(v) if v else "" for v in r))
            ma, ten, gt, cccd, sdt, email, diachi = r
            self.tv.insert("", "end", values=(
                str(ma)   if ma    else "",
                str(ten)  if ten   else "",
                str(gt)   if gt    else "",
                str(cccd).zfill(12) if cccd else "",
                str(sdt).zfill(10)  if sdt  else "",
                str(email)  if email  else "",
                str(diachi) if diachi else "",
            ))

    def _on_select(self, _=None):
        sel = self.tv.selection()
        if not sel:
            return
        vals = self.tv.item(sel[0])["values"]
        # thứ tự view: Mã, Họ tên, Giới tính, CCCD, SĐT, Email, Địa chỉ
        keys = ["ma", "ten", "gioiTinh", "cccd", "sdt", "email", "diaChi"]
        for k, v in zip(keys, vals):
            self.v[k].set(str(v) if v else "")
        # Fix số 0 đầu
        self.v["cccd"].set(str(vals[3]).zfill(12) if vals[3] else "")
        self.v["sdt"].set(str(vals[4]).zfill(10)  if vals[4] else "")

    def _validate(self):
        ten   = self.v["ten"].get().strip()
        cccd  = self.v["cccd"].get().strip()
        sdt   = self.v["sdt"].get().strip()
        email = self.v["email"].get().strip()
        if not ten:
            messagebox.showerror("Lỗi", "Họ tên không được để trống."); return False
        if len(cccd) != 12 or not cccd.isdigit():
            messagebox.showerror("Lỗi", "CCCD phải đúng 12 chữ số."); return False
        if not sdt or len(sdt) != 10 or not sdt.isdigit():
            messagebox.showerror("Lỗi", "Số điện thoại phải đúng 10 chữ số."); return False
        if "@" not in email:
            messagebox.showerror("Lỗi", "Email không hợp lệ."); return False
        return True

    def _them(self):
        if not self._validate():
            return
        ma     = tao_ma_moi(self.conn, "KHACH_HANG", "maKhachHang", "KH")
        ten    = self.v["ten"].get().strip()
        cccd   = self.v["cccd"].get().strip()
        sdt    = self.v["sdt"].get().strip()
        email  = self.v["email"].get().strip()
        diachi = self.v["diaChi"].get().strip()
        gt     = self.v["gioiTinh"].get()
        cur = self.conn.cursor()
        try:
            # EXEC themKhachHang @makh, @tenkh, @cccd, @sdt, @email, @diachi, @gioitinh
            cur.execute("EXEC themKhachHang ?,?,?,?,?,?,?",
                        ma, ten, cccd, sdt, email, diachi, gt)
            self.conn.commit()
            messagebox.showinfo("Thành công", f"Đã thêm khách hàng {ma}.")
            self._load()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi DB", str(e))

    def _sua(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Vui lòng chọn khách hàng cần sửa.")
            return
        if not self._validate():
            return
        ma = self.tv.item(sel[0])["values"][0]
        cur = self.conn.cursor()
        try:
            cur.execute("""
                UPDATE KHACH_HANG SET
                  hoTenKhachHang = ?, soCCCD = ?, soDienThoai = ?,
                  email = ?, diaChi = ?, gioiTinh = ?
                WHERE maKhachHang = ?
            """,
                self.v["ten"].get().strip(),
                self.v["cccd"].get().strip(),
                self.v["sdt"].get().strip(),
                self.v["email"].get().strip(),
                self.v["diaChi"].get().strip(),
                self.v["gioiTinh"].get(),
                ma)
            self.conn.commit()
            messagebox.showinfo("Thành công", f"Đã cập nhật khách hàng {ma}.")
            self._load()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi DB", str(e))

    def _xoa(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Vui lòng chọn khách hàng cần xóa.")
            return
        ma = self.tv.item(sel[0])["values"][0]
        if not messagebox.askyesno("Xác nhận",
                                   f"Xóa khách hàng {ma}? Hành động này không thể hoàn tác!"):
            return
        cur = self.conn.cursor()
        try:
            # EXEC xoaKhachHang @makh
            cur.execute("EXEC xoaKhachHang ?", ma)
            self.conn.commit()
            messagebox.showinfo("Thành công", f"Đã xóa khách hàng {ma}.")
            self._load()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror(
                "Lỗi",
                f"Không thể xóa. Có thể khách hàng đang có đơn đặt vé.\n{e}")


# ─────────────────────────────────────────────────────────
#  QUẢN LÝ TÀI KHOẢN  (raw SQL – chưa có proc)
# ─────────────────────────────────────────────────────────
class PanelTaiKhoan(ttk.Frame):
    LOAI_TK     = ["Khách Hàng", "Nhân viên"]
    TRANG_THAI_TK = ["Hoạt Động", "Bị khóa"]

    def __init__(self, parent, conn):
        super().__init__(parent)
        self.conn = conn
        self._build()

    def _build(self):
        cols = ("Mã TK", "Tên đăng nhập", "Loại TK",
                "Trạng thái", "Ngày tạo", "Mã KH", "Mã NV")
        self.tv = ttk.Treeview(self, columns=cols, show="headings", height=12)
        widths  = [80, 150, 110, 100, 110, 90, 90]
        for c, w in zip(cols, widths):
            self.tv.heading(c, text=c)
            self.tv.column(c, width=w, anchor="center")
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.tv.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=6, pady=6)
        sb.grid(row=0, column=4, sticky="ns", pady=6)
        self.tv.bind("<<TreeviewSelect>>", self._on_select)

        frm = ttk.LabelFrame(self, text="Thông tin tài khoản")
        frm.grid(row=1, column=0, columnspan=4, sticky="ew", padx=6, pady=6)

        self.v = {k: tk.StringVar() for k in
                  ["ma", "tenDN", "matKhau", "loai", "trangThai", "maKH", "maNV"]}

        _lbl(frm, "Mã TK (tự sinh):", 0, 0)
        _entry(frm, self.v["ma"], 0, 1, state="readonly")

        _lbl(frm, "Tên đăng nhập:", 1, 0)
        _entry(frm, self.v["tenDN"], 1, 1)

        _lbl(frm, "Mật khẩu:", 2, 0)
        tk.Entry(frm, textvariable=self.v["matKhau"], width=28,
                 show="*").grid(row=2, column=1, sticky="w", padx=6, pady=4)

        _lbl(frm, "Loại TK:", 0, 2)
        ttk.Combobox(frm, textvariable=self.v["loai"],
                     values=self.LOAI_TK, state="readonly",
                     width=16).grid(row=0, column=3, sticky="w", padx=6, pady=4)
        self.v["loai"].set("Khách Hàng")

        _lbl(frm, "Trạng thái:", 1, 2)
        ttk.Combobox(frm, textvariable=self.v["trangThai"],
                     values=self.TRANG_THAI_TK, state="readonly",
                     width=14).grid(row=1, column=3, sticky="w", padx=6, pady=4)
        self.v["trangThai"].set("Hoạt Động")

        _lbl(frm, "Mã khách hàng:", 3, 0)
        _entry(frm, self.v["maKH"], 3, 1)
        tk.Label(frm, text="(Điền khi loại TK = Khách Hàng)",
                 fg="gray").grid(row=3, column=2, columnspan=2, sticky="w")

        _lbl(frm, "Mã nhân viên:", 4, 0)
        _entry(frm, self.v["maNV"], 4, 1)
        tk.Label(frm, text="(Điền khi loại TK = Nhân viên)",
                 fg="gray").grid(row=4, column=2, columnspan=2, sticky="w")

        btn_f = ttk.Frame(self)
        btn_f.grid(row=2, column=0, columnspan=4, pady=8)
        for txt, cmd in [
            ("➕ Thêm",       self._them),
            ("✏️ Sửa TT/Pass", self._sua),
            ("🔒 Khóa/Mở",   self._khoa_mo),
            ("🗑 Xóa",        self._xoa),
            ("🔄 Làm mới",    self._load),
        ]:
            ttk.Button(btn_f, text=txt, command=cmd).pack(side="left", padx=6)

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self._load()

    def _load(self):
        self.tv.delete(*self.tv.get_children())
        cur = self.conn.cursor()
        cur.execute("""
            SELECT maTaiKhoan, tenDangNhap, loaiTaiKhoan,
                   trangThai, ngayTao, maKhachHang, maNhanVien
            FROM TAI_KHOAN ORDER BY maTaiKhoan
        """)
        for r in cur.fetchall():
            tag = "khoa" if r[3] == "Bị khóa" else ""
            self.tv.insert("", "end", values=(
                r[0], r[1], r[2], r[3], str(r[4])[:10],
                r[5] or "", r[6] or ""
            ), tags=(tag,))
        self.tv.tag_configure("khoa", foreground="#cc0000")

    def _on_select(self, _=None):
        sel = self.tv.selection()
        if not sel:
            return
        vals = self.tv.item(sel[0])["values"]
        self.v["ma"].set(str(vals[0]))
        self.v["tenDN"].set(str(vals[1]))
        self.v["matKhau"].set("")
        self.v["loai"].set(str(vals[2]))
        self.v["trangThai"].set(str(vals[3]))
        self.v["maKH"].set(str(vals[5]) if vals[5] else "")
        self.v["maNV"].set(str(vals[6]) if vals[6] else "")

    def _validate_them(self):
        if not self.v["tenDN"].get().strip():
            messagebox.showerror("Lỗi", "Tên đăng nhập không được để trống."); return False
        if not self.v["matKhau"].get():
            messagebox.showerror("Lỗi", "Mật khẩu không được để trống."); return False
        loai = self.v["loai"].get()
        if loai == "Khách Hàng" and not self.v["maKH"].get().strip():
            messagebox.showerror("Lỗi", "Vui lòng nhập Mã khách hàng."); return False
        if loai == "Nhân viên" and not self.v["maNV"].get().strip():
            messagebox.showerror("Lỗi", "Vui lòng nhập Mã nhân viên."); return False
        return True

    def _them(self):
        if not self._validate_them():
            return
        ma   = tao_ma_moi(self.conn, "TAI_KHOAN", "maTaiKhoan", "TK")
        loai = self.v["loai"].get()
        makh = self.v["maKH"].get().strip() or None
        manv = self.v["maNV"].get().strip() or None
        if loai == "Khách Hàng":
            manv = None
        else:
            makh = None
        cur = self.conn.cursor()
        try:
            cur.execute("""
                INSERT INTO TAI_KHOAN
                  (maTaiKhoan, tenDangNhap, matKhau, loaiTaiKhoan,
                   trangThai, ngayTao, maKhachHang, maNhanVien)
                VALUES (?,?,?,?,?,?,?,?)
            """, ma,
                self.v["tenDN"].get().strip(),
                hash_pass(self.v["matKhau"].get()),
                loai,
                self.v["trangThai"].get(),
                date.today(),
                makh, manv)
            self.conn.commit()
            messagebox.showinfo("Thành công", f"Đã tạo tài khoản {ma}.")
            self._load()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi DB", str(e))

    def _sua(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Vui lòng chọn tài khoản.")
            return
        ma = self.tv.item(sel[0])["values"][0]
        tt = self.v["trangThai"].get()
        pw = self.v["matKhau"].get()
        cur = self.conn.cursor()
        try:
            if pw:
                cur.execute("""
                    UPDATE TAI_KHOAN SET trangThai = ?, matKhau = ?
                    WHERE maTaiKhoan = ?
                """, tt, hash_pass(pw), ma)
            else:
                cur.execute("""
                    UPDATE TAI_KHOAN SET trangThai = ?
                    WHERE maTaiKhoan = ?
                """, tt, ma)
            self.conn.commit()
            messagebox.showinfo("Thành công", f"Đã cập nhật tài khoản {ma}.")
            self._load()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi DB", str(e))

    def _khoa_mo(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Vui lòng chọn tài khoản.")
            return
        vals    = self.tv.item(sel[0])["values"]
        ma, tt  = vals[0], vals[3]
        tt_moi  = "Bị khóa" if tt == "Hoạt Động" else "Hoạt Động"
        if not messagebox.askyesno("Xác nhận", f"Đổi TK {ma} → '{tt_moi}'?"):
            return
        cur = self.conn.cursor()
        cur.execute("UPDATE TAI_KHOAN SET trangThai = ? WHERE maTaiKhoan = ?",
                    tt_moi, ma)
        self.conn.commit()
        self._load()

    def _xoa(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Vui lòng chọn tài khoản cần xóa.")
            return
        ma = self.tv.item(sel[0])["values"][0]
        if not messagebox.askyesno("Xác nhận", f"Xóa tài khoản {ma}?"):
            return
        cur = self.conn.cursor()
        try:
            cur.execute("DELETE FROM TAI_KHOAN WHERE maTaiKhoan = ?", ma)
            self.conn.commit()
            messagebox.showinfo("Thành công", f"Đã xóa tài khoản {ma}.")
            self._load()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi DB", str(e))


# ─────────────────────────────────────────────────────────
#  XÁC NHẬN / HỦY ĐƠN ĐẶT VÉ
#  Xác nhận → raw SQL UPDATE (chưa có proc)
#  Hủy      → EXEC HuyDon   (đã có proc)
# ─────────────────────────────────────────────────────────
class PanelDonDatVe(ttk.Frame):
    def __init__(self, parent, conn, ma_nv):
        super().__init__(parent)
        self.conn  = conn
        self.ma_nv = ma_nv
        self._build()

    def _build(self):
        flt = ttk.Frame(self)
        flt.grid(row=0, column=0, columnspan=5, sticky="w", padx=6, pady=6)
        tk.Label(flt, text="Trạng thái:").pack(side="left")
        self.v_tt_filter = tk.StringVar(value="Tất cả")
        ttk.Combobox(flt, textvariable=self.v_tt_filter,
                     values=["Tất cả", "Chờ xác nhận", "Đã xác nhận", "Đã hủy"],
                     state="readonly", width=16).pack(side="left", padx=4)
        ttk.Button(flt, text="🔍 Lọc", command=self._load).pack(side="left", padx=4)

        cols = ("Mã đặt", "Ngày đặt", "Ngày tham quan",
                "Số lượng", "Trạng thái", "Mã KH", "Ghi chú")
        self.tv = ttk.Treeview(self, columns=cols, show="headings", height=14)
        widths  = [90, 140, 130, 80, 120, 90, 200]
        for c, w in zip(cols, widths):
            self.tv.heading(c, text=c)
            self.tv.column(c, width=w, anchor="center")
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.tv.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=6, pady=4)
        sb.grid(row=1, column=4, sticky="ns")

        btn_f = ttk.Frame(self)
        btn_f.grid(row=2, column=0, columnspan=4, pady=8)
        ttk.Button(btn_f, text="✅ Xác nhận",
                   command=self._xac_nhan).pack(side="left", padx=6)
        ttk.Button(btn_f, text="❌ Hủy đơn",
                   command=self._huy).pack(side="left", padx=6)
        ttk.Button(btn_f, text="🔄 Làm mới",
                   command=self._load).pack(side="left", padx=6)

        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self._load()

    def _load(self):
        self.tv.delete(*self.tv.get_children())
        tt_filter = self.v_tt_filter.get()
        cur = self.conn.cursor()
        if tt_filter == "Tất cả":
            cur.execute("""
                SELECT maDatVe, ngayDatVe, ngayThamQuan,
                       soLuongVe, trangThaiDat, maKhachHang, ghiChu
                FROM DAT_VE ORDER BY ngayDatVe DESC
            """)
        else:
            cur.execute("""
                SELECT maDatVe, ngayDatVe, ngayThamQuan,
                       soLuongVe, trangThaiDat, maKhachHang, ghiChu
                FROM DAT_VE WHERE trangThaiDat = ?
                ORDER BY ngayDatVe DESC
            """, tt_filter)
        for r in cur.fetchall():
            ma, ngay_dat, ngay_tv, sl, tt, makh, gc = r
            tag = "huy" if tt == "Đã hủy" else ("xn" if tt == "Đã xác nhận" else "")
            self.tv.insert("", "end",
                           values=(ma, str(ngay_dat)[:16] if ngay_dat else "",
                                   str(ngay_tv), sl, tt, makh or "", gc or ""),
                           tags=(tag,))
        self.tv.tag_configure("huy", foreground="#999999")
        self.tv.tag_configure("xn",  foreground="#007700")

    def _get_selected(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Vui lòng chọn đơn đặt vé.")
            return None, None
        vals = self.tv.item(sel[0])["values"]
        return vals[0], vals[4]   # maDatVe, trangThaiDat

    def _xac_nhan(self):
        ma, tt = self._get_selected()
        if ma is None:
            return
        if tt != "Chờ xác nhận":
            messagebox.showwarning("Không hợp lệ",
                                   f"Đơn '{tt}' – chỉ xác nhận được đơn 'Chờ xác nhận'.")
            return
        cur = self.conn.cursor()
        try:
            # chưa có proc → dùng raw SQL
            cur.execute("""
                UPDATE DAT_VE
                SET trangThaiDat = N'Đã xác nhận', maNhanVien = ?
                WHERE maDatVe = ?
            """, self.ma_nv, ma)
            self.conn.commit()
            messagebox.showinfo("Thành công", f"Đã xác nhận đơn {ma}.")
            self._load()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi DB", str(e))

    def _huy(self):
        ma, tt = self._get_selected()
        if ma is None:
            return
        if tt == "Đã hủy":
            messagebox.showwarning("Thông báo", "Đơn này đã bị hủy rồi.")
            return
        if not messagebox.askyesno("Xác nhận", f"Hủy đơn {ma}?"):
            return
        cur = self.conn.cursor()
        try:
            # EXEC HuyDon @maDatVe  — proc xử lý toàn bộ (DAT_VE, VE, LICH_NGAY, HOA_DON, THANH_TOAN)
            cur.execute("EXEC HuyDon ?", ma)
            self.conn.commit()
            messagebox.showinfo("Thành công", f"Đã hủy đơn {ma}.")
            self._load()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi DB", str(e))


# ─────────────────────────────────────────────────────────
#  DANH SÁCH HÓA ĐƠN  (chỉ xem — hóa đơn do proc DatVe tự tạo)
#  Cần view danhsachHoaDon trong DB:
#    CREATE VIEW danhsachHoaDon AS
#    SELECT maHoaDon, ngayLap, thueVAT, giamGia, tongTien, maDatVe FROM HOA_DON
# ─────────────────────────────────────────────────────────
class PanelHoaDon(ttk.Frame):
    def __init__(self, parent, conn):
        super().__init__(parent)
        self.conn = conn
        self._build()

    def _build(self):
        tk.Label(self, text="Danh sách hóa đơn (tự sinh khi đặt vé)",
                 font=("Arial", 10, "bold")).grid(
            row=0, column=0, columnspan=2, padx=8, pady=(8, 2), sticky="w")

        # Lọc theo mã đặt vé
        flt = ttk.Frame(self)
        flt.grid(row=1, column=0, columnspan=2, sticky="w", padx=8, pady=4)
        tk.Label(flt, text="Lọc mã đặt vé:").pack(side="left")
        self.v_filter = tk.StringVar()
        tk.Entry(flt, textvariable=self.v_filter, width=12).pack(side="left", padx=4)
        ttk.Button(flt, text="🔍 Lọc", command=self._load).pack(side="left", padx=4)
        ttk.Button(flt, text="🔄 Tất cả", command=self._reset).pack(side="left", padx=4)

        cols = ("Mã HĐ", "Ngày lập", "Ngày tham quan" "Thuế VAT%", "Giảm giá%",
                "Tổng tiền", "Mã đặt vé", "Trạng thái TT")
        self.tv = ttk.Treeview(self, columns=cols, show="headings", height=16)
        widths  = [90, 110, 110, 80, 80, 130, 90, 120]
        for c, w in zip(cols, widths):
            self.tv.heading(c, text=c)
            self.tv.column(c, width=w, anchor="center")
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.tv.grid(row=2, column=0, sticky="nsew", padx=(8, 0), pady=4)
        sb.grid(row=2, column=1, sticky="ns", pady=4)

        ttk.Button(self, text="🔄 Làm mới",
                   command=self._reset).grid(row=3, column=0,
                                             columnspan=2, pady=6)
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)
        self._load()

    def _load(self):
        self.tv.delete(*self.tv.get_children())
        cur    = self.conn.cursor()
        filter_val = self.v_filter.get().strip()
        if filter_val:
            cur.execute("""
                SELECT maHoaDon, ngayLap, ngayThamQuan, thueVAT, giamGia,
               tongTien, maDatVe, trangThaiTT
                FROM danhsachHoaDon
                ORDER BY maHoaDon
            """, filter_val)
        else:
            cur.execute("""
                SELECT maHoaDon, ngayLap, thueVAT, giamGia, tongTien, maDatVe
                FROM danhsachHoaDon
                ORDER BY maHoaDon
            """)
        for r in cur.fetchall():
            ma, ngay, thue, giam, tong, dv = r
            self.tv.insert("", "end", values=(
                ma,
                str(ngay)[:10] if ngay else "",
                f"{thue or 0:.1f}%",
                f"{giam or 0:.1f}%",
                f"{tong or 0:,.0f} đ",
                dv
            ))

    def _reset(self):
        self.v_filter.set("")
        self._load()


# ─────────────────────────────────────────────────────────
#  THANH TOÁN  → EXEC ThanhToan @maDatVe, @hinhThuc
#  Hiển thị lịch sử thanh toán từ view danhsachThanhToan:
#    CREATE VIEW danhsachThanhToan AS
#    SELECT TT.maThanhToan, TT.hinhThucTT, TT.soTien,
#           TT.thoiGianTT, TT.trangThaiTT, TT.maHoaDon,
#           HD.maDatVe
#    FROM THANH_TOAN TT JOIN HOA_DON HD ON HD.maHoaDon = TT.maHoaDon
# ─────────────────────────────────────────────────────────
class PanelThanhToan(ttk.Frame):
    HINH_THUC = ["Tiền mặt", "Chuyển khoản"]

    def __init__(self, parent, conn):
        super().__init__(parent)
        self.conn = conn
        self._build()

    def _build(self):
        # ── Form thanh toán ──────────────────────────
        frm = ttk.LabelFrame(self, text="Ghi nhận thanh toán cho đơn đặt vé")
        frm.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=8)

        self.v_ma_dv    = tk.StringVar()
        self.v_hinh_thuc = tk.StringVar(value="Tiền mặt")

        _lbl(frm, "Mã đặt vé:", 0, 0)
        _entry(frm, self.v_ma_dv, 0, 1, width=14)

        _lbl(frm, "Hình thức TT:", 1, 0)
        ttk.Combobox(frm, textvariable=self.v_hinh_thuc,
                     values=self.HINH_THUC, state="readonly",
                     width=16).grid(row=1, column=1, sticky="w", padx=6, pady=4)

        # Hiển thị thông tin hóa đơn trước khi thanh toán
        self.lbl_info = tk.Label(frm, text="", fg="#0055aa",
                                 font=("Arial", 10, "bold"))
        self.lbl_info.grid(row=2, column=0, columnspan=4, pady=4)

        btn_f = ttk.Frame(frm)
        btn_f.grid(row=3, column=0, columnspan=4, pady=6)
        ttk.Button(btn_f, text="🔍 Xem hóa đơn",
                   command=self._xem_hoa_don).pack(side="left", padx=6)
        ttk.Button(btn_f, text="✅ Xác nhận thanh toán",
                   command=self._thanh_toan).pack(side="left", padx=6)

        # ── Lịch sử thanh toán ──────────────────────
        tk.Label(self, text="Lịch sử thanh toán",
                 font=("Arial", 10, "bold")).grid(
            row=1, column=0, columnspan=2, padx=8, pady=(8, 2), sticky="w")

        cols = ("Mã TT", "Hình thức", "Số tiền",
                "Thời gian TT", "Trạng thái", "Mã HĐ", "Mã đặt vé")
        self.tv = ttk.Treeview(self, columns=cols, show="headings", height=12)
        widths  = [90, 110, 140, 150, 120, 90, 100]
        for c, w in zip(cols, widths):
            self.tv.heading(c, text=c)
            self.tv.column(c, width=w, anchor="center")
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.tv.grid(row=2, column=0, sticky="nsew", padx=(8, 0), pady=4)
        sb.grid(row=2, column=1, sticky="ns", pady=4)

        ttk.Button(self, text="🔄 Làm mới",
                   command=self._load).grid(row=3, column=0,
                                            columnspan=2, pady=6)
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)
        self._load()

    def _xem_hoa_don(self):
        """Tra thông tin hóa đơn của đơn đặt vé để hiển thị trước khi thanh toán."""
        ma_dv = self.v_ma_dv.get().strip()
        if not ma_dv:
            messagebox.showerror("Lỗi", "Nhập mã đặt vé."); return
        cur = self.conn.cursor()
        cur.execute("""
            SELECT maHoaDon, tongTien, thueVAT, giamGia
            FROM HOA_DON WHERE maDatVe = ?
        """, ma_dv)
        row = cur.fetchone()
        if not row:
            self.lbl_info.config(
                text=f"Không tìm thấy hóa đơn cho đơn {ma_dv}.", fg="#cc0000")
            return
        mahd, tong, thue, giam = row
        self.lbl_info.config(
            text=f"HĐ {mahd}  |  Tổng tiền: {tong:,.0f} đ  "
                 f"(VAT {thue or 0:.0f}%  Giảm {giam or 0:.0f}%)",
            fg="#0055aa")

    def _thanh_toan(self):
        ma_dv = self.v_ma_dv.get().strip()
        if not ma_dv:
            messagebox.showerror("Lỗi", "Nhập mã đặt vé."); return
        ht = self.v_hinh_thuc.get()
        if not messagebox.askyesno("Xác nhận",
                                   f"Xác nhận thanh toán đơn {ma_dv}\nHình thức: {ht}?"):
            return
        cur = self.conn.cursor()
        try:
            # EXEC ThanhToan @maDatVe, @hinhThuc
            cur.execute("EXEC ThanhToan ?, ?", ma_dv, ht)
            # Đọc kết quả trả về từ proc
            row = cur.fetchone()
            self.conn.commit()
            if row:
                mahd, tong, msg = row
                messagebox.showinfo("Thành công",
                                    f"{msg}\nMã HĐ: {mahd} | Tổng: {tong:,.0f} đ")
            else:
                messagebox.showinfo("Thành công", "Thanh toán thành công.")
            self.v_ma_dv.set("")
            self.lbl_info.config(text="")
            self._load()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi DB", str(e))

    def _load(self):
        self.tv.delete(*self.tv.get_children())
        cur = self.conn.cursor()
        cur.execute("""
            SELECT maThanhToan, hinhThucTT, soTien,
                   thoiGianTT, trangThaiTT, maHoaDon, maDatVe
            FROM danhsachThanhToan
            ORDER BY thoiGianTT DESC
        """)
        for r in cur.fetchall():
            ma, ht, so, tg, tt, mahd, madv = r
            tag = "da_tt" if tt == "Đã thanh toán" else ""
            self.tv.insert("", "end", values=(
                ma, ht,
                f"{so:,.0f} đ" if so else "",
                str(tg)[:16] if tg else "",
                tt or "", mahd or "", madv or ""
            ), tags=(tag,))
        self.tv.tag_configure("da_tt", foreground="#007700")


# ─────────────────────────────────────────────────────────
#  Tab tổng hợp – Nhân viên Quản lý
# ─────────────────────────────────────────────────────────
class TabQuanLy:
    """
    parent – widget cha
    conn   – pyodbc connection
    ma_nv  – mã nhân viên quản lý đang đăng nhập
    """

    def __init__(self, parent, conn, ma_nv="NV001"):
        self.conn  = conn
        self.ma_nv = ma_nv
        self.frame = ttk.Frame(parent)

        self.nb = ttk.Notebook(self.frame)
        self.nb.pack(fill="both", expand=True, padx=8, pady=8)

        self.nb.add(PanelNhanVien(self.nb, conn),
                    text="  👷 Nhân viên  ")

        self.nb.add(PanelKhachHang(self.nb, conn),
                    text="  🧑‍💼 Khách hàng  ")

        self.nb.add(PanelTaiKhoan(self.nb, conn),
                    text="  🔑 Tài khoản  ")

        self.nb.add(PanelDonDatVe(self.nb, conn, ma_nv),
                    text="  📋 Đơn đặt vé  ")

        self.nb.add(PanelHoaDon(self.nb, conn),
                    text="  🧾 Hóa đơn  ")

        self.nb.add(PanelThanhToan(self.nb, conn),
                    text="  💳 Thanh toán  ")