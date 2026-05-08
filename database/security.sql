-- ============================================================
-- FILE: security.sql
-- PURPOSE: Create restricted DB user, grant minimal permissions
-- PRINCIPLE: Principle of Least Privilege - app user cannot DROP tables
-- ============================================================

USE personal_finance;

-- ------------------------------------------------------------
-- 1. USER MANAGEMENT
-- Remove existing application user if it already exists to avoid errors.
-- ------------------------------------------------------------
DROP USER IF EXISTS 'finance_app'@'localhost';

-- ------------------------------------------------------------
-- 2. CREATE RESTRICTED USER
-- Create a new user for the Python application with a secure password.
-- ------------------------------------------------------------
CREATE USER 'finance_app'@'localhost' IDENTIFIED BY 'FinApp@2025!';

-- ------------------------------------------------------------
-- 3. DATA RETRIEVAL PERMISSIONS
-- Grant SELECT access on all tables and Views for reporting purposes.
-- This allows the app to query financial summaries and transaction history.
-- ------------------------------------------------------------
GRANT SELECT ON personal_finance.* TO 'finance_app'@'localhost';

-- ------------------------------------------------------------
-- 4. PROCEDURAL PERMISSIONS
-- Grant EXECUTE permission to allow the user to run Stored Procedures 
-- and User Defined Functions (UDFs) for financial logic.
-- ------------------------------------------------------------
GRANT EXECUTE ON personal_finance.* TO 'finance_app'@'localhost';

-- ------------------------------------------------------------
-- 5. TRANSACTIONAL PERMISSIONS
-- Grant INSERT, UPDATE, and DELETE on transactional tables.
-- Users must be able to manage their own income and expense records[cite: 2].
-- ------------------------------------------------------------
GRANT INSERT, UPDATE, DELETE ON personal_finance.Income TO 'finance_app'@'localhost';
GRANT INSERT, UPDATE, DELETE ON personal_finance.Expenses TO 'finance_app'@'localhost';

-- ------------------------------------------------------------
-- 6. MANAGEMENT PERMISSIONS
-- Grant INSERT, UPDATE, and DELETE for managing budget settings.
-- DELETE is strictly required to allow users to remove set limits.
-- Grant INSERT and UPDATE for user profiles and categories.
-- ------------------------------------------------------------
GRANT INSERT, UPDATE, DELETE ON personal_finance.Budgets TO 'finance_app'@'localhost';
GRANT INSERT, UPDATE ON personal_finance.Users TO 'finance_app'@'localhost';
GRANT INSERT ON personal_finance.ExpenseCategories TO 'finance_app'@'localhost';

-- ------------------------------------------------------------
-- 7. BANK ACCOUNT PERMISSIONS
-- Allow the app to create new accounts (INSERT).
-- CRITICAL: We DO NOT grant UPDATE on the 'Balance' column.
-- This ensures Balance can only be changed by DATABASE TRIGGERS.
-- ------------------------------------------------------------
GRANT INSERT ON personal_finance.BankAccounts TO 'finance_app'@'localhost';

-- ------------------------------------------------------------
-- 8. APPLY AND VERIFY
-- Finalize privileges and display them for confirmation.
-- ------------------------------------------------------------
FLUSH PRIVILEGES;

-- Verification query to be included in the project report
SHOW GRANTS FOR 'finance_app'@'localhost';

-- ============================================================
-- DATABASE ADMINISTRATION: BACKUP & RECOVERY
-- Run these commands in the terminal (Command Prompt/PowerShell), NOT in MySQL.
-- ============================================================

-- BACKUP COMMAND:
-- Includes Triggers, Routines, and full schema[cite: 2].
-- mysqldump -u root -p --routines --triggers personal_finance > pf_full_backup.sql

-- RESTORE COMMAND:
-- mysql -u root -p personal_finance < pf_full_backup.sql
-- ============================================================