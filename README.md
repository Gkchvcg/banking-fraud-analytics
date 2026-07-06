# 🛡️ SafeVault: Banking Fraud Analytics & ML Intelligence

SafeVault is a comprehensive, production-grade Banking Fraud Analytics and Machine Learning system. It combines supervised machine learning (XGBoost), unsupervised anomaly detection (Isolation Forest), SQL relational modeling, and interactive dashboards to simulate, flag, and analyze suspicious banking activities.

---

## 🏗️ System Architecture

The project consists of three core layers orchestrating data, machine learning, and visualization:

```
                  ┌─────────────────────────────────────┐
                  │      Synthetic Data Generator       │
                  │ (Customer profiles & Fraud vectors) │
                  └──────────────────┬──────────────────┘
                                     ▼
                  ┌─────────────────────────────────────┐
                  │       SQLite Relational DB          │
                  │ (Normalized customer/merch schemas)  │
                  └─────────┬───────────────────┬───────┘
                            │                   │
                            ▼                   ▼
                  ┌──────────────────┐ ┌──────────────────┐
                  │  XGBoost Model   │ │ Isolation Forest │
                  │   (Supervised)   │ │  (Unsupervised)  │
                  └─────────┬────────┘ └────────┬─────────┘
                            │                   │
                            └─────────┬─────────┘
                                      ▼
                  ┌─────────────────────────────────────┐
                  │     Blended Risk Engine & Alerts    │
                  │   (Computes overall threat index)   │
                  └──────────────────┬──────────────────┘
                                     ▼
                 ┌───────────────────┴───────────────────┐
                 │                                       │
                 ▼                                       ▼
    ┌─────────────────────────┐             ┌─────────────────────────┐
    │   Streamlit Dashboard   │             │   Power BI SQL & CSV   │
    │  (Operational Hub)      │             │  (Business Intelligence)│
    └─────────────────────────┘             └─────────────────────────┘
```

### 1. Relational Database Layer (`data/`)
- **`schema.sql`**: Configures database indexing and tables for `customers`, `merchants`, `transactions`, and transaction-based `alerts`.
- **`synthetic_generator.py`**: Generates 1,000 customers, 150 merchants, and 40,000 transaction events over a 12-month period. It embeds 4 distinct fraud typologies:
  - **Card Cloning**: Geographic distance anomalies simulating travel velocities that are physically impossible (velocity check).
  - **Account Takeover / Phishing**: Sudden large-scale transactions occurring at abnormal times (e.g. 3:00 AM) in online networks.
  - **Stolen Card (Card Testing)**: High frequency, micro-value transaction bursts.
  - **Phishing/Merchant Risk**: Suspicious transactions targeting historically high-risk merchant categories.

### 2. Machine Learning Layer (`models/`)
- **`fraud_detection.py`**: A supervised **XGBoost Classifier** that calculates features (transaction hour, day of the week, geodesic distance, transaction amount relative to average spending, and credit limit usage) to predict transaction fraud probabilities. Handles class imbalance using class scaling weights.
- **`anomaly_detection.py`**: An unsupervised **Isolation Forest** outlier model designed to flag novel, out-of-distribution transactions.
- **`inference_pipeline.py`**: Blends supervised prediction probabilities (70%) and unsupervised anomaly metrics (30%) to generate an overall **Risk Score (0 - 100)** for every transaction, automatically populating the `alerts` center for high-risk anomalies.

### 3. Business Intelligence & Dashboards (`dashboard/`)
- **Streamlit Web Hub (`app.py`)**: An interactive security operations center to investigate customer profiles, monitor fraud patterns, track merchant risks, and process alert resolutions.
- **Power BI Integration (`power_bi_export.py`)**: Exports clean, pre-joined datasets to CSV alongside pre-configured SQL templates for direct Power BI connection.

---

## 🚀 Setup & Execution

### 1. Environment Setup
Make sure you have Python 3.8+ installed. Set up a virtual environment and install dependencies:

```bash
# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Pipelines & Dashboard
Use the master orchestrator `run.py` to trigger the entire flow (data generation, database building, ML training, inference, and CSV exports) and launch the dashboard:

```bash
python run.py
```

### Run Options
- **Only Start Dashboard**: If you have already run the pipeline and trained models once:
  ```bash
  python run.py --only-dashboard
  ```
- **Skip ML Model Re-Training**: Generates new transactions and updates databases using existing trained models:
  ```bash
  python run.py --skip-train
  ```
- **Run Pipeline Without Dashboard**: Runs full training and data prep only:
  ```bash
  python run.py --no-dashboard
  ```

---

## 📊 Power BI Analytics

### Direct SQLite Import
1. In **Power BI Desktop**, choose **Get Data** ➡️ **ODBC**.
2. Select or create an ODBC data source mapping to SQLite.
3. Browse and select `/data/fraud_analytics.db`.

### CSV Export Import
If you don't use ODBC, import the exported CSV files located in `dashboard/power_bi_exports/`:
- `master_fraud_ledger.csv`: Consolidates customer, merchant, and transaction records for single-table fast reporting.
- `customers.csv`, `merchants.csv`, `transactions.csv`, `alerts.csv`: Normalized tables to build custom dimensional star-schemas.

### Ready-To-Run SQL Dashboards
Open `dashboard/power_bi_exports/power_bi_queries.sql` to access copy-paste SQL scripts for direct database query inputs inside Power BI.
