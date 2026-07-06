-- SQLite Banking Fraud Analytics Database Schema

-- Drop tables if they exist to allow clean reseeding
DROP TABLE IF EXISTS alerts;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS merchants;
DROP TABLE IF EXISTS customers;

-- 1. Customers Table
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    age INTEGER,
    gender TEXT,
    state TEXT,
    city TEXT,
    latitude REAL,
    longitude REAL,
    signup_date TEXT,
    credit_limit REAL
);

-- 2. Merchants Table
CREATE TABLE merchants (
    merchant_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    base_risk_score REAL DEFAULT 0.0
);

-- 3. Transactions Table
CREATE TABLE transactions (
    transaction_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    merchant_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    amount REAL NOT NULL,
    channel TEXT NOT NULL, -- 'online', 'in-store', 'atm'
    latitude REAL,
    longitude REAL,
    is_fraud INTEGER DEFAULT 0, -- 0 = No, 1 = Yes
    fraud_category TEXT, -- 'Card Cloning', 'Phishing', 'Account Takeover', 'Stolen Card', etc.
    anomaly_score REAL DEFAULT 0.0,
    risk_score REAL DEFAULT 0.0,
    FOREIGN KEY(customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY(merchant_id) REFERENCES merchants(merchant_id)
);

-- 4. Alerts Table
CREATE TABLE alerts (
    alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'INVESTIGATING', 'RESOLVED_FRAUD', 'RESOLVED_FALSE_POSITIVE'
    severity TEXT NOT NULL DEFAULT 'MEDIUM', -- 'LOW', 'MEDIUM', 'HIGH'
    trigger_time TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY(transaction_id) REFERENCES transactions(transaction_id)
);

-- Indexes for performance & query optimization in Dashboards/Power BI
CREATE INDEX idx_transactions_customer ON transactions(customer_id);
CREATE INDEX idx_transactions_merchant ON transactions(merchant_id);
CREATE INDEX idx_transactions_timestamp ON transactions(timestamp);
CREATE INDEX idx_transactions_is_fraud ON transactions(is_fraud);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_transaction ON alerts(transaction_id);
