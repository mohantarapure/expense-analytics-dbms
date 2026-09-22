
-- Expense Analytics & Budget Management System: SQLite query collection

-- 1. All expenses
SELECT * FROM expenses;

-- 2. Expenses above a value
SELECT * FROM expenses WHERE amount > 500;

-- 3. Sort highest expenses first
SELECT * FROM expenses ORDER BY amount DESC;

-- 4. Expenses for a date range
SELECT * FROM expenses WHERE expense_date BETWEEN '2026-01-01' AND '2026-12-31';

-- 5. Insert example (use a valid user/category/payment_mode ID)
-- INSERT INTO expenses(user_id,category_id,payment_mode_id,amount,description,expense_date)
-- VALUES(1,1,1,250,'Example','2026-01-15');

-- 6. Update an expense
-- UPDATE expenses SET amount=300 WHERE expense_id=1;

-- 7. Delete an expense
-- DELETE FROM expenses WHERE expense_id=1;

-- 8. Total spending
SELECT ROUND(SUM(amount),2) AS total_spending FROM expenses;

-- 9. Average transaction
SELECT ROUND(AVG(amount),2) AS average_expense FROM expenses;

-- 10. Category totals using GROUP BY
SELECT c.category_name, ROUND(SUM(e.amount),2) AS total
FROM expenses e JOIN categories c ON c.category_id=e.category_id
GROUP BY c.category_id ORDER BY total DESC;

-- 11. HAVING: categories over 1000
SELECT c.category_name, SUM(e.amount) AS total
FROM expenses e JOIN categories c ON c.category_id=e.category_id
GROUP BY c.category_id HAVING SUM(e.amount) > 1000;

-- 12. Payment mode totals
SELECT p.mode_name, COUNT(*) AS transactions, ROUND(SUM(e.amount),2) AS total
FROM expenses e JOIN payment_modes p ON p.payment_mode_id=e.payment_mode_id
GROUP BY p.payment_mode_id;

-- 13. LEFT JOIN all categories, including unused categories
SELECT c.category_name, COALESCE(SUM(e.amount),0) AS total
FROM categories c LEFT JOIN expenses e ON e.category_id=c.category_id
GROUP BY c.category_id;

-- 14. Monthly summary view
SELECT * FROM monthly_expense_summary ORDER BY month_year DESC;

-- 15. High-value expenses above the user's average
SELECT * FROM expenses
WHERE amount > (SELECT AVG(amount) FROM expenses);

-- 16. Maximum expense
SELECT MAX(amount) AS maximum_expense FROM expenses;

-- 17. Minimum expense
SELECT MIN(amount) AS minimum_expense FROM expenses;

-- 18. Count transactions by user
SELECT user_id, COUNT(*) AS transaction_count FROM expenses GROUP BY user_id;

-- 19. Budget vs actual
SELECT b.month_year,c.category_name,b.amount AS budget,
       COALESCE(SUM(e.amount),0) AS actual
FROM budgets b JOIN categories c ON c.category_id=b.category_id
LEFT JOIN expenses e ON e.user_id=b.user_id AND e.category_id=b.category_id
 AND substr(e.expense_date,1,7)=b.month_year
GROUP BY b.budget_id;

-- 20. Categories whose total is greater than the overall average transaction
SELECT c.category_name, SUM(e.amount) AS total
FROM expenses e JOIN categories c ON c.category_id=e.category_id
GROUP BY c.category_id
HAVING SUM(e.amount) > (SELECT AVG(amount) FROM expenses);
