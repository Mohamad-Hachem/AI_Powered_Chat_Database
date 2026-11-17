
import sys

from ai_powered_chat_database.agent.graph import build_graph

def main():
    question = (
        " ".join(sys.argv[1:]).strip()
        if len(sys.argv) > 1
        else "What are the top 5 best-selling products?"
    )

    print("\n=== USER QUESTION ===")
    print(question)

    # Build the workflow.
    graph = build_graph()

    print("\n=== LANGGRAPH DIAGRAM ===")
    print(graph.get_graph().draw_mermaid())

    # Execute the graph.
    result = graph.invoke({
        "question": question,
    })

    print("\n=== GENERATED SQL ===")
    print(result.get("sql", ""))

    print("\n=== EXPLANATION ===")
    print(result.get("explanation", ""))

    print("\n=== WORKFLOW STATUS ===")
    print(result.get("status", "unknown"))

    if result.get("status") != "executed":
        print("\n=== ERROR ===")
        print(result.get("error", "Unknown error"))
        return

    print("\n=== QUERY RESULTS ===")

    columns = result["columns"]

    for row in result["rows"]:
        print(dict(zip(columns, row)))

    print("\n=== EXECUTION METRICS ===")
    print(
        f"Execution time: "
        f"{result['execution_time_ms']:.2f} ms"
    )

    print(f"Rows returned: {len(result['rows'])}")
    print(f"Results truncated: {result['truncated']}")


if __name__ == "__main__":
    main()
    