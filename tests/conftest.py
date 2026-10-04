import sqlite3

import pytest

from src.generate_data import generate


@pytest.fixture()
def db(tmp_path):
    """DB مؤقتة لكل اختبار: مفيش اختبار بيلمس data/sales.db الحقيقية."""
    path = tmp_path / "sales.db"
    with sqlite3.connect(path) as conn:
        generate(n=600, seed=7).to_sql("sales", conn, index=False)
    return path
