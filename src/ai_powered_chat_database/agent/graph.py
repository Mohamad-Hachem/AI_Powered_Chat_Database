
from typing import Any, Literal, TypedDict

from langgraph.graph import StateGraph, START, END

from ai_powered_chat_database.database.schema import (
    get_database_schema,
    format_schema,
)
from ai_powered_chat_database.database.sql_validator import (
    validate_sql,
)
from ai_powered_chat_database.database.sql_executor import (
    SQLExecutionError,
    execute_readonly_sql,
)
from ai_powered_chat_database.llm.sql_generator import (
    generate_sql,
)
from ai_powered_chat_database.llm.sql_repair import (
    repair_sql,
)


# One initial generation plus two correction attempts.
MAX_CORRECTIONS = 2
MAX_GENERATIONS = 1 + MAX_CORRECTIONS


class SQLAgentState(TypedDict, total=False):
    # Original user input
    question: str

    # Database context
    schema: list[dict]

    # SQL generation
    sql: str
    explanation: str

    # Validation
    is_valid: bool
    retryable: bool
    error: str | None

    # Correction tracking
    generation_attempts: int
    attempt_history: list[dict[str, Any]]

    # Execution
    columns: list[str]
    rows: list[tuple[Any, ...]]
    truncated: bool
    execution_time_ms: float

    # Workflow status
    status: str


# --------------------------------------------------
# NODE 1: INSPECT SCHEMA
# --------------------------------------------------

def inspect_schema_node(
    state: SQLAgentState,
) -> dict:
    schema = get_database_schema()

    return {
        "schema": schema,
    }


# --------------------------------------------------
# NODE 2: GENERATE INITIAL SQL
# --------------------------------------------------

def generate_sql_node(
    state: SQLAgentState,
) -> dict:
    schema_context = format_schema(
        state["schema"]
    )

    result = generate_sql(
        question=state["question"],
        schema_context=schema_context,
    )

    return {
        "sql": result.sql,
        "explanation": result.explanation,
        "generation_attempts": 1,
        "attempt_history": [],
        "status": "generated",
    }


# --------------------------------------------------
# NODE 3: VALIDATE SQL
# --------------------------------------------------

def validate_sql_node(
    state: SQLAgentState,
) -> dict:

    validation = validate_sql(
        sql=state["sql"],
        schema=state["schema"],
    )

    # Record every validation attempt.
    history = list(
        state.get("attempt_history", [])
    )

    history.append({
        "attempt": state["generation_attempts"],
        "sql": state["sql"],
        "valid": validation.is_valid,
        "error": validation.error,
    })

    return {
        "is_valid": validation.is_valid,
        "retryable": validation.retryable,
        "error": validation.error,
        "attempt_history": history,
        "status": (
            "validated"
            if validation.is_valid
            else "rejected"
        ),
    }


# --------------------------------------------------
# NODE 4: REPAIR SQL
# --------------------------------------------------

def repair_sql_node(
    state: SQLAgentState,
) -> dict:
    """Repair SQL using validator feedback."""

    schema_context = format_schema(
        state["schema"]
    )

    result = repair_sql(
        question=state["question"],
        schema_context=schema_context,
        previous_sql=state["sql"],
        validation_error=(
            state["error"] or "SQL validation failed."
        ),
    )

    return {
        "sql": result.sql,
        "explanation": result.explanation,
        "generation_attempts": (
            state["generation_attempts"] + 1
        ),
        "status": "repaired",
    }


# --------------------------------------------------
# NODE 5: EXECUTE SQL
# --------------------------------------------------

def execute_sql_node(
    state: SQLAgentState,
) -> dict:

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


# --------------------------------------------------
# CONDITIONAL ROUTING
# --------------------------------------------------

def route_after_validation(
    state: SQLAgentState,
) -> Literal["run", "repair", "stop"]:
    """Decide whether to execute, repair, or stop."""

    if state.get("is_valid", False):
        return "run"

    # Only retry eligible validation failures.
    if (
        state.get("retryable", False)
        and state["generation_attempts"] < MAX_GENERATIONS
    ):
        return "repair"

    return "stop"


# --------------------------------------------------
# BUILD LANGGRAPH
# --------------------------------------------------

def build_graph():

    workflow = StateGraph(SQLAgentState)

    # Register nodes
    workflow.add_node(
        "inspect_schema",
        inspect_schema_node,
    )

    workflow.add_node(
        "generate_sql",
        generate_sql_node,
    )

    workflow.add_node(
        "validate_sql",
        validate_sql_node,
    )

    workflow.add_node(
        "repair_sql",
        repair_sql_node,
    )

    workflow.add_node(
        "execute_sql",
        execute_sql_node,
    )

    # Initial workflow
    workflow.add_edge(
        START,
        "inspect_schema",
    )

    workflow.add_edge(
        "inspect_schema",
        "generate_sql",
    )

    workflow.add_edge(
        "generate_sql",
        "validate_sql",
    )

    # Dynamic routing
    workflow.add_conditional_edges(
        "validate_sql",
        route_after_validation,
        {
            "run": "execute_sql",
            "repair": "repair_sql",
            "stop": END,
        },
    )

    # Correction loop
    workflow.add_edge(
        "repair_sql",
        "validate_sql",
    )

    # Successful execution ends the workflow.
    workflow.add_edge(
        "execute_sql",
        END,
    )

    return workflow.compile()
