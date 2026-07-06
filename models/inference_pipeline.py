import os
import sqlite3
import pandas as pd
import numpy as np
import xgboost as xgb
import pickle
from datetime import datetime
from fraud_detection import engineer_features

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'fraud_analytics.db')
MODEL_DIR = os.path.dirname(__file__)

def load_models():
    """Load models, scalers, and configs from disk."""
    print("Loading models for inference...")
    
    # 1. XGBoost
    xgb_model_path = os.path.join(MODEL_DIR, 'xgb_fraud_model.bin')
    xgb_model = xgb.XGBClassifier()
    xgb_model.load_model(xgb_model_path)
    
    # XGBoost features
    xgb_features_path = os.path.join(MODEL_DIR, 'model_features.pkl')
    with open(xgb_features_path, 'rb') as f:
        xgb_features = pickle.load(f)
        
    # 2. Isolation Forest
    iso_model_path = os.path.join(MODEL_DIR, 'iso_forest_model.pkl')
    with open(iso_model_path, 'rb') as f:
        iso_model = pickle.load(f)
        
    # Scaler
    scaler_path = os.path.join(MODEL_DIR, 'anomaly_scaler.pkl')
    with open(scaler_path, 'rb') as f:
        anomaly_scaler = pickle.load(f)
        
    # Anomaly Config
    config_path = os.path.join(MODEL_DIR, 'anomaly_config.pkl')
    with open(config_path, 'rb') as f:
        anomaly_config = pickle.load(f)
        
    return xgb_model, xgb_features, iso_model, anomaly_scaler, anomaly_config

def run_inference_on_db():
    xgb_model, xgb_features, iso_model, anomaly_scaler, anomaly_config = load_models()
    
    # Load all transactions and join with customers & merchants
    print("Loading data from SQLite for inference scoring...")
    conn = sqlite3.connect(DB_PATH)
    
    query = """
        SELECT 
            t.transaction_id, t.customer_id, t.merchant_id, t.timestamp, t.amount, t.channel,
            t.latitude AS tx_lat, t.longitude AS tx_lon, t.is_fraud,
            c.age, c.latitude AS cust_lat, c.longitude AS cust_lon, c.credit_limit,
            m.category AS merch_category, m.base_risk_score AS merch_risk
        FROM transactions t
        JOIN customers c ON t.customer_id = c.customer_id
        JOIN merchants m ON t.merchant_id = m.merchant_id
    """
    df_raw = pd.read_sql_query(query, conn)
    
    if len(df_raw) == 0:
        print("No transactions found in database.")
        conn.close()
        return
        
    # Preprocess and engineer features
    df_feat = engineer_features(df_raw)
    
    # 1. XGBoost Scoring
    print("Scoring transactions with XGBoost Classifier...")
    X_xgb = df_feat[xgb_features]
    xgb_probs = xgb_model.predict_proba(X_xgb)[:, 1]
    
    # 2. Isolation Forest Scoring
    print("Scoring transactions with Isolation Forest...")
    anomaly_cols = anomaly_config['features']
    X_anom = df_feat[anomaly_cols]
    X_anom_scaled = anomaly_scaler.transform(X_anom)
    
    raw_anom_scores = iso_model.score_samples(X_anom_scaled)
    # Scale from 0 to 1 (1 being highly anomalous)
    min_s = anomaly_config['min_score']
    max_s = anomaly_config['max_score']
    
    # Min-max scale and invert (so that lower raw score = higher scaled score)
    anom_scores_scaled = 1.0 - (raw_anom_scores - min_s) / (max_s - min_s + 1e-8)
    anom_scores_scaled = np.clip(anom_scores_scaled, 0.0, 1.0)
    
    # 3. Calculate Risk Score: 70% XGBoost, 30% Isolation Forest anomaly
    # Scale risk score to 0 - 100
    risk_scores = (0.7 * xgb_probs + 0.3 * anom_scores_scaled) * 100.0
    
    # Add to DataFrame
    df_raw['anomaly_score'] = anom_scores_scaled
    df_raw['risk_score'] = risk_scores
    
    # Update transactions table in database
    print("Updating transactions table in SQLite...")
    cursor = conn.cursor()
    
    # Prepare batch update
    update_data = []
    for index, row in df_raw.iterrows():
        update_data.append((
            float(row['anomaly_score']),
            float(row['risk_score']),
            str(row['transaction_id'])
        ))
        
    cursor.executemany("""
        UPDATE transactions
        SET anomaly_score = ?, risk_score = ?
        WHERE transaction_id = ?
    """, update_data)
    conn.commit()
    print(f"Successfully updated {len(update_data)} transaction scores in database.")
    
    # 4. Alert Generation
    # Create alerts for high-risk transactions (risk_score >= 50)
    print("Generating system alerts for high-risk transactions...")
    
    # Delete existing alerts to prevent duplicates during run scripting
    cursor.execute("DELETE FROM alerts")
    conn.commit()
    
    alert_transactions = df_raw[df_raw['risk_score'] >= 50.0].copy()
    
    alert_records = []
    for index, row in alert_transactions.iterrows():
        r_score = row['risk_score']
        
        # Severity assignment
        if r_score >= 80.0:
            severity = 'HIGH'
        elif r_score >= 65.0:
            severity = 'MEDIUM'
        else:
            severity = 'LOW'
            
        # Compose a helpful investigative note
        trigger_reasons = []
        if row['amount'] > 1000:
            trigger_reasons.append("High amount transaction")
        if row['anomaly_score'] > 0.7:
            trigger_reasons.append(f"Highly anomalous pattern (Unsupervised score: {row['anomaly_score']:.2f})")
        if row['channel'] == 'online':
            trigger_reasons.append("Online transaction channel")
            
        note_str = f"Blended Risk Score: {r_score:.1f}%. Supervised Fraud Prob: {row['is_fraud'] * 100:.1f}%. "
        if trigger_reasons:
            note_str += "Flags: " + ", ".join(trigger_reasons) + "."
        else:
            note_str += "Suspicious overall profile."
            
        alert_records.append((
            str(row['transaction_id']),
            'PENDING',
            severity,
            str(row['timestamp']),
            note_str
        ))
        
    cursor.executemany("""
        INSERT INTO alerts (transaction_id, status, severity, trigger_time, notes)
        VALUES (?, ?, ?, ?, ?)
    """, alert_records)
    conn.commit()
    print(f"Generated {len(alert_records)} alerts in SQLite database.")
    
    conn.close()
    print("Inference and alerting complete!")

if __name__ == '__main__':
    run_inference_on_db()
