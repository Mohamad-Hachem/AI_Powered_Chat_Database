import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

# Project root
BASE_DIR = Path(__file__).resolve().parents[3]

# Load environment variables
load_dotenv(BASE_DIR / ".env")


class SQLDraft(BaseModel):
    """Structured output from the SQL generator."""

    sql: str = Field(description=("One SQLite SELECT query. Return an empty string if the question cannot be answered using the schema."))
    explanation: str = Field(description=("A brief explanation of the SQL query or why the question cannot be answered."))


SYSTEM_PROMPT = """
You are an expert SQLite query generator.

Your task is to translate natural-language questions
into accurate SQLite SELECT queries.

Rules:
1. Use only tables and columns in the provided schema.
2. Generate SQLite-compatible SQL.
3. Return exactly one SELECT query.
4. Never generate INSERT, UPDATE, DELETE, DROP,
   ALTER, CREATE, or other write operations.
5. Use foreign key relationships for joins.
6. Use explicit JOIN conditions.
7. For best-selling product metrics, count only
   orders where status = 'completed'.
8. Do not invent missing tables or columns.
9. If the question cannot be answered using the
   available schema, return an empty SQL string.
10. Do not include Markdown code fences in SQL.

The following database schema is the available context:

{schema_context}
"""


def generate_sql(question: str, schema_context: str) -> SQLDraft:
    """Generate SQL without executing it."""

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing. Check your .env file.")

    model_name = os.getenv("OPENAI_MODEL","gpt-6-luna")

    llm = ChatOpenAI(model=model_name, timeout=60, max_retries=2,)

    # Ask the model to return a structured response.
    structured_llm = llm.with_structured_output(SQLDraft, method="json_schema")

    messages = [
        ("system", SYSTEM_PROMPT.format(schema_context=schema_context)),
        ("human", question),
    ]

    result = structured_llm.invoke(messages)

    if not isinstance(result, SQLDraft):
        raise TypeError("The model did not return a valid SQLDraft.")

    return result
