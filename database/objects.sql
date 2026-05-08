-- ============================================================
-- FILE: objects.sql
-- PURPOSE: Advanced DB objects, run AFTER schema.sql + sample_data.sql
-- ORDER: Index → View → UDF → Stored Procedure → Trigger
-- ============================================================

USE personal_finance;

-- ============================================================
-- SECTION 1: INDEXES
-- Why: Speed up the most common queries in this app
-- ============================================================

-- Index 1: UserID + ExpenseDate on Expenses
-- Most queries filter "show me expenses for user X in month Y"
-- Composite index covers both conditions efficiently

CREATE INDEX idx_expenses_user_date
    ON Expenses(UserID, ExpenseDate);

-- Index 2: UserID + IncomeDate on Income
-- Same reasoning — monthly income lookups per user
CREATE INDEX idx_income_user_date
    ON Income(UserID, IncomeDate);

-- Index 3: UserID + CategoryID + MonthYear on Budgets
-- Budget checks always filter by all three columns
CREATE INDEX idx_budgets_user_cat_month
    ON Budgets(UserID, CategoryID, MonthYear);


-- ============================================================
-- SECTION 2: VIEWS
-- Why: Simplify complex JOINs into reusable named queries
-- ============================================================

-- VIEW 1: Monthly Financial Overview (Income vs Expenses)
-- Purpose: Provides a high-level summary of net savings per month.
-- Optimization: Aggregates data in subqueries first to prevent 
-- duplicate sums caused by joining multiple many-to-many records.
-- Python reports.py will query this view for bar charts
CREATE OR REPLACE VIEW vw_monthly_summary AS
SELECT 
    u.UserID,
    u.UserName,
    summary.MonthYear,
    summary.TotalIncome,
    summary.TotalExpenses,
    (summary.TotalIncome - summary.TotalExpenses) AS NetSavings
FROM Users u
JOIN (
    SELECT 
        COALESCE(inc.UserID, exp.UserID) AS UserID,
        COALESCE(inc.MonthYear, exp.MonthYear) AS MonthYear,
        COALESCE(inc.TotalIncome, 0) AS TotalIncome,
        COALESCE(exp.TotalExpenses, 0) AS TotalExpenses
    FROM (
        -- Aggregate Income by User and Month
        SELECT UserID, DATE_FORMAT(IncomeDate, '%Y-%m') AS MonthYear, SUM(Amount) AS TotalIncome 
        FROM Income GROUP BY UserID, MonthYear
    ) inc
    LEFT JOIN (
        -- Aggregate Expenses by User and Month
        SELECT UserID, DATE_FORMAT(ExpenseDate, '%Y-%m') AS MonthYear, SUM(Amount) AS TotalExpenses 
        FROM Expenses GROUP BY UserID, MonthYear
    ) exp ON inc.UserID = exp.UserID AND inc.MonthYear = exp.MonthYear
    
    UNION -- Ensure months with only expenses (and no income) are included
    
    SELECT 
        COALESCE(inc.UserID, exp.UserID) AS UserID,
        COALESCE(inc.MonthYear, exp.MonthYear) AS MonthYear,
        COALESCE(inc.TotalIncome, 0) AS TotalIncome,
        COALESCE(exp.TotalExpenses, 0) AS TotalExpenses
    FROM (
        SELECT UserID, DATE_FORMAT(IncomeDate, '%Y-%m') AS MonthYear, SUM(Amount) AS TotalIncome 
        FROM Income GROUP BY UserID, MonthYear
    ) inc
    RIGHT JOIN (
        SELECT UserID, DATE_FORMAT(ExpenseDate, '%Y-%m') AS MonthYear, SUM(Amount) AS TotalExpenses 
        FROM Expenses GROUP BY UserID, MonthYear
    ) exp ON inc.UserID = exp.UserID AND inc.MonthYear = exp.MonthYear
) summary ON u.UserID = summary.UserID;

-- View 2: Category-wise spending per user per month
-- Used for pie chart in reports
CREATE OR REPLACE VIEW vw_category_spending AS
SELECT
    e.UserID,
    u.UserName,
    ec.CategoryID,
    ec.CategoryName,
    DATE_FORMAT(e.ExpenseDate, '%Y-%m')     AS MonthYear,
    SUM(e.Amount)                           AS TotalSpent,
    COUNT(e.ExpenseID)                      AS TransactionCount
FROM Expenses e
JOIN Users u             ON e.UserID     = u.UserID
JOIN ExpenseCategories ec ON e.CategoryID = ec.CategoryID
GROUP BY e.UserID, u.UserName, ec.CategoryID, ec.CategoryName, MonthYear;

-- VIEW 3: Budget Performance Tracking
-- Purpose: Monitors budget compliance by comparing limits to actuals.
-- Labels: OK, WARNING (80%+ usage), EXCEEDED (100%+ usage).
CREATE OR REPLACE VIEW vw_budget_status AS
SELECT
    b.BudgetID,
    b.UserID,
    b.CategoryID,
    u.UserName,
    ec.CategoryName,
    b.MonthYear,
    b.LimitAmount,
    COALESCE(spent.TotalSpent, 0)              AS SpentAmount,
    b.LimitAmount - COALESCE(spent.TotalSpent, 0) AS RemainingAmount,
    ROUND(
        COALESCE(spent.TotalSpent, 0) / b.LimitAmount * 100, 2
    )                                       AS UsagePercent,
    CASE
        WHEN COALESCE(spent.TotalSpent, 0) >= b.LimitAmount THEN 'EXCEEDED'
        WHEN COALESCE(spent.TotalSpent, 0) >= b.LimitAmount * 0.8 THEN 'WARNING'
        ELSE 'OK'
    END                                     AS BudgetStatus
FROM Budgets b
JOIN Users u              ON b.UserID     = u.UserID
JOIN ExpenseCategories ec ON b.CategoryID = ec.CategoryID
LEFT JOIN (
    -- Subquery to get total spent per user/category/month
    SELECT UserID, CategoryID, DATE_FORMAT(ExpenseDate, '%Y-%m') AS MonthYear, SUM(Amount) AS TotalSpent
    FROM Expenses GROUP BY UserID, CategoryID, MonthYear
) spent ON b.UserID = spent.UserID AND b.CategoryID = spent.CategoryID AND b.MonthYear = spent.MonthYear;


-- ============================================================
-- SECTION 3: USER DEFINED FUNCTIONS (UDF)
-- Why: Reusable calculations callable inside SELECT statements
-- ============================================================

DROP FUNCTION IF EXISTS fn_get_total_income;
DROP FUNCTION IF EXISTS fn_get_total_expenses;
DROP FUNCTION IF EXISTS fn_get_budget_usage_percent;

DELIMITER $$

-- UDF 1: Calculate Total Monthly Income
-- Requirement: "Compute total income" 
-- Usage: SELECT fn_get_total_income(1, '2025-01');
CREATE FUNCTION fn_get_total_income(
    p_UserID    INT,
    p_MonthYear CHAR(7)
) 
RETURNS DECIMAL(15, 2)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_total DECIMAL(15, 2) DEFAULT 0.00;

    SELECT SUM(Amount) INTO v_total
    FROM Income
    WHERE UserID = p_UserID
      AND DATE_FORMAT(IncomeDate, '%Y-%m') = p_MonthYear;

    RETURN COALESCE(v_total, 0.00);
END$$

-- UDF 2: Calculate total expenses for a user in a given month
-- Usage: SELECT fn_total_expenses(1, '2025-01') → returns DECIMAL
CREATE FUNCTION fn_get_total_expenses(
    p_UserID    INT,
    p_MonthYear CHAR(7)         -- Format: 'YYYY-MM'
)
RETURNS DECIMAL(15, 2)
READS SQL DATA               -- declares it only reads, doesn't modify
DETERMINISTIC
BEGIN
    DECLARE v_total DECIMAL(15, 2) DEFAULT 0.00;

    SELECT COALESCE(SUM(Amount), 0)
    INTO   v_total
    FROM   Expenses
    WHERE  UserID = p_UserID
      AND  DATE_FORMAT(ExpenseDate, '%Y-%m') = p_MonthYear;

    RETURN v_total;
END$$

-- UDF 3: Calculate budget usage percentage for a specific budget
-- Usage: SELECT fn_budget_usage_percent(1, 2, '2025-01')
-- Returns 0–100+ (can exceed 100 if over budget)
CREATE FUNCTION fn_get_budget_usage_percent(
    p_UserID        INT,
    p_CategoryID    INT,
    p_MonthYear     CHAR(7)
)
RETURNS DECIMAL(5, 2)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE v_spent     DECIMAL(15, 2) DEFAULT 0.00;
    DECLARE v_limit     DECIMAL(15, 2) DEFAULT 0.00;
    DECLARE v_start_date DATE;
    SET v_start_date = STR_TO_DATE(CONCAT(p_MonthYear, '-01'), '%Y-%m-%d');

    -- Get actual spending this month in this category
    SELECT COALESCE(SUM(Amount), 0)
    INTO   v_spent
    FROM   Expenses
    WHERE  UserID     = p_UserID
        AND  CategoryID = p_CategoryID
        AND  ExpenseDate >= v_start_date 
        AND  ExpenseDate <  DATE_ADD(v_start_date, INTERVAL 1 MONTH);

    -- Get the budget limit
    SELECT COALESCE(LimitAmount, 0)
    INTO   v_limit
    FROM   Budgets
    WHERE  UserID     = p_UserID
        AND  CategoryID = p_CategoryID
        AND  MonthYear  = p_MonthYear
    LIMIT 1;

    -- Avoid division by zero
    IF v_limit = 0 THEN
        RETURN 0.00;
    END IF;

    RETURN ROUND((v_spent / v_limit) * 100, 2);
END$$

DELIMITER ;


-- ============================================================
-- SECTION 4: STORED PROCEDURES
-- Why: Encapsulate business logic in DB; Python just calls SP name
-- ============================================================
DROP PROCEDURE IF EXISTS sp_monthly_report;
DROP PROCEDURE IF EXISTS sp_close_month;

DELIMITER $$

-- SP 1: Get full monthly financial report for a user
-- Returns: income summary, expense summary, category breakdown, budget status
-- Python calls: CALL sp_monthly_report(1, '2025-01')
CREATE PROCEDURE sp_monthly_report(IN p_UserID INT, IN p_MonthYear CHAR(7))
BEGIN
    -- Result set 1: Summary
    SELECT 
        p_MonthYear AS ReportMonth,
        fn_get_total_income(p_UserID, p_MonthYear) AS TotalIncome,
        fn_get_total_expenses(p_UserID, p_MonthYear) AS TotalExpenses,
        (fn_get_total_income(p_UserID, p_MonthYear) - fn_get_total_expenses(p_UserID, p_MonthYear)) AS NetSavings;

    -- Result set 2: Category breakdown
    SELECT CategoryName, SpentAmount, UsagePercent, BudgetStatus
    FROM vw_budget_status
    WHERE UserID = p_UserID AND MonthYear = p_MonthYear
    ORDER BY SpentAmount DESC;
END$$

-- SP 2: Monthly snapshot - close the month and record balance
-- Useful for audit trail; creates a summary row
-- Python calls: CALL sp_close_month(1, '2025-01')
CREATE PROCEDURE sp_close_month(IN p_UserID INT, IN p_MonthYear CHAR(7))
BEGIN
    SELECT 
        p_UserID AS UserID,
        p_MonthYear AS Month,
        fn_get_total_income(p_UserID, p_MonthYear) AS Income,
        fn_get_total_expenses(p_UserID, p_MonthYear) AS Expenses,
        (fn_get_total_income(p_UserID, p_MonthYear) - fn_get_total_expenses(p_UserID, p_MonthYear)) AS NetSavings,
        NOW() AS ClosedAt;
END$$

DELIMITER ;

-- ============================================================
-- SECTION 5: TRIGGERS
-- Why: Auto-update BankAccount balance on every transaction
-- This ensures balance is ALWAYS consistent with transactions
-- ============================================================

DROP TRIGGER IF EXISTS trg_income_after_insert;
DROP TRIGGER IF EXISTS trg_income_after_delete;
DROP TRIGGER IF EXISTS trg_income_after_update;
DROP TRIGGER IF EXISTS trg_expense_after_insert;
DROP TRIGGER IF EXISTS trg_expense_after_delete;
DROP TRIGGER IF EXISTS trg_expense_after_update;

DELIMITER $$

-- Trigger 1: After INSERT on Income → ADD amount to bank balance
CREATE TRIGGER trg_income_after_insert
AFTER INSERT ON Income
FOR EACH ROW
BEGIN
    UPDATE BankAccounts
    SET    Balance = Balance + NEW.Amount
    WHERE  AccountID = NEW.AccountID;
END$$

-- Trigger 2: After INSERT on Expenses → SUBTRACT amount from balance
-- Note: schema CHECK constraint ensures Balance >= 0 AFTER update;
-- if this trigger would make balance negative, MySQL raises an error
CREATE TRIGGER trg_expense_after_insert
AFTER INSERT ON Expenses
FOR EACH ROW
BEGIN
    UPDATE BankAccounts
    SET    Balance = Balance - NEW.Amount
    WHERE  AccountID = NEW.AccountID;
END$$

-- Trigger 3: After DELETE on Income → reverse the balance addition
CREATE TRIGGER trg_income_after_delete
AFTER DELETE ON Income
FOR EACH ROW
BEGIN
    UPDATE BankAccounts
    SET    Balance = Balance - OLD.Amount
    WHERE  AccountID = OLD.AccountID;
END$$

-- Trigger 4: After DELETE on Expenses → reverse the deduction
CREATE TRIGGER trg_expense_after_delete
AFTER DELETE ON Expenses
FOR EACH ROW
BEGIN
    UPDATE BankAccounts
    SET    Balance = Balance + OLD.Amount
    WHERE  AccountID = OLD.AccountID;
END$$

-- Trigger 5: Adjust balance when income amount is UPDATED
CREATE TRIGGER trg_income_after_update
AFTER UPDATE ON Income
FOR EACH ROW
BEGIN
    -- UPDATE BankAccounts 
    -- SET Balance = Balance - OLD.Amount + NEW.Amount 
    -- WHERE AccountID = NEW.AccountID;
    
    -- Trường hợp 1: Thay đổi tài khoản nhận tiền
    IF OLD.AccountID <> NEW.AccountID THEN
        -- 1. Trừ tiền ở tài khoản cũ (vì thực tế tiền không vào đây)
        UPDATE BankAccounts 
        SET Balance = Balance - OLD.Amount 
        WHERE AccountID = OLD.AccountID;

        -- 2. Cộng tiền vào tài khoản mới
        UPDATE BankAccounts 
        SET Balance = Balance + NEW.Amount 
        WHERE AccountID = NEW.AccountID;

    -- Trường hợp 2: Cùng tài khoản nhưng thay đổi số tiền
    ELSEIF OLD.Amount <> NEW.Amount THEN
        UPDATE BankAccounts 
        SET Balance = Balance + (NEW.Amount - OLD.Amount)
        WHERE AccountID = NEW.AccountID;
    END IF;
END$$

-- Trigger 6: Adjust balance when expense amount is UPDATED
CREATE TRIGGER trg_expense_after_update
AFTER UPDATE ON Expenses
FOR EACH ROW
BEGIN
    -- UPDATE BankAccounts 
    -- SET Balance = Balance + OLD.Amount - NEW.Amount 
    -- WHERE AccountID = NEW.AccountID;
    
    -- Trường hợp 1: Thay đổi tài khoản ngân hàng
    IF OLD.AccountID <> NEW.AccountID THEN
        -- 1. Hoàn tiền lại cho tài khoản cũ
        UPDATE BankAccounts 
        SET Balance = Balance + OLD.Amount 
        WHERE AccountID = OLD.AccountID;

        -- 2. Trừ tiền ở tài khoản mới
        UPDATE BankAccounts 
        SET Balance = Balance - NEW.Amount 
        WHERE AccountID = NEW.AccountID;

    -- Trường hợp 2: Cùng tài khoản nhưng thay đổi số tiền
    ELSEIF OLD.Amount <> NEW.Amount THEN
        UPDATE BankAccounts 
        SET Balance = Balance + (OLD.Amount - NEW.Amount)
        WHERE AccountID = NEW.AccountID;
    END IF;
END$$

DELIMITER ;