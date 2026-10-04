from src import analytics
from src.sql_analytics import load_queries, run_query


def test_all_queries_are_loaded():
    assert set(load_queries()) == {"branch_rank_per_month", "running_total", "mom_growth",
                                   "top_product_per_category", "customer_quartiles"}


def test_running_total_ends_at_total_revenue(db):
    rt = run_query("running_total", db)
    assert rt["cumulative_revenue"].is_monotonic_increasing
    total = analytics.load_sales(db)["total_amount"].sum()
    assert abs(rt["cumulative_revenue"].iloc[-1] - total) < 1


def test_exactly_one_rank_one_branch_per_month(db):
    r = run_query("branch_rank_per_month", db)
    firsts = r[r["rank_in_month"] == 1].groupby("month").size()
    assert (firsts == 1).all()


def test_one_top_product_per_category(db):
    t = run_query("top_product_per_category", db)
    assert t["category"].is_unique


def test_quartiles_cover_every_customer(db):
    q = run_query("customer_quartiles", db)
    assert q["customers"].sum() == analytics.load_sales(db)["customer_id"].nunique()
    assert q["avg_revenue"].is_monotonic_decreasing


def test_first_month_has_no_growth_value(db):
    g = run_query("mom_growth", db)
    assert g["growth_pct"].isna().iloc[0]


def test_unknown_query_name_is_rejected(db):
    import pytest
    with pytest.raises(KeyError):
        run_query("x; DROP TABLE sales", db)
