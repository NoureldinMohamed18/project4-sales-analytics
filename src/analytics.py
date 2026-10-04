import os
import sqlite3
from functools import lru_cache
from pathlib import Path

import pandas as pd

DB_PATH = Path("data/sales.db")


def load_sales(db_path=DB_PATH):
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql("SELECT * FROM sales", conn)
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df


@lru_cache(maxsize=4)
def _cached(db_path, mtime):
    return load_sales(db_path)


def load_sales_cached(db_path=DB_PATH):
    """نحمّل من الـ DB مرة، ونعيد التحميل تلقائياً لما الملف يتغيّر (مثلاً بعد POST)."""
    path = str(db_path)
    return _cached(path, os.path.getmtime(path)).copy()


def filter_df(df, branch=None, date_from=None, date_to=None):
    if branch:
        df = df[df["branch"] == branch]
    if date_from:
        df = df[df["order_date"] >= pd.Timestamp(date_from)]
    if date_to:
        df = df[df["order_date"] <= pd.Timestamp(date_to)]
    return df


def summary(df):
    if df.empty:
        return {"orders": 0, "revenue": 0.0, "avg_order_value": 0.0,
                "customers": 0, "first_date": None, "last_date": None}
    return {
        "orders": int(len(df)),
        "revenue": round(float(df["total_amount"].sum()), 2),
        "avg_order_value": round(float(df["total_amount"].mean()), 2),
        "customers": int(df["customer_id"].nunique()),
        "first_date": df["order_date"].min().strftime("%Y-%m-%d"),
        "last_date": df["order_date"].max().strftime("%Y-%m-%d"),
    }


def by_branch(df):
    out = (df.groupby("branch")
             .agg(revenue=("total_amount", "sum"),
                  orders=("order_id", "count"),
                  avg_order=("total_amount", "mean"))
             .round(2)
             .sort_values("revenue", ascending=False)
             .reset_index())
    total = out["revenue"].sum()
    out["share_pct"] = (out["revenue"] / total * 100).round(1) if total else 0.0
    return out


def top_products(df, n=5):
    return (df.groupby(["product", "category"])
              .agg(revenue=("total_amount", "sum"), units=("quantity", "sum"))
              .round(2)
              .sort_values("revenue", ascending=False)
              .head(n)
              .reset_index())


def top_customers(df, n=5):
    return (df.groupby("customer_id")
              .agg(revenue=("total_amount", "sum"), orders=("order_id", "count"))
              .round(2)
              .sort_values("revenue", ascending=False)
              .head(n)
              .reset_index())


def monthly_sales(df):
    """مبيعات شهرية، والشهور الفاضية بتظهر بصفر مش بتختفي."""
    s = df.set_index("order_date")["total_amount"].resample("MS").sum()
    out = s.reset_index()
    out.columns = ["month", "revenue"]
    out["month"] = out["month"].dt.strftime("%Y-%m")
    out["revenue"] = out["revenue"].round(2)
    out["mom_growth_pct"] = (s.pct_change().replace([float("inf"), float("-inf")], 0)
                             * 100).round(1).fillna(0).values
    return out


def category_by_branch(df):
    return df.pivot_table(index="category", columns="branch",
                          values="total_amount", aggfunc="sum",
                          fill_value=0).round(0)
