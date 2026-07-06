import os
import sqlite3
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
import pickle

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'fraud_analytics.db')
MODEL_DIR = os.path.dirname(__file__)

def haversine_np(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 3956 # Radius of earth in miles
    return c * r

def load_data_from_db():
    """Load transactions, customers, and merchants tables from SQLite and join them."""
    print("Loading data from SQLite for training...")
    conn = sqlite3.connect(DB_PATH)
    
    query = """
        SELECT 
            t.transaction_id, t.customer_id, t.merchant_id, t.timestamp, t.amount, t.channel,
            t.latitude AS tx_lat, t.longitude AS tx_lon, t.is_fraud, t.fraud_category,
            c.age, c.latitude AS cust_lat, c.longitude AS cust_lon, c.credit_limit,
            m.category AS merch_category, m.base_risk_score AS merch_risk
        FROM transactions t
        JOIN customers c ON t.customer_id = c.customer_id
        JOIN merchants m ON t.merchant_id = m.merchant_id
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def engineer_features(df):
    """Create features for fraud modeling."""
    print("Engineering features...")
    df = df.copy()
    
    # Parse timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    
    # Geodist (distance between customer home and transaction location)
    df['distance_miles'] = haversine_np(df['cust_lon'], df['cust_lat'], df['tx_lon'], df['tx_lat'])
    
    # Handle NaNs in distance if coordinates are missing
    df['distance_miles'] = df['distance_miles'].fillna(0.0)
    
    # Categorical encoding for Channel
    df['channel_online'] = (df['channel'] == 'online').astype(int)
    df['channel_atm'] = (df['channel'] == 'atm').astype(int)
    df['channel_instore'] = (df['channel'] == 'in-store').astype(int)
    
    # Calculate customer historical aggregate metrics
    # Note: In production we compute rolling aggregates. For this analytical project,
    # we compute global average and maximum per customer as reference features.
    cust_stats = df.groupby('customer_id')['amount'].agg(['mean', 'max']).rename(
        columns={'mean': 'cust_avg_amount', 'max': 'cust_max_amount'}
    )
    df = df.join(cust_stats, on='customer_id')
    
    # Ratio of current transaction amount to customer avg
    df['amount_to_avg_ratio'] = df['amount'] / (df['cust_avg_amount'] + 1e-5)
    # Ratio of transaction amount to customer's credit limit
    df['amount_to_limit_ratio'] = df['amount'] / (df['credit_limit'] + 1e-5)
    
    # One-hot encoding of merchant categories
    categories = ['Groceries', 'Dining', 'Travel', 'Luxury', 'Retail', 'Entertainment', 'Utilities', 'ATM/Cash']
    for cat in categories:
        df[f'cat_{cat}'] = (df['merch_category'] == cat).astype(int)
        
    return df

def train_model():
    df_raw = load_data_from_db()
    df_feat = engineer_features(df_raw)
    
    # Define features
    feature_cols = [
        'amount', 'age', 'hour', 'day_of_week', 'distance_miles',
        'channel_online', 'channel_atm', 'channel_instore',
        'cust_avg_amount', 'cust_max_amount', 'amount_to_avg_ratio', 'amount_to_limit_ratio',
        'merch_risk'
    ] + [f'cat_{cat}' for cat in ['Groceries', 'Dining', 'Travel', 'Luxury', 'Retail', 'Entertainment', 'Utilities', 'ATM/Cash']]
    
    X = df_feat[feature_cols]
    y = df_feat['is_fraud']
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Account for class imbalance
    num_neg = (y_train == 0).sum()
    num_pos = (y_train == 1).sum()
    scale_weight = num_neg / num_pos
    print(f"Class imbalance ratio: {scale_weight:.2f} (Negative: {num_neg}, Positive: {num_pos})")
    
    # Train XGBoost
    print("Training XGBoost Classifier...")
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        scale_pos_weight=scale_weight,
        random_state=42,
        eval_metric='logloss',
        use_label_encoder=False
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate
    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1]
    
    print("\n--- Model Evaluation Results ---")
    print(classification_report(y_test, preds))
    print("ROC-AUC Score:", roc_auc_score(y_test, probs))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, preds))
    
    # Save Feature Importance
    importances = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
    print("\nFeature Importances:")
    print(importances.head(10))
    
    # Save model and features list
    model_path = os.path.join(MODEL_DIR, 'xgb_fraud_model.bin')
    features_path = os.path.join(MODEL_DIR, 'model_features.pkl')
    
    print(f"Saving model to {model_path}")
    model.save_model(model_path)
    
    with open(features_path, 'wb') as f:
        pickle.dump(feature_cols, f)
        
    print("Supervised training complete!")

if __name__ == '__main__':
    train_model()
