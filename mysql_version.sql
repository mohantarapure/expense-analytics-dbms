
-- ACADEMIC MYSQL REFERENCE ONLY
-- The running application uses SQLite. This file demonstrates equivalent
-- MySQL DBMS concepts, including procedures/functions which SQLite does not support.

CREATE DATABASE IF NOT EXISTS expense_analytics;
USE expense_analytics;

CREATE TABLE users (
  user_id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(150) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE categories (
  category_id INT PRIMARY KEY AUTO_INCREMENT,
  category_name VARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE payment_modes (
  payment_mode_id INT PRIMARY KEY AUTO_INCREMENT,
  mode_name VARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE expenses (
  expense_id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  category_id INT NOT NULL,
  payment_mode_id INT NOT NULL,
  amount DECIMAL(10,2) NOT NULL CHECK (amount > 0),
  description VARCHAR(255),
  expense_date DATE NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(user_id),
  FOREIGN KEY(category_id) REFERENCES categories(category_id),
  FOREIGN KEY(payment_mode_id) REFERENCES payment_modes(payment_mode_id)
);

CREATE TABLE budgets (
  budget_id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  category_id INT NOT NULL,
  amount DECIMAL(10,2) NOT NULL CHECK (amount > 0),
  month_year CHAR(7) NOT NULL,
  UNIQUE(user_id, category_id, month_year),
  FOREIGN KEY(user_id) REFERENCES users(user_id),
  FOREIGN KEY(category_id) REFERENCES categories(category_id)
);

CREATE VIEW monthly_expense_summary AS
SELECT user_id, DATE_FORMAT(expense_date,'%Y-%m') AS month_year,
       COUNT(*) AS transaction_count, SUM(amount) AS total_amount,
       AVG(amount) AS average_amount
FROM expenses
GROUP BY user_id, DATE_FORMAT(expense_date,'%Y-%m');

DELIMITER //
CREATE TRIGGER trg_log_deleted_expense
AFTER DELETE ON expenses
FOR EACH ROW
BEGIN
  INSERT INTO deleted_expense_log(expense_id,user_id,amount,description)
  VALUES(OLD.expense_id,OLD.user_id,OLD.amount,OLD.description);
END//
DELIMITER ;

DELIMITER //
CREATE PROCEDURE GetUserTotalExpense(IN p_user_id INT)
BEGIN
  SELECT COALESCE(SUM(amount),0) AS total_expense
  FROM expenses WHERE user_id=p_user_id;
END//
DELIMITER ;

DELIMITER //
CREATE FUNCTION SpendingPercentage(p_spent DECIMAL(10,2), p_budget DECIMAL(10,2))
RETURNS DECIMAL(10,2)
DETERMINISTIC
BEGIN
  IF p_budget <= 0 THEN RETURN 0; END IF;
  RETURN (p_spent / p_budget) * 100;
END//
DELIMITER ;

-- JOIN example
SELECT c.category_name, SUM(e.amount) AS total
FROM expenses e JOIN categories c ON c.category_id=e.category_id
GROUP BY c.category_id HAVING SUM(e.amount) > 1000;

-- Subquery example
SELECT * FROM expenses
WHERE amount > (SELECT AVG(amount) FROM expenses);
