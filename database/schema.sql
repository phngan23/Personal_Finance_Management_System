-- Drop database if exists and recreate (for clean setup)
DROP DATABASE IF EXISTS personal_finance;
CREATE DATABASE personal_finance
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE personal_finance;

-- ============================================================
-- TABLE 1: Users
-- Stores core user profile information
-- ============================================================
CREATE TABLE Users (
    UserID      INT             AUTO_INCREMENT PRIMARY KEY,
    UserName    VARCHAR(100)    NOT NULL,
    Email       VARCHAR(150)    NOT NULL UNIQUE,
    PhoneNumber VARCHAR(15),
    CreatedAt   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_email CHECK (Email LIKE '%@%.%')
);

-- ============================================================
-- TABLE 2: BankAccounts
-- Each user can have multiple bank accounts.
-- Balance is updated automatically by Triggers (see objects.sql).
-- ============================================================
CREATE TABLE BankAccounts (
    AccountID   INT             AUTO_INCREMENT PRIMARY KEY,
    UserID      INT             NOT NULL,
    BankName    VARCHAR(100)    NOT NULL,
    Balance     DECIMAL(15, 2)  NOT NULL DEFAULT 0.00,
    CreatedAt   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_bankaccount_user
        FOREIGN KEY (UserID) REFERENCES Users(UserID)
        ON DELETE CASCADE,

    -- Balance must never go negative (business rule)
    CONSTRAINT chk_balance CHECK (Balance >= 0)
);

-- ============================================================
-- TABLE 3: ExpenseCategories
-- Master list of spending categories (Food, Transport, etc.)
-- Kept separate so we can add categories without touching other tables.
-- ============================================================
CREATE TABLE ExpenseCategories (
    CategoryID      INT             AUTO_INCREMENT PRIMARY KEY,
    CategoryName    VARCHAR(100)    NOT NULL UNIQUE,
    Description     VARCHAR(255)
);

-- ============================================================
-- TABLE 4: Income
-- Records every income transaction for a user.
-- AccountID links which bank account received the money —
-- the Trigger on this table will UPDATE BankAccounts.Balance.
-- ============================================================
CREATE TABLE Income (
    IncomeID        INT             AUTO_INCREMENT PRIMARY KEY,
    UserID          INT             NOT NULL,
    AccountID       INT             NOT NULL,
    Amount          DECIMAL(15, 2)  NOT NULL,
    IncomeDate      DATE            NOT NULL,
    Description     VARCHAR(255),

    CONSTRAINT fk_income_user
        FOREIGN KEY (UserID) REFERENCES Users(UserID)
        ON DELETE CASCADE,
    CONSTRAINT fk_income_account
        FOREIGN KEY (AccountID) REFERENCES BankAccounts(AccountID),
    CONSTRAINT chk_income_amount CHECK (Amount > 0)
);

-- ============================================================
-- TABLE 5: Expenses
-- Records every expense transaction.
-- CategoryID classifies the spending type.
-- AccountID tells which account money was deducted from.
-- ============================================================
CREATE TABLE Expenses (
    ExpenseID       INT             AUTO_INCREMENT PRIMARY KEY,
    UserID          INT             NOT NULL,
    CategoryID      INT             NOT NULL,
    AccountID       INT             NOT NULL,
    Amount          DECIMAL(15, 2)  NOT NULL,
    ExpenseDate     DATE            NOT NULL,
    Description     VARCHAR(255),

    CONSTRAINT fk_expense_user
        FOREIGN KEY (UserID) REFERENCES Users(UserID)
        ON DELETE CASCADE,
    CONSTRAINT fk_expense_category
        FOREIGN KEY (CategoryID) REFERENCES ExpenseCategories(CategoryID),
    CONSTRAINT fk_expense_account
        FOREIGN KEY (AccountID) REFERENCES BankAccounts(AccountID),
    CONSTRAINT chk_expense_amount CHECK (Amount > 0)
);

-- ============================================================
-- TABLE 6: Budgets
-- Monthly spending limits per category per user.
-- MonthYear stored as VARCHAR 'YYYY-MM' for easy filtering.
-- ============================================================
CREATE TABLE Budgets (
    BudgetID        INT             AUTO_INCREMENT PRIMARY KEY,
    UserID          INT             NOT NULL,
    CategoryID      INT             NOT NULL,
    MonthYear       CHAR(7)         NOT NULL,   -- Format: 'YYYY-MM'
    LimitAmount     DECIMAL(15, 2)  NOT NULL,
    CreatedAt       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_budget_user
        FOREIGN KEY (UserID) REFERENCES Users(UserID)
        ON DELETE CASCADE,
    CONSTRAINT fk_budget_category
        FOREIGN KEY (CategoryID) REFERENCES ExpenseCategories(CategoryID),
    CONSTRAINT chk_budget_amount CHECK (LimitAmount > 0),

    -- One budget per user per category per month
    UNIQUE KEY uq_budget (UserID, CategoryID, MonthYear)
);