# Sales Analytics API + Dashboard

An analytics service over sales data: a **Flask REST API**, an interactive
**Plotly Dash dashboard**, a static **Seaborn report**, and an analytics layer
written twice on purpose, in **Pandas** and in **SQL window functions / CTEs**.

> The data is synthetic (5,000 generated orders over 2 years). Month-to-month
> swings are random noise, not business signals.

## Architecture

```
data/sales.db (SQLite)
        |
   src/analytics.py  (Pandas: groupby, pivot, resample)      sql/analytics.sql
        |                                                    (RANK, LAG, NTILE, running total)
        +--> src/api.py        Flask REST API  <-- src/sql_analytics.py
        +--> src/dashboard.py  Dash dashboard
        +--> src/report.py     Seaborn PNG report
```

All three outputs call the same functions in `analytics.py`, so a number can
never differ between the API, the dashboard and the report.

## Quick start

```bash
pip install -r requirements.txt
python -m src.generate_data     # create data/sales.db
python -m src.api               # API on http://localhost:5000
python -m src.dashboard         # dashboard on http://localhost:8050
python -m src.report            # PNG charts in reports/
python -m pytest -v             # 46 tests
```

## API

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/health` | liveness check |
| GET | `/api/summary` | orders, revenue, average order, customers |
| GET | `/api/sales/monthly` | monthly revenue with month-over-month growth |
| GET | `/api/branches` | revenue, orders and share per branch |
| GET | `/api/products/top?n=5` | best-selling products |
| GET | `/api/customers/top?n=5` | highest-spending customers |
| GET | `/api/analytics/<name>` | SQL reports: `branch_rank_per_month`, `running_total`, `mom_growth`, `top_product_per_category`, `customer_quartiles` |
| GET | `/api/orders?limit=50&offset=0&branch=` | paginated list (limit max 200) |
| POST | `/api/orders` | create an order (validated) |

Most GET endpoints accept the filters `branch`, `from` and `to` (`YYYY-MM-DD`).

```bash
curl "localhost:5000/api/summary?branch=Cairo&from=2024-01-01"

curl -X POST localhost:5000/api/orders -H "Content-Type: application/json" \
     -d '{"branch":"Giza","customer_id":7,"product":"Headset","quantity":3}'
```

Errors are always JSON: `400` for invalid input (with a message saying what is
wrong), `404` for unknown routes or reports, `405` for a wrong method, `500`
for unexpected failures (logged, never leaked to the client).

## Design decisions

- **Parameterized SQL only.** Filters go through `?` placeholders. Branch and
  product values are checked against whitelists, and SQL report names are
  looked up in the parsed `.sql` file, never interpolated into a query.
- **The server decides the price.** `POST /api/orders` takes the unit price
  from the product catalog and computes the total itself; a client cannot
  send its own price.
- **Safe order ids.** Inserts run inside `BEGIN IMMEDIATE`, so two writers
  cannot receive the same `order_id`.
- **JSON-safe output.** NumPy types and `NaN` are converted before serializing
  (`int64` and `NaN` both break JSON).
- **No silent gaps.** `resample("MS")` keeps months with no sales as zero, so
  charts do not skip them.
- **Cache with invalidation.** The dashboard caches the loaded data, keyed by
  the database file's modification time, so a `POST` shows up automatically.
- **Tests never touch real data.** Every test runs on a temporary database.

## Limitations

- Flask's built-in server and Dash's dev server are not for production
  (use gunicorn behind a reverse proxy, or Docker).
- No authentication; anyone who can reach the API can create orders.
- SQLite allows one writer at a time; a real deployment would use PostgreSQL.
- Unit price comes from a fixed catalog, so historical price changes are not modeled.

## Tech stack

Python, Flask, Pandas, NumPy, SQLite, Matplotlib, Seaborn, Plotly Dash, pytest
