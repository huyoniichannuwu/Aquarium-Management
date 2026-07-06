import pyodbc
from tkinter import messagebox

def connect_db():
    conn_str = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=LAPTOP-HR89OJ90;"         
        "DATABASE=QLThuyCung;"
        "Trusted_Connection=yes;"
    )
    try:
        return pyodbc.connect(conn_str)
    except Exception as e:
        messagebox.showerror("Lỗi kết nối", f"Không thể kết nối SQL Server!\n{e}")
        return None
