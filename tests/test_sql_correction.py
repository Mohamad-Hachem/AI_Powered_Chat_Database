
from ai_powered_chat_database.agent import (
    graph as agent_graph,
)
from ai_powered_chat_database.llm.sql_generator import (
    SQLDraft,
)


def test_agent_repairs_invalid_column(monkeypatch):
    """The agent repairs a bad column name."""

    def fake_generate(question, schema_context):
        return SQLDraft(
            sql="SELECT customer_name FROM customers",
            explanation="Initial query.",
        )

    def fake_repair(
        question,
        schema_context,
        previous_sql,
        validation_error,
    ):
        assert "customer_name" in previous_sql
        assert validation_error

        return SQLDraft(
            sql="SELECT name FROM customers LIMIT 2",
            explanation="Corrected column name.",
        )

    monkeypatch.setattr(
        agent_graph,
        "generate_sql",
        fake_generate,
    )

    monkeypatch.setattr(
        agent_graph,
        "repair_sql",
        fake_repair,
    )

    graph = agent_graph.build_graph()

    result = graph.invoke({
        "question": "Show two customer names."
    })

    assert result["status"] == "executed"
    assert result["generation_attempts"] == 2
    assert len(result["attempt_history"]) == 2
    assert result["attempt_history"][0]["valid"] is False
    assert result["attempt_history"][1]["valid"] is True
    assert len(result["rows"]) == 2


def test_agent_stops_after_retry_limit(monkeypatch):
    """A repeatedly failing query cannot loop forever."""

    correction_calls = 0

    def fake_generate(question, schema_context):
        return SQLDraft(
            sql="SELECT customer_name FROM customers",
            explanation="Invalid initial query.",
        )

    def fake_repair(
        question,
        schema_context,
        previous_sql,
        validation_error,
    ):
        nonlocal correction_calls
        correction_calls += 1

        return SQLDraft(
            sql="SELECT customer_name FROM customers",
            explanation="Still incorrect.",
        )

    monkeypatch.setattr(
        agent_graph,
        "generate_sql",
        fake_generate,
    )

    monkeypatch.setattr(
        agent_graph,
        "repair_sql",
        fake_repair,
    )

    graph = agent_graph.build_graph()

    result = graph.invoke({
        "question": "Show customer names."
    })

    assert result["status"] == "rejected"
    assert result["generation_attempts"] == 3
    assert correction_calls == 2
    assert len(result["attempt_history"]) == 3
    assert "rows" not in result


def test_unsafe_query_is_not_repaired(monkeypatch):
    """Unsafe SQL is rejected immediately."""

    def fake_generate(question, schema_context):
        return SQLDraft(
            sql="DROP TABLE customers",
            explanation="Unsafe query.",
        )

    def forbidden_repair(*args, **kwargs):
        raise AssertionError(
            "Unsafe SQL must not trigger repair."
        )

    def forbidden_execution(*args, **kwargs):
        raise AssertionError(
            "Unsafe SQL must never execute."
        )

    monkeypatch.setattr(
        agent_graph,
        "generate_sql",
        fake_generate,
    )

    monkeypatch.setattr(
        agent_graph,
        "repair_sql",
        forbidden_repair,
    )

    monkeypatch.setattr(
        agent_graph,
        "execute_readonly_sql",
        forbidden_execution,
    )

    graph = agent_graph.build_graph()

    result = graph.invoke({
        "question": "Delete all customers."
    })

    assert result["status"] == "rejected"
    assert result["generation_attempts"] == 1
    assert "rows" not in result


def test_valid_query_skips_repair(monkeypatch):
    """Already-valid SQL shouldn't invoke the repair model."""

    def fake_generate(question, schema_context):
        return SQLDraft(
            sql="SELECT COUNT(*) AS total FROM customers",
            explanation="Count customers.",
        )

    def forbidden_repair(*args, **kwargs):
        raise AssertionError(
            "Repair should not be called."
        )

    monkeypatch.setattr(
        agent_graph,
        "generate_sql",
        fake_generate,
    )

    monkeypatch.setattr(
        agent_graph,
        "repair_sql",
        forbidden_repair,
    )

    graph = agent_graph.build_graph()

    result = graph.invoke({
        "question": "How many customers?"
    })

    assert result["status"] == "executed"
    assert result["generation_attempts"] == 1
    assert result["rows"][0][0] == 6
