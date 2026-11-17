
import sys

from ai_powered_chat_database.database.schema import format_schema, get_database_schema
from ai_powered_chat_database.database.sql_executor import SQLExecutionError, execute_readonly_sql
from ai_powered_chat_database.llm.sql_generator import generate_sql


def main():
    question = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else "What are the top 5 best-selling products?"
    )

    print("\n=== USER QUESTION ===")
    print(question)

    # Step 1: Inspect schema
    schema = get_database_schema()
    schema_context = format_schema(schema)

    # Step 2: Generate SQL
    result = generate_sql(question=question, schema_context=schema_context)

    print("\n=== GENERATED SQL ===")
    print(result.sql or "(No SQL generated)")

    print("\n=== LLM EXPLANATION ===")
    print(result.explanation)

    if not result.sql.strip():
        print("\nNo SQL query was generated.")
        return

    # Step 3: Validate and execute SQL
    print("\n=== DATABASE EXECUTION ===")

    try:
        query_result = execute_readonly_sql(sql=result.sql, max_rows=100)

    except SQLExecutionError as exc:
        print(f"Query rejected: {exc}")
        raise SystemExit(1) from exc

    # Step 4: Display real database results.
    print("\n=== QUERY RESULTS ===")
    print("Columns:", query_result.columns)

    for row in query_result.rows:
        print(row)

    print("\n=== EXECUTION METRICS ===")
    print(
        f"Execution time: "
        f"{query_result.execution_time_ms:.2f} ms"
    )
    print(f"Rows returned: {len(query_result.rows)}")
    print(f"Results truncated: {query_result.truncated}")


if __name__ == "__main__":
    main()
