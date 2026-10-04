import logging
import sqlite3
from datetime import date, datetime

from flask import Flask, jsonify, request

from src import analytics, sql_analytics
from src.generate_data import BRANCHES, PRODUCTS

logger = logging.getLogger(__name__)

MAX_LIMIT = 200


class ValidationError(Exception):
    """بيتحوّل لـ HTTP 400 برسالة واضحة."""


# ---------- helpers ----------
def records(df):
    """DataFrame -> list of dicts بأنواع Python و NaN -> None (عشان JSON)."""
    return df.astype(object).where(df.notna(), None).to_dict(orient="records")


def parse_date(value, name):
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        raise ValidationError(f"'{name}' must be a date in YYYY-MM-DD format, got '{value}'")


def get_int(name, default, minimum, maximum):
    raw = request.args.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValidationError(f"'{name}' must be an integer, got '{raw}'")
    if not minimum <= value <= maximum:
        raise ValidationError(f"'{name}' must be between {minimum} and {maximum}")
    return value


def get_filters():
    branch = request.args.get("branch")
    if branch and branch not in BRANCHES:
        raise ValidationError(f"unknown branch '{branch}'. Valid: {BRANCHES}")
    date_from = request.args.get("from")
    date_to = request.args.get("to")
    date_from = parse_date(date_from, "from") if date_from else None
    date_to = parse_date(date_to, "to") if date_to else None
    if date_from and date_to and date_from > date_to:
        raise ValidationError("'from' must not be after 'to'")
    return branch, date_from, date_to


def validate_new_order(body):
    if not isinstance(body, dict):
        raise ValidationError("body must be a JSON object")

    def need(field):
        if field not in body:
            raise ValidationError(f"missing field '{field}'")
        return body[field]

    def as_int(field, minimum, maximum):
        value = need(field)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValidationError(f"'{field}' must be an integer")
        if not minimum <= value <= maximum:
            raise ValidationError(f"'{field}' must be between {minimum} and {maximum}")
        return value

    branch = need("branch")
    if branch not in BRANCHES:
        raise ValidationError(f"unknown branch '{branch}'. Valid: {BRANCHES}")
    product = need("product")
    if product not in PRODUCTS:
        raise ValidationError(f"unknown product '{product}'. Valid: {sorted(PRODUCTS)}")

    discount = body.get("discount", 0)
    if isinstance(discount, bool) or not isinstance(discount, (int, float)) or not 0 <= discount < 1:
        raise ValidationError("'discount' must be a number >= 0 and < 1")

    order_date = parse_date(body["order_date"], "order_date") if "order_date" in body \
        else date.today().isoformat()

    return {
        "branch": branch, "product": product,
        "customer_id": as_int("customer_id", 1, 10**9),
        "quantity": as_int("quantity", 1, 100),
        "discount": float(discount), "order_date": order_date,
    }


# ---------- app ----------
def create_app(db_path="data/sales.db"):
    app = Flask(__name__)
    app.config["DB_PATH"] = str(db_path)
    app.json.sort_keys = False

    def data():
        return analytics.load_sales_cached(app.config["DB_PATH"])

    @app.errorhandler(ValidationError)
    def on_validation(e):
        return jsonify(error=str(e)), 400

    @app.errorhandler(404)
    def on_404(e):
        return jsonify(error="not found"), 404

    @app.errorhandler(405)
    def on_405(e):
        return jsonify(error="method not allowed"), 405

    @app.errorhandler(Exception)
    def on_error(e):
        logger.exception("Unhandled error")
        return jsonify(error="internal server error"), 500

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/api/summary")
    def summary():
        df = analytics.filter_df(data(), *get_filters())
        return jsonify(analytics.summary(df))

    @app.get("/api/sales/monthly")
    def monthly():
        df = analytics.filter_df(data(), *get_filters())
        return jsonify(records(analytics.monthly_sales(df)))

    @app.get("/api/branches")
    def branches():
        _, date_from, date_to = get_filters()
        df = analytics.filter_df(data(), None, date_from, date_to)
        return jsonify(records(analytics.by_branch(df)))

    @app.get("/api/products/top")
    def top_products():
        n = get_int("n", 5, 1, 50)
        df = analytics.filter_df(data(), *get_filters())
        return jsonify(records(analytics.top_products(df, n)))

    @app.get("/api/customers/top")
    def top_customers():
        n = get_int("n", 5, 1, 50)
        df = analytics.filter_df(data(), *get_filters())
        return jsonify(records(analytics.top_customers(df, n)))

    @app.get("/api/analytics/<name>")
    def sql_report(name):
        try:
            df = sql_analytics.run_query(name, app.config["DB_PATH"])
        except KeyError:
            return jsonify(error=f"unknown report '{name}'",
                           available=list(sql_analytics.load_queries())), 404
        return jsonify(records(df))

    @app.get("/api/orders")
    def list_orders():
        limit = get_int("limit", 50, 1, MAX_LIMIT)
        offset = get_int("offset", 0, 0, 10**9)
        branch, _, _ = get_filters()
        with sqlite3.connect(app.config["DB_PATH"]) as conn:
            conn.row_factory = sqlite3.Row
            total = conn.execute(           # parameters، مش string formatting
                "SELECT COUNT(*) FROM sales WHERE (? IS NULL OR branch = ?)",
                (branch, branch)).fetchone()[0]
            rows = conn.execute(
                "SELECT * FROM sales WHERE (? IS NULL OR branch = ?) "
                "ORDER BY order_id LIMIT ? OFFSET ?",
                (branch, branch, limit, offset)).fetchall()
        return jsonify(total=total, limit=limit, offset=offset,
                       items=[dict(r) for r in rows])

    @app.post("/api/orders")
    def create_order():
        order = validate_new_order(request.get_json(silent=True))
        category, price = PRODUCTS[order["product"]]
        total = round(order["quantity"] * price * (1 - order["discount"]), 2)

        conn = sqlite3.connect(app.config["DB_PATH"], timeout=10, isolation_level=None)
        try:
            conn.execute("BEGIN IMMEDIATE")       # نقفل الكتابة لحد ما نخلص (id مش بيتكرر)
            order_id = conn.execute(
                "SELECT COALESCE(MAX(order_id), 0) + 1 FROM sales").fetchone()[0]
            conn.execute(
                "INSERT INTO sales (order_id, order_date, branch, customer_id, product, "
                "category, quantity, unit_price, discount, total_amount) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (order_id, order["order_date"], order["branch"], order["customer_id"],
                 order["product"], category, order["quantity"], float(price),
                 order["discount"], total))
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

        return jsonify(order_id=order_id, category=category, unit_price=float(price),
                       total_amount=total, **order), 201

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_app().run(port=5000, debug=False)
