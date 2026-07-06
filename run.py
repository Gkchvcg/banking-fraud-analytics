import os
import sys
import subprocess

# Ensure project directories are in the import path
sys.path.append(os.path.join(os.path.dirname(__file__), 'data'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'models'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'dashboard'))

# Import tasks
from db_manager import initialize_database, populate_database
from fraud_detection import train_model
from anomaly_detection import train_anomaly_model
from inference_pipeline import run_inference_on_db
from power_bi_export import export_power_bi_datasets

def run_pipeline(skip_training=False):
    print("==========================================================================")
    # Step 1: Database Setup & Data Generation
    print("\n--- STEP 1/5: Database Setup and Data Generation ---")
    initialize_database()
    populate_database()
    
    if not skip_training:
        # Step 2: Supervised ML Model Training (XGBoost)
        print("\n--- STEP 2/5: Supervised XGBoost Model Training ---")
        train_model()
        
        # Step 3: Unsupervised ML Model Training (Isolation Forest)
        print("\n--- STEP 3/5: Unsupervised Anomaly Detection Training ---")
        train_anomaly_model()
    else:
        print("\n--- SKIPPING STEP 2 & 3: Model Training (re-using existing weights) ---")
        
    # Step 4: Run Inference & Score Transaction History
    print("\n--- STEP 4/5: Scoring Transactions & Populating Alerts ---")
    run_inference_on_db()
    
    # Step 5: Export Power BI Datasets
    print("\n--- STEP 5/5: Exporting Clean CSVs for Power BI ---")
    export_power_bi_datasets()
    
    print("\n==========================================================================")
    print("🎉 All pipeline steps executed successfully!")
    print("Database: data/fraud_analytics.db")
    print("Power BI CSV Exports: dashboard/power_bi_exports/")
    print("==========================================================================")

def launch_dashboard():
    print("\n🚀 Starting SafeVault Streamlit Dashboard...")
    dashboard_path = os.path.join(os.path.dirname(__file__), 'dashboard', 'app.py')
    
    try:
        subprocess.run(["streamlit", "run", dashboard_path], check=True)
    except KeyboardInterrupt:
        print("\nDashboard server terminated by user.")
    except FileNotFoundError:
        print("\n❌ Error: Streamlit command not found in your environment.")
        print("Please activate your virtual environment or run: pip install streamlit")

if __name__ == '__main__':
    # Options for run script:
    # default: runs full pipeline and starts dashboard
    # --skip-train: runs data-gen, scoring and dashboard (skips XGB/IF training)
    # --only-dashboard: just starts the dashboard
    
    args = sys.argv[1:]
    
    if '--only-dashboard' in args:
        launch_dashboard()
    else:
        skip_tr = '--skip-train' in args
        run_pipeline(skip_training=skip_tr)
        
        if '--no-dashboard' not in args:
            launch_dashboard()
