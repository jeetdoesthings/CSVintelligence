import os
import pandas as pd
import numpy as np

os.makedirs("datasets", exist_ok=True)
np.random.seed(42)

print("Generating 10 synthetic CSV datasets...")

# -------------------------------------------------------------
# 1. E-Commerce Orders Dataset (1,500 rows)
# -------------------------------------------------------------
categories = {
    "Electronics": ["MacBook Pro 16", "Sony WH-1000XM5", "Dell UltraSharp 32", "iPad Pro 12.9", "Logitech MX Master 3S"],
    "Home & Office": ["Ergonomic Desk Chair", "Electric Standing Desk", "LED Desk Lamp", "Monitor Arm Mount"],
    "Apparel": ["Merino Wool Sweater", "Waterproof Shell Jacket", "Athletic Joggers", "Leather Oxford Shoes"],
    "Fitness": ["Adjustable Dumbbell Set", "Yoga Mat Pro", "Smart Fitness Tracker", "Resistance Bands Set"]
}
regions = ["North America", "Western Europe", "Asia-Pacific", "Latin America", "Middle East"]
segments = ["Enterprise", "Mid-Market", "Consumer", "Small Business"]
pay_methods = ["Credit Card", "PayPal", "Bank Wire", "Apple Pay"]

rows_1 = []
start_date = pd.Timestamp("2024-01-01")
for i in range(1500):
    cat = np.random.choice(list(categories.keys()))
    prod = np.random.choice(categories[cat])
    reg = np.random.choice(regions)
    seg = np.random.choice(segments)
    date_val = start_date + pd.Timedelta(days=np.random.randint(0, 365))
    units = np.random.randint(1, 10)
    base_price = {"Electronics": 650, "Home & Office": 320, "Apparel": 95, "Fitness": 140}[cat]
    unit_price = int(base_price * (0.85 + np.random.uniform(0, 0.4)))
    discount = np.random.choice([0.0, 0.05, 0.10, 0.15, 0.20])
    gross_rev = units * unit_price
    revenue = int(gross_rev * (1 - discount))
    cost = int(revenue * np.random.uniform(0.45, 0.70))
    profit = revenue - cost
    
    rows_1.append({
        "order_id": f"ORD-{2024000 + i}",
        "order_date": date_val.strftime("%Y-%m-%d"),
        "customer_segment": seg,
        "region": reg,
        "category": cat,
        "product_name": prod,
        "units_sold": units,
        "unit_price": unit_price,
        "discount_percent": int(discount * 100),
        "revenue": revenue,
        "cost": cost,
        "profit": profit,
        "payment_method": np.random.choice(pay_methods)
    })

pd.DataFrame(rows_1).to_csv("datasets/01_ecommerce_orders.csv", index=False)
print("✓ 01_ecommerce_orders.csv (1,500 rows)")

# -------------------------------------------------------------
# 2. SaaS Subscriptions Dataset (1,200 rows)
# -------------------------------------------------------------
tiers = ["Starter", "Professional", "Business", "Enterprise"]
cycles = ["Monthly", "Annual"]
plan_mrr = {"Starter": 49, "Professional": 199, "Business": 599, "Enterprise": 2400}
rows_2 = []
for i in range(1200):
    tier = np.random.choice(tiers, p=[0.35, 0.35, 0.20, 0.10])
    cycle = np.random.choice(cycles, p=[0.45, 0.55])
    mrr = int(plan_mrr[tier] * np.random.uniform(0.9, 1.25))
    seats = {"Starter": np.random.randint(1, 5), "Professional": np.random.randint(5, 25), "Business": np.random.randint(25, 100), "Enterprise": np.random.randint(100, 500)}[tier]
    arr = mrr * 12
    usage_score = np.random.randint(30, 100)
    churn_risk = "Low" if usage_score > 70 else ("Medium" if usage_score > 50 else "High")
    status = np.random.choice(["Active", "Active", "Active", "At Risk", "Churned"], p=[0.75, 0.10, 0.05, 0.06, 0.04])
    
    rows_2.append({
        "subscription_id": f"SUB-{10000 + i}",
        "signup_date": (start_date + pd.Timedelta(days=np.random.randint(0, 365))).strftime("%Y-%m-%d"),
        "plan_tier": tier,
        "billing_cycle": cycle,
        "monthly_recurring_revenue": mrr,
        "annual_contract_value": arr,
        "seats_purchased": seats,
        "usage_score": usage_score,
        "churn_risk": churn_risk,
        "status": status,
        "region": np.random.choice(regions)
    })

pd.DataFrame(rows_2).to_csv("datasets/02_saas_subscriptions.csv", index=False)
print("✓ 02_saas_subscriptions.csv (1,200 rows)")

# -------------------------------------------------------------
# 3. Healthcare Patient Admissions (1,000 rows)
# -------------------------------------------------------------
depts = ["Cardiology", "Neurology", "Orthopedics", "Oncology", "Pediatrics", "Emergency"]
insurers = ["BlueCross", "Aetna", "UnitedHealth", "Medicare", "Cigna"]
diagnoses = ["Hypertension", "Acute Fracture", "Pneumonia", "Coronary Artery Disease", "Arrhythmia", "Stroke Rehab"]
rows_3 = []
for i in range(1000):
    dept = np.random.choice(depts)
    stay = np.random.randint(1, 21)
    base_cost = {"Cardiology": 1800, "Neurology": 2200, "Orthopedics": 1600, "Oncology": 2800, "Pediatrics": 1100, "Emergency": 950}[dept]
    total_bill = int(stay * base_cost + np.random.uniform(500, 5000))
    age = np.random.randint(18, 88)
    
    rows_3.append({
        "patient_id": f"PAT-{3000 + i}",
        "admission_date": (start_date + pd.Timedelta(days=np.random.randint(0, 365))).strftime("%Y-%m-%d"),
        "age": age,
        "gender": np.random.choice(["Male", "Female"]),
        "department": dept,
        "diagnosis": np.random.choice(diagnoses),
        "length_of_stay_days": stay,
        "total_bill_amount": total_bill,
        "insurance_provider": np.random.choice(insurers),
        "medication_count": np.random.randint(1, 8),
        "readmitted_30_days": np.random.choice(["No", "No", "No", "Yes"])
    })

pd.DataFrame(rows_3).to_csv("datasets/03_healthcare_admissions.csv", index=False)
print("✓ 03_healthcare_admissions.csv (1,000 rows)")

# -------------------------------------------------------------
# 4. Finance Banking Transactions (2,000 rows)
# -------------------------------------------------------------
merchants = ["Groceries", "Airlines & Travel", "Restaurants", "Online Retail", "Entertainment", "Utilities", "Gas Stations"]
rows_4 = []
for i in range(2000):
    cat = np.random.choice(merchants)
    amt = int(np.random.exponential(scale=120) + 5)
    risk = int(np.clip(np.random.normal(25, 20), 1, 99))
    if amt > 800:
        risk = int(np.clip(risk + 40, 1, 99))
    fraud = "Yes" if risk > 85 else "No"
    
    rows_4.append({
        "transaction_id": f"TXN-{800000 + i}",
        "transaction_date": (start_date + pd.Timedelta(days=np.random.randint(0, 365))).strftime("%Y-%m-%d"),
        "account_type": np.random.choice(["Checking", "Savings", "Credit Card", "Business Platinum"]),
        "merchant_category": cat,
        "transaction_amount": amt,
        "fee_amount": round(amt * 0.018, 2),
        "channel": np.random.choice(["Mobile App", "Online Web", "In-Store POS", "ATM"]),
        "is_international": np.random.choice(["No", "No", "No", "Yes"]),
        "risk_score": risk,
        "fraud_flag": fraud
    })

pd.DataFrame(rows_4).to_csv("datasets/04_finance_banking_transactions.csv", index=False)
print("✓ 04_finance_banking_transactions.csv (2,000 rows)")

# -------------------------------------------------------------
# 5. HR Workforce & Salaries (1,000 rows)
# -------------------------------------------------------------
hr_depts = ["Engineering", "Product", "Sales", "Marketing", "Finance", "Human Resources", "Customer Support"]
base_salaries = {"Engineering": 135000, "Product": 125000, "Sales": 95000, "Marketing": 90000, "Finance": 110000, "Human Resources": 80000, "Customer Support": 62000}
rows_5 = []
for i in range(1000):
    dept = np.random.choice(hr_depts)
    tenure = np.random.randint(1, 15)
    sal = int(base_salaries[dept] * (1 + tenure * 0.04) * np.random.uniform(0.9, 1.2))
    perf = np.random.choice([2, 3, 4, 5], p=[0.08, 0.45, 0.35, 0.12])
    bonus = int(sal * (perf * 0.035))
    satisfaction = np.random.randint(40, 100)
    attrition = "Yes" if satisfaction < 55 and perf > 3 else "No"
    
    rows_5.append({
        "employee_id": f"EMP-{5000 + i}",
        "hire_date": (pd.Timestamp("2015-01-01") + pd.Timedelta(days=np.random.randint(0, 3000))).strftime("%Y-%m-%d"),
        "department": dept,
        "education_level": np.random.choice(["Bachelor", "Master", "PhD", "Associate"]),
        "performance_rating": perf,
        "annual_salary": sal,
        "bonus_amount": bonus,
        "tenure_years": tenure,
        "satisfaction_score": satisfaction,
        "attrition": attrition
    })

pd.DataFrame(rows_5).to_csv("datasets/05_hr_workforce_salaries.csv", index=False)
print("✓ 05_hr_workforce_salaries.csv (1,000 rows)")

# -------------------------------------------------------------
# 6. Digital Marketing Campaigns (800 rows)
# -------------------------------------------------------------
platforms = ["Google Ads", "Meta Ads", "LinkedIn Ads", "TikTok Ads", "YouTube Ads", "Twitter/X"]
rows_6 = []
for i in range(800):
    plat = np.random.choice(platforms)
    spend = int(np.random.uniform(500, 15000))
    cpm = {"Google Ads": 24, "Meta Ads": 18, "LinkedIn Ads": 45, "TikTok Ads": 12, "YouTube Ads": 20, "Twitter/X": 15}[plat]
    impressions = int((spend / cpm) * 1000)
    ctr = np.random.uniform(0.015, 0.048)
    clicks = int(impressions * ctr)
    cvr = np.random.uniform(0.03, 0.09)
    conversions = int(clicks * cvr)
    val_per_conv = np.random.uniform(75, 250)
    rev = int(conversions * val_per_conv)
    roas = round(rev / spend, 2) if spend > 0 else 0
    
    rows_6.append({
        "campaign_id": f"CMP-{1000 + i}",
        "launch_date": (start_date + pd.Timedelta(days=np.random.randint(0, 365))).strftime("%Y-%m-%d"),
        "platform": plat,
        "target_audience": np.random.choice(["B2B Decision Makers", "Tech Enthusiasts", "Small Business Owners", "Gen Z Shoppers", "Affluent Homeowners"]),
        "ad_spend": spend,
        "impressions": impressions,
        "clicks": clicks,
        "conversions": conversions,
        "revenue_generated": rev,
        "roas": roas
    })

pd.DataFrame(rows_6).to_csv("datasets/06_digital_marketing_campaigns.csv", index=False)
print("✓ 06_digital_marketing_campaigns.csv (800 rows)")

# -------------------------------------------------------------
# 7. Supply Chain Logistics (1,500 rows)
# -------------------------------------------------------------
modes = ["Air Freight", "Ocean Cargo", "Rail Transit", "Express Roadway"]
hubs = ["Chicago Gateway", "Rotterdam Port", "Singapore Terminal", "Shenzhen Hub", "Dallas Depot"]
rows_7 = []
for i in range(1500):
    mode = np.random.choice(modes)
    hub = np.random.choice(hubs)
    weight = int(np.random.uniform(50, 4500))
    rate = {"Air Freight": 4.5, "Ocean Cargo": 0.8, "Rail Transit": 1.2, "Express Roadway": 2.1}[mode]
    freight_cost = int(weight * rate + np.random.uniform(100, 500))
    est_days = {"Air Freight": 2, "Express Roadway": 4, "Rail Transit": 8, "Ocean Cargo": 24}[mode]
    actual_days = int(max(1, est_days + np.random.normal(0, 2)))
    delay = max(0, actual_days - est_days)
    
    rows_7.append({
        "shipment_id": f"SHP-{70000 + i}",
        "dispatch_date": (start_date + pd.Timedelta(days=np.random.randint(0, 365))).strftime("%Y-%m-%d"),
        "origin_hub": hub,
        "destination_country": np.random.choice(["USA", "Germany", "Japan", "UK", "Australia", "Brazil", "Canada"]),
        "transport_mode": mode,
        "freight_cost": freight_cost,
        "weight_kg": weight,
        "estimated_days": est_days,
        "actual_days": actual_days,
        "delay_days": delay,
        "carrier_rating": round(np.random.uniform(3.0, 5.0), 1)
    })

pd.DataFrame(rows_7).to_csv("datasets/07_supply_chain_logistics.csv", index=False)
print("✓ 07_supply_chain_logistics.csv (1,500 rows)")

# -------------------------------------------------------------
# 8. Real Estate Property Sales (1,000 rows)
# -------------------------------------------------------------
cities = ["Seattle", "Austin", "Denver", "Boston", "San Diego", "Atlanta", "Miami"]
prop_types = ["Single Family Home", "Condo", "Townhouse", "Multi-Family"]
rows_8 = []
for i in range(1000):
    city = np.random.choice(cities)
    sqft = int(np.random.uniform(850, 4200))
    beds = int(np.clip(sqft // 600, 1, 6))
    baths = round(beds * 0.75 + np.random.choice([0, 0.5, 1]), 1)
    base_sqft_price = {"Seattle": 580, "Austin": 390, "Denver": 420, "Boston": 620, "San Diego": 650, "Atlanta": 290, "Miami": 480}[city]
    list_price = int(sqft * base_sqft_price * np.random.uniform(0.9, 1.15))
    discount_pct = np.random.uniform(-0.04, 0.05)
    sale_price = int(list_price * (1 - discount_pct))
    dom = np.random.randint(4, 95)
    
    rows_8.append({
        "property_id": f"PROP-{2000 + i}",
        "listing_date": (start_date + pd.Timedelta(days=np.random.randint(0, 365))).strftime("%Y-%m-%d"),
        "city": city,
        "property_type": np.random.choice(prop_types),
        "bedrooms": beds,
        "bathrooms": baths,
        "square_feet": sqft,
        "year_built": np.random.randint(1975, 2024),
        "list_price": list_price,
        "sale_price": sale_price,
        "days_on_market": dom
    })

pd.DataFrame(rows_8).to_csv("datasets/08_real_estate_property_sales.csv", index=False)
print("✓ 08_real_estate_property_sales.csv (1,000 rows)")

# -------------------------------------------------------------
# 9. Streaming Media Viewership (1,500 rows)
# -------------------------------------------------------------
genres = ["Sci-Fi", "Crime Drama", "Comedy", "Documentary", "Action Thriller", "Animation"]
devices = ["Smart TV", "Mobile Phone", "Laptop Browser", "Tablet", "Gaming Console"]
rows_9 = []
for i in range(1500):
    genre = np.random.choice(genres)
    dur = int(np.random.exponential(scale=65) + 10)
    rating = np.random.choice([1, 2, 3, 4, 5], p=[0.05, 0.08, 0.22, 0.40, 0.25])
    
    rows_9.append({
        "session_id": f"STRM-{90000 + i}",
        "watch_date": (start_date + pd.Timedelta(days=np.random.randint(0, 365))).strftime("%Y-%m-%d"),
        "user_tier": np.random.choice(["Premium 4K", "Standard HD", "Ad-Supported Basic"]),
        "genre": genre,
        "watch_duration_minutes": dur,
        "device_type": np.random.choice(devices),
        "user_rating": rating,
        "completed_stream": "Yes" if dur > 45 else "No"
    })

pd.DataFrame(rows_9).to_csv("datasets/09_streaming_media_viewership.csv", index=False)
print("✓ 09_streaming_media_viewership.csv (1,500 rows)")

# -------------------------------------------------------------
# 10. Cryptocurrency Market Daily (1,200 rows)
# -------------------------------------------------------------
tickers = [
    {"ticker": "BTC", "name": "Bitcoin", "base": 64000, "cap": 1250},
    {"ticker": "ETH", "name": "Ethereum", "base": 3400, "cap": 410},
    {"ticker": "SOL", "name": "Solana", "base": 155, "cap": 72},
    {"ticker": "AVAX", "name": "Avalanche", "base": 36, "cap": 14},
    {"ticker": "LINK", "name": "Chainlink", "base": 18, "cap": 11}
]
rows_10 = []
for t in tickers:
    price = t["base"]
    for day in range(240):
        dt = (start_date + pd.Timedelta(days=day)).strftime("%Y-%m-%d")
        pct_change = np.random.normal(0.001, 0.035)
        close_p = round(price * (1 + pct_change), 2)
        high_p = round(max(price, close_p) * (1 + abs(np.random.normal(0, 0.015))), 2)
        low_p = round(min(price, close_p) * (1 - abs(np.random.normal(0, 0.015))), 2)
        vol = int(np.random.uniform(500, 8500))
        cap = round(t["cap"] * (close_p / t["base"]), 2)
        
        rows_10.append({
            "record_id": f"{t['ticker']}-{day+100}",
            "trade_date": dt,
            "ticker_symbol": t["ticker"],
            "asset_name": t["name"],
            "open_price": round(price, 2),
            "high_price": high_p,
            "low_price": low_p,
            "close_price": close_p,
            "volume_millions": vol,
            "market_cap_billions": cap,
            "daily_return_percent": round(pct_change * 100, 2)
        })
        price = close_p

pd.DataFrame(rows_10).to_csv("datasets/10_cryptocurrency_market_daily.csv", index=False)
print("✓ 10_cryptocurrency_market_daily.csv (1,200 rows)")

print("\n✨ All 10 synthetic datasets generated successfully in ./datasets/!")
