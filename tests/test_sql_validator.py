import pytest

from ai_powered_chat_database.database.schema import get_database_schema
from ai_powered_chat_database.database.sql_validator import validate_sql


@pytest.fixture
def schema():
    return get_database_schema()


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT name FROM customers",

        "SELECT COUNT(*) FROM orders",

        """
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
        ORDER BY units_sold DESC
        LIMIT 5
        """,
    ],
)
def test_valid_queries(schema, sql):
    result = validate_sql(sql, schema)
    assert result.is_valid, result.error


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE customers",

        "DELETE FROM customers",

        "UPDATE products SET price_cents = 0",

        "SELECT name FROM customers; DELETE FROM orders",

        "SELECT customer_name FROM customers",

        "SELECT name FROM nonexistent_table",

        "SELECT load_extension('example') FROM customers",

        "WITH cte AS (SELECT * FROM customers) SELECT * FROM cte"
    ],
)
def test_invalid_queries(schema, sql):
    result = validate_sql(sql, schema)
    assert not result.is_valid
    assert result.error is not None
