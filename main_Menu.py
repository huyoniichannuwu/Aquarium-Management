"""
QLThuyCung – Ứng dụng quản lý thủy cung
=========================================
Chạy file này để khởi động ứng dụng.

Cấu trúc:
  main.py            ← file này (khởi động + đăng nhập)
  database.py        ← kết nối DB
  tab_khach_hang.py  ← Tab Khách hàng
  tab_quan_ly.py     ← Tab Nhân viên quản lý
  dang_ky.py         ← Cửa sổ Đăng ký tài khoản (Khách hàng)

Cài đặt trước:
  pip install pyodbc
"""

import tkinter as tk
from tkinter import ttk, messagebox
import hashlib

from database import connect_db
from tab_khach_hang import TabKhachHang
from tab_NV_Quanly import TabQuanLy
from tab_NV_Kiembanve import TabNhanVienKiemBanVe
from tab_NV_Chamsoc import TabChamSocSinhVat
from tab_NV_Kythuat import TabKyThuat
from main_Dangky import RegisterWindow


# ─────────────────────────────────────────────────────────
#  Helper hash (phải trùng với tab_quan_ly.py)
# ─────────────────────────────────────────────────────────
def hash_pass(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

# ─────────────────────────────────────────────────────────
#  Dọn dẹp đơn/vé hết hạn (chạy nền định kỳ)
# ─────────────────────────────────────────────────────────
def don_dep_ve_het_han(conn, root, interval_ms=60000):
    """Gọi procedure HuyDonQuaHanThanhToan mỗi interval_ms (mặc định 60s)."""
    try:
        cur = conn.cursor()
        cur.execute("EXEC HuyDonQuaHanThanhToan")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("Lỗi dọn đơn hết hạn:", e)
    finally:
        # Tự lên lịch gọi lại lần tiếp theo (chỉ gọi nếu root còn tồn tại)
        if root.winfo_exists():
            root.after(interval_ms, don_dep_ve_het_han, conn, root, interval_ms)


# ─────────────────────────────────────────────────────────
#  Cửa sổ đăng nhập
# ─────────────────────────────────────────────────────────
class LoginWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Đăng nhập Quản lý Thủy Cung")
        self.root.geometry("400x320")
        self.root.resizable(False, False)

        # Căn giữa màn hình
        self.root.eval("tk::PlaceWindow . center")

        self.conn = connect_db()
        if self.conn is None:
            self.root.after(100, self.root.destroy)
            return

        self._build()
        self.root.mainloop()

    def _build(self):
        frm = tk.Frame(self.root, padx=30, pady=30)
        frm.pack(expand=True)

        tk.Label(frm, text="Ứng dụng Quản lý Thủy Cung",
                 font=("Arial", 14, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 20))

        tk.Label(frm, text="Tên đăng nhập:").grid(
            row=1, column=0, sticky="e", pady=6)
        self.v_user = tk.StringVar()
        e_user = tk.Entry(frm, textvariable=self.v_user, width=24)
        e_user.grid(row=1, column=1, sticky="w", pady=6)

        tk.Label(frm, text="Mật khẩu:").grid(
            row=2, column=0, sticky="e", pady=6)
        self.v_pass = tk.StringVar()
        e_pw = tk.Entry(frm, textvariable=self.v_pass, show="*", width=24)
        e_pw.grid(row=2, column=1, sticky="w", pady=6)
        # Enter để đăng nhập
        e_pw.bind("<Return>", lambda _: self._login())

        ttk.Button(frm, text="Đăng nhập",
                   command=self._login).grid(
            row=3, column=0, columnspan=2, pady=(16, 6), ipadx=20)

        # Nút đăng ký (chỉ tạo tài khoản Khách Hàng)
        ttk.Button(frm, text="Đăng ký tài khoản mới",
                   command=self._mo_dang_ky).grid(
            row=4, column=0, columnspan=2, pady=(0, 6))

        # Ghi chú demo
        tk.Label(frm,
                 text="Demo: dùng tài khoản có trong bảng TAI_KHOAN",
                 fg="gray", font=("Arial", 8)).grid(
            row=5, column=0, columnspan=2)

    def _mo_dang_ky(self):
        """Mở cửa sổ đăng ký tài khoản Khách hàng (modal)."""
        RegisterWindow(self.root, self.conn, on_success=self._dien_lai_dang_nhap)

    def _dien_lai_dang_nhap(self, ten_dang_nhap: str):
        """Callback sau khi đăng ký thành công: điền sẵn tên đăng nhập."""
        self.v_user.set(ten_dang_nhap)
        self.v_pass.set("")

    def _login(self):
        ten_dn = self.v_user.get().strip()
        mat_khau = self.v_pass.get()

        if not ten_dn or not mat_khau:
            messagebox.showwarning("Thiếu thông tin",
                                   "Vui lòng nhập tên đăng nhập và mật khẩu.")
            return

        cur = self.conn.cursor()
        cur.execute("""
            SELECT maTaiKhoan, loaiTaiKhoan, trangThai,
                   maKhachHang, maNhanVien, matKhau
            FROM TAI_KHOAN
            WHERE tenDangNhap = ?
        """, ten_dn)
        row = cur.fetchone()

        if row is None:
            messagebox.showerror("Lỗi", "Tên đăng nhập không tồn tại.")
            return

        ma_tk, loai, tt, ma_kh, ma_nv, hash_db = row

        if tt == "Bị khóa":
            messagebox.showerror("Tài khoản bị khóa",
                                 "Tài khoản của bạn đã bị khóa. Liên hệ quản trị viên.")
            return

        # So sánh mật khẩu (hỗ trợ cả plain-text lẫn hashed cho demo)
        input_hash = hash_pass(mat_khau)
        if hash_db != input_hash and hash_db != mat_khau:
            messagebox.showerror("Lỗi", "Mật khẩu không đúng.")
            return

        # Lấy chức vụ nếu là nhân viên
        chuc_vu = None
        if loai == "Nhân viên" and ma_nv:
            cur.execute("SELECT chucVu FROM NHAN_VIEN WHERE maNhanVien = ?", ma_nv)
            r2 = cur.fetchone()
            if r2:
                chuc_vu = r2[0]

        # Đóng login, mở app chính
        self.root.destroy()
        app = MainApp(self.conn, loai, ma_kh, ma_nv, chuc_vu, ten_dn)
        app.run()


# ─────────────────────────────────────────────────────────
#  Ứng dụng chính sau đăng nhập
# ─────────────────────────────────────────────────────────
class MainApp:
    TAB_LABELS = {
        "Nhân viên quản lý":            "  🗂 Quản lý  ",
        "Nhân viên kiểm bán vé":        "  🎫 Kiểm bán vé  ",
        "Nhân viên kỹ thuật":           "  🔧 Kỹ thuật  ",
        "Nhân viên chăm sóc sinh vật":  "  🐟 Chăm sóc SV  ",
        "Khách Hàng":                   "  🧑 Khách hàng  ",
    }

    def __init__(self, conn, loai_tk, ma_kh, ma_nv, chuc_vu, ten_dn):
        self.conn = conn
        self.loai_tk = loai_tk
        self.ma_kh = ma_kh
        self.ma_nv = ma_nv
        self.chuc_vu = chuc_vu
        self.ten_dn = ten_dn

        self.root = tk.Tk()
        self.root.title("🐠 Quản lý Thủy Cung")
        self.root.geometry("1100x680")
        self.root.eval("tk::PlaceWindow . center")

        self._build_header()
        self._build_tabs()

        don_dep_ve_het_han(self.conn, self.root, interval_ms=60000)

    def _build_header(self):
        role_str = self.chuc_vu or self.loai_tk
        bar = tk.Frame(self.root, bg="#0077b6", pady=6)
        bar.pack(fill="x")
        tk.Label(bar, text="🐠 Thủy Cung Quản Lý",
                 bg="#0077b6", fg="white",
                 font=("Arial", 13, "bold")).pack(side="left", padx=16)
        tk.Label(bar, text=f"  |  Xin chào: {self.ten_dn}  ({role_str})",
                 bg="#0077b6", fg="#cce7ff",
                 font=("Arial", 10)).pack(side="left")
        ttk.Button(bar, text="Đăng xuất",
                   command=self._dang_xuat).pack(side="right", padx=12)

    def _build_tabs(self):
        self._cap_nhat_ve_het_han()

        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=4, pady=4)

        if self.loai_tk == "Khách Hàng":
            # ── Tab khách hàng ────────────────────
            tab_kh = TabKhachHang(self.nb, self.conn, self.ma_kh)
            self.nb.add(tab_kh.frame, text="  🧑 Khách hàng  ")

        else:
            # ── Nhân viên quản lý ─────────────────
            if self.chuc_vu == "Nhân viên quản lý":
                tab_ql = TabQuanLy(self.nb, self.conn, self.ma_nv)
                self.nb.add(tab_ql.frame, text="  🗂 Quản lý  ")

            # ── Nhân viên kiểm bán vé ─────────────
            elif self.chuc_vu == "Nhân viên kiểm bán vé":
                tab_ql = TabNhanVienKiemBanVe(self.nb, self.conn, self.ma_nv)
                self.nb.add(tab_ql.frame, text="  Nhân viên kiểm bán vé  ")

            # ── Nhân viên kỹ thuật ────────────────
            elif self.chuc_vu == "Nhân viên kỹ thuật":
                tab_ql = TabKyThuat(self.nb, self.conn, self.ma_nv)
                self.nb.add(tab_ql.frame, text="  Nhân viên kỹ thuật  ")

            # ── Nhân viên chăm sóc sinh vật ───────
            elif self.chuc_vu == "Nhân viên chăm sóc sinh vật":
                tab_ql = TabChamSocSinhVat(self.nb, self.conn, self.ma_nv)
                self.nb.add(tab_ql.frame, text="  Nhân viên chăm sóc sinh vật  ")

    def _add_placeholder(self, label: str, msg: str):
        f = ttk.Frame(self.nb)
        tk.Label(f, text=msg,
                 font=("Arial", 12), justify="left",
                 fg="#555").pack(expand=True)
        self.nb.add(f, text=label)

    def _dang_xuat(self):
        if messagebox.askyesno("Đăng xuất", "Bạn có muốn đăng xuất không?"):
            self.root.destroy()
            # Mở lại màn hình đăng nhập
            LoginWindow()

    def run(self):
        self.root.mainloop()

    def _cap_nhat_ve_het_han(self):
        try:
            cur = self.conn.cursor()
            cur.execute("EXEC CapNhatVeHetHan")
            self.conn.commit()
        except Exception as e:
            print(f"[Warning] Không thể cập nhật vé hết hạn: {e}")


# ─────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    LoginWindow()