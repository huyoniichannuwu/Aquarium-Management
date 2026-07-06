"""
Tab NHÂN VIÊN KIỂM BÁN VÉ
Chức năng:
  1. Xem lịch tham quan (LICH_NGAY) - còn bao nhiêu vé (giống y hệt khách hàng)
  2. Đặt vé cho khách hàng - gọi ĐÚNG procedure DatVe như bên khách hàng,
     chỉ khác là có chọn khách hàng + truyền thêm @maNhanVien
  3. Xem danh sách đơn đặt vé khách hàng (toàn bộ, không chỉ 1 khách) + hủy đơn
  4. Xem hóa đơn khách hàng + xác nhận thanh toán (Tiền mặt / Chuyển khoản),
     logic y chang procedure ThanhToan bên khách hàng
  5. Xem danh sách khách hàng (view danhsachKH_Public)
  6. Đăng ký tài khoản khách hàng mới (procedure DangKy, băm SHA-256 trước khi gửi)

Ghi chú / giả định (vì không có định nghĩa đầy đủ của 2 view dưới đây):
  - View DatVeKhach và dbo.HoaDonKhachHang bên tab khách hàng được lọc bằng
    "WHERE maKhachHang = ?", nghĩa là 2 view này chắc chắn có cột maKhachHang.
    Ở đây mình JOIN thêm bảng KHACH_HANG để lấy hoTenKhachHang hiển thị cho
    nhân viên biết đơn/hóa đơn đó là của khách nào.
  - Nếu 2 view đó đã có sẵn cột tên khách hàng thì có thể bỏ JOIN đi cho gọn,
    chỉ cần sửa lại câu SELECT trong lay_tat_ca_dat_ve() / lay_tat_ca_hoa_don().

Cập nhật (giảm giá theo hạng thành viên):
  - Giả định view danhsachKH_Public trả về cột cuối cùng là "Hạng thành viên"
    (tức r[7]), và giá trị đó khớp với cột tenHang trong bảng HANG_VIP.
    Nếu tên cột/khóa không khớp thì phần tra % giảm giá sẽ luôn ra 0 — cần
    chỉnh lại index r[7] hoặc câu SELECT trong lay_danh_sach_kh() cho đúng.
"""

import hashlib
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, timedelta


# ── Font/kích thước dùng chung cho cả giao diện (to hơn mặc định của Tk) ──
FONT_NORMAL = ("Arial", 12)
FONT_BOLD   = ("Arial", 12, "bold")
ROW_HEIGHT  = 32


#  Helper nhỏ
def _lbl(parent, text, row, col, sticky="e", padx=8, pady=6, **kw):
    kw.setdefault("font", FONT_NORMAL)
    tk.Label(parent, text=text, **kw).grid(row=row, column=col,
                                           sticky=sticky, padx=padx, pady=pady)


def _entry(parent, var, row, col, width=28, state="normal", show=None):
    e = tk.Entry(parent, textvariable=var, width=width, state=state, show=show,
                 font=FONT_NORMAL)
    e.grid(row=row, column=col, sticky="w", padx=8, pady=6)
    return e


#  Hàm tiện ích đọc DB
def lay_loai_ve(conn):
    cur = conn.cursor()
    cur.execute("select * from danhsachLoaive")
    return cur.fetchall()


def lay_lich_ngay(conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM LichNgay ORDER BY ngayThamQuan")
    return cur.fetchall()


def lay_danh_sach_kh(conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM danhsachKH_Public ORDER BY maKhachHang")
    return cur.fetchall()


def lay_hang_vip_map(conn):
    """Trả về dict {tenHang: phanTramGiam} từ bảng HANG_VIP để tra cứu nhanh."""
    cur = conn.cursor()
    cur.execute("SELECT tenHang, phanTramGiam FROM HANG_VIP")
    return {r[0]: float(r[1]) for r in cur.fetchall()}


def lay_hang_vip(conn):
    """Trả về danh sách (tenHang, nguongTien, phanTramGiam) để hiển thị lên bảng, sắp theo ngưỡng tiền tăng dần."""
    cur = conn.cursor()
    cur.execute("SELECT tenHang, nguongTien, phanTramGiam FROM HANG_VIP ORDER BY nguongTien")
    return cur.fetchall()


def lay_tat_ca_dat_ve(conn, ma_kh=None):
    """Đơn đặt vé của TẤT CẢ khách hàng, hoặc lọc theo 1 mã KH nếu có truyền vào."""
    cur = conn.cursor()
    sql = """
        SELECT dv.maDatVe, dv.maKhachHang, kh.hoTenKhachHang,
               dv.ngayDatVe, dv.ngayThamQuan, dv.soLuongVe,
               dv.trangThaiDat, dv.ghiChu
        FROM dbo.danhsachDatVeKhach dv
        JOIN KHACH_HANG kh ON dv.maKhachHang = kh.maKhachHang
    """
    if ma_kh:
        sql += " WHERE dv.maKhachHang = ? ORDER BY dv.ngayDatVe DESC"
        cur.execute(sql, ma_kh)
    else:
        sql += " ORDER BY dv.ngayDatVe DESC"
        cur.execute(sql)
    return cur.fetchall()

def lay_danh_sach_ve(conn, tu_khoa=None):
    """Danh sách vé kèm thông tin loại vé, đơn đặt vé, khách hàng — phục vụ soát vé tại cổng.
    Nếu có tu_khoa: lọc theo maVe / maDatVe / maKhachHang / tên khách hàng (LIKE, không phân biệt vị trí)."""
    cur = conn.cursor()
    sql = """
        SELECT * from danhsachSoatVe
    """
    if tu_khoa:
        like = f"%{tu_khoa}%"
        sql += """ WHERE maVe LIKE ? OR maDatVe LIKE ?
                    OR maKhachHang LIKE ? OR hoTenKhachHang LIKE ?
                    ORDER BY ngayThamQuan DESC, maDatVe"""
        cur.execute(sql, like, like, like, like)
    else:
        sql += " ORDER BY ngayThamQuan DESC, maDatVe"
        cur.execute(sql)
    return cur.fetchall()


def lay_tat_ca_hoa_don(conn, ma_kh=None):
    """Hóa đơn của TẤT CẢ khách hàng, hoặc lọc theo 1 mã KH nếu có truyền vào."""
    cur = conn.cursor()
    sql = """
        SELECT hd.maHoaDon, hd.maKhachHang, kh.hoTenKhachHang,
               hd.ngayLap, hd.thueVAT, hd.giamGia, hd.tongTien,
               hd.maDatVe, hd.ngayThamQuan, hd.trangThaiTT
        FROM dbo.HoaDonKhachHang hd
        JOIN KHACH_HANG kh ON hd.maKhachHang = kh.maKhachHang
    """
    if ma_kh:
        sql += " WHERE hd.maKhachHang = ? ORDER BY hd.ngayLap DESC"
        cur.execute(sql, ma_kh)
    else:
        sql += " ORDER BY hd.ngayLap DESC"
        cur.execute(sql)
    return cur.fetchall()


# ─────────────────────────────────────────────────────────
#  Lớp chính
# ─────────────────────────────────────────────────────────
class TabNhanVienKiemBanVe:
    """
    Nhận vào:
      parent   widget cha (ttk.Notebook hoặc Frame)
      conn     kết nối pyodbc
      ma_nv    mã nhân viên đang đăng nhập (dùng để ghi @maNhanVien khi đặt vé)
    """

    def __init__(self, parent, conn, ma_nv="NV001"):
        self.conn = conn
        self.ma_nv = ma_nv
        self._phan_tram_giam_hien_tai = 0  # % giảm giá của khách hàng đang chọn

        self.frame = ttk.Frame(parent)
        self._apply_scale()

        self.nb = ttk.Notebook(self.frame)
        self.nb.pack(fill="both", expand=True, padx=12, pady=12)

        self._build_lich_ngay()
        self._build_dat_ve()
        self._build_don_dat_ve()
        self._build_soat_ve()
        self._build_hoa_don()
        self._build_danh_sach_kh()
        self._build_dang_ky_kh()

    def _apply_scale(self):
        """Tăng cỡ chữ + độ cao dòng cho toàn bộ giao diện (áp dụng 1 lần, dùng chung
        cho mọi widget tk cổ điển chưa set font riêng, và mọi widget ttk)."""
        # Widget tk cổ điển (Label/Entry/Button... không truyền font riêng)
        self.frame.option_add("*Font", FONT_NORMAL)

        style = ttk.Style()
        style.configure("TButton",       font=FONT_NORMAL, padding=6)
        style.configure("TLabel",        font=FONT_NORMAL)
        style.configure("TCombobox",     font=FONT_NORMAL)
        style.configure("TRadiobutton",  font=FONT_NORMAL)
        style.configure("TNotebook.Tab", font=FONT_NORMAL, padding=(14, 8))
        style.configure("Treeview",         font=FONT_NORMAL, rowheight=ROW_HEIGHT)
        style.configure("Treeview.Heading", font=FONT_BOLD)
        # Font cho danh sách xổ xuống của Combobox
        self.frame.option_add("*TCombobox*Listbox.font", FONT_NORMAL)

    # ── 1. Lịch tham quan (giống y hệt khách hàng) ───────
    def _build_lich_ngay(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  📅 Lịch tham quan  ")

        tk.Label(f, text="Lịch ngày tham quan còn vé",
                 font=("Arial", 15, "bold")).pack(pady=(10, 4))

        cols = ("Ngày", "Tối đa", "Đã bán", "Còn lại")
        tv = ttk.Treeview(f, columns=cols, show="headings", height=14)
        for c in cols:
            tv.heading(c, text=c)
            tv.column(c, width=140, anchor="center")

        sb = ttk.Scrollbar(f, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=6)
        sb.pack(side="left", fill="y", pady=6)

        self.tv_lich = tv

        ttk.Button(f, text="🔄 Làm mới",
                   command=self._load_lich_ngay).pack(pady=6)
        self._load_lich_ngay()

    def _load_lich_ngay(self):
        self.tv_lich.delete(*self.tv_lich.get_children())
        rows = lay_lich_ngay(self.conn)
        for r in rows:
            ngay, toi_da, da_ban, con_lai = r
            tag = "het" if con_lai == 0 else ("gan_het" if con_lai <= 10 else "")
            self.tv_lich.insert("", "end",
                                values=(str(ngay), toi_da, da_ban, con_lai),
                                tags=(tag,))
        self.tv_lich.tag_configure("het",     background="#ffcccc")
        self.tv_lich.tag_configure("gan_het", background="#fff3cc")

    # ── 2. Đặt vé cho khách ───────────────────────────────
    def _build_dat_ve(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  🎫 Đặt vé cho khách  ")

        tk.Label(f, text="Đặt vé tham quan cho khách hàng",
                 font=("Arial", 15, "bold")).grid(row=0, column=0,
                                                  columnspan=3, pady=(12, 10))

        self.var_khach_hang = tk.StringVar()
        _lbl(f, "Khách hàng:", 1, 0)
        self.cb_khach_hang = ttk.Combobox(f, textvariable=self.var_khach_hang,
                                          width=42, state="readonly")
        self.cb_khach_hang.grid(row=1, column=1, sticky="w", padx=6, pady=4)
        ttk.Button(f, text="🔄", width=3,
                   command=self._load_khach_hang_combo).grid(row=1, column=2, sticky="w")

        # Khi nhân viên chọn 1 khách hàng -> hiện hạng + % giảm giá ngay kế bên
        self.cb_khach_hang.bind("<<ComboboxSelected>>", self._on_chon_khach_hang)
        self.var_hang_kh = tk.StringVar(value="Hạng: —")
        tk.Label(f, textvariable=self.var_hang_kh,
                 font=("Arial", 11, "italic"), fg="#0055aa").grid(
            row=1, column=3, sticky="w", padx=(10, 0))

        self.var_ngay_tv   = tk.StringVar(value=str(date.today() + timedelta(days=1)))
        self.var_loai_ve   = tk.StringVar()
        self.var_so_luong  = tk.StringVar(value="1")
        self.var_ghi_chu   = tk.StringVar()

        _lbl(f, "Ngày tham quan (YYYY-MM-DD):", 2, 0)
        _entry(f, self.var_ngay_tv, 2, 1)

        _lbl(f, "Loại vé:", 3, 0)
        self.cb_loai_ve = ttk.Combobox(f, textvariable=self.var_loai_ve,
                                       width=26, state="readonly")
        self.cb_loai_ve.grid(row=3, column=1, sticky="w", padx=6, pady=4)
        self._load_loai_ve()

        _lbl(f, "Số lượng vé:", 4, 0)
        _entry(f, self.var_so_luong, 4, 1, width=10)

        _lbl(f, "Ghi chú:", 5, 0)
        _entry(f, self.var_ghi_chu, 5, 1)

        self.lbl_tong = tk.Label(f, text="Tổng tiền ước tính: —",
                                 font=("Arial", 12, "italic"), fg="#0055aa")
        self.lbl_tong.grid(row=6, column=0, columnspan=3, pady=4)

        ttk.Button(f, text="Tính tiền",
                   command=self._tinh_tien).grid(row=7, column=0, pady=8, padx=6)
        ttk.Button(f, text="✅ Đặt vé",
                   command=self._dat_ve).grid(row=7, column=1, pady=8, padx=6, sticky="w")

        # ── Bảng giá vé (trái) + Bảng hạng thành viên (phải), đặt cạnh nhau ──
        bang_f = tk.Frame(f)
        bang_f.grid(row=8, column=0, columnspan=4, padx=10, pady=(16, 4), sticky="nsew")

        gia_f = tk.Frame(bang_f)
        gia_f.pack(side="left", fill="both", expand=True, padx=(0, 10))
        tk.Label(gia_f, text="Bảng giá vé", font=("Arial", 13, "bold")).pack(pady=(0, 4))
        cols_gv = ("Mã", "Tên loại vé", "Giá (VNĐ)", "Điều kiện")
        tv_gv = ttk.Treeview(gia_f, columns=cols_gv, show="headings", height=5)
        for c in cols_gv:
            tv_gv.heading(c, text=c)
            tv_gv.column(c, width=135, anchor="center")
        tv_gv.pack(fill="both", expand=True)
        self.tv_gia_ve = tv_gv
        self._load_bang_gia()

        hang_f = tk.Frame(bang_f)
        hang_f.pack(side="left", fill="both", expand=True)
        tk.Label(hang_f, text="Bảng hạng thành viên", font=("Arial", 13, "bold")).pack(pady=(0, 4))
        cols_hv = ("Hạng", "Ngưỡng tiền (VNĐ)", "Giảm giá (%)")
        tv_hv = ttk.Treeview(hang_f, columns=cols_hv, show="headings", height=5)
        for c in cols_hv:
            tv_hv.heading(c, text=c)
            tv_hv.column(c, width=150, anchor="center")
        tv_hv.pack(fill="both", expand=True)
        self.tv_hang_vip = tv_hv
        self._load_bang_hang_vip()

        tk.Label(f,
            text="⚠ Tại cổng kiểm soát, khách hàng không chứng minh được điều kiện vé sẽ phải phụ thu theo quy định",
            font=("Arial", 11, "italic"),
            fg="#cc0000",
            wraplength=520,
            justify="left").grid(row=9, column=0, columnspan=4, padx=10, pady=(4, 8), sticky="w")

        self._load_khach_hang_combo()

    def _load_khach_hang_combo(self):
        rows = lay_danh_sach_kh(self.conn)
        # r = (maKhachHang, hoTenKhachHang, gioiTinh, soCCCD, soDienThoai, email, diaChi, hangThanhVien)
        self._kh_map = {f"{r[0]} – {r[1]} ({r[4]})": r for r in rows}
        self._hang_vip_map = lay_hang_vip_map(self.conn)  # {tenHang: phanTramGiam}

        cur_val = self.var_khach_hang.get()
        self.cb_khach_hang["values"] = list(self._kh_map.keys())
        if cur_val not in self._kh_map and self._kh_map:
            self.cb_khach_hang.current(0)

        self._on_chon_khach_hang()

    def _on_chon_khach_hang(self, event=None):
        """Cập nhật nhãn hạng + % giảm giá mỗi khi nhân viên chọn 1 khách hàng."""
        key = self.var_khach_hang.get()
        if key not in getattr(self, "_kh_map", {}):
            self.var_hang_kh.set("Hạng: —")
            self._phan_tram_giam_hien_tai = 0
            return

        ten_hang = self._kh_map[key][7]  # cột "Hạng thành viên" trong danhsachKH_Public
        phan_tram = self._hang_vip_map.get(ten_hang, 0)
        self._phan_tram_giam_hien_tai = phan_tram
        self.var_hang_kh.set(f"Hạng: {ten_hang or '—'}  (giảm {phan_tram:.1f}%)")

    def _load_loai_ve(self):
        loais = lay_loai_ve(self.conn)
        self._loai_ve_map = {f"{r[1]} – {r[2]:,}đ": r for r in loais}
        self.cb_loai_ve["values"] = list(self._loai_ve_map.keys())
        if self._loai_ve_map:
            self.cb_loai_ve.current(0)

    def _load_bang_gia(self):
        self.tv_gia_ve.delete(*self.tv_gia_ve.get_children())
        for r in lay_loai_ve(self.conn):
            self.tv_gia_ve.insert("", "end",
                                  values=(r[0], r[1], f"{r[2]:,}", r[3] or "—"))

    def _load_bang_hang_vip(self):
        self.tv_hang_vip.delete(*self.tv_hang_vip.get_children())
        for ten_hang, nguong_tien, phan_tram in lay_hang_vip(self.conn):
            self.tv_hang_vip.insert("", "end",
                                    values=(ten_hang, f"{nguong_tien:,.0f}", f"{phan_tram:.1f}%"))

    def _tinh_tien(self):
        key = self.var_loai_ve.get()
        if not key:
            return
        ma_loai_ve = self._loai_ve_map[key][0]

        try:
            sl = int(self.var_so_luong.get())
            if sl <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Lỗi", "Số lượng phải là số nguyên dương.")
            return

        # Không hardcode 0 nữa: dùng % giảm giá theo hạng của khách đang chọn
        phan_tram_giam = getattr(self, "_phan_tram_giam_hien_tai", 0)

        try:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT dbo.TinhTongTienDon(?, ?, ?)", ma_loai_ve, sl, phan_tram_giam
            )
            tong = cur.fetchone()[0]
            self.lbl_tong.config(
                text=f"Tổng tiền ước tính (đã gồm VAT 10% và giảm giá hạng "
                     f"thành viên {phan_tram_giam:.1f}%): {tong:,.0f} VNĐ"
            )
        except Exception as e:
            messagebox.showerror("Lỗi tính tiền", str(e))

    def _dat_ve(self):
        key_kh = self.var_khach_hang.get()
        if not key_kh or key_kh not in self._kh_map:
            messagebox.showerror("Lỗi", "Vui lòng chọn khách hàng.")
            return
        ma_kh = self._kh_map[key_kh][0]

        ngay_str = self.var_ngay_tv.get().strip()
        try:
            ngay_tv = date.fromisoformat(ngay_str)
        except ValueError:
            messagebox.showerror("Lỗi", "Ngày tham quan không hợp lệ (YYYY-MM-DD).")
            return

        key = self.var_loai_ve.get()
        if not key:
            messagebox.showerror("Lỗi", "Vui lòng chọn loại vé.")
            return
        ma_loai_ve = self._loai_ve_map[key][0]

        try:
            so_luong = int(self.var_so_luong.get())
            if so_luong <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Lỗi", "Số lượng phải là số nguyên dương.")
            return

        ghi_chu = self.var_ghi_chu.get().strip() or None

        # ── Gọi ĐÚNG stored procedure DatVe (y chang bên khách hàng),
        #    chỉ thêm @maNhanVien vì đây là nhân viên đặt vé giúp khách ──
        try:
            cur = self.conn.cursor()
            cur.execute("""
                EXEC DatVe
                    @maKhachHang  = ?,
                    @maNhanVien   = ?,
                    @ngayThamQuan = ?,
                    @maLoaiVe     = ?,
                    @soLuongVe    = ?,
                    @ghiChu       = ?
            """, ma_kh, self.ma_nv, ngay_tv, ma_loai_ve, so_luong, ghi_chu)

            row = cur.fetchone()          # SP trả về maDatVe + thongBao
            ma_dat_ve = row[0]
            self.conn.commit()

            messagebox.showinfo("Thành công",
                                f"Đặt vé thành công cho khách {ma_kh}!\n"
                                f"Mã đặt vé: {ma_dat_ve}\n"
                                f"Nhắc khách thanh toán trong 10 phút!")
            self._load_lich_ngay()
            self._load_don_dat_ve()

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi đặt vé", str(e))

    # ── 3. Đơn đặt vé khách hàng (toàn bộ khách) ─────────
    def _build_don_dat_ve(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  📋 Đơn đặt vé KH  ")

        tk.Label(f, text="Danh sách đơn đặt vé khách hàng",
                 font=("Arial", 15, "bold")).pack(pady=(10, 4))

        search_f = ttk.Frame(f)
        search_f.pack(fill="x", padx=10, pady=4)
        tk.Label(search_f, text="Lọc theo mã KH:").pack(side="left", padx=4)
        self.var_loc_ma_kh_don = tk.StringVar()
        tk.Entry(search_f, textvariable=self.var_loc_ma_kh_don, width=15).pack(side="left", padx=4)
        ttk.Button(search_f, text="🔍 Tìm",
                   command=lambda: self._load_don_dat_ve(
                       self.var_loc_ma_kh_don.get().strip() or None)
                   ).pack(side="left", padx=4)
        ttk.Button(search_f, text="Xem tất cả",
                   command=lambda: (self.var_loc_ma_kh_don.set(""), self._load_don_dat_ve())
                   ).pack(side="left", padx=4)

        cols = ("Mã đặt", "Mã KH", "Tên khách hàng", "Ngày đặt", "Ngày tham quan",
                "Số lượng vé", "Trạng thái", "Ghi chú")
        tv = ttk.Treeview(f, columns=cols, show="headings", height=14)
        widths = [95, 85, 170, 150, 140, 100, 130, 200]
        for c, w in zip(cols, widths):
            tv.heading(c, text=c)
            tv.column(c, width=w, anchor="center")

        sb = ttk.Scrollbar(f, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=6)
        sb.pack(side="left", fill="y", pady=6)
        self.tv_don = tv

        btn_f = ttk.Frame(f)
        btn_f.pack(fill="x", padx=10, pady=4)
        ttk.Button(btn_f, text="🔄 Làm mới",
                   command=lambda: self._load_don_dat_ve()).pack(side="left", padx=4)
        ttk.Button(btn_f, text="❌ Hủy đơn",
                   command=self._huy_don).pack(side="left", padx=4)

        self._load_don_dat_ve()

    def _load_don_dat_ve(self, ma_kh_filter=None):
        self.tv_don.delete(*self.tv_don.get_children())
        rows = lay_tat_ca_dat_ve(self.conn, ma_kh_filter)
        for r in rows:
            ma, ma_kh, ten_kh, ngay_dat, ngay_tv, sl, tt, gc = r
            tag = "huy" if tt == "Đã hủy" else ("xn" if tt == "Đã xác nhận" else "")
            self.tv_don.insert("", "end",
                               values=(ma, ma_kh, ten_kh,
                                       str(ngay_dat)[:16] if ngay_dat else "",
                                       str(ngay_tv), sl, tt, gc or ""),
                               tags=(tag,))
        self.tv_don.tag_configure("huy", foreground="#999999")
        self.tv_don.tag_configure("xn",  foreground="#007700")

    def _huy_don(self):
        sel = self.tv_don.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Vui lòng chọn một đơn để hủy.")
            return
        vals = self.tv_don.item(sel[0])["values"]
        ma_dat_ve, ma_kh, ten_kh, _, ngay_tv, sl, tt, _ = vals
        if tt != "Chờ xác nhận":
            messagebox.showwarning("Không thể hủy",
                                   f"Đơn có trạng thái '{tt}' – không thể hủy.")
            return
        if not messagebox.askyesno(
                "Xác nhận",
                f"Bạn có chắc muốn hủy đơn {ma_dat_ve} của khách {ten_kh} ({ma_kh})?"):
            return
        try:
            cur = self.conn.cursor()
            cur.execute("EXEC HuyDon @maDatVe = ?", ma_dat_ve)

            row = cur.fetchone()
            self.conn.commit()

            if row:
                messagebox.showinfo("Thành công", f"{row[1]}\nMã đặt vé: {row[0]}")
            else:
                messagebox.showinfo("Thành công", f"Đã hủy đơn {ma_dat_ve}.")

            self._load_don_dat_ve()
            self._load_lich_ngay()

            if hasattr(self, "_load_hoa_don"):
                self._load_hoa_don()

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi hủy đơn", str(e))
    
    # ── 3b. Soát vé tại cổng vào ──────────────────────────
    def _build_soat_ve(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  🎟️ Soát vé  ")

        tk.Label(f, text="Soát vé tại cổng vào",
                 font=("Arial", 15, "bold")).pack(pady=(10, 4))

        search_f = ttk.Frame(f)
        search_f.pack(fill="x", padx=10, pady=4)
        tk.Label(search_f, text="Tìm (mã vé / mã đặt vé / mã KH / tên KH):").pack(side="left", padx=4)
        self.var_tim_ve = tk.StringVar()
        e = tk.Entry(search_f, textvariable=self.var_tim_ve, width=30, font=FONT_NORMAL)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda ev: self._tim_ve())
        ttk.Button(search_f, text="🔍 Tìm", command=self._tim_ve).pack(side="left", padx=4)
        ttk.Button(search_f, text="Xem tất cả",
                   command=lambda: (self.var_tim_ve.set(""), self._load_ve())
                   ).pack(side="left", padx=4)

        cols = ("Mã vé", "Tình trạng", "Loại vé", "Mã đặt vé",
                "Ngày tham quan", "TT đơn", "Mã KH", "Tên KH", "SĐT")
        tv = ttk.Treeview(f, columns=cols, show="headings", height=14)
        widths = [90, 110, 130, 95, 120, 110, 85, 170, 110]
        for c, w in zip(cols, widths):
            tv.heading(c, text=c)
            tv.column(c, width=w, anchor="center")

        sb = ttk.Scrollbar(f, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=6)
        sb.pack(side="left", fill="y", pady=6)
        self.tv_ve = tv

        btn_f = ttk.Frame(f)
        btn_f.pack(fill="x", padx=10, pady=4)
        ttk.Button(btn_f, text="🔄 Làm mới",
                   command=lambda: self._load_ve()).pack(side="left", padx=4)
        ttk.Button(btn_f, text="✅ Xác nhận cho vào cổng",
                   command=self._xac_nhan_ve).pack(side="left", padx=4)

        self._load_ve()

    def _load_ve(self, tu_khoa=None):
        self.tv_ve.delete(*self.tv_ve.get_children())
        rows = lay_danh_sach_ve(self.conn, tu_khoa)
        for r in rows:
            ma_ve, tinh_trang, ten_lv, ma_dv, ngay_tv, tt_don, ma_kh, ten_kh, sdt = r
            if tinh_trang == "Đã sử dụng" if False else tinh_trang == "Đã sử dụng":
                tag = "dasudung"
            elif tinh_trang in ("Đã hủy", "Đã hết hạn"):
                tag = "huy"
            else:
                tag = ""
            self.tv_ve.insert("", "end",
                               values=(ma_ve, tinh_trang, ten_lv, ma_dv,
                                       str(ngay_tv), tt_don, ma_kh, ten_kh, sdt),
                               tags=(tag,))
        self.tv_ve.tag_configure("dasudung", foreground="#999999")
        self.tv_ve.tag_configure("huy", foreground="#cc0000")

    def _tim_ve(self):
        self._load_ve(self.var_tim_ve.get().strip() or None)

    def _xac_nhan_ve(self):
        sel = self.tv_ve.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Vui lòng chọn một vé để xác nhận.")
            return

        vals = self.tv_ve.item(sel[0])["values"]
        ma_ve, tinh_trang, ten_lv, ma_dv, ngay_tv, tt_don, ma_kh, ten_kh, sdt = vals

        if tinh_trang != "Chưa sử dụng":
            messagebox.showwarning(
                "Không thể xác nhận",
                f"Vé {ma_ve} đang ở trạng thái '{tinh_trang}', không thể cho vào cổng.")
            return

        if not messagebox.askyesno(
                "Xác nhận cho vào cổng",
                f"Vé: {ma_ve}\nLoại vé: {ten_lv}\n"
                f"Khách hàng: {ten_kh} ({ma_kh})\nNgày tham quan: {ngay_tv}\n\n"
                f"Xác nhận cho khách vào cổng?"):
            return

        try:
            cur = self.conn.cursor()
            cur.execute("EXEC XacNhanVaoCong @maVe = ?", ma_ve)
            row = cur.fetchone()
            self.conn.commit()
            messagebox.showinfo(
                "Thành công",
                row[1] if row else f"Đã xác nhận vé {ma_ve} vào cổng.")
            self._load_ve(self.var_tim_ve.get().strip() or None)
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi xác nhận vé", str(e))

    # ── 4. Hóa đơn khách hàng + Thanh toán ───────────────
    def _build_hoa_don(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  🧾 Hóa đơn / Thanh toán  ")

        tk.Label(f, text="Hóa đơn khách hàng",
                font=("Arial", 15, "bold")).pack(pady=(10, 4))

        search_f = ttk.Frame(f)
        search_f.pack(fill="x", padx=10, pady=4)
        tk.Label(search_f, text="Lọc theo mã KH:").pack(side="left", padx=4)
        self.var_loc_ma_kh_hd = tk.StringVar()
        tk.Entry(search_f, textvariable=self.var_loc_ma_kh_hd, width=15).pack(side="left", padx=4)
        ttk.Button(search_f, text="🔍 Tìm",
                   command=lambda: self._load_hoa_don(
                       self.var_loc_ma_kh_hd.get().strip() or None)
                   ).pack(side="left", padx=4)
        ttk.Button(search_f, text="Xem tất cả",
                   command=lambda: (self.var_loc_ma_kh_hd.set(""), self._load_hoa_don())
                   ).pack(side="left", padx=4)

        cols = ("Mã HĐ", "Mã KH", "Tên KH", "Ngày lập", "Ngày tham quan",
                "Thuế VAT%", "Giảm giá%", "Tổng tiền", "Trạng thái TT", "maDatVe")
        tv = ttk.Treeview(f, columns=cols, show="headings", height=12,
                        displaycolumns=cols[:-1])  # ẩn cột maDatVe
        widths = [90, 85, 160, 120, 140, 90, 90, 150, 150]
        for c, w in zip(cols[:-1], widths):
            tv.heading(c, text=c)
            tv.column(c, width=w, anchor="center")

        sb = ttk.Scrollbar(f, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=6)
        sb.pack(side="left", fill="y", pady=6)
        self.tv_hd = tv

        action_f1 = ttk.Frame(f)
        action_f1.pack(fill="x", padx=10, pady=(6, 2))

        ttk.Button(action_f1, text="🔄 Làm mới",
                   command=lambda: self._load_hoa_don()).pack(side="left", padx=4)
        ttk.Button(action_f1, text="✅ Xác nhận khách đã trả tiền",
                   command=self._thanh_toan).pack(side="left", padx=4)

        action_f2 = ttk.Frame(f)
        action_f2.pack(fill="x", padx=10, pady=(2, 6))

        tk.Label(action_f2, text="Hình thức TT:").pack(side="left", padx=(0, 4))
        self.var_hinh_thuc = tk.StringVar(value="Tiền mặt")
        ttk.Radiobutton(action_f2, text="💵 Tiền mặt", value="Tiền mặt",
                        variable=self.var_hinh_thuc,
                        command=self._toggle_qr).pack(side="left", padx=4)
        ttk.Radiobutton(action_f2, text="🏦 Chuyển khoản", value="Chuyển khoản",
                        variable=self.var_hinh_thuc,
                        command=self._toggle_qr).pack(side="left", padx=4)

        # ── Ảnh QR tĩnh - chỉ hiện khi chọn Chuyển khoản ────────
        self._qr_label = None
        try:
            self._qr_img = tk.PhotoImage(file="qr.png").subsample(3, 3)
            self._qr_label = tk.Label(f, image=self._qr_img)
            self._qr_label.pack(pady=10)
        except Exception:
            self._qr_img = None  # không có file qr.png thì thôi, không crash app

        self._load_hoa_don()
        self._toggle_qr()

    def _toggle_qr(self):
        if self._qr_label is None:
            return
        if self.var_hinh_thuc.get() == "Chuyển khoản":
            self._qr_label.pack(pady=10)
        else:
            self._qr_label.pack_forget()

    def _load_hoa_don(self, ma_kh_filter=None):
        self.tv_hd.delete(*self.tv_hd.get_children())
        rows = lay_tat_ca_hoa_don(self.conn, ma_kh_filter)
        for r in rows:
            ma_hd, ma_kh, ten_kh, ngay_lap, thue, giam, tong, ma_dv, ngay_tv, trang_thai_tt = r
            tag = "paid" if trang_thai_tt == "Đã thanh toán" else ""
            self.tv_hd.insert("", "end", values=(
                ma_hd, ma_kh, ten_kh, str(ngay_lap)[:10], str(ngay_tv),
                f"{thue or 0:.1f}%",
                f"{giam or 0:.1f}%",
                f"{tong or 0:,.0f} đ",
                trang_thai_tt or "Chưa thanh toán",
                ma_dv
            ), tags=(tag,))
        self.tv_hd.tag_configure("paid", foreground="#007700")

    def _thanh_toan(self):
        sel = self.tv_hd.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Vui lòng chọn hóa đơn cần xác nhận thanh toán.")
            return

        vals = self.tv_hd.item(sel[0])["values"]
        ma_hd      = vals[0]
        ma_kh      = vals[1]
        ten_kh     = vals[2]
        trang_thai = vals[8]
        ma_dv      = vals[9]   # ✅ maDatVe ẩn

        hinh_thuc = self.var_hinh_thuc.get()

        if not messagebox.askyesno("Xác nhận thanh toán",
                                    f"Hóa đơn: {ma_hd}\n"
                                    f"Khách hàng: {ten_kh} ({ma_kh})\n"
                                    f"Hình thức: {hinh_thuc}\n"
                                    f"Xác nhận khách đã trả tiền?"):
            return

        try:
            cur = self.conn.cursor()
            # Logic y chang procedure ThanhToan bên khách hàng, chỉ khác
            # là hình thức (@hinhThuc) do nhân viên chọn (Tiền mặt / Chuyển khoản)
            # thay vì luôn cố định "Chuyển khoản".
            cur.execute(
                "EXEC ThanhToan @maDatVe = ?, @hinhThuc = ?",
                ma_dv, hinh_thuc
            )
            row = cur.fetchone()
            self.conn.commit()
            messagebox.showinfo("Thành công",
                                f"Thanh toán thành công!\n"
                                f"Mã HĐ: {row[0]}\n"
                                f"Số tiền: {row[1]:,.0f} VNĐ\n"
                                f"Hình thức: {hinh_thuc}")
            self._load_hoa_don()
            self._load_don_dat_ve()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi thanh toán", str(e))

    # ── 5. Danh sách khách hàng (view danhsachKH_Public) ─
    def _build_danh_sach_kh(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  👥 Danh sách KH  ")

        tk.Label(f, text="Danh sách khách hàng",
                 font=("Arial", 15, "bold")).pack(pady=(10, 4))

        search_f = ttk.Frame(f)
        search_f.pack(fill="x", padx=10, pady=4)
        tk.Label(search_f, text="Tìm (mã / tên / SĐT):").pack(side="left", padx=4)
        self.var_tim_kh = tk.StringVar()
        tk.Entry(search_f, textvariable=self.var_tim_kh, width=30).pack(side="left", padx=4)
        ttk.Button(search_f, text="🔍 Tìm", command=self._tim_kh).pack(side="left", padx=4)
        ttk.Button(search_f, text="🔄 Làm mới",
                   command=self._load_danh_sach_kh).pack(side="left", padx=4)

        cols = ("Mã KH", "Họ tên", "Giới tính", "Số CCCD", "SĐT", "Email", "Địa chỉ", "Hạng thành viên")
        tv = ttk.Treeview(f, columns=cols, show="headings", height=14)
        widths = [85, 180, 85, 130, 120, 180, 200, 130]
        for c, w in zip(cols, widths):
            tv.heading(c, text=c)
            tv.column(c, width=w, anchor="center")

        sb = ttk.Scrollbar(f, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=6)
        sb.pack(side="left", fill="y", pady=6)
        self.tv_kh = tv

        self._kh_rows = []
        self._load_danh_sach_kh()

    def _load_danh_sach_kh(self):
        self.tv_kh.delete(*self.tv_kh.get_children())
        self._kh_rows = lay_danh_sach_kh(self.conn)
        for r in self._kh_rows:
            self.tv_kh.insert("", "end", values=tuple(r))

    def _tim_kh(self):
        kw = self.var_tim_kh.get().strip().lower()
        self.tv_kh.delete(*self.tv_kh.get_children())
        if not kw:
            rows = self._kh_rows
        else:
            rows = [r for r in self._kh_rows
                    if kw in str(r[0]).lower() or kw in str(r[1]).lower()
                    or kw in str(r[4]).lower()]
        for r in rows:
            self.tv_kh.insert("", "end", values=tuple(r))

    # ── 6. Đăng ký tài khoản khách hàng mới (procedure DangKy) ─
    def _build_dang_ky_kh(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  📝 Đăng ký KH mới  ")

        tk.Label(f, text="Đăng ký tài khoản khách hàng mới",
                 font=("Arial", 15, "bold")).grid(row=0, column=0, columnspan=2, pady=(12, 10))

        self.var_dk_ten_dn    = tk.StringVar()
        self.var_dk_mat_khau  = tk.StringVar()
        self.var_dk_xn_mk     = tk.StringVar()
        self.var_dk_ho_ten    = tk.StringVar()
        self.var_dk_cccd      = tk.StringVar()
        self.var_dk_sdt       = tk.StringVar()
        self.var_dk_email     = tk.StringVar()
        self.var_dk_dia_chi   = tk.StringVar()
        self.var_dk_gioi_tinh = tk.StringVar(value="Nam")

        _lbl(f, "Tên đăng nhập:", 1, 0)
        _entry(f, self.var_dk_ten_dn, 1, 1)

        _lbl(f, "Mật khẩu:", 2, 0)
        _entry(f, self.var_dk_mat_khau, 2, 1, show="*")

        _lbl(f, "Xác nhận mật khẩu:", 3, 0)
        _entry(f, self.var_dk_xn_mk, 3, 1, show="*")

        _lbl(f, "Họ tên:", 4, 0)
        _entry(f, self.var_dk_ho_ten, 4, 1)

        _lbl(f, "Số CCCD:", 5, 0)
        _entry(f, self.var_dk_cccd, 5, 1)

        _lbl(f, "Số điện thoại:", 6, 0)
        _entry(f, self.var_dk_sdt, 6, 1)

        _lbl(f, "Email:", 7, 0)
        _entry(f, self.var_dk_email, 7, 1)

        _lbl(f, "Địa chỉ:", 8, 0)
        _entry(f, self.var_dk_dia_chi, 8, 1)

        _lbl(f, "Giới tính:", 9, 0)
        cb_gt = ttk.Combobox(f, textvariable=self.var_dk_gioi_tinh,
                              values=["Nam", "Nữ", "Khác"], width=25, state="readonly")
        cb_gt.grid(row=9, column=1, sticky="w", padx=6, pady=4)

        ttk.Button(f, text="📝 Đăng ký",
                   command=self._dang_ky_kh).grid(row=10, column=0, columnspan=2, pady=12)
        
    def _dang_ky_kh(self):
        ten_dn    = self.var_dk_ten_dn.get().strip()
        mat_khau  = self.var_dk_mat_khau.get()
        xn_mk     = self.var_dk_xn_mk.get()
        ho_ten    = self.var_dk_ho_ten.get().strip()
        cccd      = self.var_dk_cccd.get().strip()
        sdt       = self.var_dk_sdt.get().strip()
        email     = self.var_dk_email.get().strip()
        dia_chi   = self.var_dk_dia_chi.get().strip()
        gioi_tinh = self.var_dk_gioi_tinh.get()

        if not all([ten_dn, mat_khau, ho_ten, cccd, sdt]):
            messagebox.showerror(
                "Lỗi", "Vui lòng nhập đủ Tên đăng nhập, Mật khẩu, Họ tên, CCCD, SĐT.")
            return

        if mat_khau != xn_mk:
            messagebox.showerror("Lỗi", "Mật khẩu xác nhận không khớp.")
            return

        if len(cccd) != 12 or not cccd.isdigit():
            messagebox.showerror("Lỗi", "Số CCCD phải gồm đúng 12 chữ số.")
            return

        if len(sdt) != 10 or not sdt.isdigit():
            messagebox.showerror("Lỗi", "Số điện thoại phải gồm đúng 10 chữ số.")
            return

        # Băm mật khẩu SHA-256 trước khi gửi xuống DB (đúng comment trong SP DangKy)
        mat_khau_hash = hashlib.sha256(mat_khau.encode("utf-8")).hexdigest()

        try:
            cur = self.conn.cursor()
            cur.execute("""
                EXEC DangKy
                    @tenDangNhap = ?,
                    @matKhau     = ?,
                    @hoTen       = ?,
                    @soCCCD      = ?,
                    @soDienThoai = ?,
                    @email       = ?,
                    @diaChi      = ?,
                    @gioiTinh    = ?
            """, ten_dn, mat_khau_hash, ho_ten, cccd, sdt,
                 email or None, dia_chi or None, gioi_tinh)

            row = cur.fetchone()
            self.conn.commit()

            messagebox.showinfo("Thành công",
                                f"Đăng ký thành công!\n"
                                f"Mã khách hàng: {row[0]}\n"
                                f"Mã tài khoản: {row[1]}")

            # reset form
            for var in (self.var_dk_ten_dn, self.var_dk_mat_khau, self.var_dk_xn_mk,
                        self.var_dk_ho_ten, self.var_dk_cccd, self.var_dk_sdt,
                        self.var_dk_email, self.var_dk_dia_chi):
                var.set("")
            self.var_dk_gioi_tinh.set("Nam")

            # cập nhật lại danh sách KH ở tab "Danh sách KH" và combobox ở tab "Đặt vé"
            self._load_danh_sach_kh()
            self._load_khach_hang_combo()

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi đăng ký", str(e))