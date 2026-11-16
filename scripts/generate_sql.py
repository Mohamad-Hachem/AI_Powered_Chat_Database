
import sys

from ai_powered_chat_database.database.schema import format_schema, get_database_schema
from ai_powered_chat_database.llm.sql_generator import generate_sql
from ai_powered_chat_database.database.sql_validator import validate_sql

def main():
    # Allow a question from the terminal.
    question = input("Insert your question to query database such as What are the top 5 best-selling products?:\n")

    # Step 1: Discover the database schema.
    schema = get_database_schema()

    # Step 2: Format the schema for the LLM.
    schema_context = format_schema(schema)

    print("\n=== USER QUESTION ===")
    print(question)

    print("\n=== SCHEMA CONTEXT ===")
    print(schema_context)

    # Step 3: Generate SQL using the LLM.
    result = generate_sql(
        question=question,
        schema_context=schema_context,
    )

    print("\n=== GENERATED SQL ===")
    print(result.sql or "(No SQL generated)")

    print("\n=== EXPLANATION ===")
    print(result.explanation)

    print("\n=== SQL VALIDATION ===")

    validation = validate_sql(
        sql=result.sql,
        schema=schema,
    )

    if validation.is_valid:
        print("VALID: SQL passed the current validation rules.")
    else:
        print("REJECTED:", validation.error)

    print("\nSQL was NOT executed.")


if __name__ == "__main__":
    main()
