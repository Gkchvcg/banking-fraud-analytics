import os
import sqlite3
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import pickle
from fraud_detection import load_data_from_db, engineer_features

MODEL_DIR = os.path.dirname(__file__)

def train_anomaly_model():
    df_raw = load_data_from_db()
    df_feat = engineer_features(df_raw)
    
    # We only train anomaly detection on NORMAL transactions (unsupervised / semi-supervised approach)
    # or the entire dataset if we assume it's unlabeled. Let's use the entire dataset as is typical in unsupervised detection.
    # We select numeric columns for anomaly detection
    anomaly_features = [
        'amount', 'distance_miles', 'hour', 'amount_to_avg_ratio', 'amount_to_limit_ratio', 'merch_risk'
    ]
    
    X = df_feat[anomaly_features]
    
    print("Scaling features for Isolation Forest...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    print("Training Isolation Forest Anomaly Detector...")
    # contamination is the expected proportion of outliers (roughly matching our fraud rate of ~1.8%)
    iso_forest = IsolationForest(
        n_estimators=100,
        contamination=0.02,
        random_state=42,
        n_jobs=-1
    )
    
    iso_forest.fit(X_scaled)
    
    # Let's inspect anomaly scoring
    scores = iso_forest.score_samples(X_scaled) # returns negative anomaly scores (lower is more anomalous)
    # Convert to 0-1 scale where 1 is highly anomalous
    min_score = scores.min()
    max_score = scores.max()
    print(f"Raw Score Range: min={min_score:.4f}, max={max_score:.4f}")
    
    # Save the isolation forest model, scaler, and configuration
    model_path = os.path.join(MODEL_DIR, 'iso_forest_model.pkl')
    scaler_path = os.path.join(MODEL_DIR, 'anomaly_scaler.pkl')
    config_path = os.path.join(MODEL_DIR, 'anomaly_config.pkl')
    
    print(f"Saving Isolation Forest model to {model_path}")
    with open(model_path, 'wb') as f:
        pickle.dump(iso_forest, f)
        
    print(f"Saving StandardScaler to {scaler_path}")
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
        
    # Save score boundaries to normalize scores during inference
    anomaly_config = {
        'features': anomaly_features,
        'min_score': float(min_score),
        'max_score': float(max_score)
    }
    with open(config_path, 'wb') as f:
        pickle.dump(anomaly_config, f)
        
    print("Anomaly training complete!")

if __name__ == '__main__':
    train_anomaly_model()
