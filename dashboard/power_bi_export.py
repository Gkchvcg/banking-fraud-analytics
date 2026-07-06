import os
import sqlite3
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'fraud_analytics.db')
EXPORT_DIR = os.path.join(os.path.dirname(__file__), 'power_bi_exports')

def export_power_bi_datasets():
    """Reads tables from SQLite database and exports them to clean CSV files for Power BI."""
    print("Connecting to database...")
    conn = sqlite3.connect(DB_PATH)
    
    # Create export directory if it doesn't exist
    if not os.path.exists(EXPORT_DIR):
        os.makedirs(EXPORT_DIR)
        print(f"Created export directory: {EXPORT_DIR}")
        
    tables = ['customers', 'merchants', 'transactions', 'alerts']
    
    print("\n--- Exporting Tables to CSV ---")
    for table in tables:
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        export_path = os.path.join(EXPORT_DIR, f"{table}.csv")
        df.to_csv(export_path, index=False)
        print(f"Exported {table} table ({len(df)} rows) to: {export_path}")
        
    # Create a consolidated master view for direct import to single-table models if needed
    master_query = """
        SELECT 
            t.transaction_id, t.timestamp, t.amount, t.channel, t.is_fraud, t.fraud_category,
            t.anomaly_score, t.risk_score,
            c.customer_id, c.name AS customer_name, c.age AS customer_age, c.gender AS customer_gender,
            c.city AS customer_city, c.state AS customer_state, c.latitude AS customer_latitude, c.longitude AS customer_longitude,
            c.credit_limit,
            m.merchant_id, m.name AS merchant_name, m.category AS merchant_category,
            m.latitude AS merchant_latitude, m.longitude AS merchant_longitude
        FROM transactions t
        JOIN customers c ON t.customer_id = c.customer_id
        JOIN merchants m ON t.merchant_id = m.merchant_id
    """
    print("\nExporting consolidated Master Fraud Ledger view...")
    df_master = pd.read_sql_query(master_query, conn)
    master_path = os.path.join(EXPORT_DIR, "master_fraud_ledger.csv")
    df_master.to_csv(master_path, index=False)
    print(f"Consolidated Ledger exported ({len(df_master)} rows) to: {master_path}")
    
    conn.close()
    
    # Generate SQL template file for direct database connection models
    sql_template_path = os.path.join(EXPORT_DIR, "power_bi_queries.sql")
    with open(sql_template_path, 'w') as f:
        f.write(get_sql_templates())
    print(f"Saved Power BI ready SQL queries to: {sql_template_path}")
    
    print("\nPower BI Export Process Completed successfully!")

def get_sql_templates():
    return """/* 
   ==========================================================================
   POWER BI ANALYTICAL SQL TEMPLATES
   Banking Fraud Analytics Project
   ==========================================================================
   These queries are pre-written and optimized for direct pasting into Power BI 
   Database Connector or SQL database connections.
*/

-- 1. Dashboard Overview Metrics (Financial Loss & Prevention)
SELECT 
    COUNT(transaction_id) as total_transactions,
    SUM(amount) as total_volume,
    SUM(CASE WHEN is_fraud = 1 THEN amount ELSE 0 END) as total_fraud_loss,
    SUM(CASE WHEN is_fraud = 1 AND risk_score >= 75.0 THEN amount ELSE 0 END) as prevented_fraud_loss,
    (SUM(CASE WHEN is_fraud = 1 THEN amount ELSE 0 END) / SUM(amount)) * 100.0 as fraud_rate_percentage
FROM transactions;

-- 2. Fraud Trend (Aggregated weekly)
SELECT 
    strftime('%Y-%W', timestamp) as week_identifier,
    MIN(date(timestamp)) as week_start_date,
    SUM(amount) as weekly_total_volume,
    SUM(CASE WHEN is_fraud = 1 THEN amount ELSE 0 END) as weekly_fraud_loss,
    SUM(is_fraud) as weekly_fraud_count
FROM transactions
GROUP BY week_identifier
ORDER BY week_start_date ASC;

-- 3. Merchant Vulnerability Analysis
SELECT 
    m.category as merchant_category,
    COUNT(t.transaction_id) as transaction_count,
    SUM(t.amount) as total_volume,
    SUM(t.is_fraud) as fraud_count,
    SUM(CASE WHEN t.is_fraud = 1 THEN t.amount ELSE 0 END) as fraud_loss,
    (SUM(t.is_fraud) * 1.0 / COUNT(t.transaction_id)) * 100.0 as fraud_rate_pct
FROM transactions t
JOIN merchants m ON t.merchant_id = m.merchant_id
GROUP BY m.category
ORDER BY fraud_rate_pct DESC;

-- 4. High-Risk Customers Segment
SELECT 
    c.customer_id,
    c.name as customer_name,
    c.age as customer_age,
    c.state as customer_state,
    MAX(t.risk_score) as max_risk_score,
    COUNT(t.transaction_id) as total_transactions,
    SUM(t.is_fraud) as confirmed_fraud_cases
FROM customers c
JOIN transactions t ON c.customer_id = t.customer_id
GROUP BY c.customer_id
HAVING max_risk_score >= 50.0
ORDER BY max_risk_score DESC;

-- 5. Geographic Fraud Spread
SELECT 
    c.state as customer_home_state,
    COUNT(t.transaction_id) as transaction_count,
    SUM(CASE WHEN t.is_fraud = 1 THEN 1 ELSE 0 END) as fraud_cases,
    SUM(CASE WHEN t.is_fraud = 1 THEN t.amount ELSE 0 END) as fraud_loss
FROM transactions t
JOIN customers c ON t.customer_id = c.customer_id
GROUP BY c.state
ORDER BY fraud_loss DESC;
"""

if __name__ == '__main__':
    export_power_bi_datasets()
