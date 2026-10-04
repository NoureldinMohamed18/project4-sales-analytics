import sqlite3

import pytest

from src.api import create_app


@pytest.fixture()
def client(db):
    return create_app(db).test_client()


def count_rows(db):
    with sqlite3.connect(db) as conn:
        return conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]


GOOD = {"branch": "Cairo", "customer_id": 5, "product": "Gaming Mouse", "quantity": 2}


def test_health(client):
    assert client.get("/health").get_json() == {"status": "ok"}


def test_summary_ok(client, db):
    body = client.get("/api/summary").get_json()
    assert body["orders"] == count_rows(db)


def test_filters_change_the_result(client):
    all_orders = client.get("/api/summary").get_json()["orders"]
    cairo = client.get("/api/summary?branch=Cairo").get_json()["orders"]
    assert 0 < cairo < all_orders


@pytest.mark.parametrize("url", [
    "/api/summary?from=hello",
    "/api/summary?from=2024-13-45",
    "/api/summary?from=2024-05-01&to=2024-01-01",
    "/api/summary?branch=Atlantis",
    "/api/products/top?n=abc",
    "/api/products/top?n=0",
    "/api/orders?limit=100000",
    "/api/orders?offset=-1",
])
def test_bad_input_returns_400_not_500(client, url):
    r = client.get(url)
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_sql_injection_attempt_is_rejected_and_table_survives(client, db):
    r = client.get("/api/orders?branch=Cairo' OR '1'='1")
    assert r.status_code == 400
    r = client.get("/api/analytics/running_total'; DROP TABLE sales;--")
    assert r.status_code == 404
    assert count_rows(db) > 0


def test_orders_pagination(client, db):
    page1 = client.get("/api/orders?limit=10&offset=0").get_json()
    page2 = client.get("/api/orders?limit=10&offset=10").get_json()
    assert page1["total"] == count_rows(db)
    assert len(page1["items"]) == len(page2["items"]) == 10
    assert page1["items"][0]["order_id"] != page2["items"][0]["order_id"]


def test_create_order_success_persists_and_updates_reports(client, db):
    before = count_rows(db)
    revenue_before = client.get("/api/summary").get_json()["revenue"]
    r = client.post("/api/orders", json={**GOOD, "discount": 0.1})
    assert r.status_code == 201
    body = r.get_json()
    assert body["total_amount"] == round(2 * 450 * 0.9, 2)     # السعر من الكتالوج مش من العميل
    assert count_rows(db) == before + 1
    revenue_after = client.get("/api/summary").get_json()["revenue"]
    assert abs(revenue_after - revenue_before - body["total_amount"]) < 0.01


def test_order_ids_never_repeat(client):
    a = client.post("/api/orders", json=GOOD).get_json()["order_id"]
    b = client.post("/api/orders", json=GOOD).get_json()["order_id"]
    assert b == a + 1


@pytest.mark.parametrize("patch", [
    {"branch": "Atlantis"}, {"product": "Flying Car"}, {"quantity": 0},
    {"quantity": "5"}, {"quantity": True}, {"quantity": 5000},
    {"discount": 1.5}, {"discount": -0.1}, {"customer_id": 0},
    {"order_date": "yesterday"},
])
def test_create_order_rejects_invalid_fields(client, db, patch):
    before = count_rows(db)
    r = client.post("/api/orders", json={**GOOD, **patch})
    assert r.status_code == 400
    assert count_rows(db) == before            # مفيش حاجة اتكتبت


def test_create_order_rejects_missing_field_and_non_json(client):
    body = {k: v for k, v in GOOD.items() if k != "product"}
    assert client.post("/api/orders", json=body).status_code == 400
    assert client.post("/api/orders", data="not json").status_code == 400
    assert client.post("/api/orders", json=[1, 2]).status_code == 400


def test_sql_report_endpoint_and_unknown_report(client):
    ok = client.get("/api/analytics/customer_quartiles")
    assert ok.status_code == 200 and len(ok.get_json()) == 4
    bad = client.get("/api/analytics/nope")
    assert bad.status_code == 404 and "available" in bad.get_json()


def test_unknown_route_and_wrong_method_are_json(client):
    assert client.get("/nope").get_json() == {"error": "not found"}
    assert client.delete("/api/summary").status_code == 405
