"""
dang_ky.py – Cửa sổ Đăng ký tài khoản (chỉ dành cho Khách hàng)
================================================================
Gọi stored procedure DangKy (xem file DangKy.sql) để thực hiện
transaction: INSERT KHACH_HANG + INSERT TAI_KHOAN.

Trùng CCCD / SĐT / Email / Tên đăng nhập sẽ bị chặn ở tầng CSDL
(trigger + ràng buộc UNIQUE) và trả lỗi về đây để hiển thị cho người dùng.
"""

import re
import hashlib
import tkinter as tk
from tkinter import ttk, messagebox


# Phải trùng với hàm hash_pass trong main.py / tab_quan_ly.py
def hash_pass(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


class RegisterWindow:
    """Cửa sổ đăng ký tài khoản Khách hàng (Toplevel, modal)."""

    def __init__(self, parent, conn, on_success=None):
        """
        parent      : cửa sổ cha (root của LoginWindow)
        conn        : kết nối pyodbc đang mở
        on_success  : callback(ten_dang_nhap: str) được gọi sau khi
                      đăng ký thành công (dùng để điền lại ô đăng nhập)
        """
        self.conn = conn
        self.on_success = on_success

        self.win = tk.Toplevel(parent)
        self.win.title("Đăng ký tài khoản Khách hàng")
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()          # modal: khoá cửa sổ cha

        self._build()
        self._center(440, 560)

    def _center(self, w: int, h: int):
        """Căn giữa cửa sổ Toplevel trên màn hình.
        (Toplevel không có sẵn .eval() như Tk() nên phải tự tính toạ độ.)"""
        self.win.update_idletasks()
        ws = self.win.winfo_screenwidth()
        hs = self.win.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.win.geometry(f"{w}x{h}+{x}+{y}")

    # ------------------------------------------------------------------
    def _build(self):
        frm = tk.Frame(self.win, padx=24, pady=20)
        frm.pack(expand=True, fill="both")

        tk.Label(frm, text="Đăng ký tài khoản Khách hàng",
                 font=("Arial", 13, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 16))

        self.v_hoten    = tk.StringVar()
        self.v_cccd     = tk.StringVar()
        self.v_sdt      = tk.StringVar()
        self.v_email    = tk.StringVar()
        self.v_diachi   = tk.StringVar()
        self.v_gioitinh = tk.StringVar(value="Nam")
        self.v_user     = tk.StringVar()
        self.v_pass     = tk.StringVar()
        self.v_pass2    = tk.StringVar()

        r = 1
        r = self._row(frm, r, "Họ tên:", self.v_hoten)
        r = self._row(frm, r, "Số CCCD (12 số):", self.v_cccd)
        r = self._row(frm, r, "Số điện thoại (10 số):", self.v_sdt)
        r = self._row(frm, r, "Email:", self.v_email)
        r = self._row(frm, r, "Địa chỉ:", self.v_diachi)

        tk.Label(frm, text="Giới tính:").grid(row=r, column=0, sticky="e", pady=4)
        ttk.Combobox(frm, textvariable=self.v_gioitinh, width=23, state="readonly",
                     values=["Nam", "Nữ", "Khác"]).grid(row=r, column=1, pady=4, sticky="w")
        r += 1

        ttk.Separator(frm, orient="horizontal").grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=12)
        r += 1

        r = self._row(frm, r, "Tên đăng nhập:", self.v_user)
        r = self._row(frm, r, "Mật khẩu:", self.v_pass, show="*")
        r = self._row(frm, r, "Xác nhận mật khẩu:", self.v_pass2, show="*")

        ttk.Button(frm, text="Đăng ký", command=self._submit).grid(
            row=r, column=0, columnspan=2, pady=(18, 4), ipadx=24)
        r += 1

        ttk.Button(frm, text="Huỷ", command=self.win.destroy).grid(
            row=r, column=0, columnspan=2)

    @staticmethod
    def _row(frm, r, label, var, show=None):
        tk.Label(frm, text=label).grid(row=r, column=0, sticky="e", pady=4)
        kwargs = {"show": show} if show else {}
        tk.Entry(frm, textvariable=var, width=26, **kwargs).grid(
            row=r, column=1, pady=4, sticky="w")
        return r + 1

    # ------------------------------------------------------------------
    def _validate(self) -> bool:
        ho_ten   = self.v_hoten.get().strip()
        cccd     = self.v_cccd.get().strip()
        sdt      = self.v_sdt.get().strip()
        email    = self.v_email.get().strip()
        dia_chi  = self.v_diachi.get().strip()
        ten_dn   = self.v_user.get().strip()
        mat_khau = self.v_pass.get()
        mat_khau2 = self.v_pass2.get()

        if not all([ho_ten, cccd, sdt, email, dia_chi, ten_dn, mat_khau, mat_khau2]):
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập đầy đủ các trường.")
            return False

        if not re.fullmatch(r"\d{12}", cccd):
            messagebox.showwarning("Lỗi", "Số CCCD phải gồm đúng 12 chữ số.")
            return False

        if not re.fullmatch(r"\d{10}", sdt):
            messagebox.showwarning("Lỗi", "Số điện thoại phải gồm đúng 10 chữ số.")
            return False

        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            messagebox.showwarning("Lỗi", "Email không hợp lệ.")
            return False

        if len(mat_khau) < 1:
            messagebox.showwarning("Lỗi", "Mật khẩu phải có ít nhất 1 ký tự.")
            return False

        if mat_khau != mat_khau2:
            messagebox.showwarning("Lỗi", "Mật khẩu xác nhận không khớp.")
            return False

        return True

    # ------------------------------------------------------------------
    def _submit(self):
        if not self._validate():
            return

        try:
            cur = self.conn.cursor()
            cur.execute(
                """
                EXEC DangKy
                    @tenDangNhap = ?, @matKhau = ?, @hoTen = ?, @soCCCD = ?,
                    @soDienThoai = ?, @email = ?, @diaChi = ?, @gioiTinh = ?
                """,
                self.v_user.get().strip(),
                hash_pass(self.v_pass.get()),
                self.v_hoten.get().strip(),
                self.v_cccd.get().strip(),
                self.v_sdt.get().strip(),
                self.v_email.get().strip(),
                self.v_diachi.get().strip(),
                self.v_gioitinh.get(),
            )
            self.conn.commit()

            ten_dn = self.v_user.get().strip()
            messagebox.showinfo(
                "Thành công",
                f"Đăng ký tài khoản '{ten_dn}' thành công!\nBạn có thể đăng nhập ngay bây giờ.")

            if self.on_success:
                self.on_success(ten_dn)
            self.win.destroy()

        except Exception as e:
            # DangKy đã tự rollback ở phía SQL khi có lỗi, ở đây rollback
            # thêm cho chắc để giải phóng mọi transaction còn treo trên connection.
            try:
                self.conn.rollback()
            except Exception:
                pass
            messagebox.showerror("Đăng ký thất bại", self._friendly_error(str(e)))

    @staticmethod
    def _friendly_error(msg: str) -> str:
        """Rút gọn thông báo lỗi do RAISERROR (trigger / SP) phát ra,
        bỏ bớt phần tiền tố kỹ thuật của pyodbc/ODBC driver."""
        for part in msg.replace("\\r\\n", "\n").split("\n"):
            if "rùng" in part:  # bắt cả "Trùng" và "trùng"
                # Cắt bỏ phần mã lỗi ODBC ở đầu nếu có, ví dụ "[42000] ..."
                idx = part.find("Trùng") if "Trùng" in part else part.find("trùng")
                return part[idx:].strip()
        return msg