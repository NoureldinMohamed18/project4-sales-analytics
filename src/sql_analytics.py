import re
import sqlite3
from pathlib import Path

import pandas as pd

SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "analytics.sql"


def load_queries(path=SQL_FILE):
    """يقسّم الملف على سطور '-- name: xxx' ويرجّع {اسم: استعلام}."""
    text = Path(path).read_text(encoding="utf-8")
    parts = re.split(r"^-- name:\s*(\w+)\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def run_query(name, db_path, params=()):
    queries = load_queries()
    if name not in queries:                      # whitelist: الاسم لازم يكون من الملف
        raise KeyError(name)
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql(queries[name], conn, params=params)
