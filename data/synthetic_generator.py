import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
import uuid

# Set seed for reproducibility
np.random.seed(42)
random.seed(42)

CITIES = [
    {'city': 'New York', 'state': 'NY', 'lat': 40.7128, 'lon': -74.0060},
    {'city': 'Los Angeles', 'state': 'CA', 'lat': 34.0522, 'lon': -118.2437},
    {'city': 'Chicago', 'state': 'IL', 'lat': 41.8781, 'lon': -87.6298},
    {'city': 'Houston', 'state': 'TX', 'lat': 29.7604, 'lon': -95.3698},
    {'city': 'Miami', 'state': 'FL', 'lat': 25.7617, 'lon': -80.1918},
    {'city': 'Seattle', 'state': 'WA', 'lat': 47.6062, 'lon': -122.3321},
    {'city': 'Boston', 'state': 'MA', 'lat': 42.3601, 'lon': -71.0589},
    {'city': 'San Francisco', 'state': 'CA', 'lat': 37.7749, 'lon': -122.4194},
    {'city': 'Austin', 'state': 'TX', 'lat': 30.2672, 'lon': -97.7431},
    {'city': 'Denver', 'state': 'CO', 'lat': 39.7392, 'lon': -104.9903}
]

MERCHANT_CATEGORIES = {
    'Groceries': {'min_amt': 10, 'max_amt': 250, 'base_risk': 0.05},
    'Dining': {'min_amt': 15, 'max_amt': 180, 'base_risk': 0.08},
    'Travel': {'min_amt': 150, 'max_amt': 3000, 'base_risk': 0.25},
    'Luxury': {'min_amt': 300, 'max_amt': 5000, 'base_risk': 0.35},
    'Retail': {'min_amt': 20, 'max_amt': 600, 'base_risk': 0.12},
    'Entertainment': {'min_amt': 10, 'max_amt': 300, 'base_risk': 0.09},
    'Utilities': {'min_amt': 40, 'max_amt': 400, 'base_risk': 0.02},
    'ATM/Cash': {'min_amt': 20, 'max_amt': 1000, 'base_risk': 0.15}
}

FIRST_NAMES = ['John', 'Jane', 'Michael', 'Emily', 'David', 'Sarah', 'James', 'Jessica', 'Robert', 'Ashley',
               'William', 'Amanda', 'Joseph', 'Melissa', 'Christopher', 'Stephanie', 'Daniel', 'Nicole', 'Matthew', 'Elizabeth']
LAST_NAMES = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Miller', 'Davis', 'Garcia', 'Rodriguez', 'Wilson',
              'Martinez', 'Anderson', 'Taylor', 'Thomas', 'Hernandez', 'Moore', 'Martin', 'Jackson', 'Thompson', 'White']

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points in miles."""
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 3956 # Radius of earth in miles
    return c * r

def generate_customers(n=1000):
    customers = []
    start_date = datetime(2023, 1, 1)
    
    for i in range(n):
        cust_id = f"CUST{i:04d}"
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower()}{i}@example.com"
        age = int(np.clip(np.random.normal(42, 15), 18, 85))
        gender = random.choice(['Male', 'Female', 'Other'])
        
        city_info = random.choice(CITIES)
        # Jitter lat/lon around the city center (approx 10-15 miles)
        lat = city_info['lat'] + np.random.normal(0, 0.15)
        lon = city_info['lon'] + np.random.normal(0, 0.15)
        
        signup_days = random.randint(0, 730)
        signup_date = (start_date + timedelta(days=signup_days)).strftime('%Y-%m-%d')
        
        credit_limit = float(random.choice([1500, 3000, 5000, 10000, 15000, 25000]))
        
        customers.append({
            'customer_id': cust_id,
            'name': name,
            'email': email,
            'age': age,
            'gender': gender,
            'state': city_info['state'],
            'city': city_info['city'],
            'latitude': lat,
            'longitude': lon,
            'signup_date': signup_date,
            'credit_limit': credit_limit
        })
        
    return pd.DataFrame(customers)

def generate_merchants(n=150):
    merchants = []
    categories = list(MERCHANT_CATEGORIES.keys())
    
    for i in range(n):
        merch_id = f"MERCH{i:04d}"
        category = random.choice(categories)
        name = f"{category} Store #{random.randint(100, 999)}"
        
        city_info = random.choice(CITIES)
        # Jitter coordinates around the city
        lat = city_info['lat'] + np.random.normal(0, 0.2)
        lon = city_info['lon'] + np.random.normal(0, 0.2)
        
        base_risk = MERCHANT_CATEGORIES[category]['base_risk']
        
        merchants.append({
            'merchant_id': merch_id,
            'name': name,
            'category': category,
            'latitude': lat,
            'longitude': lon,
            'base_risk_score': base_risk
        })
        
    return pd.DataFrame(merchants)

def generate_transactions(df_cust, df_merch, n_tx=40000):
    transactions = []
    
    # Timeline: Jan 1, 2025 to Jan 1, 2026
    start_time = datetime(2025, 1, 1, 0, 0, 0)
    
    cust_list = df_cust.to_dict('records')
    merch_list = df_merch.to_dict('records')
    
    # Store customer last transaction timestamp and location for geographic velocity checks
    cust_last_tx = {}
    
    # Distribute transaction timestamps
    time_deltas = np.random.exponential(13.0, n_tx) # Average ~13 minutes between transactions globally
    current_time = start_time
    
    print(f"Generating {n_tx} transactions...")
    
    for i in range(n_tx):
        tx_id = f"TX{i:06d}"
        current_time += timedelta(minutes=float(time_deltas[i]))
        
        # Pick customer and merchant
        cust = random.choice(cust_list)
        merch = random.choice(merch_list)
        
        # Determine channel
        channel = random.choice(['in-store', 'online', 'atm'])
        if merch['category'] == 'ATM/Cash':
            channel = 'atm'
        elif channel == 'atm':
            # Force merchant category to match ATM
            merch = random.choice([m for m in merch_list if m['category'] == 'ATM/Cash'])
            
        # Standard transaction amount parameters based on category
        cat_params = MERCHANT_CATEGORIES[merch['category']]
        amount = np.random.lognormal(
            mean=np.log((cat_params['min_amt'] + cat_params['max_amt'])/2),
            sigma=0.6
        )
        amount = np.clip(amount, cat_params['min_amt'], cat_params['max_amt'])
        amount = round(float(amount), 2)
        
        # Standard location
        if channel == 'in-store' or channel == 'atm':
            # Local transaction: within a small radius of customer's home
            tx_lat = cust['latitude'] + np.random.normal(0, 0.05)
            tx_lon = cust['longitude'] + np.random.normal(0, 0.05)
        else: # online
            # Online transaction location is server/merchant center or random
            tx_lat = merch['latitude']
            tx_lon = merch['longitude']
            
        # Setup base fraud indicators
        is_fraud = 0
        fraud_category = None
        
        # Geolocation distance check for velocity anomaly simulation
        is_velocity_anomaly = False
        hours_since_last = 0
        dist_miles = 0
        
        if cust['customer_id'] in cust_last_tx:
            last_tx = cust_last_tx[cust['customer_id']]
            last_time = last_tx['timestamp']
            hours_since_last = (current_time - last_time).total_seconds() / 3600.0
            
            dist_miles = haversine_distance(
                last_tx['lat'], last_tx['lon'],
                tx_lat, tx_lon
            )
            
            # If distance is greater than 100 miles and time is less than 2 hours (impossible velocity)
            if dist_miles > 100 and hours_since_last < 2.0 and hours_since_last > 0:
                is_velocity_anomaly = True
                
        # Fraud injection probability (1.8% base target)
        fraud_roll = random.random()
        
        # Scenario 1: Natural physical velocity anomaly (Card Cloning)
        if is_velocity_anomaly and fraud_roll < 0.65:
            is_fraud = 1
            fraud_category = 'Card Cloning'
            # Enhance transaction details to look suspicious
            amount = round(amount * random.uniform(1.5, 3.5), 2)
            
        # Scenario 2: Late-night high-value online spend (Account Takeover / Phishing)
        elif (current_time.hour >= 1 and current_time.hour <= 5) and channel == 'online' and fraud_roll < 0.12:
            is_fraud = 1
            fraud_category = 'Account Takeover'
            # Huge transaction amount relative to credit limit
            amount = round(min(cust['credit_limit'] * random.uniform(0.3, 0.75), 4500.0), 2)
            
        # Scenario 3: Stolen Card testing pattern (multiple high-frequency small payments)
        elif i > 5 and fraud_roll < 0.005:
            # We will force a sequence of transactions for this customer as a stolen card testing run
            is_fraud = 1
            fraud_category = 'Stolen Card'
            amount = round(random.uniform(1.0, 15.0), 2)
            channel = 'online'
            
        # Scenario 4: Random high-risk merchant fraud
        elif merch['base_risk_score'] >= 0.25 and fraud_roll < 0.08:
            is_fraud = 1
            fraud_category = 'Phishing'
            amount = round(amount * random.uniform(2.0, 5.0), 2)
            
        # Ensure transaction fits within credit limit
        if amount > cust['credit_limit']:
            amount = round(cust['credit_limit'] * random.uniform(0.1, 0.4), 2)
            
        # Record transaction
        tx_record = {
            'transaction_id': tx_id,
            'customer_id': cust['customer_id'],
            'merchant_id': merch['merchant_id'],
            'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'amount': amount,
            'channel': channel,
            'latitude': tx_lat,
            'longitude': tx_lon,
            'is_fraud': is_fraud,
            'fraud_category': fraud_category,
            'anomaly_score': 0.0, # Filled by model later
            'risk_score': 0.0     # Filled by model later
        }
        transactions.append(tx_record)
        
        # Update last transaction status
        cust_last_tx[cust['customer_id']] = {
            'timestamp': current_time,
            'lat': tx_lat,
            'lon': tx_lon
        }
        
    return pd.DataFrame(transactions)

def generate_all_data(n_cust=1000, n_merch=150, n_tx=40000):
    print("Generating Customers...")
    df_cust = generate_customers(n_cust)
    
    print("Generating Merchants...")
    df_merch = generate_merchants(n_merch)
    
    print("Generating Transactions...")
    df_tx = generate_transactions(df_cust, df_merch, n_tx)
    
    # Calculate global fraud percentage
    fraud_pct = (df_tx['is_fraud'].sum() / len(df_tx)) * 100
    print(f"Generated {len(df_tx)} transactions. Total Fraud: {df_tx['is_fraud'].sum()} ({fraud_pct:.2f}%)")
    
    return df_cust, df_merch, df_tx

if __name__ == '__main__':
    df_cust, df_merch, df_tx = generate_all_data()
    # Test output sizes
    print("Customer shape:", df_cust.shape)
    print("Merchant shape:", df_merch.shape)
    print("Transaction shape:", df_tx.shape)
