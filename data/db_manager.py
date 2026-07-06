import sqlite3
import os
import pandas as pd
from synthetic_generator import generate_all_data

DB_PATH = os.path.join(os.path.dirname(__file__), 'fraud_analytics.db')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schema.sql')

def initialize_database():
    """Reads schema.sql and sets up database tables."""
    print(f"Connecting to database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Read schema file
    print(f"Reading schema from: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r') as f:
        schema_sql = f.read()
        
    # Execute SQL statements (semicolon separated)
    cursor.executescript(schema_sql)
    conn.commit()
    print("Database tables initialized successfully.")
    conn.close()

def populate_database(n_cust=1000, n_merch=150, n_tx=40000):
    """Generates synthetic data and inserts it into database."""
    # Generate data
    df_cust, df_merch, df_tx = generate_all_data(n_cust, n_merch, n_tx)
    
    conn = sqlite3.connect(DB_PATH)
    
    print("Inserting customers into DB...")
    df_cust.to_sql('customers', conn, if_exists='append', index=False)
    
    print("Inserting merchants into DB...")
    df_merch.to_sql('merchants', conn, if_exists='append', index=False)
    
    print("Inserting transactions into DB...")
    df_tx.to_sql('transactions', conn, if_exists='append', index=False)
    
    conn.commit()
    print("Database seeding completed successfully.")
    
    # Run simple count check
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM customers")
    c_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM merchants")
    m_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM transactions")
    t_count = cursor.fetchone()[0]
    
    print(f"Verification - Customers: {c_count}, Merchants: {m_count}, Transactions: {t_count}")
    conn.close()

def main():
    initialize_database()
    populate_database()

if __name__ == '__main__':
    main()
