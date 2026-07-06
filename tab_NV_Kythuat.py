"""
Tab NHÂN VIÊN BẢO TRÌ
Chức năng:
  1. Danh mục thiết bị (thêm / sửa / xóa thiết bị)
  2. Danh mục bể (thêm / sửa / xóa bể, đổi trạng thái bể)
  3. Danh sách thiết bị (theo dõi tình trạng theo bể)
  4. Lập phiếu bảo trì
  5. Lịch sử bảo trì
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date


# ── Font/kích thước dùng chung (đồng bộ với các tab khác) ──
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


# ── Hàm tiện ích đọc DB ─────────────────────────────────────
def lay_be_de_chon(conn):
    """Danh sách bể (mã, tên) để đổ vào combobox chọn bể."""
    cur = conn.cursor()
    cur.execute("SELECT maBe, tenBe FROM BE ORDER BY tenBe")
    return cur.fetchall()


def lay_danh_sach_be(conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM danhmucBe ORDER BY maBe")
    return cur.fetchall()


def lay_danh_muc_thiet_bi(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT maThietBi, tenThietBi, loaiThietBi, nhaSanXuat,
               ngayMua, hanBaoHanh, trangThai, maBe, tenBe
        FROM danhmucThietBi
        ORDER BY maThietBi
    """)
    return cur.fetchall()


def lay_danh_sach_thiet_bi(conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM DanhSachThietBi ORDER BY maBe, maThietBi")
    return cur.fetchall()


def lay_thiet_bi_de_chon(conn):
    """Danh sách thiết bị (mã, tên, trạng thái) để đổ vào combobox."""
    cur = conn.cursor()
    cur.execute("SELECT maThietBi, tenThietBi, trangThai FROM THIET_BI ORDER BY tenThietBi")
    return cur.fetchall()


def lay_lich_su_bao_tri(conn, ma_thiet_bi=None):
    cur = conn.cursor()
    if ma_thiet_bi:
        cur.execute("""
            SELECT maBaoTri, maThietBi, tenThietBi, maNhanVien, hoTenNhanVien,
                   ngayBaoTri, loaiBaoTri, chiPhi, ketQua, ghiChu
            FROM LichSuBaoTri
            WHERE maThietBi = ?
            ORDER BY ngayBaoTri DESC
        """, ma_thiet_bi)
    else:
        cur.execute("""
            SELECT maBaoTri, maThietBi, tenThietBi, maNhanVien, hoTenNhanVien,
                   ngayBaoTri, loaiBaoTri, chiPhi, ketQua, ghiChu
            FROM LichSuBaoTri
            ORDER BY ngayBaoTri DESC
        """)
    return cur.fetchall()


# ─────────────────────────────────────────────────────────
#  Lớp chính
# ─────────────────────────────────────────────────────────
class TabKyThuat:
    """
    Nhận vào:
      parent   widget cha (ttk.Notebook hoặc Frame)
      conn     kết nối pyodbc
      ma_nv    mã nhân viên đang đăng nhập (vai trò: Nhân viên bảo trì)
    """

    LOAI_BAO_TRI  = ["Định kỳ", "Đột xuất"]
    KET_QUA       = ["Hoàn thành", "Đang sửa chữa"]
    TRANG_THAI_BE = ["Hoạt động", "Bảo trì", "Ngừng hoạt động"]

    def __init__(self, parent, conn, ma_nv="NV001"):
        self.conn = conn
        self.ma_nv = ma_nv

        self._be_map = {}            # "MA - Ten" -> maBe
        self._thiet_bi_be_map = {}   # maThietBi -> maBe (tra ngược khi chọn sửa)
        self._thiet_bi_map = {}      # "MA - Ten (TrangThai)" -> (maThietBi, tenThietBi, trangThai)
        self._loc_tb_map = {}        # "MA - Ten" -> maThietBi (dùng ở tab Lịch sử)

        self._dang_sua_thiet_bi = None   # maThietBi đang chọn để sửa (None = đang thêm mới)
        self._dang_sua_be = None         # maBe đang chọn để sửa (None = đang thêm mới)

        self.frame = ttk.Frame(parent)
        self._apply_scale()

        self.nb = ttk.Notebook(self.frame)
        self.nb.pack(fill="both", expand=True, padx=12, pady=12)

        self._build_danh_muc_thiet_bi()
        self._build_danh_muc_be()
        self._build_danh_sach_thiet_bi()
        self._build_lap_phieu_bao_tri()
        self._build_lich_su_bao_tri()

    def _apply_scale(self):
        self.frame.option_add("*Font", FONT_NORMAL)
        style = ttk.Style()
        style.configure("TButton",       font=FONT_NORMAL, padding=6)
        style.configure("TLabel",        font=FONT_NORMAL)
        style.configure("TCombobox",     font=FONT_NORMAL)
        style.configure("TNotebook.Tab", font=FONT_NORMAL, padding=(14, 8))
        style.configure("Treeview",         font=FONT_NORMAL, rowheight=ROW_HEIGHT)
        style.configure("Treeview.Heading", font=FONT_BOLD)
        self.frame.option_add("*TCombobox*Listbox.font", FONT_NORMAL)

    def _tim_key_be(self, ma_be):
        """Tra ngược 'MA - Ten' trong _be_map theo maBe, dùng khi nạp form sửa."""
        for key, mb in self._be_map.items():
            if mb == ma_be:
                return key
        return None

    # ══════════════════════════════════════════════════════
    # 1. Danh mục thiết bị (thêm / sửa)
    # ══════════════════════════════════════════════════════
    def _build_danh_muc_thiet_bi(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  🔧 Danh mục thiết bị  ")

        tk.Label(f, text="Quản lý danh mục thiết bị",
                 font=("Arial", 15, "bold")).grid(row=0, column=0,
                                                  columnspan=4, pady=(12, 8))

        self.var_ten_tb   = tk.StringVar()
        self.var_be_tb    = tk.StringVar()
        self.var_loai_tb  = tk.StringVar()
        self.var_nsx_tb   = tk.StringVar()
        self.var_ngay_mua = tk.StringVar()
        self.var_han_bh   = tk.StringVar()

        _lbl(f, "Tên thiết bị:", 1, 0)
        _entry(f, self.var_ten_tb, 1, 1)

        _lbl(f, "Bể lắp đặt:", 1, 2)
        self.cb_be_tb = ttk.Combobox(f, textvariable=self.var_be_tb,
                                     width=26, state="readonly")
        self.cb_be_tb.grid(row=1, column=3, sticky="w", padx=8, pady=6)

        _lbl(f, "Loại thiết bị:", 2, 0)
        _entry(f, self.var_loai_tb, 2, 1)

        _lbl(f, "Nhà sản xuất:", 2, 2)
        _entry(f, self.var_nsx_tb, 2, 3)

        _lbl(f, "Ngày mua (YYYY-MM-DD):", 3, 0)
        _entry(f, self.var_ngay_mua, 3, 1)

        _lbl(f, "Hạn bảo hành (YYYY-MM-DD):", 3, 2)
        _entry(f, self.var_han_bh, 3, 3)

        btn_form = ttk.Frame(f)
        btn_form.grid(row=4, column=0, columnspan=4, pady=10)
        ttk.Button(btn_form, text="➕ Thêm mới",
                   command=self._them_thiet_bi).pack(side="left", padx=4)
        ttk.Button(btn_form, text="💾 Cập nhật đã chọn",
                   command=self._sua_thiet_bi).pack(side="left", padx=4)
        ttk.Button(btn_form, text="🆕 Nhập mới form",
                   command=self._clear_form_thiet_bi).pack(side="left", padx=4)

        cols = ("Mã TB", "Tên thiết bị", "Bể", "Loại", "Nhà SX",
                "Ngày mua", "Hạn BH", "Trạng thái")
        tv = ttk.Treeview(f, columns=cols, show="headings", height=12)
        widths = [70, 150, 100, 100, 110, 95, 95, 110]
        for c, w in zip(cols, widths):
            tv.heading(c, text=c)
            tv.column(c, width=w, anchor="center")
        tv.grid(row=5, column=0, columnspan=4, sticky="nsew", padx=10, pady=6)
        f.grid_rowconfigure(5, weight=1)
        self.tv_danh_muc_tb = tv
        self.tv_danh_muc_tb.bind("<<TreeviewSelect>>", self._on_chon_thiet_bi_danh_muc)
        self.tv_danh_muc_tb.tag_configure("hong", background="#ffcccc")
        self.tv_danh_muc_tb.tag_configure("baotri", background="#fff3cc")

        btn_f = ttk.Frame(f)
        btn_f.grid(row=6, column=0, columnspan=4, pady=6)
        ttk.Button(btn_f, text="🔄 Làm mới",
                   command=self._load_danh_muc_thiet_bi).pack(side="left", padx=4)

        self._load_be_combobox_dung_chung()
        self._load_danh_muc_thiet_bi()

    def _load_be_combobox_dung_chung(self):
        rows = lay_be_de_chon(self.conn)
        self._be_map = {f"{ma} - {ten}": ma for ma, ten in rows}
        values = list(self._be_map.keys())
        self.cb_be_tb["values"] = values
        if values:
            self.cb_be_tb.current(0)

    def _load_danh_muc_thiet_bi(self):
        self.tv_danh_muc_tb.delete(*self.tv_danh_muc_tb.get_children())
        self._thiet_bi_be_map = {}
        rows = lay_danh_muc_thiet_bi(self.conn)
        for r in rows:
            ma, ten, loai, nsx, ngay_mua, han_bh, trang_thai, ma_be, ten_be = r
            self._thiet_bi_be_map[ma] = ma_be
            tag = ""
            if trang_thai == "Dừng hoạt động":
                tag = "hong"
            elif trang_thai == "Đang bảo trì":
                tag = "baotri"
            self.tv_danh_muc_tb.insert("", "end", values=(
                ma, ten, ten_be or "—", loai or "—", nsx or "—",
                str(ngay_mua) if ngay_mua else "—",
                str(han_bh) if han_bh else "—",
                trang_thai
            ), tags=(tag,))

    def _on_chon_thiet_bi_danh_muc(self, event=None):
        sel = self.tv_danh_muc_tb.selection()
        if not sel:
            return
        vals = self.tv_danh_muc_tb.item(sel[0])["values"]
        ma, ten, _ten_be, loai, nsx, ngay_mua, han_bh, _trang_thai = vals

        self._dang_sua_thiet_bi = ma
        self.var_ten_tb.set(ten)
        self.var_loai_tb.set("" if loai == "—" else loai)
        self.var_nsx_tb.set("" if nsx == "—" else nsx)
        self.var_ngay_mua.set("" if ngay_mua == "—" else ngay_mua)
        self.var_han_bh.set("" if han_bh == "—" else han_bh)

        ma_be = self._thiet_bi_be_map.get(ma)
        key_be = self._tim_key_be(ma_be) if ma_be else None
        if key_be:
            self.var_be_tb.set(key_be)

    def _clear_form_thiet_bi(self):
        self._dang_sua_thiet_bi = None
        self.var_ten_tb.set("")
        self.var_loai_tb.set("")
        self.var_nsx_tb.set("")
        self.var_ngay_mua.set("")
        self.var_han_bh.set("")
        if self.cb_be_tb["values"]:
            self.cb_be_tb.current(0)
        self.tv_danh_muc_tb.selection_remove(self.tv_danh_muc_tb.selection())

    def _doc_form_thiet_bi(self):
        """Đọc + validate dữ liệu form. Trả về dict hoặc None nếu lỗi (đã tự báo lỗi)."""
        ten = self.var_ten_tb.get().strip()
        if not ten:
            messagebox.showerror("Lỗi", "Vui lòng nhập tên thiết bị.")
            return None

        key_be = self.var_be_tb.get()
        if key_be not in self._be_map:
            messagebox.showerror("Lỗi", "Vui lòng chọn bể lắp đặt.")
            return None
        ma_be = self._be_map[key_be]

        def _parse_date(s, ten_truong):
            s = s.strip()
            if not s:
                return None
            return date.fromisoformat(s)  # có thể raise ValueError

        try:
            ngay_mua = _parse_date(self.var_ngay_mua.get(), "Ngày mua")
        except ValueError:
            messagebox.showerror("Lỗi", "Ngày mua không hợp lệ (YYYY-MM-DD).")
            return None

        try:
            han_bh = _parse_date(self.var_han_bh.get(), "Hạn bảo hành")
        except ValueError:
            messagebox.showerror("Lỗi", "Hạn bảo hành không hợp lệ (YYYY-MM-DD).")
            return None

        return {
            "ten": ten,
            "ma_be": ma_be,
            "loai": self.var_loai_tb.get().strip() or None,
            "nsx": self.var_nsx_tb.get().strip() or None,
            "ngay_mua": ngay_mua,
            "han_bh": han_bh,
        }

    def _them_thiet_bi(self):
        du_lieu = self._doc_form_thiet_bi()
        if du_lieu is None:
            return

        try:
            cur = self.conn.cursor()
            cur.execute("""
                EXEC ThemThietBi
                    @tenThietBi  = ?,
                    @maBe        = ?,
                    @loaiThietBi = ?,
                    @nhaSanXuat  = ?,
                    @ngayMua     = ?,
                    @hanBaoHanh  = ?
            """, du_lieu["ten"], du_lieu["ma_be"], du_lieu["loai"],
                 du_lieu["nsx"], du_lieu["ngay_mua"], du_lieu["han_bh"])

            row = cur.fetchone()
            self.conn.commit()

            messagebox.showinfo("Thành công", f"{row[1]}\nMã thiết bị: {row[0]}")

            self._clear_form_thiet_bi()
            self._load_danh_muc_thiet_bi()
            self._load_danh_sach_thiet_bi()
            self._load_thiet_bi_combobox()
            self._load_loc_tb_combobox()

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi thêm thiết bị", str(e))

    def _sua_thiet_bi(self):
        if not self._dang_sua_thiet_bi:
            messagebox.showinfo("Thông báo", "Vui lòng chọn thiết bị cần sửa trong danh sách.")
            return

        du_lieu = self._doc_form_thiet_bi()
        if du_lieu is None:
            return

        try:
            cur = self.conn.cursor()
            cur.execute("""
                EXEC SuaThietBi
                    @maThietBi   = ?,
                    @tenThietBi  = ?,
                    @maBe        = ?,
                    @loaiThietBi = ?,
                    @nhaSanXuat  = ?,
                    @ngayMua     = ?,
                    @hanBaoHanh  = ?
            """, self._dang_sua_thiet_bi, du_lieu["ten"], du_lieu["ma_be"],
                 du_lieu["loai"], du_lieu["nsx"], du_lieu["ngay_mua"], du_lieu["han_bh"])

            row = cur.fetchone()
            self.conn.commit()

            messagebox.showinfo("Thành công", row[1] if row else "Đã cập nhật thiết bị.")

            self._clear_form_thiet_bi()
            self._load_danh_muc_thiet_bi()
            self._load_danh_sach_thiet_bi()
            self._load_thiet_bi_combobox()
            self._load_loc_tb_combobox()

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi cập nhật thiết bị", str(e))


    # ══════════════════════════════════════════════════════
    # 2. Danh mục bể (thêm / sửa / đổi trạng thái)
    # ══════════════════════════════════════════════════════
    def _build_danh_muc_be(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  □ Danh mục bể  ")

        tk.Label(f, text="Quản lý danh mục bể",
                 font=("Arial", 15, "bold")).grid(row=0, column=0,
                                                  columnspan=4, pady=(12, 8))

        self.var_ten_be      = tk.StringVar()
        self.var_vi_tri_be   = tk.StringVar()
        self.var_loai_be     = tk.StringVar()
        self.var_the_tich_be = tk.StringVar()
        self.var_suc_chua_be = tk.StringVar()

        _lbl(f, "Tên bể:", 1, 0)
        _entry(f, self.var_ten_be, 1, 1)

        _lbl(f, "Vị trí:", 1, 2)
        _entry(f, self.var_vi_tri_be, 1, 3)

        _lbl(f, "Loại bể:", 2, 0)
        _entry(f, self.var_loai_be, 2, 1)

        _lbl(f, "Thể tích (m³):", 2, 2)
        _entry(f, self.var_the_tich_be, 2, 3, width=15)

        _lbl(f, "Sức chứa (con):", 3, 0)
        _entry(f, self.var_suc_chua_be, 3, 1, width=15)

        btn_form = ttk.Frame(f)
        btn_form.grid(row=4, column=0, columnspan=4, pady=10)
        ttk.Button(btn_form, text="➕ Thêm mới",
                   command=self._them_be).pack(side="left", padx=4)
        ttk.Button(btn_form, text="💾 Cập nhật đã chọn",
                   command=self._sua_be).pack(side="left", padx=4)
        ttk.Button(btn_form, text="🆕 Nhập mới (xóa form)",
                   command=self._clear_form_be).pack(side="left", padx=4)

        cols = ("Mã bể", "Tên bể", "Vị trí", "Loại bể", "Thể tích",
                "Sức chứa", "Hiện tại", "Trạng thái")
        tv = ttk.Treeview(f, columns=cols, show="headings", height=12)
        widths = [70, 130, 120, 100, 90, 90, 80, 120]
        for c, w in zip(cols, widths):
            tv.heading(c, text=c)
            tv.column(c, width=w, anchor="center")
        tv.grid(row=5, column=0, columnspan=4, sticky="nsew", padx=10, pady=6)
        f.grid_rowconfigure(5, weight=1)
        self.tv_danh_muc_be = tv
        self.tv_danh_muc_be.bind("<<TreeviewSelect>>", self._on_chon_be_danh_muc)
        self.tv_danh_muc_be.tag_configure("ngung", foreground="#999999")
        self.tv_danh_muc_be.tag_configure("baotri", background="#fff3cc")

        btn_f = ttk.Frame(f)
        btn_f.grid(row=6, column=0, columnspan=4, pady=6)
        ttk.Button(btn_f, text="🔄 Làm mới",
                   command=self._load_danh_sach_be).pack(side="left", padx=4)

        self.var_trang_thai_be_moi = tk.StringVar(value=self.TRANG_THAI_BE[0])
        ttk.Combobox(btn_f, textvariable=self.var_trang_thai_be_moi,
                    values=self.TRANG_THAI_BE, width=18,
                    state="readonly").pack(side="left", padx=(16, 4))
        ttk.Button(btn_f, text="🔁 Cập nhật trạng thái",
                   command=self._doi_trang_thai_be).pack(side="left", padx=4)

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

    def _on_chon_be_danh_muc(self, event=None):
        sel = self.tv_danh_muc_be.selection()
        if not sel:
            return
        vals = self.tv_danh_muc_be.item(sel[0])["values"]
        ma, ten, vi_tri, loai, the_tich, suc_chua, _hien_tai, _trang_thai = vals

        self._dang_sua_be = ma
        self.var_ten_be.set(ten)
        self.var_vi_tri_be.set("" if vi_tri == "—" else vi_tri)
        self.var_loai_be.set("" if loai == "—" else loai)
        self.var_the_tich_be.set("" if the_tich == "—" else str(the_tich))
        self.var_suc_chua_be.set("" if suc_chua == "—" else str(suc_chua))

    def _clear_form_be(self):
        self._dang_sua_be = None
        self.var_ten_be.set("")
        self.var_vi_tri_be.set("")
        self.var_loai_be.set("")
        self.var_the_tich_be.set("")
        self.var_suc_chua_be.set("")
        self.tv_danh_muc_be.selection_remove(self.tv_danh_muc_be.selection())

    def _doc_form_be(self):
        ten = self.var_ten_be.get().strip()
        if not ten:
            messagebox.showerror("Lỗi", "Vui lòng nhập tên bể.")
            return None

        the_tich = None
        if self.var_the_tich_be.get().strip():
            try:
                the_tich = float(self.var_the_tich_be.get().strip())
            except ValueError:
                messagebox.showerror("Lỗi", "Thể tích phải là số.")
                return None

        suc_chua = None
        if self.var_suc_chua_be.get().strip():
            try:
                suc_chua = int(self.var_suc_chua_be.get().strip())
                if suc_chua <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Lỗi", "Sức chứa phải là số nguyên dương.")
                return None

        return {
            "ten": ten,
            "vi_tri": self.var_vi_tri_be.get().strip() or None,
            "loai": self.var_loai_be.get().strip() or None,
            "the_tich": the_tich,
            "suc_chua": suc_chua,
        }

    def _them_be(self):
        du_lieu = self._doc_form_be()
        if du_lieu is None:
            return

        try:
            cur = self.conn.cursor()
            cur.execute("""
                EXEC ThemBe
                    @tenBe   = ?,
                    @viTri   = ?,
                    @theTich = ?,
                    @loaiBe  = ?,
                    @sucChua = ?
            """, du_lieu["ten"], du_lieu["vi_tri"], du_lieu["the_tich"],
                 du_lieu["loai"], du_lieu["suc_chua"])

            row = cur.fetchone()
            self.conn.commit()

            messagebox.showinfo("Thành công", f"{row[1]}\nMã bể: {row[0]}")

            self._clear_form_be()
            self._load_danh_sach_be()
            self._load_be_combobox_dung_chung()

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi thêm bể", str(e))

    def _sua_be(self):
        if not self._dang_sua_be:
            messagebox.showinfo("Thông báo", "Vui lòng chọn bể cần sửa trong danh sách.")
            return

        du_lieu = self._doc_form_be()
        if du_lieu is None:
            return

        try:
            cur = self.conn.cursor()
            cur.execute("""
                EXEC SuaBe
                    @maBe    = ?,
                    @tenBe   = ?,
                    @viTri   = ?,
                    @theTich = ?,
                    @loaiBe  = ?,
                    @sucChua = ?
            """, self._dang_sua_be, du_lieu["ten"], du_lieu["vi_tri"],
                 du_lieu["the_tich"], du_lieu["loai"], du_lieu["suc_chua"])

            row = cur.fetchone()
            self.conn.commit()

            messagebox.showinfo("Thành công", row[1] if row else "Đã cập nhật bể.")

            self._clear_form_be()
            self._load_danh_sach_be()
            self._load_be_combobox_dung_chung()
            self._load_danh_muc_thiet_bi()
            self._load_danh_sach_thiet_bi()

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi cập nhật bể", str(e))

    def _doi_trang_thai_be(self):
        sel = self.tv_danh_muc_be.selection()
        if not sel:
            messagebox.showinfo("Thông báo", "Vui lòng chọn bể cần đổi trạng thái.")
            return
        vals = self.tv_danh_muc_be.item(sel[0])["values"]
        ma_be, ten_be = vals[0], vals[1]
        trang_thai_moi = self.var_trang_thai_be_moi.get()

        if not messagebox.askyesno(
            "Xác nhận",
            f"Đổi trạng thái bể {ten_be} ({ma_be}) sang \"{trang_thai_moi}\"?"
        ):
            return

        try:
            cur = self.conn.cursor()
            cur.execute("""
                EXEC CapNhatTrangThaiBe @maBe = ?, @trangThaiMoi = ?
            """, ma_be, trang_thai_moi)
            row = cur.fetchone()
            self.conn.commit()

            messagebox.showinfo("Thành công", row[1] if row else "Đã cập nhật trạng thái.")

            self._load_danh_sach_be()

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi cập nhật trạng thái bể", str(e))

    # ══════════════════════════════════════════════════════
    # 3. Danh sách thiết bị (theo dõi theo bể)
    # ══════════════════════════════════════════════════════
    def _build_danh_sach_thiet_bi(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  📡 Danh sách thiết bị  ")

        tk.Label(f, text="Theo dõi tình trạng thiết bị theo bể",
                 font=("Arial", 15, "bold")).pack(pady=(10, 4))

        cols = ("Mã bể", "Loại bể", "Tên bể", "Vị trí bể",
                "Mã thiết bị", "Tên thiết bị", "Trạng thái")
        tv = ttk.Treeview(f, columns=cols, show="headings", height=14)
        for c in cols:
            tv.heading(c, text=c)
            tv.column(c, width=130, anchor="center")

        sb = ttk.Scrollbar(f, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=6)
        sb.pack(side="left", fill="y", pady=6)
        self.tv_ds_tb = tv
        self.tv_ds_tb.tag_configure("hong", background="#ffcccc")
        self.tv_ds_tb.tag_configure("baotri", background="#fff3cc")

        ttk.Button(f, text="🔄 Làm mới",
                   command=self._load_danh_sach_thiet_bi).pack(pady=6)
        self._load_danh_sach_thiet_bi()

    def _load_danh_sach_thiet_bi(self):
        self.tv_ds_tb.delete(*self.tv_ds_tb.get_children())
        rows = lay_danh_sach_thiet_bi(self.conn)
        for r in rows:
            ma_be, loai_be, ten_be, vi_tri, ma_tb, ten_tb, trang_thai = r
            tag = ""
            if trang_thai == "Dừng hoạt động":
                tag = "hong"
            elif trang_thai == "Đang bảo trì":
                tag = "baotri"
            self.tv_ds_tb.insert("", "end",
                                 values=(ma_be, loai_be, ten_be, vi_tri, ma_tb, ten_tb, trang_thai),
                                 tags=(tag,))

    # ══════════════════════════════════════════════════════
    # 4. Lập phiếu bảo trì
    # ══════════════════════════════════════════════════════
    def _build_lap_phieu_bao_tri(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  🧰 Lập phiếu bảo trì  ")

        tk.Label(f, text="Lập phiếu bảo trì thiết bị",
                 font=("Arial", 15, "bold")).grid(row=0, column=0,
                                                  columnspan=2, pady=(12, 8))

        self.var_tb_bt   = tk.StringVar()
        self.var_loai_bt = tk.StringVar(value=self.LOAI_BAO_TRI[0])
        self.var_ngay_bt = tk.StringVar(value=str(date.today()))
        self.var_chi_phi = tk.StringVar()
        self.var_ket_qua = tk.StringVar(value=self.KET_QUA[0])

        _lbl(f, "Thiết bị:", 1, 0)
        self.cb_thiet_bi_bt = ttk.Combobox(f, textvariable=self.var_tb_bt,
                                           width=40, state="readonly")
        self.cb_thiet_bi_bt.grid(row=1, column=1, sticky="w", padx=8, pady=6)
        self.cb_thiet_bi_bt.bind("<<ComboboxSelected>>", self._on_chon_thiet_bi_bt)

        self.lbl_trang_thai_tb = tk.Label(f, text="Trạng thái hiện tại: —",
                                          font=("Arial", 12, "bold"), fg="#aa5500")
        self.lbl_trang_thai_tb.grid(row=2, column=0, columnspan=2, pady=(0, 8))

        _lbl(f, "Loại bảo trì:", 3, 0)
        ttk.Combobox(f, textvariable=self.var_loai_bt, values=self.LOAI_BAO_TRI,
                    width=26, state="readonly").grid(row=3, column=1, sticky="w", padx=8, pady=6)

        _lbl(f, "Ngày bảo trì (YYYY-MM-DD):", 4, 0)
        _entry(f, self.var_ngay_bt, 4, 1)

        _lbl(f, "Mô tả sự cố / công việc:", 5, 0, sticky="ne")
        self.txt_mo_ta = tk.Text(f, width=40, height=3, font=FONT_NORMAL)
        self.txt_mo_ta.grid(row=5, column=1, sticky="w", padx=8, pady=6)

        _lbl(f, "Chi phí (VNĐ):", 6, 0)
        _entry(f, self.var_chi_phi, 6, 1, width=20)

        _lbl(f, "Kết quả xử lý:", 7, 0)
        ttk.Combobox(f, textvariable=self.var_ket_qua, values=self.KET_QUA,
                    width=26, state="readonly").grid(row=7, column=1, sticky="w", padx=8, pady=6)

        _lbl(f, "Ghi chú:", 8, 0, sticky="ne")
        self.txt_ghi_chu_bt = tk.Text(f, width=40, height=3, font=FONT_NORMAL)
        self.txt_ghi_chu_bt.grid(row=8, column=1, sticky="w", padx=8, pady=6)

        ttk.Button(f, text="✅ Lập phiếu",
                   command=self._lap_phieu_bao_tri).grid(row=9, column=0,
                                                         columnspan=2, pady=12)

        self._load_thiet_bi_combobox()

    def _load_thiet_bi_combobox(self):
        rows = lay_thiet_bi_de_chon(self.conn)
        self._thiet_bi_map = {
            f"{ma} - {ten} ({trang_thai})": (ma, ten, trang_thai)
            for ma, ten, trang_thai in rows
        }
        self.cb_thiet_bi_bt["values"] = list(self._thiet_bi_map.keys())
        if self._thiet_bi_map:
            self.cb_thiet_bi_bt.current(0)
            self._on_chon_thiet_bi_bt()
        else:
            self.var_tb_bt.set("")
            self.lbl_trang_thai_tb.config(text="Trạng thái hiện tại: —", fg="#aa5500")

    def _on_chon_thiet_bi_bt(self, event=None):
        key = self.var_tb_bt.get()
        if key not in self._thiet_bi_map:
            return
        _, _, trang_thai = self._thiet_bi_map[key]
        mau = "#cc0000" if trang_thai != "Hoạt động" else "#007700"
        self.lbl_trang_thai_tb.config(text=f"Trạng thái hiện tại: {trang_thai}", fg=mau)

    def _lap_phieu_bao_tri(self):
        key = self.var_tb_bt.get()
        if key not in self._thiet_bi_map:
            messagebox.showerror("Lỗi", "Vui lòng chọn thiết bị.")
            return
        ma_tb, ten_tb, _tt = self._thiet_bi_map[key]

        ngay_str = self.var_ngay_bt.get().strip()
        try:
            ngay_bt = date.fromisoformat(ngay_str) if ngay_str else None
        except ValueError:
            messagebox.showerror("Lỗi", "Ngày bảo trì không hợp lệ (YYYY-MM-DD).")
            return

        try:
            chi_phi = float(self.var_chi_phi.get().strip())

        except ValueError:
            messagebox.showerror("Lỗi", "Chi phí phải là số không âm.")
            return

        loai_bt = self.var_loai_bt.get()
        ket_qua = self.var_ket_qua.get()
        mo_ta = self.txt_mo_ta.get("1.0", "end").strip() or None
        ghi_chu = self.txt_ghi_chu_bt.get("1.0", "end").strip() or None

        if not messagebox.askyesno(
            "Xác nhận",
            f"Thiết bị: {ten_tb}\nLoại bảo trì: {loai_bt}\n"
            f"Chi phí: {chi_phi:,.0f} VNĐ\nKết quả: {ket_qua}\n\nXác nhận lập phiếu?"
        ):
            return

        try:
            cur = self.conn.cursor()
            cur.execute("""
                EXEC LapPhieuBaoTri
                    @maThietBi  = ?,
                    @maNhanVien = ?,
                    @loaiBaoTri = ?,
                    @chiPhi     = ?,
                    @ketQua     = ?,
                    @ngayBaoTri = ?,
                    @moTa       = ?,
                    @ghiChu     = ?
            """, ma_tb, self.ma_nv, loai_bt, chi_phi, ket_qua, ngay_bt, mo_ta, ghi_chu)

            row = cur.fetchone()
            self.conn.commit()

            messagebox.showinfo("Thành công", f"{row[1]}\nMã phiếu: {row[0]}")

            self.var_chi_phi.set("")
            self.txt_mo_ta.delete("1.0", "end")
            self.txt_ghi_chu_bt.delete("1.0", "end")

            self._load_thiet_bi_combobox()
            self._load_danh_muc_thiet_bi()
            self._load_danh_sach_thiet_bi()
            self._load_loc_tb_combobox()
            self._load_lich_su_bao_tri()

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Lỗi lập phiếu bảo trì", str(e))

    # ══════════════════════════════════════════════════════
    # 5. Lịch sử bảo trì
    # ══════════════════════════════════════════════════════
    def _build_lich_su_bao_tri(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  📜 Lịch sử bảo trì  ")

        top = ttk.Frame(f)
        top.pack(fill="x", padx=10, pady=(10, 4))

        tk.Label(top, text="Xem theo thiết bị:", font=FONT_NORMAL).pack(side="left", padx=(0, 6))
        self.var_loc_tb = tk.StringVar()
        self.cb_loc_tb = ttk.Combobox(top, textvariable=self.var_loc_tb,
                                      width=40, state="readonly")
        self.cb_loc_tb.pack(side="left", padx=6)

        ttk.Button(top, text="🔍 Lọc",
                   command=self._load_lich_su_bao_tri).pack(side="left", padx=6)
        ttk.Button(top, text="Xem tất cả",
                   command=self._xem_tat_ca_lich_su_bt).pack(side="left", padx=6)

        cols = ("Mã phiếu", "Mã TB", "Tên thiết bị", "Nhân viên",
                "Ngày bảo trì", "Loại", "Chi phí", "Kết quả", "Ghi chú")
        tv = ttk.Treeview(f, columns=cols, show="headings", height=14)
        widths = [80, 70, 140, 140, 100, 90, 100, 110, 200]
        for c, w in zip(cols, widths):
            tv.heading(c, text=c)
            tv.column(c, width=w, anchor="center")

        sb = ttk.Scrollbar(f, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=6)
        sb.pack(side="left", fill="y", pady=6)
        self.tv_ls_bt = tv
        self.tv_ls_bt.tag_configure("chua_xong", background="#fff3cc")

        self._load_loc_tb_combobox()
        self._load_lich_su_bao_tri()

    def _load_loc_tb_combobox(self):
        rows = lay_thiet_bi_de_chon(self.conn)
        self._loc_tb_map = {f"{ma} - {ten}": ma for ma, ten, _tt in rows}
        self.cb_loc_tb["values"] = list(self._loc_tb_map.keys())

    def _xem_tat_ca_lich_su_bt(self):
        self.var_loc_tb.set("")
        self._load_lich_su_bao_tri()

    def _load_lich_su_bao_tri(self):
        ma_tb = self._loc_tb_map.get(self.var_loc_tb.get()) if self.var_loc_tb.get() else None
        self.tv_ls_bt.delete(*self.tv_ls_bt.get_children())
        rows = lay_lich_su_bao_tri(self.conn, ma_tb)
        for r in rows:
            ma_bt, ma_tb_, ten_tb, ma_nv, ten_nv, ngay_bt, loai_bt, chi_phi, ket_qua, ghi_chu = r
            tag = "chua_xong" if ket_qua == "Chưa hoàn thành" else ""
            self.tv_ls_bt.insert("", "end", values=(
                ma_bt, ma_tb_, ten_tb, ten_nv or ma_nv,
                str(ngay_bt), loai_bt,
                f"{chi_phi:,.0f}" if chi_phi is not None else "—",
                ket_qua, ghi_chu or ""
            ), tags=(tag,))