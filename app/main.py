# ============================================================
# FILE: app/main.py
# PURPOSE: Main application UI using CustomTkinter
# ARCHITECTURE: Single-window app with sidebar navigation.
#   Each "screen" is a CTkFrame that is shown/hidden.
#   Data flow: UI events → models.py functions → MySQL
# ============================================================

import customtkinter as ctk
from tkinter import messagebox, ttk
import tkinter as tk
from datetime import datetime
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Import our business logic modules
import models
import reports
from db_connection import test_connection

# ============================================================
# APP CONFIGURATION
# ============================================================
#ctk.set_appearance_mode("dark")           # Options: "dark", "light", "system"
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

FONT_TITLE   = ("Segoe UI", 20, "bold")
FONT_HEADING = ("Segoe UI", 14, "bold")
FONT_BODY    = ("Segoe UI", 12)
FONT_SMALL   = ("Segoe UI", 10)

COLOR_INCOME  = "#2ecc71"
COLOR_EXPENSE = "#e74c3c"
COLOR_NEUTRAL = "#3498db"
COLOR_WARNING = "#f39c12"

# ============================================================
# HELPER POPUPS
# ============================================================

class UserProfilePopup(ctk.CTkToplevel):
    def __init__(self, parent_app, user_id=None, current_data=None):
        super().__init__()
        self.parent_app = parent_app
        self.user_id = user_id  
        self.initial_data = current_data # Lưu lại để đối chiếu khi bấm Save
        
        self.title("User Profile Management")
        self.geometry("450x600")
        self.attributes("-topmost", True)
        self.grab_set() # Ngăn người dùng bấm ra ngoài khi đang edit

        # Header
        title_text = "👤 Edit User Profile" if user_id else "👤 New User Registration"
        ctk.CTkLabel(self, text=title_text, font=("Segoe UI", 22, "bold"), 
                     text_color=COLOR_NEUTRAL).pack(pady=25)

        # Cấu trúc các ô nhập liệu (Pre-filled)
        self.name_entry  = self._add_input("Full Name:", "Ex: Nguyen Van A")
        self.email_entry = self._add_input("Email:", "a@example.com")
        self.phone_entry = self._add_input("Phone Number:", "090xxxxxxx")
        
        if not user_id:
            # Chỉ hiện Bank Account khi tạo mới
            ctk.CTkFrame(self, height=2, fg_color="gray80").pack(fill="x", padx=40, pady=10)
            self.bank_entry = self._add_input("Initial Bank Account:", "Ex: Techcombank")
        
        # ĐIỀN THÔNG TIN CŨ (Dành cho chế độ Edit)
        if current_data:
            self.name_entry.insert(0, current_data.get('UserName', ''))
            self.email_entry.insert(0, current_data.get('Email', ''))
            phone_val = current_data.get('PhoneNumber', '')
            self.phone_entry.delete(0, 'end') # Xóa trắng trước khi chèn
            self.phone_entry.insert(0, str(phone_val))

        # Button Frame (Cancel & Save)
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=40, padx=40, fill="x")

        # Nút CANCEL
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray", hover_color="#7f8c8d",
                      width=140, height=45, font=("Segoe UI", 13, "bold"),
                      command=self.destroy).pack(side="left", padx=(0, 10), expand=True, fill="x")

        # Nút SAVE (Update/Create)
        btn_text = "Save Changes" if user_id else "Create Profile"
        self.submit_btn = ctk.CTkButton(btn_frame, text=btn_text, command=self._handle_submit,
                                        font=("Segoe UI", 13, "bold"),
                                        fg_color=COLOR_NEUTRAL if user_id else COLOR_INCOME, 
                                        height=45)
        self.submit_btn.pack(side="right", expand=True, fill="x")

    def _add_input(self, label, placeholder):
        ctk.CTkLabel(self, text=label, font=("Segoe UI", 12, "bold")).pack(padx=40, anchor="w")
        entry = ctk.CTkEntry(self, placeholder_text=placeholder, width=350, height=38)
        entry.pack(pady=(2, 12), padx=40)
        return entry

    def _handle_submit(self):
        name = self.name_entry.get().strip()
        email = self.email_entry.get().strip()
        phone = self.phone_entry.get().strip()

        # 1. Kiểm tra rỗng
        if not name or not email:
            messagebox.showwarning("Input Error", "Name and Email cannot be empty!")
            return

        try:
            # 2. LOGIC CHO CHẾ ĐỘ EDIT
            if self.user_id:
                # Lấy lại data cũ để so sánh
                old_name  = self.initial_data.get('UserName', '')
                old_email = self.initial_data.get('Email', '')
                old_phone = self.initial_data.get('PhoneNumber', '')
                
                # Kiểm tra xem CÓ THAY ĐỔI gì không
                if name == old_name and email == old_email and phone == str(old_phone):
                    messagebox.showwarning("No Changes", "You haven't changed any profile information.")
                    return

                # Thực hiện Update
                models.update_user_profile(self.user_id, name, email, phone)
                messagebox.showinfo("Success", "Profile updated successfully!")
            
            # 3. LOGIC CHO CHẾ ĐỘ TẠO MỚI (Giữ nguyên như cũ)
            else:
                bank = self.bank_entry.get().strip()
                if not bank:
                    messagebox.showwarning("Warning", "Initial Bank Account is required!")
                    return
                    
                new_uid = models.create_user(name, email, phone)
                if new_uid:
                    models.create_account(new_uid, bank, 0)
                    messagebox.showinfo("Success", f"User {name} created with initial account!")

            self.parent_app.refresh_user_dropdown() 
            self.destroy()
        
        except Exception as e:
            messagebox.showerror("Database Error", f"Action failed: {str(e)}")

class AddCategoryPopup(ctk.CTkToplevel):
    def __init__(self, parent_app):
        super().__init__()
        self.parent_app = parent_app
        self.title("Add New Category")
        self.geometry("400x400")
        self.attributes("-topmost", True)

        ctk.CTkLabel(self, text="📂 New Category", font=("Segoe UI", 20, "bold"), 
                     text_color=COLOR_NEUTRAL).pack(pady=25)
        
        ctk.CTkLabel(self, text="Category Name:", font=("Segoe UI", 12, "bold")).pack(padx=40, anchor="w")
        self.cat_name = ctk.CTkEntry(self, width=320, height=35)
        self.cat_name.pack(pady=(2, 15), padx=40)

        ctk.CTkLabel(self, text="Description:", font=("Segoe UI", 12, "bold")).pack(padx=40, anchor="w")
        self.cat_desc = ctk.CTkEntry(self, width=320, height=35)
        self.cat_desc.pack(pady=(2, 25), padx=40)

        ctk.CTkButton(self, text="Save Category", command=self._handle_submit,
                      font=("Segoe UI", 14, "bold"),
                      fg_color=COLOR_NEUTRAL, height=40).pack(pady=10, padx=40, fill="x")

    def _handle_submit(self):
        name = self.cat_name.get().strip()
        desc = self.cat_desc.get().strip()
        
        # 1. Kiểm tra rỗng tại GUI
        if not name:
            messagebox.showwarning("Warning", "Please enter a category name.")
            return

        # 2. Xử lý logic và Database
        try:
            # Gọi model thực hiện insert
            # Nếu tên danh mục đã tồn tại, lỗi UNIQUE KEY từ MySQL sẽ được raise lên đây
            models.create_category(name, desc)
            
            # Nếu không có lỗi, thực hiện thông báo và cập nhật giao diện
            messagebox.showinfo("Success", f"Category '{name}' added successfully!")
            
            # Refresh các màn hình liên quan để cập nhật danh sách mới
            if "transactions" in self.parent_app.screens:
                self.parent_app.screens["transactions"].refresh()
            if "budgets" in self.parent_app.screens:
                self.parent_app.screens["budgets"].refresh()
                
            self.destroy()

        except Exception as e:
            # 3. Bắt mọi lỗi từ Database (Ví dụ: trùng tên, lỗi kết nối...)
            # Thông báo lỗi thực tế cho người dùng
            messagebox.showerror("Category Error", f"Cannot add category: \n{str(e)}")

class EditTransactionPopup(ctk.CTkToplevel):
    def __init__(self, parent_screen, trans_type, trans_id, initial_data):
        super().__init__(parent_screen)
        self.parent_screen = parent_screen
        self.app = parent_screen.app
        self.trans_type = trans_type # "INCOME" hoặc "EXPENSE"
        self.trans_id = trans_id
        self.initial_data = initial_data # Lưu lại để so sánh thay đổi

        # Window Setup
        self.title(f"Edit {trans_type.title()}")
        self.geometry("500x600")
        self.grab_set() # Giữ focus vào popup
        self.resizable(False, False)

        self._build_ui()
        self._populate_data()

    def _build_ui(self):
        # Header
        color = COLOR_INCOME if self.trans_type == "INCOME" else COLOR_EXPENSE
        ctk.CTkLabel(self, text=f"Edit {self.trans_type}", font=("Segoe UI", 20, "bold"), 
                     text_color=color).pack(pady=20)

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=40)

        # Fields
        self.fields = {}
        
        # 1. Category (Chỉ hiện cho Expense)
        if self.trans_type == "EXPENSE":
            ctk.CTkLabel(self.container, text="Category:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 0))
            self.cat_menu = ctk.CTkOptionMenu(self.container, width=400, height=35, fg_color=("#3498db", "#1f538d"))
            self.cat_menu.pack(pady=5)
            self.cat_menu.configure(values=list(self.parent_screen._cat_map.keys()))

        # 2. Account
        ctk.CTkLabel(self.container, text="Bank Account:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 0))
        self.acc_menu = ctk.CTkOptionMenu(self.container, width=400, height=35, fg_color=("#3498db", "#1f538d"))
        self.acc_menu.pack(pady=5)
        self.acc_menu.configure(values=list(self.parent_screen._account_map.keys()))

        # 3. Amount
        ctk.CTkLabel(self.container, text="Amount (VND):", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 0))
        self.amount_entry = ctk.CTkEntry(self.container, width=400, height=35)
        self.amount_entry.pack(pady=5)

        # 4. Date
        ctk.CTkLabel(self.container, text="Date (YYYY-MM-DD):", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 0))
        self.date_entry = ctk.CTkEntry(self.container, width=400, height=35)
        self.date_entry.pack(pady=5)

        # 5. Description
        ctk.CTkLabel(self.container, text="Description:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 0))
        self.desc_entry = ctk.CTkEntry(self.container, width=400, height=35)
        self.desc_entry.pack(pady=5)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", pady=30, padx=40)

        ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray", width=120, height=35, 
                      command=self.destroy).pack(side="left")
        ctk.CTkButton(btn_frame, text="Save Changes", fg_color=color, width=120, height=35, 
                      command=self._handle_save).pack(side="right")

    def _populate_data(self):
        """Điền thông tin cũ vào các ô nhập liệu."""
        # data: (Type, Date, Details, Amount, Account, Description)
        if self.trans_type == "EXPENSE":
            self.cat_menu.set(self.initial_data[2])
        
        self.date_entry.insert(0, self.initial_data[1])
        self.amount_entry.insert(0, self.initial_data[3].replace(' ₫', '').replace(',', ''))
        self.acc_menu.set(self.initial_data[4])
        self.desc_entry.insert(0, self.initial_data[5] if self.initial_data[5] else "")

    def _handle_save(self):
        # Lấy dữ liệu mới
        new_amount = self.amount_entry.get().strip()
        new_date = self.date_entry.get().strip()
        new_acc = self.acc_menu.get()
        new_desc = self.desc_entry.get().strip()
        new_cat = self.cat_menu.get() if self.trans_type == "EXPENSE" else None

        # 1. Kiểm tra xem có thay đổi gì không
        has_changed = (
            new_amount != self.initial_data[3].replace(' ₫', '').replace(',', '') or
            new_date != str(self.initial_data[1]) or
            new_acc != self.initial_data[4] or
            new_desc != (self.initial_data[5] if self.initial_data[5] else "") or
            (self.trans_type == "EXPENSE" and new_cat != self.initial_data[2])
        )

        if not has_changed:
            messagebox.showwarning("No Changes", "You haven't changed any information.")
            return

        # 2. Thực hiện cập nhật Database
        try:
            selected_acc_text = self.acc_menu.get()
            pure_bank_name = selected_acc_text.split(" (")[0]
            acc_id = self.parent_screen._account_name_only_map[pure_bank_name]

            #acc_id = self.parent_screen._account_map[new_acc]
            if self.trans_type == "INCOME":
                success = models.update_income(self.trans_id, acc_id, float(new_amount), new_date, new_desc)
            else:
                cat_id = self.parent_screen._cat_map[self.cat_menu.get()]
                success = models.update_expense(self.trans_id, cat_id, acc_id, float(new_amount), new_date, new_desc)

            if success:
                messagebox.showinfo("Success", "Transaction updated successfully!")
                self.parent_screen.refresh() # Cập nhật lại bảng History ngay lập tức
                self.app.screens["dashboard"].refresh() # Cập nhật số dư Dashboard
                self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update: {e}")

# ============================================================
# MAIN APPLICATION CLASS
# ============================================================

class FinanceApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window setup ---
        self.title("Personal Finance Manager")
        self.geometry("1250x780")
        self.minsize(1100, 700)

        # --- App state ---
        self.current_user_id  = tk.IntVar(value=1)       # Selected user
        self.current_month    = tk.StringVar(
            value=datetime.now().strftime('%Y-%m'))        # 'YYYY-MM'

        # --- Build layout ---
        self._build_layout()
        self._build_sidebar()
        self._build_screens()

        # --- Load initial screen ---
        self.show_screen("dashboard")
        self.refresh_user_dropdown()

    # ----------------------------------------------------------
    # LAYOUT STRUCTURE
    # ----------------------------------------------------------

    def _build_layout(self):
        """Create the 2-column root grid: sidebar | main content."""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar (fixed width)
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, 
                                    fg_color=("#f8f9fa", "#1a1a1a"),
                                    border_width=1, border_color="gray85")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Main content area
        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=15)
        self.main_area.grid_columnconfigure(0, weight=1)
        self.main_area.grid_rowconfigure(0, weight=1)

    def _build_sidebar(self):
        """Build navigation sidebar with user selector and nav buttons."""
        # App logo / title
        logo = ctk.CTkLabel(self.sidebar, text="💰 FinTrack",
                            font=("Segoe UI", 26, "bold"), text_color=COLOR_NEUTRAL)
        logo.pack(pady=(30, 5), padx=10)

        ctk.CTkLabel(self.sidebar, text="Personal Finance System", font=FONT_SMALL,
                     text_color="gray50").pack(pady=(0, 25))

        # --- User Selector ---
        ctk.CTkLabel(self.sidebar, text="Active User:", font=("Segoe UI", 12, "bold")).pack(padx=(25, 10), anchor="w")
        self.user_dropdown = ctk.CTkOptionMenu(
            self.sidebar, width=200, height=35,
            command=self._on_user_change,
            fg_color=("#3498db", "#1f538d"),
            button_color=("#2980b9", "#1a457a"),
            dynamic_resizing=False
        )
        self.user_dropdown.pack(padx=10, pady=(5, 10))

        btn_opts = {"width": 200, "height": 32, "font": ("Segoe UI", 12, "bold"), "border_width": 1}
        
        ctk.CTkButton(self.sidebar, text="+ New Profile", **btn_opts,
                      fg_color="transparent", border_color=COLOR_INCOME, text_color=("#27ae60", "#2ecc71"),
                      command=lambda: UserProfilePopup(self)).pack(pady=5)

        ctk.CTkButton(self.sidebar, text="⚙️ Edit Profile", **btn_opts,
                      fg_color="transparent", border_color=COLOR_NEUTRAL, text_color=COLOR_NEUTRAL,
                      command=self._handle_edit_profile).pack(pady=5)

        # --- Month Selector ---
        ctk.CTkLabel(self.sidebar, text="Month:", font=("Segoe UI", 12, "bold")).pack(padx=(25, 10), anchor="w")
        self.month_entry = ctk.CTkEntry(self.sidebar, width=200, height=35,
                                        textvariable=self.current_month, justify="center", font=("Consolas", 14))
        self.month_entry.pack(padx=10, pady=(5, 5))
        ctk.CTkLabel(self.sidebar, text="Format: YYYY-MM", font=FONT_SMALL,
                     text_color="gray50").pack()

        ctk.CTkButton(self.sidebar, text="Apply Month", width=200, height=38,
                      font=("Segoe UI", 13, "bold"), fg_color=COLOR_NEUTRAL,
                      command=self._refresh_current_screen).pack(pady=(10, 30))

        ctk.CTkFrame(self.sidebar, height=1, fg_color="gray80").pack(fill="x", padx=20, pady=10)

        # --- Navigation buttons ---
        nav_buttons = [
            ("🏠  Dashboard",     "dashboard"),
            ("💳  Transactions",  "transactions"),
            ("📊  Reports",       "reports"),
            ("🎯  Budgets",       "budgets"),
        ]
        self._nav_buttons = {}
        for label, screen in nav_buttons:
            btn = ctk.CTkButton(self.sidebar, text=label, width=200, height=45, anchor="w",
                                font=("Segoe UI", 14), fg_color="transparent",
                                text_color=("black", "white"), hover_color=("gray85", "#2d2d2d"),
                                command=lambda s=screen: self.show_screen(s))
            btn.pack(padx=10, pady=4)
            self._nav_buttons[screen] = btn

        # Version info at bottom
        ctk.CTkLabel(self.sidebar, text="v1.0 - 2026",
                     font=FONT_SMALL, text_color="gray").pack(side="bottom", pady=15)

    def _handle_edit_profile(self):
        """Mở Popup Edit Profile với dữ liệu hiện tại"""
        uid = self.get_user_id()
        users = models.get_all_users()
        current_user = next((u for u in users if u['UserID'] == uid), None)
        
        if current_user:
            # Gọi Popup thông minh ở chế độ Edit
            UserProfilePopup(self, user_id=uid, current_data=current_user)

    def _build_screens(self):
        """Instantiate all screen frames."""
        self.screens = {}
        self.screens["dashboard"]    = DashboardScreen(self.main_area, self)
        self.screens["transactions"] = TransactionsScreen(self.main_area, self)
        self.screens["reports"]      = ReportsScreen(self.main_area, self)
        self.screens["budgets"]      = BudgetsScreen(self.main_area, self)

        for screen in self.screens.values():
            screen.grid(row=0, column=0, sticky="nsew")

    # ----------------------------------------------------------
    # NAVIGATION & STATE
    # ----------------------------------------------------------

    def show_screen(self, name):
        """Bring a screen to front and refresh its data."""
        self.active_screen_name = name
        self.screens[name].tkraise()
        self.screens[name].refresh()

        # Highlight active nav button
        for btn_name, btn in self._nav_buttons.items():
            if btn_name == name:
                btn.configure(fg_color=("#3498db", "#1f538d"), text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=("black", "white"))

    def _refresh_current_screen(self):
        """Called when month changes — refresh whichever screen is visible."""
        if not hasattr(self, 'active_screen_name'):
            self.active_screen_name = "dashboard"
            
        print(f"\n>>> [ACTION] Button 'Apply Month' clicked. Refreshing: {self.active_screen_name}")
        
        # Gọi lệnh làm mới cho đúng màn hình đang hiện ra
        self.screens[self.active_screen_name].refresh()

    def get_user_id(self):
        return self.current_user_id.get()

    def get_month(self):
        return self.current_month.get().strip()

    def refresh_user_dropdown(self):
        """Populate the user dropdown from DB."""
        users = models.get_all_users()
        if not users:
            return
        self._user_map = {u['UserName']: u['UserID'] for u in users}
        names = list(self._user_map.keys())
        self.user_dropdown.configure(values=names)
        current_name = next((name for name, id in self._user_map.items() if id == self.get_user_id()), names[0])
        self.user_dropdown.set(current_name)
        self.current_user_id.set(self._user_map[current_name])

    def _on_user_change(self, selection):
        self.current_user_id.set(self._user_map[selection])
        self.show_screen("dashboard")


# ============================================================
# SCREEN 1: DASHBOARD
# ============================================================

class DashboardScreen(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._build()

    def _build(self):
        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure(3, weight=1) # Recent Expenses giãn nở

        # Title
        ctk.CTkLabel(self, text="Financial Overview", font=("Segoe UI", 24, "bold"),
                     text_color=COLOR_NEUTRAL).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 20))

        # KPI Cards (Tích hợp thêm nhãn Daily/Yearly bên trong)
        self.card_balance, self.sub_balance = self._make_kpi_card("Total Balance", "0 ₫", COLOR_NEUTRAL, 0, "Current Assets")
        self.card_income,  self.sub_income  = self._make_kpi_card("Month Income",  "0 ₫", COLOR_INCOME,  1, "Today's In")
        self.card_expense, self.sub_expense = self._make_kpi_card("Month Expenses", "0 ₫", COLOR_EXPENSE, 2, "Today's Out")

        # Alerts section
        alert_frame = ctk.CTkFrame(self, fg_color=("white", "#2b2b2b"), border_width=1, border_color="gray80")
        alert_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=5, pady=(15, 10))
        
        ctk.CTkLabel(alert_frame, text="⚠️  Budget Alerts",
                     font=("Segoe UI", 14, "bold"), text_color=COLOR_WARNING).pack(anchor="w", padx=15, pady=(10, 5))
        
        self.alert_box = ctk.CTkTextbox(alert_frame, height=150, font=("Segoe UI", 14),
                                        fg_color="transparent", state="disabled")
        self.alert_box.pack(fill="x", padx=15, pady=(0, 10))

        # Recent transactions
        recent_frame = ctk.CTkFrame(self, fg_color="transparent")
        recent_frame.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=5, pady=10)
        recent_frame.grid_rowconfigure(1, weight=1)
        recent_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(recent_frame, text="Recent Expenses", font=("Segoe UI", 15, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=(10, 5))
        
        self.recent_tree = self._make_treeview(
            recent_frame,
            columns=("Date", "Category", "Amount", "Description"),
            row=1
        )

    def _make_kpi_card(self, title, value, color, col, sub_title):
        frame = ctk.CTkFrame(self, fg_color=("gray95", "#252525"), border_width=1, border_color="gray85")
        frame.grid(row=1, column=col, padx=8, pady=5, sticky="nsew")
        
        ctk.CTkLabel(frame, text=title.upper(), font=("Segoe UI", 11, "bold"), text_color="gray50").pack(pady=(15, 0))
        
        lbl_main = ctk.CTkLabel(frame, text=value, font=("Segoe UI", 28, "bold"), text_color=color)
        lbl_main.pack(pady=(5, 2))
        
        # Nhãn phụ để hiện Daily/Yearly
        lbl_sub = ctk.CTkLabel(frame, text=f"{sub_title}: 0 ₫", font=("Segoe UI", 11), text_color="gray60")
        lbl_sub.pack(pady=(0, 15))
        
        return lbl_main, lbl_sub

    def _make_treeview(self, parent, columns, row):
        style = ttk.Style()
        style.theme_use("clam")
        bg_color = "#fdfdfd" if ctk.get_appearance_mode() == "Light" else "#2b2b2b"
        fg_color = "black" if ctk.get_appearance_mode() == "Light" else "white"
        
        style.configure("Dashboard.Treeview", 
                        background=bg_color, 
                        foreground=fg_color, 
                        fieldbackground=bg_color, 
                        rowheight=60, 
                        font=("Segoe UI", 18))
    
        style.configure("Dashboard.Treeview.Heading", 
                        background="#eeeeee" if bg_color=="#fdfdfd" else "#1a1a1a", 
                        foreground=fg_color, font=("Segoe UI", 18, "bold"))
        
        tree = ttk.Treeview(parent, columns=columns, show="headings", style="Dashboard.Treeview", height=8)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=250, anchor="center")
        
        tree.grid(row=row, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        scrollbar = ctk.CTkScrollbar(parent, orientation="vertical", command=tree.yview, width=12)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=row, column=1, sticky="ns", pady=(0, 10))
        return tree

    def refresh(self):
        uid = self.app.get_user_id()
        month = self.app.get_month()
        year = month.split('-')[0]

        # 1. Fetch Daily/Yearly data
        daily_data = models.get_daily_summary(uid)
        yearly_data = models.get_yearly_summary(uid, year)

        d_in = daily_data['day_in'] if daily_data else 0
        d_out = daily_data['day_out'] if daily_data else 0
        y_in = yearly_data['yr_in'] if yearly_data else 0
        y_out = yearly_data['yr_out'] if yearly_data else 0

        # 2. Update KPI cards + Sub-labels (Daily/Yearly)
        balance = models.get_total_balance(uid)
        self.card_balance.configure(text=f"{balance:,.0f} ₫")
        self.sub_balance.configure(text=f"Year {year} Net: {(y_in - y_out):,.0f} ₫")

        income_rows = models.get_income_by_user_month(uid, month)
        total_income = sum(float(r['Amount']) for r in income_rows)
        self.card_income.configure(text=f"{total_income:,.0f} ₫")
        self.sub_income.configure(text=f"Today In: {d_in:,.0f} ₫")

        expense_rows = models.get_expenses_by_user_month(uid, month)
        total_expense = sum(float(r['Amount']) for r in expense_rows)
        self.card_expense.configure(text=f"{total_expense:,.0f} ₫")
        self.sub_expense.configure(text=f"Today Out: {d_out:,.0f} ₫")

        # 3. Budget alerts (giữ nguyên logic)
        alerts = models.get_budget_alerts(uid, month)
        self.alert_box.configure(state="normal")
        self.alert_box.delete("1.0", "end")
        if alerts:
            for a in alerts:
                icon = "🔴" if a['BudgetStatus'] == 'EXCEEDED' else "🟡"
                self.alert_box.insert("end", f"{icon} {a['CategoryName']}: {a['UsagePercent']}% used ({a['SpentAmount']:,.0f} / {a['LimitAmount']:,.0f} ₫)\n")
        else:
            self.alert_box.insert("end", "✅ All budgets are within limits.")
        self.alert_box.configure(state="disabled")

        # 4. Recent expenses (giữ nguyên logic)
        for row in self.recent_tree.get_children():
            self.recent_tree.delete(row)
        for row in expense_rows[:10]:
            self.recent_tree.insert("", "end", values=(str(row['ExpenseDate']), row['CategoryName'], f"{float(row['Amount']):,.0f} ₫", row['Description'] or ""))


# ============================================================
# SCREEN 2: TRANSACTIONS
# ============================================================

class TransactionsScreen(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Transactions", font=FONT_TITLE,
                     text_color=COLOR_NEUTRAL).grid(
            row=0, column=0, sticky="w", pady=(0, 15))

        # Tab view: Add Income | Add Expense | History
        self.tabs = ctk.CTkTabview(self, segmented_button_selected_color=COLOR_NEUTRAL, 
                                   segmented_button_fg_color=("#dbdbdb", "#2d2d2d"))
        self.tabs.grid(row=1, column=0, sticky="nsew")

        self.tabs.add("➕ Add Income")
        self.tabs.add("➖ Add Expense")
        self.tabs.add("📋 History")

        self._build_income_tab(self.tabs.tab("➕ Add Income"))
        self._build_expense_tab(self.tabs.tab("➖ Add Expense"))
        self._build_history_tab(self.tabs.tab("📋 History"))

    def _build_income_tab(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(padx=40, pady=30, fill="both")

        fields = [
            ("Bank Account", "income_account"),
            ("Amount (VND)", "income_amount"),
            ("Date",         "income_date"),
            ("Description",  "income_desc"),
        ]
        self._income_vars = {}
        for i, (label, key) in enumerate(fields):
            ctk.CTkLabel(frame, text=label, font=("Segoe UI", 13, "bold")).grid(row=i, column=0, sticky="w", pady=15)
            
            if key == "income_account":
                acct_container = ctk.CTkFrame(frame, fg_color="transparent")
                acct_container.grid(row=i, column=1, padx=20, sticky="w")

                self.income_account_menu = ctk.CTkOptionMenu(
                    acct_container, width=280, height=38,
                    fg_color=("#3498db", "#1f538d"), button_color=("#2980b9", "#1a457a"),
                    text_color="white"
                )
                self.income_account_menu.set("Choose Bank Account")
                self.income_account_menu.pack(side="left", padx=(0, 10))

                ctk.CTkButton(acct_container, text="+ New Account", width=100, height=38,
                              font=("Segoe UI", 12, "bold"),
                              fg_color="transparent", border_color=COLOR_NEUTRAL, text_color=COLOR_NEUTRAL,
                              command=self._add_new_account_to_current_user).pack(side="left")
            else:
                var = ctk.CTkEntry(frame, width=350, height=38, font=("Segoe UI", 13))
                var.grid(row=i, column=1, padx=20, pady=10)
                if key == "income_date": var.insert(0, datetime.now().strftime('%Y-%m-%d'))
                self._income_vars[key] = var

        ctk.CTkButton(frame, text="Save Income", width=220, height=45,
                      fg_color=COLOR_INCOME, hover_color="#27ae60", font=("Segoe UI", 14, "bold"),
                      command=self._save_income).grid(row=len(fields), column=1,
                                                      pady=35, sticky="e")

    def _add_new_account_to_current_user(self):
        """Mở hộp thoại nhập tên tài khoản mới cho User đang chọn."""
        uid = self.app.get_user_id()
        dialog = ctk.CTkInputDialog(text="Enter Bank/Wallet Name (e.g., Techcombank):", title="New Account")
        bank_name = dialog.get_input()
        
        if bank_name:
            # Gọi hàm models.create_account (Lưu ý: dùng đúng tên bảng BankAccounts)
            if models.create_account(uid, bank_name, 0):
                messagebox.showinfo("Success", f"New account '{bank_name}' opened with 0 ₫ balance.")
                self.refresh() # Load lại danh sách tài khoản mới vào menu
            else:
                messagebox.showerror("Error", "Failed to create account. Check Terminal for details.")
    
    def _build_expense_tab(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(padx=40, pady=30, fill="both")

        self._expense_vars = {}
        labels = [("Expense Category", "cat"), ("Source Account", "acc"), ("Amount (VND)", "amt"), ("Date", "date"), ("Description", "desc")]
        for i, (label, key) in enumerate(labels):
            ctk.CTkLabel(frame, text=label, font=("Segoe UI", 13, "bold")).grid(row=i, column=0, sticky="w", pady=15)
            
            if key == "cat":
                cat_container = ctk.CTkFrame(frame, fg_color="transparent")
                cat_container.grid(row=i, column=1, padx=20, sticky="w")
                self.expense_category_menu = ctk.CTkOptionMenu(cat_container, width=300, height=38,
                                                               fg_color=("#3498db", "#1f538d"), text_color="white")
                self.expense_category_menu.set("Choose Category")
                self.expense_category_menu.pack(side="left", padx=(0, 10))
                ctk.CTkButton(cat_container, text="+", width=40, height=38, font=("Segoe UI", 16, "bold"),
                              fg_color="transparent", border_color=COLOR_NEUTRAL, text_color=COLOR_NEUTRAL, 
                              command=lambda: AddCategoryPopup(self.app)).pack(side="left")
            
            elif key == "acc":
                self.expense_account_menu = ctk.CTkOptionMenu(frame, width=350, height=38,
                                                              fg_color=("#3498db", "#1f538d"), text_color="white")
                self.expense_account_menu.set("Choose Account")
                self.expense_account_menu.grid(row=i, column=1, padx=20)
            
            else:
                w = ctk.CTkEntry(frame, width=350, height=38, font=("Segoe UI", 13))
                w.grid(row=i, column=1, padx=20, pady=10)
                if key == "date": w.insert(0, datetime.now().strftime('%Y-%m-%d'))
                self._expense_vars[key] = w

        ctk.CTkButton(frame, text="Save Expense", width=220, height=45, 
                      fg_color=COLOR_EXPENSE, font=("Segoe UI", 14, "bold"), 
                      command=self._save_expense).grid(row=len(labels), column=1, pady=35, sticky="e")

    def _build_history_tab(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=15, pady=15)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        bg_color = "#fdfdfd" if ctk.get_appearance_mode() == "Light" else "#2b2b2b"
        fg_color = "black" if ctk.get_appearance_mode() == "Light" else "white"

        style.configure("History.Treeview", 
                        background=bg_color, 
                        foreground="black" if bg_color=="#fdfdfd" else "white", 
                        rowheight=60, 
                        font=("Segoe UI", 18))
        style.configure("History.Treeview.Heading", 
                        background="#eeeeee" if bg_color=="#fdfdfd" else "#1a1a1a", 
                        foreground=fg_color, font=("Segoe UI", 18, "bold"))

        cols = ("Type", "Date", "Category/Source", "Amount", "Account", "Description")
        self.history_tree = ttk.Treeview(frame, columns=cols, show="headings", style="History.Treeview", height=8)
        for col in cols:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=250, anchor="center")
        self.history_tree.grid(row=0, column=0, sticky="nsew")

        # Action buttons
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.grid(row=1, column=0, columnspan=2, pady=15, sticky="e")
        
        ctk.CTkButton(btn_frame, text="🗑️ Delete", fg_color="#e74c3c", width=120, height=35,
                      command=self._delete_selected_trans).pack(side="right", padx=10)
        ctk.CTkButton(btn_frame, text="✏️ Edit", fg_color=COLOR_NEUTRAL, width=120, height=35,
                      command=self._edit_selected_trans).pack(side="right", padx=10)

        scrollbar = ctk.CTkScrollbar(frame, orientation="vertical", command=self.history_tree.yview, width=12)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

    def refresh(self):
        uid = self.app.get_user_id()
        month = self.app.get_month()

        # 1. Fetch Data First
        accounts = models.get_accounts_by_user(uid)
        categories = models.get_categories()
        income_rows = models.get_income_by_user_month(uid, month)
        expense_rows = models.get_expenses_by_user_month(uid, month)

        # 2. Update Menus
        acct_opts = [f"{a['BankName']} ({a['BalanceFormatted']} ₫)" for a in accounts]
        self._account_map = {opt: a['AccountID'] for opt, a in zip(acct_opts, accounts)}
        self._account_name_only_map = {a['BankName']: a['AccountID'] for a in accounts}
        
        if acct_opts:
            self.income_account_menu.configure(values=acct_opts)
            self.expense_account_menu.configure(values=acct_opts)

        cat_opts = [c['CategoryName'] for c in categories]
        self._cat_map = {c['CategoryName']: c['CategoryID'] for c in categories}
        if cat_opts: self.expense_category_menu.configure(values=cat_opts)

        # 3. Clear and Fill Tree
        for row in self.history_tree.get_children(): self.history_tree.delete(row)
        
        self.history_tree.tag_configure("income", foreground="#27ae60")
        self.history_tree.tag_configure("expense", foreground="#c0392b")

        for r in income_rows:
            self.history_tree.insert("", "end", iid=f"inc_{r['IncomeID']}", tags=("income",), 
                                     values=("INCOME", str(r['IncomeDate']), "Salary/Bonus", f"{float(r['Amount']):,.0f} ₫", r['BankName'], r['Description'] or ""))
        
        for r in expense_rows:
            self.history_tree.insert("", "end", iid=f"exp_{r['ExpenseID']}", tags=("expense",), 
                                     values=("EXPENSE", str(r['ExpenseDate']), r['CategoryName'], f"{float(r['Amount']):,.0f} ₫", r['BankName'], r['Description'] or ""))
        
        self.update_idletasks()

    def _save_income(self):
        uid = self.app.get_user_id()
        try:
            acct_key = self.income_account_menu.get()
            if acct_key == "Choose Bank Account": raise KeyError("Account")
            acct_id  = self._account_map[acct_key]
            amount   = float(self._income_vars['income_amount'].get().replace(',', ''))
            date     = self._income_vars['income_date'].get()
            desc     = self._income_vars['income_desc'].get()

            if models.add_income(uid, acct_id, amount, date, desc):
                messagebox.showinfo("Success", f"Income of {amount:,.0f} ₫ added successfully.")
                self.refresh()
                self.app.screens["dashboard"].refresh()
            else:
                messagebox.showerror("Error", "Failed to save income record.")
        except Exception as e:
            messagebox.showerror("Input Error", "Please ensure all fields are correct.")

    def _save_expense(self):
        uid = self.app.get_user_id()
        try:
            cat_name = self.expense_category_menu.get()
            acct_key = self.expense_account_menu.get()
            if cat_name == "Choose Category" or acct_key == "Choose Account": raise KeyError("Selection")
            
            cat_id   = self._cat_map[cat_name]
            acct_id  = self._account_map[acct_key]
            amount   = float(self._expense_vars['amt'].get().replace(',', ''))
            date     = self._expense_vars['date'].get()
            desc     = self._expense_vars['desc'].get()

            if models.add_expense(uid, cat_id, acct_id, amount, date, desc):
                messagebox.showinfo("Success", f"Expense of {amount:,.0f} ₫ recorded.")
                self.refresh()
                self.app.screens["dashboard"].refresh()
            else:
                messagebox.showerror("Error", "Insufficient balance in selected account.")
        except Exception:
            messagebox.showerror("Input Error", "Check your inputs (Amount/Category/Account).")

    def _delete_selected_trans(self):
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select a transaction to delete.")
            return
        
        iid = selected[0]
        trans_type, trans_id = iid.split("_") # inc_1 -> ['inc', '1']
        
        if messagebox.askyesno("Confirm", f"Permanently delete this record? Bank balance will restore automatically via Database Triggers."):
            success = models.delete_income(trans_id) if trans_type == "inc" else models.delete_expense(trans_id)
            if success:
                messagebox.showinfo("Success", "Record removed.")
                self.refresh()
                self.app.screens["dashboard"].refresh()

    def _edit_selected_trans(self):
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a transaction to edit.")
            return
        
        # Lấy iid (ví dụ: "inc_12")
        iid = selected[0]
        trans_type_code, trans_id = iid.split("_")
        
        # Lấy dữ liệu dòng hiện tại
        current_data = self.history_tree.item(iid)['values']
        
        # Mở Popup chuyên dụng
        type_str = "INCOME" if trans_type_code == "inc" else "EXPENSE"
        EditTransactionPopup(self, type_str, trans_id, current_data)

# ============================================================
# SCREEN 3: REPORTS
# ============================================================

class ReportsScreen(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._current_canvas = None
        self._active_chart = None
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self, text="Financial Reports", font=("Segoe UI", 24, "bold"), text_color=COLOR_NEUTRAL).grid(row=0, column=0, sticky="w", pady=(0, 20))
        self.tabs = ctk.CTkTabview(self, segmented_button_selected_color=COLOR_NEUTRAL)
        self.tabs.grid(row=1, column=0, sticky="nsew")
        self.tab_summaries = self.tabs.add("📌 Performance Snapshots")
        self.tab_visuals = self.tabs.add("📊 Visual Analytics")
        self._setup_summaries_tab()
        self._setup_visuals_tab()

    def _setup_summaries_tab(self):
        self.tab_summaries.grid_columnconfigure((0, 1, 2), weight=1)
        self.sum_cards = {}
        configs = [("Daily Status (Today)", "day"), ("Monthly Status (Selected)", "month"), ("Yearly Status (Current)", "year")]
        for i, (title, key) in enumerate(configs):
            card = ctk.CTkFrame(self.tab_summaries, fg_color=("white", "#1e1e1e"), border_width=1, border_color="gray80")
            card.grid(row=0, column=i, padx=10, pady=20, sticky="nsew")
            ctk.CTkLabel(card, text=title.upper(), font=("Segoe UI", 12, "bold"), text_color="gray50").pack(pady=(15, 5))
            lbl = ctk.CTkLabel(card, text="Fetching...", font=("Consolas", 15), justify="left")
            lbl.pack(pady=20)
            self.sum_cards[key] = lbl

    def _setup_visuals_tab(self):
        """Thiết kế tab chứa các biểu đồ trực quan."""
        # Frame chứa các nút chọn loại biểu đồ
        btn_frame = ctk.CTkFrame(self.tab_visuals, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 15))

        self.chart_configs = [
            ("📊 Income vs Expenses", "bar"),
            ("🥧 Spending by Category", "pie"),
            ("📈 Balance Trend", "line"),
        ]
        self._chart_btns = {}

        for label, chart_type in self.chart_configs:
            btn = ctk.CTkButton(
                btn_frame, text=label, width=200, height=40,
                font=("Segoe UI", 13, "bold"),
                fg_color=("#dbdbdb", "#2d2d2d"),
                text_color=("black", "white"),
                hover_color=COLOR_NEUTRAL,
                command=lambda ct=chart_type: self._show_chart(ct)
            )
            btn.pack(side="left", padx=8)
            self._chart_btns[chart_type] = btn

        # Khu vực hiển thị biểu đồ
        self.chart_frame = ctk.CTkFrame(self.tab_visuals, fg_color=("white", "#1e1e1e"), 
                                        border_width=1, border_color="gray80")
        self.chart_frame.pack(fill="both", expand=True)

        self.placeholder = ctk.CTkLabel(self.chart_frame, text="Select an analysis type above",
                                        font=("Segoe UI", 15), text_color="gray")
        self.placeholder.pack(expand=True)

    def refresh(self):        
        uid = self.app.get_user_id()
        month_str = self.app.get_month()
        year = month_str.split("-")[0]

        # 1. Lấy dữ liệu (Dùng đúng tên hàm execute_query)
        daily = models.get_daily_summary(uid)
        yearly = models.get_yearly_summary(uid, year)
        m_inc = models.execute_query("SELECT fn_get_total_income(%s, %s) as val", (uid, month_str), fetch=True)
        m_exp = models.execute_query("SELECT fn_get_total_expenses(%s, %s) as val", (uid, month_str), fetch=True)

        def fmt(inc, exp):
            inc, exp = float(inc or 0), float(exp or 0)
            return (f"🟢 INCOME:  {inc:14,.0f} ₫\n"
                    f"🔴 EXPENSE: {exp:14,.0f} ₫\n"
                    f"──────────────────────────\n"
                    f"⚖️ NET:     {(inc-exp):14,.0f} ₫")

        # 2. ÉP GIAO DIỆN CẬP NHẬT (Không dùng IF để tránh đứng hình)
        # Ô Daily
        d_in = daily.get('day_in', 0) if daily else 0
        d_out = daily.get('day_out', 0) if daily else 0
        self.sum_cards["day"].configure(text=fmt(d_in, d_out))
        
        # Ô Monthly
        mi = m_inc['val'] if m_inc else 0
        me = m_exp['val'] if m_exp else 0
        self.sum_cards["month"].configure(text=fmt(mi, me))

        # Ô Yearly
        yi = yearly.get('yr_in', 0) if yearly else 0
        yo = yearly.get('yr_out', 0) if yearly else 0
        self.sum_cards["year"].configure(text=fmt(yi, yo))

        # Update chart
        if self._active_chart:
            print(f"[REPORTS] Redrawing active chart: {self._active_chart} for {month_str}")
            self._show_chart(self._active_chart)
            
        # Ép toàn bộ màn hình vẽ lại ngay lập tức
        self.update_idletasks()
    
    def _show_chart(self, chart_type):
        """Logic vẽ biểu đồ (giữ nguyên logic tooltip và phóng to chữ của bạn)."""
        self._active_chart = chart_type
        uid = self.app.get_user_id()
        month = self.app.get_month()

        # Highlight button
        for ct, btn in self._chart_btns.items():
            btn.configure(fg_color=COLOR_NEUTRAL if ct == chart_type else ("#dbdbdb", "#2d2d2d"),
                          text_color="white" if ct == chart_type else ("black", "white"))

        # Xóa canvas cũ
        for child in self.chart_frame.winfo_children():
            child.destroy()
        # self.update_idletasks()

        try:
            # figure from reports.py
            if chart_type == "bar": fig = reports.create_income_expense_chart(uid)
            elif chart_type == "pie": fig = reports.create_category_pie_chart(uid, month)
            else: fig = reports.create_balance_trend_chart(uid)

            face_color = "#ffffff" if ctk.get_appearance_mode() == "Light" else "#1e1e1e"
            fig.patch.set_facecolor(face_color)

            canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            canvas.draw()
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.pack(fill="both", expand=True, padx=20, pady=20)
            self._current_canvas = canvas

            # --- LOGIC DI CHUỘT (TOOLTIP) ---
            ax = fig.gca()
            annot = ax.annotate("", xy=(0,0), xytext=(20,20), textcoords="offset points",
                    bbox=dict(boxstyle="round,pad=0.5", fc="white", ec=COLOR_NEUTRAL, alpha=0.9, lw=2),
                    arrowprops=dict(arrowstyle="->", color=COLOR_NEUTRAL),
                    fontsize=16,
                    fontweight='bold',
                    color="black")
            annot.set_visible(False)

            def update_annot(artist, label, x, y):
                annot.xy = (x, y)
                annot.set_text(label)
                annot.get_bbox_patch().set_alpha(0.9)

            def hover(event):
                vis = annot.get_visible()
                if event.inaxes == ax:
                    # A. Xử lý cho Bar Chart (Cột)
                    for container in ax.containers:
                        for bar in container:
                            cont, ind = bar.contains(event)
                            if cont:
                                x = bar.get_x() + bar.get_width() / 2
                                y = bar.get_height()
                                update_annot(bar, f"{container.get_label()}: {y:,.0f} ₫", x, y)
                                annot.set_visible(True)
                                fig.canvas.draw_idle()
                                return

                    # B. Xử lý cho Pie Chart (Miếng bánh)
                    # Tìm các đối tượng Wedge trong biểu đồ
                    wedges = [c for c in ax.patches if isinstance(c, matplotlib.patches.Wedge)]
                    if wedges:
                        for i, wedge in enumerate(wedges):
                            cont, ind = wedge.contains(event)
                            if cont:
                                # Lấy label từ legend nếu có
                                try:
                                    label = ax.get_legend().get_texts()[i].get_text()
                                except:
                                    label = "Category Detail"
                                annot.xy = (event.xdata, event.ydata)
                                annot.set_text(label)
                                annot.set_visible(True)
                                fig.canvas.draw_idle()
                                return

                    # C. Xử lý cho Line Chart (Điểm mốc)
                    for line in ax.get_lines():
                        cont, ind = line.contains(event)
                        if cont:
                            idx = ind['ind'][0]
                            x_data, y_data = line.get_data()
                            x, y = x_data[idx], y_data[idx]
                            update_annot(line, f"Balance: {y:,.0f} ₫", x, y)
                            annot.set_visible(True)
                            fig.canvas.draw_idle()
                            return

                # Nếu chuột không chạm vào gì, ẩn tooltip
                if vis:
                    annot.set_visible(False)
                    fig.canvas.draw_idle()

            # Kết nối sự kiện di chuột
            fig.canvas.mpl_connect("motion_notify_event", hover)
            
            # Ép vẽ lại toàn bộ sau khi hoàn tất
            #self.update_idletasks()
            self.chart_frame.update()
        
        except Exception as e:
            print(f"[ERROR] Chart failed: {e}")
            self.placeholder = ctk.CTkLabel(self.chart_frame, text=f"Error: {e}", font=FONT_BODY)
            self.placeholder.pack(expand=True)

# ============================================================
# SCREEN 4: BUDGETS
# ============================================================

class BudgetsScreen(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text="Budget Management", font=FONT_TITLE,
                     text_color=COLOR_NEUTRAL).grid(
            row=0, column=0, sticky="w", pady=(0, 15))

        # Set budget form
        form = ctk.CTkFrame(self, fg_color=("white", "#2b2b2b"), border_width=1, border_color="gray80")
        form.grid(row=1, column=0, sticky="ew", padx=2, pady=(0, 20))
        
        ctk.CTkLabel(form, text="🎯 Set Category Monthly Limit", 
                     font=("Segoe UI", 14, "bold"), text_color=("#333333", "white")).grid(
            row=0, column=0, columnspan=5, sticky="w", padx=20, pady=(15, 10))

        # Category Menu
        ctk.CTkLabel(form, text="Category:", font=("Segoe UI", 12, "bold")).grid(row=1, column=0, padx=(20, 5), pady=20)
        self.budget_cat_menu = ctk.CTkOptionMenu(
            form, width=240, height=38,
            fg_color=("#3498db", "#1f538d"),
            button_color=("#2980b9", "#1a457a"),
            text_color="white"
        )
        self.budget_cat_menu.set("Choose Category") 
        self.budget_cat_menu.grid(row=1, column=1, padx=5)

        # Amount Entry
        ctk.CTkLabel(form, text="Limit (VND):", font=("Segoe UI", 12, "bold")).grid(row=1, column=2, padx=(25, 5))
        self.budget_amount_entry = ctk.CTkEntry(form, width=220, height=38, border_color="gray70", 
                                                justify="center", font=("Consolas", 14))
        self.budget_amount_entry.grid(row=1, column=3, padx=5)

        # Save Button
        ctk.CTkButton(form, text="💾 Save Budget", font=("Segoe UI", 13, "bold"),
                      command=self._save_budget, width=180, height=42,
                      fg_color=COLOR_INCOME, hover_color="#27ae60").grid(row=1, column=4, padx=(30, 20), pady=20)
        
        # Budget status table
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.grid(row=2, column=0, sticky="nsew", padx=2, pady=5)
        status_frame.grid_rowconfigure(1, weight=1)
        status_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(status_frame, text="Budget Status This Month",
                     font=FONT_HEADING).grid(row=0, column=0, sticky="w", padx=5, pady=(10, 10))

        style = ttk.Style()
        style.theme_use("clam")
        bg_color = "#fdfdfd" if ctk.get_appearance_mode() == "Light" else "#2b2b2b"
        fg_color = "black" if ctk.get_appearance_mode() == "Light" else "white"
        
        style.configure("Budget.Treeview", 
                        background=bg_color, 
                        foreground=fg_color,
                        fieldbackground=bg_color, 
                        rowheight=60, 
                        font=("Segoe UI", 18))
        style.configure("Budget.Treeview.Heading", 
                        background="#eeeeee" if bg_color=="#fdfdfd" else "#1a1a1a", 
                        foreground=fg_color, 
                        font=("Segoe UI", 18, "bold"))

        cols = ("Category", "Limit", "Spent", "Remaining", "Usage %", "Status", "Delete")
        self.budget_tree = ttk.Treeview(status_frame, columns=cols,
                                        show="headings", style="Budget.Treeview", height=10)
        for col in cols:
            self.budget_tree.heading(col, text=col)
            width = 60 if col == "Delete" else 240
            self.budget_tree.column(col, width=width, anchor="center")
        
        self.budget_tree.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.budget_tree.bind("<ButtonRelease-1>", self._on_tree_click)

        # Scrollbar
        scrollbar = ctk.CTkScrollbar(status_frame, orientation="vertical", command=self.budget_tree.yview, width=12)
        self.budget_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 10))

        self.budget_tree.tag_configure("ok",       foreground="#2ecc71")
        self.budget_tree.tag_configure("warning",  foreground="#f39c12")
        self.budget_tree.tag_configure("exceeded", foreground="#e74c3c")

    def refresh(self):
        uid   = self.app.get_user_id()
        month = self.app.get_month()

        # Update categories
        categories = models.get_categories()
        cat_opts   = [c['CategoryName'] for c in categories]
        self._cat_map = {c['CategoryName']: c['CategoryID'] for c in categories}
        if cat_opts:
            self.budget_cat_menu.configure(values=cat_opts)

        # Clear & Reload table
        for row in self.budget_tree.get_children():
            self.budget_tree.delete(row)

        budgets = models.get_budget_status(uid, month)

        for i, b in enumerate(budgets):
            try:
                # --- CÁCH LẤY ID THÔNG MINH ---
                # Thử tìm theo nhiều tên khác nhau, nếu không thấy thì dùng tạm chỉ số i
                cat_id = b.get('CategoryID') or b.get('category_id') or b.get('cat_id') or i
                
                cat_name = b.get('CategoryName') or b.get('category_name') or "Unknown"
                
                # Lấy số liệu (thử cả tên cũ và tên mới Ngân hay dùng)
                limit  = float(b.get('LimitAmount') or b.get('BudgetAmount') or 0)
                spent  = float(b.get('SpentAmount') or b.get('TotalSpent') or 0)
                remain = float(b.get('RemainingAmount') or (limit - spent))
                
                # Tính % sử dụng
                percent = float(b.get('UsagePercent') or (spent/limit*100 if limit > 0 else 0))
                
                # Xác định Status và Tag màu
                status_raw = b.get('BudgetStatus') or b.get('Status') or 'OK'
                status_str = str(status_raw).upper()
                tag = status_str.lower()

                # CHÈN VÀO BẢNG
                self.budget_tree.insert("", "end", iid=f"bud_{cat_id}", tags=(tag,), values=(
                    cat_name,
                    f"{limit:,.0f} ₫",
                    f"{spent:,.0f} ₫",
                    f"{remain:,.0f} ₫",
                    f"{percent:.1f}%",
                    status_str,
                    "🗑️"
                ))
            except Exception as e:
                print(f"[DEBUG] Lỗi ở dòng {i}: {e}")
                continue 
        
        self.update_idletasks()

    def _save_budget(self):
        uid   = self.app.get_user_id()
        month = self.app.get_month()
        try:
            cat_name = self.budget_cat_menu.get()
            if cat_name == "Choose Category": raise KeyError("Category")
            
            cat_id     = self._cat_map[cat_name]
            amount_str = self.budget_amount_entry.get().replace(',', '').replace('.', '')
            amount     = float(amount_str)

            if models.set_budget(uid, cat_id, month, amount):
                messagebox.showinfo("Success", f"Budget for '{cat_name}' successfully updated to {amount:,.0f} ₫.")
                self.refresh()
                self.app.screens["dashboard"].refresh() # Cập nhật luôn cảnh báo ở Dashboard
                self.budget_amount_entry.delete(0, 'end')
            else:
                messagebox.showerror("Database Error", "Failed to save budget settings.")
        except Exception:
            messagebox.showwarning("Input Error", "Please select a category and enter a valid numeric limit.")

    def _on_tree_click(self, event):
        """Xử lý khi người dùng nhấn vào biểu tượng thùng rác trên dòng."""
        region = self.budget_tree.identify_region(event.x, event.y)
        if region == "cell":
            # Xác định cột nào bị nhấn
            column = self.budget_tree.identify_column(event.x)
            if column == "#7": # cột 7
                item_id = self.budget_tree.identify_row(event.y)
                if item_id:
                    self._handle_delete_action(item_id)

    def _handle_delete_action(self, item_id):
        """Xử lý xóa ngân sách với dòng kiểm tra dữ liệu."""
        try:
            # 1. Lấy thông tin
            cat_id = item_id.split("_")[1]
            cat_name = self.budget_tree.item(item_id)['values'][0]
            month = self.app.get_month() # Ví dụ: "2026-05"
            uid = self.app.get_user_id()

            # DÒNG NÀY ĐỂ KIỂM TRA TRÊN TERMINAL
            print(f"\n[DEBUG DELETE] Attempting to delete Budget:")
            print(f" > UserID: {uid} | CatID: {cat_id} | Month: {month}")

            if messagebox.askyesno("Confirm Delete", f"Remove budget for '{cat_name}' in {month}?"):
                # 2. Gọi hàm xóa và kiểm tra kết quả trả về
                success = models.delete_budget(uid, cat_id, month)
                
                if success:
                    print("[DEBUG DELETE] Success: Record removed from DB.")
                    messagebox.showinfo("Success", "Budget record deleted.")
                    self.refresh()
                    self.app.screens["dashboard"].refresh()
                else:
                    print("[DEBUG DELETE] Failed: No row found in DB to delete.")
                    messagebox.showerror("Error", "Could not delete. The record may have changed.")
        except Exception as e:
            print(f"[DEBUG DELETE] System Error: {e}")

# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == '__main__':
    # Verify DB connection before launching UI
    if not test_connection():
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Database Error",
            "Cannot connect to MySQL.\n\n"
            "Please check:\n"
            "1. MySQL service is running\n"
            "2. Credentials in db_connection.py are correct\n"
            "3. Database 'personal_finance' exists"
        )
        root.destroy()
    else:
        app = FinanceApp()
        app.mainloop()