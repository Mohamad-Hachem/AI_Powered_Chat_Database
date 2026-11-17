
import pytest

from ai_powered_chat_database.database.sql_executor import (
    SQLExecutionError,
    execute_readonly_sql,
)


def test_select_customers():
    result = execute_readonly_sql(
        "SELECT name FROM customers ORDER BY customer_id LIMIT 2"
    )

    assert result.columns == ["name"]
    assert len(result.rows) == 2
    assert result.rows[0][0] == "Alice Martin"
    assert result.truncated is False


def test_count_customers():
    result = execute_readonly_sql(
        "SELECT COUNT(*) AS total FROM customers"
    )

    assert result.rows[0][0] == 6


def test_reject_delete():
    with pytest.raises(SQLExecutionError):
        execute_readonly_sql(
            "DELETE FROM customers"
        )


def test_reject_unknown_column():
    with pytest.raises(SQLExecutionError):
        execute_readonly_sql(
            "SELECT customer_name FROM customers"
        )


def test_reject_multiple_statements():
    with pytest.raises(SQLExecutionError):
        execute_readonly_sql(
            "SELECT name FROM customers; DELETE FROM orders;"
        )


def test_row_limit():
    result = execute_readonly_sql(
        "SELECT name FROM customers ORDER BY customer_id",
        max_rows=2,
    )

    assert len(result.rows) == 2
    assert result.truncated is True


def test_reject_unapproved_function():
    with pytest.raises(SQLExecutionError):
        execute_readonly_sql(
            "SELECT random() FROM customers"
        )


def test_instruction_budget():
    with pytest.raises(
        SQLExecutionError,
        match="interrupted",
    ):
        execute_readonly_sql(
            "SELECT name FROM customers",
            max_vm_steps=1,
            progress_interval=1,
        )
