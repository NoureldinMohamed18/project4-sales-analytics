import sqlite3
from pathlib import Path
import numpy as np
import pandas as pd

DB_PATH = Path("data/sales.db")
PRODUCTS = {
    "Laptop Pro": ("Electronics", 15000), "27in Monitor": ("Electronics", 5200),
    "Gaming Mouse": ("Accessories", 450), "Mechanical Keyboard": ("Accessories", 1200),
    "Headset": ("Accessories", 900), "Smartphone X": ("Mobiles", 12000),
    "Smartphone Lite": ("Mobiles", 6000), "Office Chair": ("Furniture", 3500),
    "Standing Desk": ("Furniture", 8000), "Router AX": ("Networking", 1800),
}
BRANCHES = ["Cairo", "Alexandria", "Giza", "Mansoura"]

def generate(n=5000, seed=42):
    rng = np.random.default_rng(seed)
    days = (rng.beta(1.4, 1.0, n) * 730).astype(int)
    dates = pd.Timestamp("2023-01-01") + pd.to_timedelta(days, unit="D")
    names = list(PRODUCTS)
    product = rng.choice(names, n)
    category = np.array([PRODUCTS[p][0] for p in product])
    price = np.array([PRODUCTS[p][1] for p in product], dtype=float)
    df = pd.DataFrame({
        "order_id": np.arange(1, n + 1), "order_date": dates.strftime("%Y-%m-%d"),
        "branch": rng.choice(BRANCHES, n, p=[0.4, 0.25, 0.2, 0.15]),
        "customer_id": rng.integers(1, 301, n), "product": product, "category": category,
        "quantity": rng.integers(1, 6, n), "unit_price": price,
        "discount": rng.choice([0, 0, 0, 0.05, 0.10, 0.15], n),
    })
    df["total_amount"] = (df["quantity"] * df["unit_price"] * (1 - df["discount"])).round(2)
    return df.sort_values("order_date").reset_index(drop=True)

if __name__ == "__main__":
    DB_PATH.parent.mkdir(exist_ok=True)
    df = generate()
    with sqlite3.connect(DB_PATH) as conn:
        df.to_sql("sales", conn, if_exists="replace", index=False)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(order_date)")
    print(f"rows: {len(df)}")
