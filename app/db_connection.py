# ============================================================
# FILE: app/db_connection.py
# PURPOSE: Centralized database connection module
# All other modules import get_connection() from here.
# Using a single connection factory ensures consistent config.
# ============================================================

import mysql.connector
from mysql.connector import Error

# --- Database configuration ---
# In production, these would come from environment variables
# or a config file that is NOT committed to git
DB_CONFIG = {
    'host':     'localhost',
    'port':     3306,
    'database': 'personal_finance',
    'user':     'finance_app',       # restricted user from security.sql
    'password': 'FinApp@2025!',
    'charset':  'utf8mb4',
    'autocommit': False,              # we handle commits manually
}


def get_connection():
    """
    Create and return a new MySQL connection.

    Returns:
        mysql.connector.connection.MySQLConnection | None

    Why return None instead of raising?
    → The UI layer can then show a user-friendly error dialog
      rather than crashing with a stack trace.
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"[DB ERROR] Could not connect to MySQL: {e}")
        return None


def test_connection():
    """Quick connectivity test — call this on app startup."""
    conn = get_connection()
    if conn:
        print("[DB] Connection successful.")
        conn.close()
        return True
    else:
        print("[DB] Connection FAILED. Check MySQL is running and credentials.")
        return False


if __name__ == '__main__':
    test_connection()