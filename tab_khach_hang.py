"""
Tab KHÁCH HÀNG
Chức năng:
  1. Xem lịch tham quan (LICH_NGAY) - còn bao nhiêu vé
  2. Đặt vé (tạo DAT_VE + VE)
  3. Xem đơn đặt vé của mình
  4. Xem hóa đơn của mình
"""

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


def _entry(parent, var, row, col, width=28, state="normal"):
    e = tk.Entry(parent, textvariable=var, width=width, state=state, font=FONT_NORMAL)
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


def lay_dat_ve_khach(conn, ma_kh):
    cur = conn.cursor()
    cur.execute("""
        SELECT maDatVe, ngayDatVe, ngayThamQuan,
               soLuongVe, trangThaiDat, ghiChu
        FROM danhsachDatVeKhach
        WHERE maKhachHang = ?
        ORDER BY ngayDatVe DESC
    """, ma_kh)
    return cur.fetchall()


def lay_hoa_don_khach(conn, ma_kh):
    cur = conn.cursor()
    cur.execute("""
        SELECT maHoaDon, ngayLap, thueVAT,
               giamGia, tongTien, maDatVe, ngayThamQuan, trangThaiTT
        FROM dbo.HoaDonKhachHang
        WHERE maKhachHang = ?
        ORDER BY ngayLap DESC
    """, ma_kh)
    return cur.fetchall()

def lay_thong_tin_vip(conn, ma_kh):
    cur = conn.cursor()
    cur.execute("""
        SELECT ISNULL(dbo.tinhtongchitieu(?), 0), kh.tenHang
        FROM KHACH_HANG kh
        WHERE kh.maKhachHang = ?
    """, ma_kh, ma_kh)
    return cur.fetchone()

def lay_phan_tram_giam(conn, ten_hang):
    """Lấy % giảm giá theo hạng thành viên từ bảng HANG_VIP. Trả về 0 nếu không có hạng."""
    if not ten_hang:
        return 0
    cur = conn.cursor()
    cur.execute("SELECT phanTramGiam FROM HANG_VIP WHERE tenHang = ?", ten_hang)
    row = cur.fetchone()
    return float(row[0]) if row else 0

def tao_ma_moi(conn, table, col_ma, prefix):
    """Sinh mã tự động: prefix + số thứ tự 3 chữ số."""
    cur = conn.cursor()
    cur.execute(f"SELECT MAX({col_ma}) FROM {table} WHERE {col_ma} LIKE ?",
                f"{prefix}%")
    row = cur.fetchone()
    if row[0] is None:
        return f"{prefix}001"
    so = int(row[0][len(prefix):]) + 1
    return f"{prefix}{so:03d}"


# ─────────────────────────────────────────────────────────
#  Lớp chính
# ─────────────────────────────────────────────────────────
class TabKhachHang:
    """
    Nhận vào:
      parent   widget cha (ttk.Notebook hoặc Frame)
      conn     kết nối pyodbc
      ma_kh    mã khách hàng đang đăng nhập
    """

    def __init__(self, parent, conn, ma_kh="KH001"):
        self.conn = conn
        self.ma_kh = ma_kh
        self._phan_tram_giam_hien_tai = 0  # % giảm giá theo hạng của chính khách này

        self.frame = ttk.Frame(parent)
        self._apply_scale()

        # Sub-notebook bên trong tab Khách hàng
        self.nb = ttk.Notebook(self.frame)
        self.nb.pack(fill="both", expand=True, padx=12, pady=12)

        self._build_lich_ngay()
        self._build_dat_ve()
        self._build_don_dat_ve()
        self._build_hoa_don()

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

    # ── 1. Lịch tham quan ────────────────────────────────
    def _build_lich_ngay(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  📅 Lịch tham quan  ")

        tk.Label(f, text="Lịch ngày tham quan còn vé (Thời gian mở cửa: 09h00 - 15h00)",
                 font=("Arial", 15, "bold")).pack(pady=(8, 5))

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

    # ── 2. Đặt vé ─────────────────────────────────────────
    def _build_dat_ve(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  🎫 Đặt vé  ")

        tk.Label(f, text="Đặt vé tham quan",
                 font=("Arial", 15, "bold")).grid(row=0, column=0,
                                                  columnspan=2, pady=(12, 8))

        self.lbl_hang = tk.Label(f, text="Hạng thành viên: —",
                                 font=("Arial", 13, "bold"), fg="#aa5500")
        self.lbl_hang.grid(row=1, column=0, columnspan=2, pady=(0, 10))

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
        self.lbl_tong.grid(row=6, column=0, columnspan=2, pady=4)

        ttk.Button(f, text="Tính tiền",
                   command=self._tinh_tien).grid(row=7, column=0, pady=8, padx=6)
        ttk.Button(f, text="✅ Đặt vé",
                   command=self._dat_ve).grid(row=7, column=1, pady=8, padx=6, sticky="w")

        tk.Label(f, text="Bảng giá vé", font=("Arial", 13, "bold")).grid(
            row=8, column=0, columnspan=2, pady=(16, 4))
        cols_gv = ("Mã", "Tên loại vé", "Giá (VNĐ)", "Điều kiện")
        tv_gv = ttk.Treeview(f, columns=cols_gv, show="headings", height=5)
        for c in cols_gv:
            tv_gv.heading(c, text=c)
            tv_gv.column(c, width=160, anchor="center")
        tv_gv.grid(row=9, column=0, columnspan=2, padx=10, pady=4, sticky="ew")
        self.tv_gia_ve = tv_gv
        self._load_bang_gia()

        tk.Label(f,
            text="⚠ Tại cổng kiểm soát, khách hàng không chứng minh được điều kiện vé sẽ phải phụ thu theo quy định",
            font=("Arial", 11, "italic"),
            fg="#cc0000",
            wraplength=500,
            justify="left").grid(row=10, column=0, columnspan=2, padx=10, pady=(4,8), sticky="w")

        self._load_hang()

    def _load_hang(self):
        try:
            _, hang = lay_thong_tin_vip(self.conn, self.ma_kh)
            self.lbl_hang.config(text=f"Hạng thành viên: {hang}")
            self._phan_tram_giam_hien_tai = lay_phan_tram_giam(self.conn, hang)
        except Exception:
            self.lbl_hang.config(text="Hạng thành viên: —")
            self._phan_tram_giam_hien_tai = 0

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
                                  values=(r[0], r[1], f"{r[2]:,}",  r[3] or "—"))

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
    # ── Validate phía UI (giữ nguyên) ──────────────────────────────
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

        # ── Gọi stored procedure ────────────────────────────────────────
        try:
            cur = self.conn.cursor()
            cur.execute("""
                EXEC DatVe
                    @maKhachHang  = ?,
                    @ngayThamQuan = ?,
                    @maLoaiVe     = ?,
                    @soLuongVe    = ?,
                    @ghiChu       = ?
            """, self.ma_kh, ngay_tv, ma_loai_ve, so_luong, ghi_chu)

            row = cur.fetchone()          # SP trả về maDatVe + thongBao
            ma_dat_ve = row[0]
            self.conn.commit()

            messagebox.showinfo("Thành công",
                                f"Đặt vé thành công!\nMã đặt vé: {ma_dat_ve}\nVui lòng thanh toán trong 10 phút!")
            self._load_lich_ngay()
            self._load_don_dat_ve()

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi đặt vé", str(e))

    # ── 3. Đơn đặt vé của khách ──────────────────────────
    def _build_don_dat_ve(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  📋 Đơn của tôi  ")

        tk.Label(f, text="Danh sách đơn đặt vé của bạn",
                 font=("Arial", 15, "bold")).pack(pady=(10, 4))

        cols = ("Mã đặt", "Ngày đặt", "Ngày tham quan",
                "Số lượng vé", "Trạng thái", "Ghi chú")
        tv = ttk.Treeview(f, columns=cols, show="headings", height=14)
        widths = [100, 160, 150, 90, 140, 220]
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
                   command=self._load_don_dat_ve).pack(side="left", padx=4)
        ttk.Button(btn_f, text="❌ Hủy đơn",
                   command=self._huy_don).pack(side="left", padx=4)

        self._load_don_dat_ve()

    def _load_don_dat_ve(self):
        self.tv_don.delete(*self.tv_don.get_children())
        rows = lay_dat_ve_khach(self.conn, self.ma_kh)
        for r in rows:
            ma, ngay_dat, ngay_tv, sl, tt, gc = r
            tag = "huy" if tt == "Đã hủy" else ("xn" if tt == "Đã xác nhận" else "")
            self.tv_don.insert("", "end",
                               values=(ma,
                                       str(ngay_dat)[:16] if ngay_dat else "",
                                       str(ngay_tv),
                                       sl, tt, gc or ""),
                               tags=(tag,))
        self.tv_don.tag_configure("huy", foreground="#999999")
        self.tv_don.tag_configure("xn",  foreground="#007700")

    def _huy_don(self):
        sel = self.tv_don.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Vui lòng chọn một đơn để hủy.")
            return
        vals = self.tv_don.item(sel[0])["values"]
        ma_dat_ve, _, ngay_tv, sl, tt, _ = vals
        if tt != "Chờ xác nhận":
            messagebox.showwarning("Không thể hủy",
                                   f"Đơn có trạng thái '{tt}' – không thể hủy.")
            return
        if not messagebox.askyesno("Xác nhận",
                                   f"Bạn có chắc muốn hủy đơn {ma_dat_ve}?"):
            return
        try:
            cur = self.conn.cursor()
            cur.execute("""
                EXEC HuyDon @maDatVe = ?
            """, ma_dat_ve)

            row = cur.fetchone()

            self.conn.commit()

            if row:
                messagebox.showinfo(
                    "Thành công",
                    f"{row[1]}\nMã đặt vé: {row[0]}"
                )
            else:
                messagebox.showinfo(
                    "Thành công",
                    f"Đã hủy đơn {ma_dat_ve}."
                )

            self._load_don_dat_ve()
            self._load_lich_ngay()

            if hasattr(self, "_load_hoa_don"):
                self._load_hoa_don()

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi hủy đơn", str(e))

    # ── 4. Hóa đơn ────────────────────────────────────────
    def _build_hoa_don(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  🧾 Hóa đơn  ")

        tk.Label(f, text="Hóa đơn của bạn",
                font=("Arial", 15, "bold")).pack(pady=(10, 4))
        
        self.lbl_vip = tk.Label(f, text="Tổng chi tiêu: — | Hạng thành viên: —",
                                font=("Arial", 13, "bold"), fg="#aa5500")
        self.lbl_vip.pack(pady=(0, 8))

        cols = ("Mã HĐ", "Ngày lập", "Ngày tham quan",
                "Thuế VAT%", "Giảm giá%", "Tổng tiền", "Trạng thái hóa đơn", "maDatVe")
        tv = ttk.Treeview(f, columns=cols, show="headings", height=14,
                        displaycolumns=cols[:-1])  # ẩn cột maDatVe
        widths = [100, 130, 150, 100, 100, 160, 150]
        for c, w in zip(cols[:-1], widths):
            tv.heading(c, text=c)
            tv.column(c, width=w, anchor="center")

        sb = ttk.Scrollbar(f, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=6)
        sb.pack(side="left", fill="y", pady=6)
        self.tv_hd = tv

        btn_f = ttk.Frame(f)
        btn_f.pack(fill="x", padx=10, pady=4)
        ttk.Button(btn_f, text="🔄 Làm mới",
                command=self._load_hoa_don).pack(side="left", padx=4)
        ttk.Button(btn_f, text="💳 Xác nhận đã chuyển khoản",
                command=self._thanh_toan).pack(side="left", padx=4)
        # ── Ảnh QR tĩnh ─────────────────────────────────────────
        self._qr_img = tk.PhotoImage(file="qr.png").subsample(2,3)
        tk.Label(f, image=self._qr_img).pack(pady=10)

        self._load_hoa_don()

    def _load_hoa_don(self):
        self._load_vip()
        self.tv_hd.delete(*self.tv_hd.get_children())
        rows = lay_hoa_don_khach(self.conn, self.ma_kh)
        for r in rows:
            ma_hd, ngay_lap, thue, giam, tong, ma_dv, ngay_tv, trang_thai_tt = r  
            tag = "paid" if trang_thai_tt == "Đã thanh toán" else ""
            self.tv_hd.insert("", "end", values=(
                ma_hd, str(ngay_lap)[:10], str(ngay_tv),
                f"{thue or 0:.1f}%",
                f"{giam or 0:.1f}%",
                f"{tong or 0:,.0f} đ",
                trang_thai_tt or "Chưa thanh toán",  
                ma_dv
            ), tags=(tag,))
        self.tv_hd.tag_configure("paid", foreground="#007700")

    def _load_vip(self):
        try:
            tong, hang = lay_thong_tin_vip(self.conn, self.ma_kh)
            self.lbl_vip.config(
                text=f"Tổng chi tiêu: {tong:,.0f} đ   |   Hạng thành viên: {hang}"
            )
        except Exception:
            self.lbl_vip.config(text="Tổng chi tiêu: — | Hạng thành viên: —")

    def _thanh_toan(self):
        sel = self.tv_hd.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Vui lòng chọn hóa đơn cần thanh toán.")
            return

        vals = self.tv_hd.item(sel[0])["values"]
        ma_hd      = vals[0]
        trang_thai = vals[6]   # ✅ Trạng thái
        ma_dv      = vals[7]   # ✅ maDatVe ẩn

        if not messagebox.askyesno("Xác nhận thanh toán",
                                    f"Hóa đơn: {ma_hd}\n"
                                    f"Bạn xác nhận đã chuyển khoản?\n"
                                    f"Hệ thống sẽ tự động xác nhận đơn."):
            return

        try:
            cur = self.conn.cursor()
            cur.execute("EXEC ThanhToan @maDatVe = ?, @hinhThuc = N'Chuyển khoản'",
                        ma_dv)
            row = cur.fetchone()
            self.conn.commit()
            messagebox.showinfo("Thành công",
                                f"Thanh toán thành công!\n"
                                f"Mã HĐ: {row[0]}\n"
                                f"Số tiền: {row[1]:,.0f} VNĐ")
            self._load_hoa_don()
            self._load_don_dat_ve()
            self._load_hang()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi thanh toán", str(e))