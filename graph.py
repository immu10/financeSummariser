"""
graph.py — LangGraph state graph definitions.

Two compiled graphs:
  ingestion_graph  — runs once per PDF upload (split → parallel summarise+parse → kpis)
  query_graph      — runs per chat message (route → answer → validate → [retry])
"""
from langgraph.graph import StateGraph, START, END

from state import FinancialGraphState
from nodes import (
    split_document,
    summarize_statement,
    parse_statement,
    build_kpis,
    route_query,
    generate_answer,
    validate_answer,
    fan_out_summaries,
    fan_out_parsing,
    should_retry,
)

# ---------------------------------------------------------------------------
# Ingestion graph
# ---------------------------------------------------------------------------
#
# Topology:
#
#   START
#     │
#     ▼
#   split_document
#     │           ╲
#     │ (Send×3)   ╲ (Send×3)
#     ▼             ▼
#   summarize_    parse_
#   statement     statement
#     │   │   │     │   │   │
#     └───┴───┘     └───┴───┘
#         │               │
#         └──────┬─────────┘
#                ▼
#            build_kpis
#                │
#               END
#
# The operator.add reducers on state["summaries"] and state["parsed_statements"]
# accumulate the 3 results from each parallel fan-out before build_kpis fires.

def _build_ingestion_graph() -> StateGraph:
    builder = StateGraph(FinancialGraphState)

    builder.add_node("split_document", split_document)
    builder.add_node("summarize_statement", summarize_statement)
    builder.add_node("parse_statement", parse_statement)
    builder.add_node("build_kpis", build_kpis)

    builder.add_edge(START, "split_document")

    # Fan-out to parallel summarisers
    builder.add_conditional_edges(
        "split_document",
        fan_out_summaries,
        ["summarize_statement"],
    )

    # Fan-out to parallel parsers
    builder.add_conditional_edges(
        "split_document",
        fan_out_parsing,
        ["parse_statement"],
    )

    # Both fan-outs converge at build_kpis
    builder.add_edge("summarize_statement", "build_kpis")
    builder.add_edge("parse_statement", "build_kpis")

    builder.add_edge("build_kpis", END)

    return builder.compile()


# ---------------------------------------------------------------------------
# Query graph
# ---------------------------------------------------------------------------
#
# Topology:
#
#   START
#     │
#     ▼
#   route_query
#     │
#     ▼
#   generate_answer ◄──────────────┐
#     │                            │ "retry" (max 2)
#     ▼                            │
#   validate_answer ───────────────┘
#     │ "done"
#    END

def _build_query_graph() -> StateGraph:
    builder = StateGraph(FinancialGraphState)

    builder.add_node("route_query", route_query)
    builder.add_node("generate_answer", generate_answer)
    builder.add_node("validate_answer", validate_answer)

    builder.add_edge(START, "route_query")
    builder.add_edge("route_query", "generate_answer")
    builder.add_edge("generate_answer", "validate_answer")

    builder.add_conditional_edges(
        "validate_answer",
        should_retry,
        {
            "retry": "generate_answer",
            "done": END,
        },
    )

    return builder.compile()


# ---------------------------------------------------------------------------
# Compiled singletons — imported by ui.py
# ---------------------------------------------------------------------------

ingestion_graph = _build_ingestion_graph()
query_graph = _build_query_graph()