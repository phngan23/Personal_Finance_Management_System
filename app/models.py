# ============================================================
# FILE: app/models.py
# PURPOSE: All database CRUD operations for the app
# DESIGN PRINCIPLE: UI layer NEVER writes SQL directly.
#   It only calls functions from this file.
#   This separates concerns and makes testing easier.
# ============================================================

from db_connection import get_connection
from mysql.connector import Error


# ============================================================
# HELPER FUNCTION
# ============================================================

def execute_query(query, params=None, fetch=False, many=False):
    """
    Internal helper to run any query safely.

    Args:
        query  : SQL string (use %s placeholders, never f-strings)
        params : tuple of values to bind (prevents SQL injection)
        fetch  : True → return rows; False → return affected row count
        many   : True → return all rows; False → return first row only

    Why parameterized queries?
    → If user types: name = "'; DROP TABLE Users; --"
      With f-string: executes DROP TABLE!
      With %s param: treated as literal string, safe.
    """
    conn = get_connection()
    if not conn:
        return None

    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(query, params or ())

            if fetch:
                result = cursor.fetchall() if many else cursor.fetchone()
            else:
                conn.commit()
                result = cursor.rowcount  # number of affected rows

            return result

    except Error as e:
        if conn:
            conn.rollback()
        raise e

    finally:
        if conn:
            conn.close()

import hashlib

def hash_password(password):
    """Băm mật khẩu bằng thuật toán SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


# ============================================================
# USER FUNCTIONS
# ============================================================

def get_all_users():
    """Return list of all users for dropdown menus."""
    return execute_query(
        "SELECT UserID, UserName, Email FROM Users ORDER BY UserName",
        fetch=True, many=True
    ) or []


def get_user_by_id(user_id):
    """Return a single user dict."""
    return execute_query(
        "SELECT * FROM Users WHERE UserID = %s",
        (user_id,), fetch=True
    )


def create_user(username, email, password, phone):
    """
    Insert a new user. Returns the new UserID or None on failure.
    """
    pwd_hash = hash_password(password)
    query = "INSERT INTO Users (UserName, Email, PasswordHash, PhoneNumber) VALUES (%s, %s, %s, %s)"
    return execute_query(query, (username, email, pwd_hash, phone))

def update_user_profile(user_id, name, email, phone, password=None):
    """Cập nhật thông tin hồ sơ người dùng."""
    if password:
        # Nếu đổi cả mật khẩu
        pwd_hash = hash_password(password)
        query = "UPDATE Users SET UserName=%s, Email=%s, PhoneNumber=%s, PasswordHash=%s WHERE UserID=%s"
        return execute_query(query, (name, email, phone, pwd_hash, user_id))
    else:
        # Chỉ đổi thông tin cơ bản
        query = "UPDATE Users SET UserName=%s, Email=%s, PhoneNumber=%s WHERE UserID=%s"
        return execute_query(query, (name, email, phone, user_id))

def verify_user(user_id, input_password):
    """Compare a plain-text input against the stored SHA-256 hash."""
    query = "SELECT PasswordHash FROM Users WHERE UserID = %s"
    result = execute_query(query, (user_id,), fetch=True)
    
    if result and len(result) > 0:
        stored_hash = result.get('PasswordHash')
        return stored_hash == hash_password(input_password)
    return False

def change_password(user_id, old_password, new_password):
    """
    Three-step validation:
    1. Verify old password is correct.
    2. Ensure new password differs from old.
    3. Hash and persist the new password.
    """
    if not verify_user(user_id, old_password):
        return False, "Old password is incorrect!"
    
    if old_password == new_password:
        return False, "New password must be different from the old one!"
    
    pwd_hash = hash_password(new_password)
    query = "UPDATE Users SET PasswordHash=%s WHERE UserID=%s"
    success = execute_query(query, (pwd_hash, user_id))
    
    if success:
        return True, "Password changed successfully!"
    return False, "Database error occurred."


# ============================================================
# BANK ACCOUNT FUNCTIONS
# ============================================================

def get_accounts_by_user(user_id):
    """Return all bank accounts for a user."""
    return execute_query(
        """SELECT AccountID, BankName,
                  FORMAT(Balance, 0) AS BalanceFormatted,
                  Balance
           FROM BankAccounts
           WHERE UserID = %s
           ORDER BY BankName""",
        (user_id,), fetch=True, many=True
    ) or []


def get_total_balance(user_id):
    """Sum of all account balances for a user."""
    result = execute_query(
        "SELECT SUM(Balance) AS Total FROM BankAccounts WHERE UserID = %s",
        (user_id,), fetch=True
    )
    return float(result['Total'] or 0) if result else 0.0


def create_account(user_id, bank_name, initial_balance=0):
    """
    Add a new bank account and return its ID.
    Suggest using custom logic like create_user if you need the ID.
    """
    conn = get_connection()
    if not conn: return None
    try:
        with conn.cursor() as cursor:
            query = "INSERT INTO BankAccounts (UserID, BankName, Balance) VALUES (%s, %s, %s)"
            cursor.execute(query, (user_id, bank_name, initial_balance))
            conn.commit()
            #return cursor.lastrowid
            return True
    except Error as e:
        conn.rollback()
        print(f"[CREATE ACCOUNT ERROR] {e}")
        return False
    finally:
        conn.close()

# ============================================================
# INCOME FUNCTIONS
# ============================================================

def add_income(user_id, account_id, amount, income_date, description):
    """
    Insert an income record.
    The Trigger (trg_income_after_insert) will automatically
    update BankAccounts.Balance — we don't need to do it here.
    """
    return execute_query(
        """INSERT INTO Income (UserID, AccountID, Amount, IncomeDate, Description)
           VALUES (%s, %s, %s, %s, %s)""",
        (user_id, account_id, amount, income_date, description)
    )


def get_income_by_user_month(user_id, month_year):
    """
    Return all income records for a user in a given month.
    month_year format: 'YYYY-MM'
    """
    return execute_query(
        """SELECT i.IncomeID, i.Amount, i.IncomeDate,
                  i.Description, b.BankName
           FROM Income i
           JOIN BankAccounts b ON i.AccountID = b.AccountID
           WHERE i.UserID = %s
             AND DATE_FORMAT(i.IncomeDate, '%Y-%m') = %s
           ORDER BY i.IncomeDate DESC""",
        (user_id, month_year), fetch=True, many=True
    ) or []

def delete_income(income_id):
    query = "DELETE FROM Income WHERE IncomeID = %s"
    return execute_query(query, (income_id,))

def update_income(income_id, account_id, amount, date, description):
    """Cập nhật khoản thu nhập. Trigger sẽ tự động xử lý chênh lệch số dư."""
    query = """
        UPDATE Income 
        SET AccountID = %s, Amount = %s, IncomeDate = %s, Description = %s
        WHERE IncomeID = %s
    """
    return execute_query(query, (account_id, amount, date, description, income_id))


# ============================================================
# EXPENSE FUNCTIONS
# ============================================================

def add_expense(user_id, category_id, account_id, amount, expense_date, description):
    """
    Insert an expense record.
    The Trigger (trg_expense_after_insert) automatically deducts
    the amount from BankAccounts.Balance.
    """
    return execute_query(
        """INSERT INTO Expenses (UserID, CategoryID, AccountID, Amount, ExpenseDate, Description)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (user_id, category_id, account_id, amount, expense_date, description)
    )


def get_expenses_by_user_month(user_id, month_year):
    """Return all expenses for a user in a given month."""
    return execute_query(
        """SELECT e.ExpenseID, ec.CategoryName, e.Amount,
                  e.ExpenseDate, e.Description, b.BankName
           FROM Expenses e
           JOIN ExpenseCategories ec ON e.CategoryID = ec.CategoryID
           JOIN BankAccounts b       ON e.AccountID  = b.AccountID
           WHERE e.UserID = %s
             AND DATE_FORMAT(e.ExpenseDate, '%Y-%m') = %s
           ORDER BY e.ExpenseDate DESC""",
        (user_id, month_year), fetch=True, many=True
    ) or []


def get_categories():
    """Return all expense categories."""
    return execute_query(
        "SELECT CategoryID, CategoryName FROM ExpenseCategories ORDER BY CategoryName",
        fetch=True, many=True
    ) or []

def create_category(name, description=""):
    """Add new ExpenseCategory."""
    conn = get_connection()
    if not conn: return None
    try:
        with conn.cursor() as cursor:
            query = "INSERT INTO ExpenseCategories (CategoryName, Description) VALUES (%s, %s)"
            cursor.execute(query, (name, description))
            conn.commit()
            return cursor.lastrowid
    except Error as e:
        conn.rollback()
        print(f"[CREATE CATEGORY ERROR] {e}")
        return None
    finally:
        conn.close()

def update_expense(expense_id, category_id, account_id, amount, date, description):
    """Cập nhật khoản chi tiêu. Trigger sẽ tự động điều chỉnh số dư tài khoản."""
    query = """
        UPDATE Expenses 
        SET CategoryID = %s, AccountID = %s, Amount = %s, ExpenseDate = %s, Description = %s
        WHERE ExpenseID = %s
    """
    return execute_query(query, (category_id, account_id, amount, date, description, expense_id))

def delete_expense(expense_id):
    query = "DELETE FROM Expenses WHERE ExpenseID = %s"
    return execute_query(query, (expense_id,))


# ============================================================
# BUDGET FUNCTIONS
# ============================================================

def set_budget(user_id, category_id, month_year, limit_amount):
    """
    Create or update a budget.
    ON DUPLICATE KEY UPDATE handles the UNIQUE constraint
    on (UserID, CategoryID, MonthYear).
    """
    return execute_query(
        """INSERT INTO Budgets (UserID, CategoryID, MonthYear, LimitAmount)
           VALUES (%s, %s, %s, %s)
           ON DUPLICATE KEY UPDATE LimitAmount = VALUES(LimitAmount)""",
        (user_id, category_id, month_year, limit_amount)
    )


def get_budget_status(user_id, month_year):
    """
    Return budget status from the vw_budget_status View.
    This is the main data source for the Budgets screen.
    """
    return execute_query(
        """SELECT CategoryID, CategoryName, LimitAmount, SpentAmount,
                  RemainingAmount, UsagePercent, BudgetStatus
           FROM vw_budget_status
           WHERE UserID = %s AND MonthYear = %s
           ORDER BY UsagePercent DESC""",
        (user_id, month_year), fetch=True, many=True
    ) or []


def get_budget_alerts(user_id, month_year):
    """Return only budgets that are WARNING or EXCEEDED."""
    return execute_query(
        """SELECT CategoryName, UsagePercent, BudgetStatus,
                  SpentAmount, LimitAmount
           FROM vw_budget_status
           WHERE UserID = %s
             AND MonthYear = %s
             AND BudgetStatus IN ('WARNING', 'EXCEEDED')
           ORDER BY UsagePercent DESC""",
        (user_id, month_year), fetch=True, many=True
    ) or []

def delete_budget(user_id, category_id, month_year):
    """Delete budget"""
    query = "DELETE FROM Budgets WHERE UserID = %s AND CategoryID = %s AND MonthYear = %s"
    return execute_query(query, (user_id, category_id, month_year))

# ============================================================
# REPORT DATA FUNCTIONS (used by reports.py)
# ============================================================

def get_monthly_summary(user_id, months=6):
    """Sử dụng View đã tạo trong Database để code gọn hơn"""
    return execute_query(
        """SELECT MonthYear, TotalIncome, TotalExpenses, NetSavings 
           FROM vw_monthly_summary 
           WHERE UserID = %s 
           ORDER BY MonthYear DESC 
           LIMIT %s""",
        (user_id, months), fetch=True, many=True
    ) or []

def get_daily_summary(user_id):
    """Return today's total income and expenses."""
    query = """
        SELECT 
            (SELECT COALESCE(SUM(Amount), 0) FROM Income WHERE UserID=%s AND IncomeDate = CURDATE()) as day_in,
            (SELECT COALESCE(SUM(Amount), 0) FROM Expenses WHERE UserID=%s AND ExpenseDate = CURDATE()) as day_out
    """
    return execute_query(query, (user_id, user_id), fetch=True) 

def get_yearly_summary(user_id, year):
    """Return total income and expenses for a full year."""
    query = """
        SELECT 
            COALESCE(SUM(TotalIncome), 0) as yr_in, 
            COALESCE(SUM(TotalExpenses), 0) as yr_out 
        FROM vw_monthly_summary 
        WHERE UserID = %s AND MonthYear LIKE %s
    """
    return execute_query(query, (user_id, f"{year}-%"), fetch=True)


def get_category_spending(user_id, month_year):
    """Return category spending breakdown for pie chart."""
    return execute_query(
        """SELECT CategoryName, TotalSpent
           FROM vw_category_spending
           WHERE UserID = %s AND MonthYear = %s
           ORDER BY TotalSpent DESC""",
        (user_id, month_year), fetch=True, many=True
    ) or []


def get_balance_trend(user_id):
    """
    Calculate monthly net movement for trend charts.
    """
    query = """
        SELECT 
            MonthYear, 
            SUM(MonthlyNet) AS MonthlyNet
        FROM (
            SELECT DATE_FORMAT(IncomeDate, '%Y-%m') AS MonthYear, Amount AS MonthlyNet
            FROM Income WHERE UserID = %s
            UNION ALL
            SELECT DATE_FORMAT(ExpenseDate, '%Y-%m') AS MonthYear, -Amount AS MonthlyNet
            FROM Expenses WHERE UserID = %s
        ) AS trends
        GROUP BY MonthYear
        ORDER BY MonthYear ASC
    """
    # Sử dụng luôn hàm helper để quản lý kết nối an toàn hơn
    return execute_query(query, (user_id, user_id), fetch=True, many=True) or []


def call_monthly_report_sp(user_id, month_year):
    """
    Call the stored procedure sp_monthly_report.
    Returns (summary_row, category_rows) tuple.
    """
    conn = get_connection()
    if not conn:
        return None, []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.callproc('sp_monthly_report', [user_id, month_year])

        results = []
        for result in cursor.stored_results():
            results.append(result.fetchall())

        summary = results[0][0] if results else {}
        categories = results[1] if len(results) > 1 else []
        return summary, categories

    except Error as e:
        print(f"[SP ERROR] {e}")
        return {}, []
    finally:
        cursor.close()
        conn.close()