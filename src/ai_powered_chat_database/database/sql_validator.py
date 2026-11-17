from dataclasses import dataclass

from sqlglot import exp, parse
from sqlglot.errors import SqlglotError
from sqlglot.optimizer.qualify import qualify


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    error: str | None = None
    retryable: bool = False


# Functions allowed in our first Text-to-SQL version.
ALLOWED_FUNCTIONS = {
    "COUNT",
    "SUM",
    "AVG",
    "MIN",
    "MAX",
    "ROUND",
    "COALESCE",
    "ABS",
    "LOWER",
    "UPPER",
    "DATE",
    "DATETIME",
    "STRFTIME",
}


def validate_sql(sql: str,schema: list[dict]) -> ValidationResult:
    """Validate a limited subset of read-only SQLite SQL."""

    if not sql.strip():
        return ValidationResult(False, "SQL query is empty.")

    # Build a schema mapping for SQLGlot.
    schema_mapping = {
        table["table"].lower(): {column["name"].lower(): column["type"] or "TEXT" for column in table["columns"] }
        for table in schema
    }

    try:
        # Parse every statement, not just the first.
        statements = parse(sql, read="sqlite")

        if len(statements) != 1 or statements[0] is None:
            return ValidationResult(False, "Exactly one SQL statement is allowed.")

        expression = statements[0]

        # Restrict the root statement to SELECT.
        if not isinstance(expression, exp.Select):
            return ValidationResult(False, "Only SELECT queries are allowed.")

        # Start with a small, explicit SQL subset.
        unsupported = (
            exp.With,
            exp.CTE,
            exp.Union,
            exp.Intersect,
            exp.Except,
            exp.Subquery,
            exp.Window,
            exp.Lateral,
        )

        if any(isinstance(node, unsupported) for node in expression.walk()):
            return ValidationResult(False, "This SQL construct is not supported yet.")

        # Ensure queries reference our approved tables.
        referenced_tables = list(expression.find_all(exp.Table))

        if not referenced_tables:
            return ValidationResult(False, "The query must reference a database table.")

        for table in referenced_tables:
            if table.db or table.catalog:
                return ValidationResult(False, "Cross-database references are not allowed.")

            if table.name.lower() not in schema_mapping:
                return ValidationResult(False, f"Unknown or unauthorized table: {table.name}", retryable=True)

        # Reject functions outside our approved subset.
        for function in expression.find_all(exp.Func):
            function_name = function.sql_name().upper()

            if function_name not in ALLOWED_FUNCTIONS:
                return ValidationResult(False,f"Unsupported SQL function: {function_name}")

        # Resolve columns using the real database schema.
        qualify(
            expression.copy(),
            dialect="sqlite",
            schema=schema_mapping,
            allow_partial_qualification=False,
            validate_qualify_columns=True,
        )

        return ValidationResult(True)

    except SqlglotError as exc:
        return ValidationResult(False,f"SQL parsing or column validation failed: {exc}", retryable=True)
