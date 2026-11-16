
import sqlite3
from pathlib import Path

# Project root
BASE_DIR = Path(__file__).resolve().parent.parent

# File paths
DB_PATH = BASE_DIR / "data" / "ecommerce.db"
SCHEMA_PATH = BASE_DIR / "data" / "schema.sql"


def create_database():
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema)
        
        tables = conn.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """).fetchall()

        print(f"Database created at: {DB_PATH}")
        print("\nTables:")

        for table in tables:
            print(f" - {table[0]}")


if __name__ == "__main__":
    create_database()
