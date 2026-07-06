#Vũ Thành Đạt
"""
Tab NHÂN VIÊN CHĂM SÓC SINH VẬT
Chức năng:
  1. Danh mục sinh vật (thêm / sửa sinh vật)
  2. Danh mục bể (chỉ xem)
  3. Danh sách sinh vật (tra cứu theo bể)
  4. Sinh vật cần chú ý (đang "Yếu")
  5. Ghi nhận chăm sóc (Kiểm tra định kỳ / Điều trị / Hoàn tất điều trị)
  6. Lịch sử chăm sóc
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date


# ── Font/kích thước dùng chung (đồng bộ với TabKhachHang) ──
FONT_NORMAL = ("Arial", 12)
FONT_BOLD   = ("Arial", 12, "bold")
ROW_HEIGHT  = 32


# Helper nhỏ
def _lbl(parent, text, row, col, sticky="e", padx=8, pady=6, **kw):
    kw.setdefault("font", FONT_NORMAL)
    tk.Label(parent, text=text, **kw).grid(row=row, column=col,
                                           sticky=sticky, padx=padx, pady=pady)


def _entry(parent, var, row, col, width=28, state="normal"):
    e = tk.Entry(parent, textvariable=var, width=width, state=state, font=FONT_NORMAL)
    e.grid(row=row, column=col, sticky="w", padx=8, pady=6)
    return e


# Hàm tiện ích đọc DB
def lay_danh_sach_sinh_vat(conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM danhsachSinhVat ORDER BY maBe, maSinhVat")
    return cur.fetchall()


def lay_sinh_vat_yeu(conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM DanhSachSinhVatYeu")
    return cur.fetchall()


def lay_sinh_vat_de_chon(conn):
    """Danh sách sinh vật (mã, tên, tình trạng hiện tại) để đổ vào combobox."""
    cur = conn.cursor()
    cur.execute("""
        SELECT maSinhVat, tenSinhVat, tinhTrangSucKhoe
        FROM SINH_VAT
        ORDER BY tenSinhVat
    """)
    return cur.fetchall()


def lay_lich_su_cham_soc(conn, ma_sv=None):
    cur = conn.cursor()
    if ma_sv:
        cur.execute("""
            SELECT maChamSoc, maSinhVat, tenSinhVat, maNhanVien, hoTenNhanVien,
                   ngayChamSoc, loaiChamSoc, ghiChu
            FROM LichSuChamSoc
            WHERE maSinhVat = ?
            ORDER BY ngayChamSoc DESC
        """, ma_sv)
    else:
        cur.execute("""
            SELECT maChamSoc, maSinhVat, tenSinhVat, maNhanVien, hoTenNhanVien,
                   ngayChamSoc, loaiChamSoc, ghiChu
            FROM LichSuChamSoc
            ORDER BY ngayChamSoc DESC
        """)
    return cur.fetchall()


# ── Hàm tiện ích DB cho tab Danh mục ────────────────────────
def lay_danh_muc_sinh_vat(conn):
    """Danh sách đầy đủ sinh vật kèm tên bể, phục vụ tab Danh mục sinh vật."""
    cur = conn.cursor()
    cur.execute("""
        select * from danhmucSinhVat
    """)
    return cur.fetchall()


def lay_thong_tin_sinh_vat_chi_tiet(conn, ma_sv):
    """Lấy đầy đủ thông tin gốc của 1 sinh vật (phục vụ mở form Sửa)."""
    cur = conn.cursor()
    cur.execute("""
        SELECT maSinhVat, tenSinhVat, maBe, ngaySinh, ngayNhap,
               cheDoDinhDuong, chuThich
        FROM SINH_VAT
        WHERE maSinhVat = ?
    """, ma_sv)
    return cur.fetchone()


def lay_be_de_chon(conn):
    """Danh sách bể (mã, tên) để đổ vào combobox chọn bể."""
    cur = conn.cursor()
    cur.execute("SELECT maBe, tenBe FROM BE ORDER BY tenBe")
    return cur.fetchall()


def lay_danh_sach_be(conn):
    """Danh sách đầy đủ bể kèm số sinh vật hiện tại, phục vụ tab Danh mục bể."""
    cur = conn.cursor()
    cur.execute("""
        select * from danhmucBe
    """)
    return cur.fetchall()


# ─────────────────────────────────────────────────────────
#  Lớp chính
# ─────────────────────────────────────────────────────────
class TabChamSocSinhVat:
    """
    Nhận vào:
      parent   widget cha (ttk.Notebook hoặc Frame)
      conn     kết nối pyodbc
      ma_nv    mã nhân viên đang đăng nhập (vai trò: Nhân viên chăm sóc sinh vật)
    """

    LOAI_CHAM_SOC = [N_ := "Kiểm tra định kỳ", "Điều trị", "Hoàn tất điều trị"]
    # Chỉ còn "Không đổi" và "Chuyển sang Yếu": việc chuyển sang "Khỏe mạnh"
    # (Hoàn tất điều trị) và "Đang điều trị" (Điều trị) đã được trigger
    # trg_CapNhatTinhTrangSinhVat trên bảng CHAM_SOC tự động xử lý.
    TRANG_THAI_MOI = ["Không đổi", "Chuyển sang Yếu"]

    def __init__(self, parent, conn, ma_nv="NV001"):
        self.conn = conn
        self.ma_nv = ma_nv
        self._sinh_vat_map = {}   # "MA - Ten (TinhTrang)" -> (maSinhVat, tenSinhVat, tinhTrang)
        self._be_map = {}         # "MA - Ten" -> maBe (dùng cho combobox chọn bể)

        self.frame = ttk.Frame(parent)
        self._apply_scale()

        self.nb = ttk.Notebook(self.frame)
        self.nb.pack(fill="both", expand=True, padx=12, pady=12)

        self._build_danh_muc_be()
        self._build_danh_muc_sinh_vat()
        self._build_danh_sach_sinh_vat()
        self._build_can_chu_y()
        self._build_ghi_nhan()
        self._build_lich_su()

    def _apply_scale(self):
        self.frame.option_add("*Font", FONT_NORMAL)
        style = ttk.Style()
        style.configure("TButton",       font=FONT_NORMAL, padding=6)
        style.configure("TLabel",        font=FONT_NORMAL)
        style.configure("TCombobox",     font=FONT_NORMAL)
        style.configure("TRadiobutton",  font=FONT_NORMAL)
        style.configure("TNotebook.Tab", font=FONT_NORMAL, padding=(14, 8))
        style.configure("Treeview",         font=FONT_NORMAL, rowheight=ROW_HEIGHT)
        style.configure("Treeview.Heading", font=FONT_BOLD)
        self.frame.option_add("*TCombobox*Listbox.font", FONT_NORMAL)

    # ── 0a. Danh mục sinh vật (thêm / sửa / xóa) ──────────
    def _build_danh_muc_sinh_vat(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  📋 Danh mục sinh vật  ")

        tk.Label(f, text="Quản lý danh mục sinh vật",
                 font=("Arial", 15, "bold")).grid(row=0, column=0,
                                                  columnspan=4, pady=(12, 8))

        # ── Form thêm mới ──
        self.var_ten_sv_moi = tk.StringVar()
        self.var_be_moi_sv  = tk.StringVar()
        self.var_ngay_sinh  = tk.StringVar()
        self.var_ngay_nhap  = tk.StringVar(value=str(date.today()))
        self.var_che_do     = tk.StringVar()

        _lbl(f, "Tên sinh vật:", 1, 0)
        _entry(f, self.var_ten_sv_moi, 1, 1)

        _lbl(f, "Bể nuôi:", 1, 2)
        self.cb_be_moi_sv = ttk.Combobox(f, textvariable=self.var_be_moi_sv,
                                         width=26, state="readonly")
        self.cb_be_moi_sv.grid(row=1, column=3, sticky="w", padx=8, pady=6)

        _lbl(f, "Ngày sinh (YYYY-MM-DD):", 2, 0)
        _entry(f, self.var_ngay_sinh, 2, 1)

        _lbl(f, "Ngày nhập (YYYY-MM-DD):", 2, 2)
        _entry(f, self.var_ngay_nhap, 2, 3)

        _lbl(f, "Chế độ dinh dưỡng:", 3, 0)
        _entry(f, self.var_che_do, 3, 1, width=60)

        _lbl(f, "Chú thích:", 4, 0, sticky="ne")
        self.txt_chu_thich_sv = tk.Text(f, width=60, height=3, font=FONT_NORMAL)
        self.txt_chu_thich_sv.grid(row=4, column=1, columnspan=3, sticky="w", padx=8, pady=6)

        ttk.Button(f, text="➕ Thêm sinh vật",
                   command=self._them_sinh_vat).grid(row=5, column=0,
                                                      columnspan=4, pady=10)

        # ── Danh sách + sửa + xóa ──
        cols = ("Mã SV", "Tên sinh vật", "Bể", "Ngày sinh", "Ngày nhập",
                "Tình trạng", "Chế độ dinh dưỡng")
        tv = ttk.Treeview(f, columns=cols, show="headings", height=12)
        widths = [70, 150, 120, 100, 100, 100, 220]
        for c, w in zip(cols, widths):
            tv.heading(c, text=c)
            tv.column(c, width=w, anchor="center")
        tv.grid(row=6, column=0, columnspan=4, sticky="nsew", padx=10, pady=6)
        f.grid_rowconfigure(6, weight=1)
        self.tv_danh_muc_sv = tv
        self.tv_danh_muc_sv.tag_configure("yeu", background="#ffcccc")

        btn_f = ttk.Frame(f)
        btn_f.grid(row=7, column=0, columnspan=4, pady=6)
        ttk.Button(btn_f, text="🔄 Làm mới",
                   command=self._load_danh_muc_sinh_vat).pack(side="left", padx=4)
        ttk.Button(btn_f, text="✏️ Sửa sinh vật đã chọn",
                   command=self._sua_sinh_vat).pack(side="left", padx=4)

        self._load_be_combobox_dung_chung()
        self._load_danh_muc_sinh_vat()

    def _load_be_combobox_dung_chung(self):
        """Nạp danh sách bể cho combobox chọn bể (thêm/sửa sinh vật)."""
        rows = lay_be_de_chon(self.conn)
        self._be_map = {f"{ma} - {ten}": ma for ma, ten in rows}
        values = list(self._be_map.keys())
        self.cb_be_moi_sv["values"] = values
        if values:
            self.cb_be_moi_sv.current(0)

    def _load_danh_muc_sinh_vat(self):
        self.tv_danh_muc_sv.delete(*self.tv_danh_muc_sv.get_children())
        rows = lay_danh_muc_sinh_vat(self.conn)
        for r in rows:
            ma, ten, ten_be, ngay_sinh, ngay_nhap, tinh_trang, che_do = r
            tag = "yeu" if tinh_trang == "Yếu" else ""
            self.tv_danh_muc_sv.insert("", "end", values=(
                ma, ten, ten_be or "—",
                str(ngay_sinh) if ngay_sinh else "—",
                str(ngay_nhap) if ngay_nhap else "—",
                tinh_trang, che_do or ""
            ), tags=(tag,))

    def _them_sinh_vat(self):
        ten = self.var_ten_sv_moi.get().strip()
        if not ten:
            messagebox.showerror("Lỗi", "Vui lòng nhập tên sinh vật.")
            return

        key_be = self.var_be_moi_sv.get()
        if key_be not in self._be_map:
            messagebox.showerror("Lỗi", "Vui lòng chọn bể nuôi.")
            return
        ma_be = self._be_map[key_be]

        ngay_sinh_str = self.var_ngay_sinh.get().strip()
        ngay_sinh = None
        if ngay_sinh_str:
            try:
                ngay_sinh = date.fromisoformat(ngay_sinh_str)
            except ValueError:
                messagebox.showerror("Lỗi", "Ngày sinh không hợp lệ (YYYY-MM-DD).")
                return

        ngay_nhap_str = self.var_ngay_nhap.get().strip()
        ngay_nhap = None
        if ngay_nhap_str:
            try:
                ngay_nhap = date.fromisoformat(ngay_nhap_str)
            except ValueError:
                messagebox.showerror("Lỗi", "Ngày nhập không hợp lệ (YYYY-MM-DD).")
                return

        che_do = self.var_che_do.get().strip() or None
        chu_thich = self.txt_chu_thich_sv.get("1.0", "end").strip() or None

        try:
            cur = self.conn.cursor()
            cur.execute("""
                EXEC ThemSinhVat
                    @tenSinhVat     = ?,
                    @maBe           = ?,
                    @ngaySinh       = ?,
                    @ngayNhap       = ?,
                    @cheDoDinhDuong = ?,
                    @chuThich       = ?
            """, ten, ma_be, ngay_sinh, ngay_nhap, che_do, chu_thich)

            row = cur.fetchone()
            self.conn.commit()

            messagebox.showinfo("Thành công", f"{row[1]}\nMã sinh vật: {row[0]}")

            self.var_ten_sv_moi.set("")
            self.var_che_do.set("")
            self.txt_chu_thich_sv.delete("1.0", "end")

            self._load_danh_muc_sinh_vat()
            self._load_sinh_vat_combobox()
            self._load_loc_sv_combobox()
            self._load_danh_sach_sinh_vat()

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi thêm sinh vật", str(e))

    def _sua_sinh_vat(self):
        sel = self.tv_danh_muc_sv.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Vui lòng chọn sinh vật cần sửa.")
            return
        ma_sv = self.tv_danh_muc_sv.item(sel[0])["values"][0]

        row = lay_thong_tin_sinh_vat_chi_tiet(self.conn, ma_sv)
        if not row:
            messagebox.showerror("Lỗi", "Không tìm thấy sinh vật.")
            return
        ma_sv, ten_hien_tai, ma_be_hien_tai, ngay_sinh, ngay_nhap, che_do, chu_thich = row

        win = tk.Toplevel(self.frame)
        win.title(f"Sửa thông tin sinh vật - {ma_sv}")
        win.option_add("*Font", FONT_NORMAL)
        win.grab_set()
        win.resizable(False, False)

        var_ten       = tk.StringVar(value=ten_hien_tai)
        var_be        = tk.StringVar()
        var_ngay_sinh = tk.StringVar(value=str(ngay_sinh) if ngay_sinh else "")
        var_ngay_nhap = tk.StringVar(value=str(ngay_nhap) if ngay_nhap else "")
        var_che_do    = tk.StringVar(value=che_do or "")

        tk.Label(win, text=f"Mã sinh vật: {ma_sv}",
                 font=FONT_BOLD).grid(row=0, column=0, columnspan=2,
                                       padx=10, pady=(10, 4), sticky="w")

        _lbl(win, "Tên sinh vật:", 1, 0)
        _entry(win, var_ten, 1, 1, width=32)

        _lbl(win, "Bể nuôi:", 2, 0)
        cb_be = ttk.Combobox(win, textvariable=var_be, width=29, state="readonly")
        cb_be["values"] = list(self._be_map.keys())
        cb_be.grid(row=2, column=1, sticky="w", padx=8, pady=6)
        for key, ma in self._be_map.items():
            if ma == ma_be_hien_tai:
                var_be.set(key)
                break

        _lbl(win, "Ngày sinh (YYYY-MM-DD):", 3, 0)
        _entry(win, var_ngay_sinh, 3, 1, width=32)

        _lbl(win, "Ngày nhập (YYYY-MM-DD):", 4, 0)
        _entry(win, var_ngay_nhap, 4, 1, width=32)

        _lbl(win, "Chế độ dinh dưỡng:", 5, 0)
        _entry(win, var_che_do, 5, 1, width=32)

        _lbl(win, "Chú thích:", 6, 0, sticky="ne")
        txt_chu_thich = tk.Text(win, width=32, height=4, font=FONT_NORMAL)
        txt_chu_thich.grid(row=6, column=1, sticky="w", padx=8, pady=6)
        if chu_thich:
            txt_chu_thich.insert("1.0", chu_thich)

        def _luu():
            ten_moi = var_ten.get().strip()
            if not ten_moi:
                messagebox.showerror("Lỗi", "Vui lòng nhập tên sinh vật.")
                return

            key_be = var_be.get()
            if key_be not in self._be_map:
                messagebox.showerror("Lỗi", "Vui lòng chọn bể nuôi.")
                return
            ma_be_moi = self._be_map[key_be]

            ngay_sinh_str = var_ngay_sinh.get().strip()
            ngay_sinh_moi = None
            if ngay_sinh_str:
                try:
                    ngay_sinh_moi = date.fromisoformat(ngay_sinh_str)
                except ValueError:
                    messagebox.showerror("Lỗi", "Ngày sinh không hợp lệ (YYYY-MM-DD).")
                    return

            ngay_nhap_str = var_ngay_nhap.get().strip()
            ngay_nhap_moi = None
            if ngay_nhap_str:
                try:
                    ngay_nhap_moi = date.fromisoformat(ngay_nhap_str)
                except ValueError:
                    messagebox.showerror("Lỗi", "Ngày nhập không hợp lệ (YYYY-MM-DD).")
                    return

            che_do_moi = var_che_do.get().strip() or None
            chu_thich_moi = txt_chu_thich.get("1.0", "end").strip() or None

            if not messagebox.askyesno("Xác nhận",
                                        f"Lưu thay đổi cho sinh vật {ma_sv}?"):
                return

            try:
                cur = self.conn.cursor()
                cur.execute("""
                    EXEC SuaSinhVat
                        @maSinhVat      = ?,
                        @tenSinhVat     = ?,
                        @maBe           = ?,
                        @ngaySinh       = ?,
                        @ngayNhap       = ?,
                        @cheDoDinhDuong = ?,
                        @chuThich       = ?
                """, ma_sv, ten_moi, ma_be_moi, ngay_sinh_moi, ngay_nhap_moi,
                     che_do_moi, chu_thich_moi)

                row = cur.fetchone()
                self.conn.commit()

                messagebox.showinfo("Thành công",
                                    row[1] if row else "Đã cập nhật thông tin sinh vật.")

                win.destroy()
                self._load_danh_muc_sinh_vat()
                self._load_sinh_vat_combobox()
                self._load_loc_sv_combobox()
                self._load_danh_sach_sinh_vat()

            except Exception as e:
                self.conn.rollback()
                messagebox.showerror("Lỗi sửa sinh vật", str(e))

        btn_f = ttk.Frame(win)
        btn_f.grid(row=7, column=0, columnspan=2, pady=12)
        ttk.Button(btn_f, text="💾 Lưu thay đổi", command=_luu).pack(side="left", padx=4)
        ttk.Button(btn_f, text="Hủy", command=win.destroy).pack(side="left", padx=4)


    # ── 0b. Danh mục bể (chỉ xem) ──────────────────────────
    def _build_danh_muc_be(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  □ Danh mục bể  ")

        tk.Label(f, text="Danh mục bể (chỉ xem)",
                 font=("Arial", 15, "bold")).pack(pady=(10, 4))

        cols = ("Mã bể", "Tên bể", "Vị trí", "Loại bể", "Thể tích",
                "Sức chứa", "Hiện tại", "Trạng thái")
        tv = ttk.Treeview(f, columns=cols, show="headings", height=16)
        widths = [70, 130, 120, 100, 90, 90, 80, 120]
        for c, w in zip(cols, widths):
            tv.heading(c, text=c)
            tv.column(c, width=w, anchor="center")

        sb = ttk.Scrollbar(f, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=6)
        sb.pack(side="left", fill="y", pady=6)
        self.tv_danh_muc_be = tv
        self.tv_danh_muc_be.tag_configure("ngung", foreground="#999999")
        self.tv_danh_muc_be.tag_configure("baotri", background="#fff3cc")

        ttk.Button(f, text="🔄 Làm mới",
                   command=self._load_danh_sach_be).pack(pady=6)
        self._load_danh_sach_be()

    def _load_danh_sach_be(self):
        self.tv_danh_muc_be.delete(*self.tv_danh_muc_be.get_children())
        rows = lay_danh_sach_be(self.conn)
        for r in rows:
            ma, ten, vi_tri, loai, the_tich, suc_chua, hien_tai, trang_thai = r
            tag = ""
            if trang_thai == "Ngừng hoạt động":
                tag = "ngung"
            elif trang_thai == "Bảo trì":
                tag = "baotri"
            self.tv_danh_muc_be.insert("", "end", values=(
                ma, ten, vi_tri or "—", loai or "—",
                the_tich if the_tich is not None else "—",
                suc_chua if suc_chua is not None else "—",
                hien_tai, trang_thai or "—"
            ), tags=(tag,))

    # ── 1. Danh sách sinh vật ─────────────────────────────
    def _build_danh_sach_sinh_vat(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  🐠 Danh sách sinh vật theo bể ")

        tk.Label(f, text="Danh sách sinh vật theo bể",
                 font=("Arial", 15, "bold")).pack(pady=(10, 4))

        cols = ("Mã bể", "Loại bể", "Tên bể", "Vị trí bể",  "Mã sinh vật", "Tên sinh vật", "Tình trạng")
        tv = ttk.Treeview(f, columns=cols, show="headings", height=14)
        for c in cols:
            tv.heading(c, text=c)
            tv.column(c, width=130, anchor="center")

        sb = ttk.Scrollbar(f, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=6)
        sb.pack(side="left", fill="y", pady=6)
        self.tv_ds = tv

        ttk.Button(f, text="🔄 Làm mới",
                   command=self._load_danh_sach_sinh_vat).pack(pady=6)
        self._load_danh_sach_sinh_vat()

    def _load_danh_sach_sinh_vat(self):
        self.tv_ds.delete(*self.tv_ds.get_children())
        rows = lay_danh_sach_sinh_vat(self.conn)
        for r in rows:
            mabe, loai_be, ten_be , vi_tri, masv, ten, tinh_trang = r
            tag = "yeu" if tinh_trang == "Yếu" else ""
            self.tv_ds.insert("", "end",
                              values=(mabe,loai_be, ten_be, vi_tri, masv , ten, tinh_trang ),
                              tags=(tag,))
        self.tv_ds.tag_configure("yeu", background="#ffcccc")

    # ── 2. Sinh vật cần chú ý ─────────────────────────────
    def _build_can_chu_y(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  ⚠ Cần chú ý  ")

        tk.Label(f, text="Sinh vật đang ở tình trạng \"Yếu\"",
                 font=("Arial", 15, "bold"), fg="#cc0000").pack(pady=(10, 4))

        cols = ("Mã sinh vật", "Tên sinh vật", "Tên bể", "Vị trí", "Lần chăm sóc gần nhất")
        tv = ttk.Treeview(f, columns=cols, show="headings", height=14)
        widths = [90, 160, 140, 140, 200]
        for c, w in zip(cols, widths):
            tv.heading(c, text=c)
            tv.column(c, width=w, anchor="center")

        sb = ttk.Scrollbar(f, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=6)
        sb.pack(side="left", fill="y", pady=6)
        self.tv_yeu = tv

        ttk.Button(f, text="🔄 Làm mới",
                   command=self._load_can_chu_y).pack(pady=6)
        self._load_can_chu_y()

    def _load_can_chu_y(self):
        self.tv_yeu.delete(*self.tv_yeu.get_children())
        rows = lay_sinh_vat_yeu(self.conn)
        for r in rows:
            ma, ten, ten_be, vi_tri, lan_gan_nhat = r
            self.tv_yeu.insert("", "end",
                               values=(ma, ten, ten_be, vi_tri,
                                       str(lan_gan_nhat)[:16] if lan_gan_nhat else "—"))

    # ── 3. Ghi nhận chăm sóc ──────────────────────────────
    def _build_ghi_nhan(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  📝 Ghi nhận chăm sóc  ")

        tk.Label(f, text="Ghi nhận một lần chăm sóc",
                 font=("Arial", 15, "bold")).grid(row=0, column=0,
                                                  columnspan=2, pady=(12, 8))

        self.var_sinh_vat   = tk.StringVar()
        self.var_loai       = tk.StringVar(value=self.LOAI_CHAM_SOC[0])
        self.var_trang_thai = tk.StringVar(value=self.TRANG_THAI_MOI[0])

        _lbl(f, "Sinh vật:", 1, 0)
        self.cb_sinh_vat = ttk.Combobox(f, textvariable=self.var_sinh_vat,
                                        width=40, state="readonly")
        self.cb_sinh_vat.grid(row=1, column=1, sticky="w", padx=8, pady=6)
        self.cb_sinh_vat.bind("<<ComboboxSelected>>", self._on_chon_sinh_vat)

        self.lbl_tinh_trang = tk.Label(f, text="Tình trạng hiện tại: —",
                                       font=("Arial", 12, "bold"), fg="#aa5500")
        self.lbl_tinh_trang.grid(row=2, column=0, columnspan=2, pady=(0, 8))

        _lbl(f, "Loại chăm sóc:", 3, 0)
        cb_loai = ttk.Combobox(f, textvariable=self.var_loai, values=self.LOAI_CHAM_SOC,
                               width=26, state="readonly")
        cb_loai.grid(row=3, column=1, sticky="w", padx=8, pady=6)
        cb_loai.bind("<<ComboboxSelected>>", self._on_chon_loai)

        _lbl(f, "Cập nhật tình trạng:", 4, 0)
        cb_tt = ttk.Combobox(f, textvariable=self.var_trang_thai,
                             values=self.TRANG_THAI_MOI, width=26, state="readonly")
        cb_tt.grid(row=4, column=1, sticky="w", padx=8, pady=6)

        _lbl(f, "Ghi chú:", 5, 0, sticky="ne")
        self.txt_ghi_chu = tk.Text(f, width=40, height=4, font=FONT_NORMAL)
        self.txt_ghi_chu.grid(row=5, column=1, sticky="w", padx=8, pady=6)

        ttk.Button(f, text="✅ Ghi nhận",
                   command=self._ghi_nhan_cham_soc).grid(row=6, column=0,
                                                         columnspan=2, pady=12)

        self._load_sinh_vat_combobox()

    def _load_sinh_vat_combobox(self):
        rows = lay_sinh_vat_de_chon(self.conn)
        self._sinh_vat_map = {
            f"{ma} - {ten} ({tinh_trang})": (ma, ten, tinh_trang)
            for ma, ten, tinh_trang in rows
        }
        self.cb_sinh_vat["values"] = list(self._sinh_vat_map.keys())
        if self._sinh_vat_map:
            self.cb_sinh_vat.current(0)
            self._on_chon_sinh_vat()
        else:
            self.var_sinh_vat.set("")
            self.lbl_tinh_trang.config(text="Tình trạng hiện tại: —", fg="#aa5500")

    def _on_chon_sinh_vat(self, event=None):
        key = self.var_sinh_vat.get()
        if key not in self._sinh_vat_map:
            return
        _, _, tinh_trang = self._sinh_vat_map[key]
        mau = "#cc0000" if tinh_trang == "Yếu" else "#007700"
        self.lbl_tinh_trang.config(text=f"Tình trạng hiện tại: {tinh_trang}", fg=mau)

    def _on_chon_loai(self, event=None):
        """Loại 'Điều trị' / 'Hoàn tất điều trị' đã được trigger
        trg_CapNhatTinhTrangSinhVat tự động cập nhật tình trạng sức khỏe,
        nên luôn để mặc định 'Không đổi'. Nhân viên chỉ cần tự chọn
        'Chuyển sang Yếu' khi Kiểm tra định kỳ phát hiện sinh vật yếu."""
        self.var_trang_thai.set("Không đổi")

    def _ghi_nhan_cham_soc(self):
        key = self.var_sinh_vat.get()
        if key not in self._sinh_vat_map:
            messagebox.showerror("Lỗi", "Vui lòng chọn sinh vật.")
            return
        ma_sv, ten_sv, tinh_trang_hien_tai = self._sinh_vat_map[key]

        loai = self.var_loai.get()
        ghi_chu = self.txt_ghi_chu.get("1.0", "end").strip() or None

        tt_lua_chon = self.var_trang_thai.get()
        trang_thai_moi = "Yếu" if tt_lua_chon == "Chuyển sang Yếu" else None

        if not messagebox.askyesno(
            "Xác nhận",
            f"Sinh vật: {ten_sv}\nLoại chăm sóc: {loai}\n"
            f"Cập nhật tình trạng: {tt_lua_chon}\n\nXác nhận ghi nhận?"
        ):
            return

        try:
            cur = self.conn.cursor()
            cur.execute("""
                EXEC GhiNhanChamSoc
                    @maSinhVat    = ?,
                    @maNhanVien   = ?,
                    @loaiChamSoc  = ?,
                    @ghiChu       = ?,
                    @trangThaiMoi = ?
            """, ma_sv, self.ma_nv, loai, ghi_chu, trang_thai_moi)

            row = cur.fetchone()
            self.conn.commit()

            messagebox.showinfo("Thành công",
                                f"{row[1]}\nMã chăm sóc: {row[0]}")

            self.txt_ghi_chu.delete("1.0", "end")
            self._load_sinh_vat_combobox()
            self._load_danh_sach_sinh_vat()
            self._load_can_chu_y()
            self._load_lich_su()

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi ghi nhận chăm sóc", str(e))

    # ── 4. Lịch sử chăm sóc ───────────────────────────────
    def _build_lich_su(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  📜 Lịch sử chăm sóc  ")

        top = ttk.Frame(f)
        top.pack(fill="x", padx=10, pady=(10, 4))

        tk.Label(top, text="Xem theo sinh vật:", font=FONT_NORMAL).pack(side="left", padx=(0, 6))
        self.var_loc_sv = tk.StringVar()
        self.cb_loc_sv = ttk.Combobox(top, textvariable=self.var_loc_sv,
                                      width=40, state="readonly")
        self.cb_loc_sv.pack(side="left", padx=6)

        ttk.Button(top, text="🔍 Lọc",
                   command=self._load_lich_su).pack(side="left", padx=6)
        ttk.Button(top, text="Xem tất cả",
                   command=self._xem_tat_ca_lich_su).pack(side="left", padx=6)

        cols = ("Mã chăm sóc", "Mã sinh vật", "Tên sinh vật", "Nhân viên",
                "Thời điểm", "Loại chăm sóc", "Ghi chú")
        tv = ttk.Treeview(f, columns=cols, show="headings", height=14)
        widths = [80, 80, 140, 150, 140, 140, 220]
        for c, w in zip(cols, widths):
            tv.heading(c, text=c)
            tv.column(c, width=w, anchor="center")

        sb = ttk.Scrollbar(f, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=6)
        sb.pack(side="left", fill="y", pady=6)
        self.tv_ls = tv

        self._load_loc_sv_combobox()
        self._load_lich_su()

    def _load_loc_sv_combobox(self):
        rows = lay_sinh_vat_de_chon(self.conn)
        self._loc_sv_map = {f"{ma} - {ten}": ma for ma, ten, _ in rows}
        self.cb_loc_sv["values"] = list(self._loc_sv_map.keys())

    def _xem_tat_ca_lich_su(self):
        self.var_loc_sv.set("")
        self._load_lich_su()

    def _load_lich_su(self):
        ma_sv = self._loc_sv_map.get(self.var_loc_sv.get()) if self.var_loc_sv.get() else None
        self.tv_ls.delete(*self.tv_ls.get_children())
        rows = lay_lich_su_cham_soc(self.conn, ma_sv)
        for r in rows:
            ma_cs, ma_sv_, ten_sv, ma_nv, ten_nv, thoi_diem, loai, ghi_chu = r
            tag = {
                "Điều trị": "dieu_tri",
                "Hoàn tất điều trị": "hoan_tat",
            }.get(loai, "")
            self.tv_ls.insert("", "end",
                              values=(ma_cs, ma_sv_, ten_sv, ten_nv,
                                      str(thoi_diem)[:16], loai, ghi_chu or ""),
                              tags=(tag,))
        self.tv_ls.tag_configure("dieu_tri", background="#fff3cc")
        self.tv_ls.tag_configure("hoan_tat", background="#ccffcc")