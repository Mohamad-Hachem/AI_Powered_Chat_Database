
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_powered_chat_database.database.schema import DB_PATH, get_database_schema
from ai_powered_chat_database.database.sql_validator import ALLOWED_FUNCTIONS, validate_sql


class SQLExecutionError(Exception):
    """Raised when a query is invalid or cannot execute safely."""


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[tuple[Any, ...]]
    truncated: bool
    execution_time_ms: float


def execute_readonly_sql(
    sql: str,
    db_path: Path = DB_PATH,
    max_rows: int = 100,
    timeout_seconds: float = 2.0,
    max_vm_steps: int = 100_000,
    progress_interval: int = 100,
) -> QueryResult:
    """Validate and execute a restricted SQLite SELECT query."""

    if not 1 <= max_rows <= 500:
        raise ValueError("max_rows must be between 1 and 500.")

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive.")

    if max_vm_steps <= 0 or progress_interval <= 0:
        raise ValueError("Instruction limits must be positive.")

    # Reject oversized SQL before parsing it.
    if len(sql.encode("utf-8")) > 20_000:
        raise SQLExecutionError("SQL statement is too long.")

    # Reuse our existing validator.
    schema = get_database_schema(db_path)
    validation = validate_sql(sql, schema)

    if not validation.is_valid:
        raise SQLExecutionError(f"SQL validation failed: {validation.error}")

    # Tables and columns permitted for this execution.
    allowed_tables = {
        table["table"].lower(): {column["name"].lower() for column in table["columns"]}
        for table in schema
    }

    def authorize(action: int, arg1: str | None, arg2: str | None, database: str | None, source: str | None) -> int:
        """Deny operations that aren't explicitly permitted."""

        # Do not permit operations originating from views/triggers.
        if source is not None:
            return sqlite3.SQLITE_DENY

        if action == sqlite3.SQLITE_SELECT:
            return sqlite3.SQLITE_OK

        if action == sqlite3.SQLITE_READ:
            table_name = (arg1 or "").lower()
            column_name = (arg2 or "").lower()

            if database not in ("main", None):
                return sqlite3.SQLITE_DENY

            if table_name not in allowed_tables:
                return sqlite3.SQLITE_DENY

            # SQLite can use an empty column for COUNT(*).
            if column_name and column_name not in allowed_tables[table_name]:
                return sqlite3.SQLITE_DENY

            return sqlite3.SQLITE_OK

        if action == sqlite3.SQLITE_FUNCTION:
            function_name = (arg2 or "").upper()

            if function_name in ALLOWED_FUNCTIONS:
                return sqlite3.SQLITE_OK

        # Deny everything else, including write operations,
        # ATTACH, PRAGMA, and other unapproved actions.
        return sqlite3.SQLITE_DENY

    start = time.monotonic()
    deadline = start + timeout_seconds
    steps = 0

    def check_progress() -> int:
        """Interrupt the query if it exceeds its work budget."""
        nonlocal steps

        steps += progress_interval

        if time.monotonic() >= deadline:
            return 1

        if steps >= max_vm_steps:
            return 1

        return 0

    if not db_path.is_file():
        raise SQLExecutionError("Database file does not exist.")

    # URI read-only mode prevents opening the database for writes.
    db_uri = db_path.resolve().as_uri() + "?mode=ro"

    try:
        with closing(sqlite3.connect(db_uri,uri=True,timeout=1.0)) as conn:

            conn.execute("PRAGMA query_only = ON")

            # Restrict resource consumption.
            conn.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 20_000)
            conn.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 100_000)
            conn.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 50)

            # Set up safeguards before executing SQL.
            conn.set_authorizer(authorize)
            conn.set_progress_handler(check_progress,progress_interval)

            cursor = conn.execute(sql)

            columns = [description[0] for description in cursor.description]

            # Fetch one extra row to detect truncation.
            fetched_rows = cursor.fetchmany(max_rows + 1)

            truncated = len(fetched_rows) > max_rows
            rows = fetched_rows[:max_rows]

        elapsed_ms = (time.monotonic() - start) * 1000

        return QueryResult(columns=columns, rows=rows, truncated=truncated, execution_time_ms=elapsed_ms)

    except sqlite3.Error as exc:
        raise SQLExecutionError(f"SQLite rejected or interrupted the query: {exc}") from exc
