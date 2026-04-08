from __future__ import annotations
from typing import TypedDict, Annotated, Optional
import operator


# ---------------------------------------------------------------------------
# Sub-types
# ---------------------------------------------------------------------------

class StatementChunk(TypedDict):
    """Raw text chunk assigned to one statement type after the split step."""
    statement_type: str   # "balance_sheet" | "profit_and_loss" | "cash_flows"
    raw_text: str         # The page text belonging to this statement
    page_range: str       # Human label e.g. "pages 45-47"


class StatementSummary(TypedDict):
    """Concise summary produced for each statement — used by the router node."""
    statement_type: str
    summary_text: str     # 3-5 sentence natural language summary
    key_figures: dict     # {"Total Revenue": 808030, ...} top ~6 numbers


class ParsedStatement(TypedDict):
    """Fully structured statement — same schema as current STATEMENTS_SCHEMA sub-objects."""
    statement_type: str
    data: dict            # The actual BS / PL / CF structured dict


class ValidationResult(TypedDict):
    is_valid: bool
    critique: str         # Empty string if valid; reason for failure if not
    retry_count: int


# ---------------------------------------------------------------------------
# Main graph state
# ---------------------------------------------------------------------------

class FinancialGraphState(TypedDict):
    # --- Ingestion ---
    raw_pages: list[str]
    company_name: str
    currency_unit: str

    # --- Split ---
    statement_chunks: list[StatementChunk]

    # --- Parallel summarisation (operator.add accumulates across Send() fan-out) ---
    summaries: Annotated[list[StatementSummary], operator.add]

    # --- Parallel parsing (operator.add accumulates across Send() fan-out) ---
    parsed_statements: Annotated[list[ParsedStatement], operator.add]

    # --- KPI ---
    kpis: list[dict]

    # --- Chat / query ---
    chat_history: list[dict]   # [{"role": "user"|"assistant", "content": str, "chart_spec": ...}]
    current_query: str

    # --- Router ---
    selected_statements: list[str]   # e.g. ["profit_and_loss"] or ["balance_sheet", "cash_flows"]

    # --- Answer generation ---
    answer_text: str
    chart_spec: Optional[dict]       # None if no chart needed

    # --- Validation / retry ---
    validation: Optional[ValidationResult]
    retry_count: int                 # increments each loop; capped at 2
