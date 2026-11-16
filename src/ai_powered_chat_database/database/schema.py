
import sqlite3
from contextlib import closing
from pathlib import Path

# Locate the project root
BASE_DIR = Path(__file__).resolve().parents[3]

DB_PATH = BASE_DIR / "data" / "ecommerce.db"


def get_database_schema(db_path: Path = DB_PATH) -> list[dict]:
    """Retrieve table, column and foreign key metadata."""

    if not db_path.is_file():
        raise FileNotFoundError(f"Database not found: {db_path}")

    schema = []

    # Open the database in read-only mode
    database_uri = db_path.resolve().as_uri() + "?mode=ro"

    with closing(sqlite3.connect(database_uri, uri=True)) as conn:

        # Discover user-defined tables
        tables = conn.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT GLOB 'sqlite_*'
            ORDER BY name
        """).fetchall()

        for (table_name,) in tables:
            print(f"Found table: {table_name}")

            columns = conn.execute(
                """
                SELECT name, type, "notnull", pk
                FROM pragma_table_info(?)
                ORDER BY cid
                """,
                (table_name,),
            ).fetchall()

            column_info = []

            for name, data_type, not_null, primary_key in columns:
                column_info.append({
                    "name": name,
                    "type": data_type,
                    "not_null": bool(not_null),
                    "primary_key": bool(primary_key),
                })

            
            foreign_keys = conn.execute(
                """
                SELECT "table", "from", "to"
                FROM pragma_foreign_key_list(?)
                ORDER BY id, seq
                """,
                (table_name,),
            ).fetchall()

            foreign_key_info = []

            for referenced_table, source_column, target_column in foreign_keys:
                foreign_key_info.append({
                    "column": source_column,
                    "references_table": referenced_table,
                    "references_column": target_column,
                })

            schema.append({
                "table": table_name,
                "columns": column_info,
                "foreign_keys": foreign_key_info,
            })

    return schema


def format_schema(schema: list[dict]) -> str:
    """Convert database metadata into readable text."""

    lines = []

    for table in schema:
        lines.append(f"\nTABLE: {table['table']}")
        lines.append("COLUMNS:")

        for column in table["columns"]:
            details = [column["type"]]

            if column["primary_key"]:
                details.append("PRIMARY KEY")

            if column["not_null"]:
                details.append("NOT NULL")

            lines.append(
                f"  - {column['name']}: {', '.join(details)}"
            )

        if table["foreign_keys"]:
            lines.append("FOREIGN KEYS:")

            for fk in table["foreign_keys"]:
                lines.append(
                    f"  - {fk['column']} -> "
                    f"{fk['references_table']}."
                    f"{fk['references_column']}"
                )

    return "\n".join(lines)


if __name__ == "__main__":
    schema = get_database_schema()

    print(f"this is schema: ==============\n{schema}")
    formatted_schema = format_schema(schema)

    print("\n=== DATABASE SCHEMA ===")
    print(formatted_schema)

    print(f"\nTotal tables discovered: {len(schema)}")

    assert len(schema) == 6, "Expected six tables"
