
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "ecommerce.db"

tables = [
    "customers",
    "products",
    "orders",
    "order_items",
    "payments",
    "refunds",
]

with sqlite3.connect(DB_PATH) as conn:
    for table in tables:
        count = conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        print(f"{table}: {count} records")

    problems = conn.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    print("Foreign key problems:", problems)

    
    print("\nTop 5 best-selling products:")

    query = """
        SELECT
            p.name,
            SUM(oi.quantity) AS units_sold
        FROM order_items AS oi
        JOIN products AS p
            ON oi.product_id = p.product_id
        JOIN orders AS o
            ON oi.order_id = o.order_id
        WHERE o.status = 'completed'
        GROUP BY p.product_id, p.name
        ORDER BY units_sold DESC, p.name
        LIMIT 5
    """

    results = conn.execute(query).fetchall()

    for product_name, units_sold in results:
        print(f"{product_name}: {units_sold} units")
