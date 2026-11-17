
from typing import Any, Literal, TypedDict

from langgraph.graph import StateGraph, START, END

from ai_powered_chat_database.database.schema import get_database_schema, format_schema
from ai_powered_chat_database.database.sql_validator import validate_sql
from ai_powered_chat_database.database.sql_executor import SQLExecutionError, execute_readonly_sql
from ai_powered_chat_database.llm.sql_generator import generate_sql

# Our GraphState
class SQLAgentState(TypedDict, total=False):
    # Original user input
    question: str

    # Database context
    schema: list[dict]

    # LLM generation
    sql: str
    explanation: str

    # Validation
    is_valid: bool
    error: str | None

    # Execution
    columns: list[str]
    rows: list[tuple[Any, ...]]
    truncated: bool
    execution_time_ms: float

    # Workflow status
    status: str

# Our Nodes
def inspect_schema_node(state: SQLAgentState) -> dict:
    """Retrieve database metadata."""

    schema = get_database_schema()

    return {
        "schema": schema,
    }

def generate_sql_node(state: SQLAgentState) -> dict:
    """Generate SQL using the LLM."""

    question = state["question"]

    schema_context = format_schema(
        state["schema"]
    )

    result = generate_sql(
        question=question,
        schema_context=schema_context,
    )

    return {
        "sql": result.sql,
        "explanation": result.explanation,
    }

def validate_sql_node(state: SQLAgentState) -> dict:
    """Check generated SQL before execution."""

    result = validate_sql(
        sql=state["sql"],
        schema=state["schema"],
    )

    return {
        "is_valid": result.is_valid,
        "error": result.error,
        "status": (
            "validated"
            if result.is_valid
            else "rejected"
        ),
    }

def execute_sql_node(state: SQLAgentState) -> dict:
    """Execute validated SQL against SQLite."""

    try:
        result = execute_readonly_sql(
            sql=state["sql"],
            max_rows=100,
        )

        return {
            "columns": result.columns,
            "rows": result.rows,
            "truncated": result.truncated,
            "execution_time_ms": (
                result.execution_time_ms
            ),
            "status": "executed",
            "error": None,
        }

    except SQLExecutionError as exc:
        return {
            "status": "execution_failed",
            "error": str(exc),
        }

# Our edges
def route_after_validation(state: SQLAgentState) -> Literal["run", "stop"]:
    """Choose the next step based on SQL validation."""

    if state.get("is_valid", False):
        return "run"

    return "stop"

def build_graph():
    """Construct and compile the Text-to-SQL workflow."""

    workflow = StateGraph(SQLAgentState)

    # Register nodes.
    workflow.add_node("inspect_schema",inspect_schema_node)
    workflow.add_node("generate_sql",generate_sql_node)
    workflow.add_node("validate_sql",validate_sql_node)
    workflow.add_node("execute_sql",execute_sql_node)

    # Fixed execution order.
    workflow.add_edge(START,"inspect_schema")
    workflow.add_edge("inspect_schema","generate_sql")
    workflow.add_edge("generate_sql","validate_sql")

    # Conditional execution.
    workflow.add_conditional_edges("validate_sql",route_after_validation,
        {
            "run": "execute_sql",
            "stop": END,
        },
    )
    workflow.add_edge("execute_sql",END)

    return workflow.compile()




