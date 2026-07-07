import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="SafeVault | Banking Fraud Analytics",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium design styling
st.markdown("""
<style>
    /* Styling for metric boxes */
    .metric-container {
        background-color: #1e293b;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        border: 1px solid #334155;
    }
    .metric-title {
        color: #94a3b8;
        font-size: 0.875rem;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }
    .metric-value {
        color: #f1f5f9;
        font-size: 1.875rem;
        font-weight: 700;
    }
    .metric-delta-pos {
        color: #ef4444;
        font-size: 0.875rem;
        font-weight: 600;
    }
    .metric-delta-neg {
        color: #22c55e;
        font-size: 0.875rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Database path definition
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'fraud_analytics.db')

def get_connection():
    return sqlite3.connect(DB_PATH)

# Cache data loading for performance
@st.cache_data(ttl=10)
def load_dashboard_data():
    conn = get_connection()
    
    # Transactions with customer and merchant info
    query_tx = """
        SELECT 
            t.transaction_id, t.customer_id, t.merchant_id, t.timestamp, t.amount, t.channel,
            t.latitude AS tx_lat, t.longitude AS tx_lon, t.is_fraud, t.fraud_category,
            t.anomaly_score, t.risk_score,
            c.name AS cust_name, c.age AS cust_age, c.gender AS cust_gender, c.state AS cust_state, 
            c.city AS cust_city, c.latitude AS cust_lat, c.longitude AS cust_lon, c.credit_limit,
            m.name AS merch_name, m.category AS merch_category, m.base_risk_score AS merch_risk
        FROM transactions t
        JOIN customers c ON t.customer_id = c.customer_id
        JOIN merchants m ON t.merchant_id = m.merchant_id
    """
    df_tx = pd.read_sql_query(query_tx, conn)
    df_tx['timestamp'] = pd.to_datetime(df_tx['timestamp'])
    
    # Active alerts
    query_alerts = """
        SELECT 
            a.alert_id, a.transaction_id, a.status, a.severity, a.trigger_time, a.notes,
            t.amount, t.channel, t.is_fraud, t.risk_score,
            c.name AS cust_name, m.name AS merch_name
        FROM alerts a
        JOIN transactions t ON a.transaction_id = t.transaction_id
        JOIN customers c ON t.customer_id = c.customer_id
        JOIN merchants m ON t.merchant_id = m.merchant_id
    """
    df_alerts = pd.read_sql_query(query_alerts, conn)
    
    conn.close()
    return df_tx, df_alerts

# Load primary datasets
try:
    df_tx, df_alerts = load_dashboard_data()
    data_loaded = True
except Exception as e:
    data_loaded = False
    st.error(f"Error connecting to database: {e}")
    st.info("Please run the orchestration script `python run.py` first to generate data and populate the database.")

if data_loaded:
    # Sidebar navigation
    st.sidebar.image("https://img.icons8.com/color/96/shield-with-crown.png", width=80)
    st.sidebar.title("SafeVault Analytics")
    st.sidebar.markdown("*Enterprise Fraud Intelligence*")
    st.sidebar.write("---")
    
    menu = st.sidebar.radio(
        "Navigation",
        ["Dashboard Overview", "Customer Risk Explorer", "Merchant Risk Profiles", "Alert Resolution Center"]
    )
    
    st.sidebar.write("---")
    st.sidebar.markdown("### Model Versions")
    st.sidebar.info("🤖 **XGBoost Classifier**: v1.2.0\n\n🌲 **Isolation Forest**: v1.1.0\n\n⚡ **DB Seeding**: Active")
    
    # ------------------
    # MENU 1: OVERVIEW
    # ------------------
    if menu == "Dashboard Overview":
        st.title("🛡️ Enterprise Banking Fraud Overview")
        st.markdown("Monitor real-time financial losses, fraud vectors, and operational risk metrics.")
        
        # Calculations for metrics
        total_volume = df_tx['amount'].sum()
        fraud_df = df_tx[df_tx['is_fraud'] == 1]
        total_fraud_loss = fraud_df['amount'].sum()
        fraud_rate_vol = (total_fraud_loss / total_volume) * 100
        
        # Prevented loss: high risk transactions (risk_score >= 75) that are fraud
        prevented_df = df_tx[(df_tx['is_fraud'] == 1) & (df_tx['risk_score'] >= 75.0)]
        prevented_loss = prevented_df['amount'].sum()
        
        active_alerts_count = len(df_alerts[df_alerts['status'].isin(['PENDING', 'INVESTIGATING'])])
        
        # Display Key Metric Cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">TOTAL TX VOLUME</div>
                <div class="metric-value">${total_volume/1e6:.2f}M</div>
                <div style="font-size: 0.8rem; color: #64748b;">{len(df_tx):,} Transactions</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">CONFIRMED FRAUD LOSS</div>
                <div class="metric-value" style="color: #f87171;">${total_fraud_loss:,.2f}</div>
                <div class="metric-delta-pos">⚠️ {fraud_rate_vol:.3f}% of total volume</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">PREVENTED FINANCIAL LOSS</div>
                <div class="metric-value" style="color: #4ade80;">${prevented_loss:,.2f}</div>
                <div class="metric-delta-neg">🛡️ {(prevented_loss / (total_fraud_loss + 1e-5)) * 100:.1f}% Mitigation Rate</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col4:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">ACTIVE INVESTIGATIONS</div>
                <div class="metric-value" style="color: #fbbf24;">{active_alerts_count}</div>
                <div style="font-size: 0.8rem; color: #64748b;">Pending or In-Progress</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.write("---")
        
        # Charts Row 1: Fraud Trend and Fraud Categories
        row1_col1, row1_col2 = st.columns([2, 1])
        
        with row1_col1:
            st.subheader("📈 Fraud Trend Analysis")
            # Group by week for smoother trend line
            df_tx['week'] = df_tx['timestamp'].dt.to_period('W').dt.to_timestamp()
            trend_df = df_tx.groupby('week').agg(
                fraud_amount=('amount', lambda x: x[df_tx.loc[x.index, 'is_fraud'] == 1].sum()),
                total_amount=('amount', 'sum'),
                fraud_count=('is_fraud', 'sum')
            ).reset_index()
            
            fig_trend = px.line(
                trend_df, x='week', y='fraud_amount',
                labels={'week': 'Timeline (Weeks)', 'fraud_amount': 'Fraud Loss ($)'},
                title="Weekly Fraud Financial Loss Trend",
                color_discrete_sequence=['#ef4444']
            )
            fig_trend.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#94a3b8',
                xaxis=dict(showgrid=True, gridcolor='#334155'),
                yaxis=dict(showgrid=True, gridcolor='#334155')
            )
            st.plotly_chart(fig_trend, width='stretch')
            
        with row1_col2:
            st.subheader("🏷️ Fraud Categories")
            cat_df = fraud_df['fraud_category'].value_counts().reset_index()
            cat_df.columns = ['Category', 'Count']
            
            fig_pie = px.pie(
                cat_df, values='Count', names='Category',
                title="Distribution of Fraud Typologies",
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Reds_r
            )
            fig_pie.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#94a3b8'
            )
            st.plotly_chart(fig_pie, width='stretch')
            
        # Charts Row 2: Heatmap and Merchant Analysis
        row2_col1, row2_col2 = st.columns([1, 1])
        
        with row2_col1:
            st.subheader("🗺️ Geographic Fraud Heatmap")
            # Draw scatter plot representing geographical coordinates of fraud
            high_risk_df = df_tx[df_tx['risk_score'] >= 60].sample(min(len(df_tx[df_tx['risk_score'] >= 60]), 1500))
            
            fig_map = px.scatter_map(
                high_risk_df,
                lat="tx_lat",
                lon="tx_lon",
                color="risk_score",
                size="amount",
                color_continuous_scale=px.colors.sequential.OrRd,
                size_max=15,
                zoom=3.5,
                map_style="carto-darkmatter",
                title="Geographic Scatter of High Risk Transactions",
                labels={'risk_score': 'Risk Score (0-100)', 'amount': 'Tx Amount ($)'}
            )
            fig_map.update_layout(
                margin={"r":0,"t":40,"l":0,"b":0},
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#94a3b8'
            )
            st.plotly_chart(fig_map, width='stretch')
            
        with row2_col2:
            st.subheader("🛍️ Merchant Category Vulnerability")
            merch_fraud = df_tx.groupby('merch_category').agg(
                total_transactions=('is_fraud', 'count'),
                fraud_count=('is_fraud', 'sum'),
                fraud_amount=('amount', lambda x: x[df_tx.loc[x.index, 'is_fraud'] == 1].sum())
            ).reset_index()
            merch_fraud['fraud_rate_%'] = (merch_fraud['fraud_count'] / merch_fraud['total_transactions']) * 100
            merch_fraud = merch_fraud.sort_values(by='fraud_rate_%', ascending=False)
            
            fig_bar = px.bar(
                merch_fraud, x='merch_category', y='fraud_rate_%',
                text_auto='.2f',
                labels={'merch_category': 'Merchant Category', 'fraud_rate_%': 'Fraud Rate (%)'},
                title="Fraud Incidence Rate by Category",
                color='fraud_amount',
                color_continuous_scale=px.colors.sequential.Reds
            )
            fig_bar.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#94a3b8',
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='#334155')
            )
            st.plotly_chart(fig_bar, width='stretch')

    # ------------------
    # MENU 2: CUSTOMER RISK EXPLORER
    # ------------------
    elif menu == "Customer Risk Explorer":
        st.title("👤 Customer Risk Explorer")
        st.markdown("Inspect customer financial details, search specific clients, and analyze individual risk parameters.")
        
        # Search panel
        search_col, stat_col = st.columns([1, 3])
        with search_col:
            st.subheader("Search Customer")
            cust_list = sorted(df_tx['customer_id'].unique())
            selected_cust_id = st.selectbox("Select Customer ID", cust_list)
            
            # Retrieve customer info
            cust_txs = df_tx[df_tx['customer_id'] == selected_cust_id].sort_values(by='timestamp', ascending=False)
            cust_profile = cust_txs.iloc[0] # Info is duplicated across transaction joins
            
            st.markdown("---")
            st.markdown("### Profile Details")
            st.markdown(f"**Name**: {cust_profile['cust_name']}")
            st.markdown(f"**Age / Gender**: {cust_profile['cust_age']} / {cust_profile['cust_gender']}")
            st.markdown(f"**Location**: {cust_profile['cust_city']}, {cust_profile['cust_state']}")
            st.markdown(f"**Credit Limit**: ${cust_profile['credit_limit']:,.2f}")
            
        with stat_col:
            st.subheader(f"Risk Dashboard for {cust_profile['cust_name']} ({selected_cust_id})")
            
            # Compute customer statistics
            total_cust_spend = cust_txs['amount'].sum()
            avg_cust_spend = cust_txs['amount'].mean()
            max_cust_risk = cust_txs['risk_score'].max()
            cust_fraud_count = cust_txs['is_fraud'].sum()
            
            # Customer KPI columns
            c_col1, c_col2, c_col3, c_col4 = st.columns(4)
            with c_col1:
                st.metric("Total Spending", f"${total_cust_spend:,.2f}")
            with c_col2:
                st.metric("Avg Transaction", f"${avg_cust_spend:,.2f}")
            with c_col3:
                # Color risk metric
                risk_status = "NORMAL"
                if max_cust_risk >= 75.0:
                    risk_status = "CRITICAL"
                elif max_cust_risk >= 50.0:
                    risk_status = "WARNING"
                st.metric("Max Risk Score", f"{max_cust_risk:.1f}%", delta=risk_status, delta_color="inverse" if risk_status != "NORMAL" else "normal")
            with c_col4:
                st.metric("Confirmed Frauds", f"{cust_fraud_count}")
                
            st.write("---")
            
            # Plot transaction history scatter colored by risk score
            st.subheader("Transaction History & Risk Scoring")
            fig_cust_hist = px.scatter(
                cust_txs, x='timestamp', y='amount',
                color='risk_score',
                size='amount',
                hover_data=['merchant_id', 'merch_name', 'channel', 'is_fraud'],
                color_continuous_scale=px.colors.sequential.Jet,
                title="Historical Transaction Ledger with ML Risk Scores",
                labels={'timestamp': 'Date', 'amount': 'Amount ($)', 'risk_score': 'Risk Score'}
            )
            fig_cust_hist.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#94a3b8',
                xaxis=dict(showgrid=True, gridcolor='#334155'),
                yaxis=dict(showgrid=True, gridcolor='#334155')
            )
            st.plotly_chart(fig_cust_hist, width='stretch')
            
            # Show transaction logs
            st.subheader("Detailed Transaction Log")
            st.dataframe(
                cust_txs[['transaction_id', 'timestamp', 'merch_name', 'amount', 'channel', 'is_fraud', 'risk_score']]
                .rename(columns={'merch_name': 'Merchant', 'amount': 'Amount ($)', 'channel': 'Channel', 'is_fraud': 'Fraud Label', 'risk_score': 'ML Risk Score (%)'}),
                width='stretch'
            )

    # ------------------
    # MENU 3: MERCHANT RISK PROFILES
    # ------------------
    elif menu == "Merchant Risk Profiles":
        st.title("🛍️ Merchant Risk Profiles")
        st.markdown("Analyze merchant vulnerability, check category risks, and identify compromised terminal nodes.")
        
        # Layout: Category list + High-risk merchant list
        m_col1, m_col2 = st.columns([1, 1])
        
        with m_col1:
            st.subheader("Merchant Categories Risk Profile")
            merch_profile = df_tx.groupby('merch_category').agg(
                total_tx=('transaction_id', 'count'),
                avg_amount=('amount', 'mean'),
                fraud_count=('is_fraud', 'sum'),
                avg_risk_score=('risk_score', 'mean')
            ).reset_index()
            
            fig_m_bar = px.bar(
                merch_profile.sort_values(by='avg_risk_score', ascending=False),
                x='merch_category', y='avg_risk_score',
                labels={'merch_category': 'Category', 'avg_risk_score': 'Avg ML Risk Score (%)'},
                title="Average Model Risk Score by Category",
                color_discrete_sequence=['#3b82f6']
            )
            fig_m_bar.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#94a3b8',
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='#334155')
            )
            st.plotly_chart(fig_m_bar, width='stretch')
            
        with m_col2:
            st.subheader("Top 10 Highest Risk Merchant Terminals")
            # Group by merchant name
            merch_individual = df_tx.groupby(['merchant_id', 'merch_name', 'merch_category']).agg(
                total_tx=('transaction_id', 'count'),
                fraud_count=('is_fraud', 'sum'),
                avg_risk_score=('risk_score', 'mean'),
                total_fraud_loss=('amount', lambda x: x[df_tx.loc[x.index, 'is_fraud'] == 1].sum())
            ).reset_index()
            
            top_risk_merch = merch_individual.sort_values(by='avg_risk_score', ascending=False).head(10)
            
            st.dataframe(
                top_risk_merch[['merch_name', 'merch_category', 'total_tx', 'fraud_count', 'total_fraud_loss', 'avg_risk_score']]
                .rename(columns={
                    'merch_name': 'Merchant Name',
                    'merch_category': 'Category',
                    'total_tx': 'Total Transacts',
                    'fraud_count': 'Confirmed Frauds',
                    'total_fraud_loss': 'Loss ($)',
                    'avg_risk_score': 'Avg Risk Score (%)'
                }),
                width='stretch',
                hide_index=True
            )
            
        st.write("---")
        st.subheader("Distribution of Transaction Channels")
        
        # Breakdown of Channels
        channel_df = df_tx.groupby('channel').agg(
            tx_count=('transaction_id', 'count'),
            fraud_count=('is_fraud', 'sum'),
            total_loss=('amount', lambda x: x[df_tx.loc[x.index, 'is_fraud'] == 1].sum())
        ).reset_index()
        channel_df['fraud_rate_%'] = (channel_df['fraud_count'] / channel_df['tx_count']) * 100
        
        ch_col1, ch_col2, ch_col3 = st.columns(3)
        for i, row in channel_df.iterrows():
            ch = row['channel'].upper()
            with [ch_col1, ch_col2, ch_col3][i]:
                st.markdown(f"""
                <div class="metric-container">
                    <div class="metric-title">{ch} CHANNEL</div>
                    <div class="metric-value">${row['total_loss']:,.2f} Loss</div>
                    <div style="font-size: 0.9rem; margin-top: 0.5rem;">
                        <span>Transacts: <b>{row['tx_count']:,}</b></span><br/>
                        <span style="color: #f87171;">Fraud rate: <b>{row['fraud_rate_%']:.2f}%</b></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ------------------
    # MENU 4: ALERT RESOLUTION CENTER
    # ------------------
    elif menu == "Alert Resolution Center":
        st.title("🚨 Alert Resolution Center")
        st.markdown("Review and update risk alerts triggered by the hybrid XGBoost & Anomaly Detection models.")
        
        # Display alerts list
        st.subheader("System Alert Log")
        
        # Filters
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            status_filter = st.multiselect("Filter by Status", ['PENDING', 'INVESTIGATING', 'RESOLVED_FRAUD', 'RESOLVED_FALSE_POSITIVE'], default=['PENDING', 'INVESTIGATING'])
        with f_col2:
            severity_filter = st.multiselect("Filter by Severity", ['LOW', 'MEDIUM', 'HIGH'], default=['MEDIUM', 'HIGH'])
        with f_col3:
            search_name = st.text_input("Search Customer Name")
            
        # Apply filters
        filtered_alerts = df_alerts.copy()
        if status_filter:
            filtered_alerts = filtered_alerts[filtered_alerts['status'].isin(status_filter)]
        if severity_filter:
            filtered_alerts = filtered_alerts[filtered_alerts['severity'].isin(severity_filter)]
        if search_name:
            filtered_alerts = filtered_alerts[filtered_alerts['cust_name'].str.contains(search_name, case=False)]
            
        # Display alerts table
        st.write(f"Showing {len(filtered_alerts)} Alerts")
        st.dataframe(
            filtered_alerts[['alert_id', 'transaction_id', 'status', 'severity', 'cust_name', 'merch_name', 'amount', 'risk_score', 'notes']]
            .rename(columns={
                'alert_id': 'Alert ID',
                'transaction_id': 'Tx ID',
                'status': 'Status',
                'severity': 'Severity',
                'cust_name': 'Customer',
                'merch_name': 'Merchant',
                'amount': 'Amount ($)',
                'risk_score': 'Risk Score (%)',
                'notes': 'Trigger Reasons'
            }),
            width='stretch',
            hide_index=True
        )
        
        # Action form to resolve alert
        st.write("---")
        st.subheader("Manage Alert Resolution")
        
        action_col1, action_col2 = st.columns([1, 2])
        
        with action_col1:
            alert_id_to_edit = st.number_input("Select Alert ID to Update", min_value=1, step=1)
            new_status = st.selectbox("Assign New Status", ['PENDING', 'INVESTIGATING', 'RESOLVED_FRAUD', 'RESOLVED_FALSE_POSITIVE'])
            new_notes = st.text_area("Resolution Notes / Comments")
            
            if st.button("Apply Status Change"):
                conn = get_connection()
                cursor = conn.cursor()
                
                # Check if alert exists
                cursor.execute("SELECT alert_id FROM alerts WHERE alert_id = ?", (alert_id_to_edit,))
                existing_alert = cursor.fetchone()
                
                if existing_alert:
                    # Update status and notes
                    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    updated_notes = f"{new_notes} (Updated at {now_str})"
                    
                    cursor.execute("""
                        UPDATE alerts
                        SET status = ?, notes = ?
                        WHERE alert_id = ?
                    """, (new_status, updated_notes, alert_id_to_edit))
                    conn.commit()
                    st.success(f"Alert ID {alert_id_to_edit} updated to {new_status} successfully!")
                    
                    # Refresh Cache
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Alert ID {alert_id_to_edit} not found in database.")
                conn.close()
                
        with action_col2:
            st.info("""
            💡 **Operational Guidelines**:
            
            1. **PENDING**: Alerts requiring initial triage. Handled automatically on ingest.
            2. **INVESTIGATING**: Account placed on temporary hold. Verification call scheduled with customer.
            3. **RESOLVED_FRAUD**: Card frozen and transaction chargeback initiated. Risk score fed back to ML model retraining pipe.
            4. **RESOLVED_FALSE_POSITIVE**: Customer whitelist updated. Model parameter weights updated to prevent similar noise.
            """)
