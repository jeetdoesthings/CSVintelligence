"""Deterministically generate the built-in synthetic retail demo dataset.

Run:  python scripts/generate_sample_data.py
Output: sample_retail_sales_2024.csv (800 rows, no missing values)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 2024
ROWS = 800

PRODUCTS = {
    "Peripherals": [
        ("Precision Wireless Mouse", 39.0),
        ("Mechanical Keyboard Pro", 119.0),
        ("USB-C Docking Station", 179.0),
        ("4K Webcam Studio", 149.0),
        ("Noise-Cancelling Headset", 229.0),
    ],
    "Furniture": [
        ("Ergonomic Executive Chair", 640.0),
        ("Standing Desk 160cm", 780.0),
        ("Modular Storage Cabinet", 310.0),
        ("Conference Table", 1250.0),
    ],
    "Displays": [
        ("27-inch 4K Monitor", 420.0),
        ("34-inch Ultrawide Monitor", 690.0),
        ("Portable Travel Display", 260.0),
    ],
    "Computing": [
        ("Developer Laptop 14", 1690.0),
        ("Workstation Mini PC", 1120.0),
        ("Graphics Dock eGPU", 980.0),
        ("Tablet Studio 11", 820.0),
    ],
    "Accessories": [
        ("Aluminium Laptop Stand", 69.0),
        ("Braided USB-C Cable", 24.0),
        ("Travel Backpack 25L", 129.0),
        ("Desk Mat XL", 49.0),
        ("Cable Management Kit", 34.0),
    ],
}

REGIONS = ["North America", "Europe", "Asia-Pacific", "Latin America", "Middle East & Africa"]
SEGMENTS = ["Enterprise", "Mid-Market", "Small Business", "Consumer"]
MONTH_WEIGHTS = np.array([0.72, 0.74, 0.82, 0.86, 0.88, 0.91, 0.90, 0.93, 0.98, 1.06, 1.18, 1.32])


def main() -> None:
    rng = np.random.default_rng(SEED)
    categories = list(PRODUCTS.keys())
    cat_weights = np.array([0.30, 0.15, 0.20, 0.20, 0.15])

    dates = []
    for month, weight in enumerate(MONTH_WEIGHTS, start=1):
        n = int(round(ROWS * weight / MONTH_WEIGHTS.sum()))
        days = pd.period_range(f"2024-{month:02d}", periods=1, freq="M")[0].days_in_month
        dates.extend(pd.Timestamp(year=2024, month=month, day=int(rng.integers(1, days + 1))) for _ in range(n))
    while len(dates) < ROWS:
        dates.append(pd.Timestamp(year=2024, month=int(rng.integers(1, 13)), day=int(rng.integers(1, 28))))
    dates = sorted(dates[:ROWS])

    rows = []
    used_orders = set()
    for idx, order_date in enumerate(dates):
        category = str(rng.choice(categories, p=cat_weights))
        product, unit_price = PRODUCTS[category][int(rng.integers(0, len(PRODUCTS[category])))]
        region = str(rng.choice(REGIONS, p=[0.34, 0.27, 0.22, 0.11, 0.06]))
        segment = str(rng.choice(SEGMENTS, p=[0.32, 0.27, 0.26, 0.15]))
        units = int(rng.choice([1, 1, 1, 2, 2, 3, 4, 5, 7, 9], p=[0.16, 0.14, 0.12, 0.14, 0.11, 0.10, 0.09, 0.07, 0.04, 0.03]))
        discount = float(rng.choice([0, 0, 0, 5, 5, 10, 10, 15, 20, 25], p=[0.18, 0.14, 0.10, 0.14, 0.10, 0.12, 0.08, 0.07, 0.04, 0.03]))
        revenue = round(units * unit_price * (1 - discount / 100.0), 2)
        cost_ratio = float(rng.uniform(0.50, 0.82))
        cost = round(revenue * cost_ratio, 2)
        profit = round(revenue - cost, 2)
        order_id = f"ORD-2024-{1001 + idx}"
        while order_id in used_orders:
            order_id = f"ORD-2024-{1001 + idx}-{len(used_orders)}"
        used_orders.add(order_id)
        rows.append(
            {
                "order_id": order_id,
                "order_date": order_date.strftime("%Y-%m-%d"),
                "product": product,
                "category": category,
                "region": region,
                "units_sold": units,
                "unit_price": unit_price,
                "discount_percent": discount,
                "revenue": revenue,
                "cost": cost,
                "profit": profit,
                "customer_segment": segment,
            }
        )

    df = pd.DataFrame(rows)
    out = Path(__file__).resolve().parent.parent / "sample_retail_sales_2024.csv"
    df.to_csv(out, index=False)
    print(f"Wrote {len(df):,} deterministic rows to {out}")
    print(f"Revenue total: {df['revenue'].sum():,.2f}; profit total: {df['profit'].sum():,.2f}")


if __name__ == "__main__":
    main()
