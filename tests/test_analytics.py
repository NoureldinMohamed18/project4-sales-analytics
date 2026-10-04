import json

import pandas as pd

from src import analytics


def test_summary_matches_raw_data(db):
    df = analytics.load_sales(db)
    s = analytics.summary(df)
    assert s["orders"] == len(df)
    assert s["revenue"] == round(df["total_amount"].sum(), 2)


def test_summary_is_json_serializable(db):
    # أنواع NumPy كانت هتكسر ده (int64 مش JSON)
    json.dumps(analytics.summary(analytics.load_sales(db)))


def test_summary_of_empty_data_does_not_crash(db):
    empty = analytics.filter_df(analytics.load_sales(db), date_from="2999-01-01")
    assert analytics.summary(empty)["orders"] == 0
    assert analytics.monthly_sales(empty).empty


def test_branch_shares_add_up_to_100(db):
    b = analytics.by_branch(analytics.load_sales(db))
    assert abs(b["share_pct"].sum() - 100) < 0.5
    assert b["revenue"].is_monotonic_decreasing


def test_monthly_sales_keeps_empty_months_as_zero():
    df = pd.DataFrame({
        "order_date": pd.to_datetime(["2024-01-10", "2024-03-05"]),
        "total_amount": [100.0, 300.0],
    })
    m = analytics.monthly_sales(df)
    assert list(m["month"]) == ["2024-01", "2024-02", "2024-03"]
    assert list(m["revenue"]) == [100.0, 0.0, 300.0]


def test_top_products_and_customers_are_sorted_and_limited(db):
    df = analytics.load_sales(db)
    assert len(analytics.top_products(df, 3)) == 3
    assert analytics.top_customers(df, 4)["revenue"].is_monotonic_decreasing


def test_filter_df_by_branch_and_dates(db):
    df = analytics.load_sales(db)
    out = analytics.filter_df(df, "Cairo", "2024-01-01", "2024-06-30")
    assert set(out["branch"]) <= {"Cairo"}
    assert out["order_date"].between("2024-01-01", "2024-06-30").all()


def test_category_by_branch_total_equals_revenue(db):
    df = analytics.load_sales(db)
    assert abs(analytics.category_by_branch(df).to_numpy().sum()
               - df["total_amount"].sum()) < len(df)   # التقريب لأقرب رقم صحيح
