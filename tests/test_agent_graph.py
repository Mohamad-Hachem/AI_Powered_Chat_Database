
from ai_powered_chat_database.agent import graph as agent_graph
from ai_powered_chat_database.llm.sql_generator import SQLDraft


def test_successful_workflow(monkeypatch):
    """Valid SQL reaches the execution node."""

    def fake_generate_sql(question, schema_context):
        return SQLDraft(
            sql="SELECT COUNT(*) AS total FROM customers",
            explanation="Counts customers.",
        )

    monkeypatch.setattr(
        agent_graph,
        "generate_sql",
        fake_generate_sql,
    )

    graph = agent_graph.build_graph()

    result = graph.invoke({
        "question": "How many customers?",
    })

    assert result["status"] == "executed"
    assert result["is_valid"] is True
    assert result["rows"][0][0] == 6


def test_invalid_sql_stops_workflow(monkeypatch):
    """Rejected SQL must never reach execution."""

    def fake_generate_sql(question, schema_context):
        return SQLDraft(
            sql="DELETE FROM customers",
            explanation="Invalid operation.",
        )

    def forbidden_execution(*args, **kwargs):
        raise AssertionError(
            "Execution must not be reached."
        )

    monkeypatch.setattr(
        agent_graph,
        "generate_sql",
        fake_generate_sql,
    )

    monkeypatch.setattr(
        agent_graph,
        "execute_readonly_sql",
        forbidden_execution,
    )

    graph = agent_graph.build_graph()

    result = graph.invoke({
        "question": "Delete all customers",
    })

    assert result["status"] == "rejected"
    assert result["is_valid"] is False
    assert result["error"] is not None
    assert "rows" not in result


def test_empty_sql_stops_workflow(monkeypatch):
    """Unanswerable questions must stop safely."""

    def fake_generate_sql(question, schema_context):
        return SQLDraft(
            sql="",
            explanation="Not enough database information.",
        )

    monkeypatch.setattr(
        agent_graph,
        "generate_sql",
        fake_generate_sql,
    )

    graph = agent_graph.build_graph()

    result = graph.invoke({
        "question": "What is the weather tomorrow?",
    })

    assert result["status"] == "rejected"
    assert result["is_valid"] is False
    assert "rows" not in result
