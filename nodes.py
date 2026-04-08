"""
nodes.py — All LangGraph node functions and edge/fan-out helpers.

Each node is a plain Python function:  state_dict -> partial_dict
LangGraph merges the returned partial dict into the global state.
"""
from __future__ import annotations
import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from langgraph.types import Send

from state import (
    FinancialGraphState,
    StatementChunk,
    StatementSummary,
    ParsedStatement,
    ValidationResult,
)

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------------------------------------------------------------------
# JSON schemas reused across nodes
# ---------------------------------------------------------------------------

_SINGLE_STATEMENT_SCHEMA_ITEMS = {
    "type": "object",
    "properties": {
        "section_name": {"type": "string"},
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "current_value": {"type": "number"},
                    "prior_value": {"type": "number"},
                    "is_subtotal": {"type": "boolean"},
                },
                "required": ["label", "current_value", "prior_value", "is_subtotal"],
            },
        },
    },
    "required": ["section_name", "line_items"],
}

BALANCE_SHEET_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "balance_sheet",
        "strict": False,
        "schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "as_of_date_current": {"type": "string"},
                "as_of_date_prior": {"type": "string"},
                "sections": {"type": "array", "items": _SINGLE_STATEMENT_SCHEMA_ITEMS},
            },
            "required": ["title", "as_of_date_current", "as_of_date_prior", "sections"],
        },
    },
}

PL_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "profit_and_loss",
        "strict": False,
        "schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "period_current": {"type": "string"},
                "period_prior": {"type": "string"},
                "sections": {"type": "array", "items": _SINGLE_STATEMENT_SCHEMA_ITEMS},
            },
            "required": ["title", "period_current", "period_prior", "sections"],
        },
    },
}

CF_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "cash_flows",
        "strict": False,
        "schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "period_current": {"type": "string"},
                "period_prior": {"type": "string"},
                "sections": {"type": "array", "items": _SINGLE_STATEMENT_SCHEMA_ITEMS},
            },
            "required": ["title", "period_current", "period_prior", "sections"],
        },
    },
}

_SCHEMA_FOR = {
    "balance_sheet": BALANCE_SHEET_SCHEMA,
    "profit_and_loss": PL_SCHEMA,
    "cash_flows": CF_SCHEMA,
}

CHART_ROUTING_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "chart_routing",
        "strict": False,
        "schema": {
            "type": "object",
            "properties": {
                "needs_chart": {"type": "boolean"},
                "reasoning": {"type": "string"},
                "chart_spec": {
                    "type": ["object", "null"],
                    "properties": {
                        "chart_type": {
                            "type": "string",
                            "enum": ["bar", "line", "pie", "waterfall", "horizontal_bar"],
                        },
                        "title": {"type": "string"},
                        "x_label": {"type": "string"},
                        "y_label": {"type": "string"},
                        "data_series": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "x": {"type": "array", "items": {"type": "string"}},
                                    "y": {"type": "array", "items": {"type": "number"}},
                                    "color": {"type": "string"},
                                },
                                "required": ["name", "x", "y"],
                            },
                        },
                        "show_legend": {"type": "boolean"},
                        "annotations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "x": {"type": "string"},
                                    "y": {"type": "number"},
                                    "text": {"type": "string"},
                                },
                                "required": ["x", "y", "text"],
                            },
                        },
                    },
                    "required": ["chart_type", "title", "data_series"],
                },
            },
            "required": ["needs_chart", "reasoning", "chart_spec"],
        },
    },
}

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SPLIT_SYSTEM_PROMPT = """You are a financial document navigator for Indian annual reports.

Given a sample of each page (first 300 characters), identify which page indices (0-based)
contain each of these three statements:
1. Standalone Balance Sheet
2. Standalone Statement of Profit and Loss
3. Standalone Statement of Cash Flows

Return JSON exactly:
{
  "company_name": "<legal entity name from any page header>",
  "currency_unit": "<e.g. INR in millions or Rs. in Crores>",
  "sections": [
    {"statement_type": "balance_sheet",   "start_page": 0, "end_page": 2},
    {"statement_type": "profit_and_loss", "start_page": 3, "end_page": 4},
    {"statement_type": "cash_flows",      "start_page": 5, "end_page": 6}
  ]
}

Notes:
- Expand each range by 1 page on each side to avoid missing content that starts mid-page
- If a statement is not found, use start_page: -1 and end_page: -1
- Ignore consolidated statements, notes, schedules, and auditor's report"""

SUMMARIZE_SYSTEM_PROMPT = """You are a financial statement summarizer.

Given the raw text of a single financial statement, produce:
1. A 3-5 sentence natural language summary of its key points
2. A flat dict of the 6 most important numerical figures (label → number)

Return JSON exactly:
{
  "summary_text": "...",
  "key_figures": {"Total Revenue": 808030, "Net Profit": 72533, ...}
}

Rules:
- Numbers must be raw values (no units, no commas), e.g. 808030 not "808,030"
- Do NOT invent figures — only use what is present in the text
- If the text is incomplete or unreadable, still return valid JSON with best effort"""

PARSE_SYSTEM_PROMPT_TEMPLATE = """You are a financial document parser specialising in Indian annual reports.

Extract the {statement_label} from the text below. Currency unit: {currency_unit}

Rules:
- Extract ALL line items including sub-items, subtotals, and totals
- Preserve section hierarchy (e.g. ASSETS > Non-current assets > Property)
- Parse numeric values: remove commas, parentheses mean negative e.g. (1,234) = -1234
- Mark subtotals/totals as is_subtotal: true
- Extract BOTH current and prior year columns
- If a value is truly missing, use 0
- Ignore any content that is not part of this specific statement"""

ROUTER_SYSTEM_PROMPT = """You are a financial query router.

You have summaries and key figures for these financial statements:
{summaries_context}

Given the user query, decide:
1. Which statements are needed (can be 1, 2, or all 3)
2. Whether a chart would help

Statement selection guide:
- Revenue, expenses, profit, EBIT, margins     → profit_and_loss
- Assets, liabilities, equity, debt ratios     → balance_sheet
- Operating/investing/financing cash, FCF      → cash_flows
- Liquidity ratios, working capital            → balance_sheet + cash_flows
- Return metrics (ROE, ROA, ROCE)              → balance_sheet + profit_and_loss
- Comprehensive / overview questions           → all three

Return JSON:
{{"selected_statements": ["profit_and_loss"], "needs_chart": false}}"""

ANSWER_SYSTEM_PROMPT_TEMPLATE = """You are an expert financial analyst for {company_name} ({currency_unit}).

You have access to the following statement(s) selected as relevant to this query:
{selected_data_json}

{retry_instruction}

Instructions:
- Answer in clear, professional paragraphs (2-4 sentences per paragraph)
- Always cite exact figures from the data above, using exact line item names
- Always mention both current and prior year when relevant, and calculate YoY change
- If a chart was generated for this query, briefly reference it ("As shown in the chart above...")
- Do NOT use markdown formatting (no bold, no bullet points, no headers)
- Do NOT compute figures not derivable from the data provided
- If you cannot answer from the data, say so clearly"""

CHART_ROUTING_SYSTEM_PROMPT = """You are a financial AI assistant routing layer.

Generate a chart ONLY when the user asks about:
- Comparisons between items or periods ("compare", "vs", "versus", "against")
- Trends or changes over time ("trend", "growth", "decline", "over time")
- Breakdowns or compositions ("breakdown", "composition", "split", "proportion")
- Visual requests ("show", "visualize", "chart", "graph", "plot", "display")
- Ratios or distributions

Do NOT generate a chart for single value lookups, definitions, or general yes/no questions.

Chart type guide:
- bar: comparing multiple items or two periods side by side
- line: trend over time (needs at least 3 data points)
- pie: composition/breakdown as percentages (max 8 slices)
- waterfall: showing how a value builds up step by step
- horizontal_bar: ranking items (many items, long labels)

CRITICAL: All y values MUST be exact numbers from the financial_data provided."""

VALIDATOR_SYSTEM_PROMPT = """You are a financial answer auditor.

Given:
- The user's query
- The financial data used to answer it
- The generated answer

Check for:
1. Are all numbers mentioned in the answer present in the financial data?
2. Are any numbers clearly wrong (off by 10x, wrong sign, etc.)?
3. Does the answer actually address the question asked?
4. Are any claims made that cannot be derived from the data?

A minor rounding difference is acceptable. A fabricated number or off-topic answer is not.

Return JSON:
{"is_valid": true, "critique": ""}
or
{"is_valid": false, "critique": "Specific reason why the answer is incorrect or ungrounded"}"""

# ---------------------------------------------------------------------------
# Node 1 — split_document
# ---------------------------------------------------------------------------

_FALLBACK_KEYWORDS: dict[str, list[str]] = {
    "balance_sheet": [
        "balance sheet", "total assets", "total liabilities",
        "shareholders equity", "shareholders' equity", "net worth",
    ],
    "profit_and_loss": [
        "profit and loss", "profit & loss", "statement of profit",
        "revenue from operations", "total income", "earnings per share",
        "other income", "profit before tax",
    ],
    "cash_flows": [
        "cash flow", "cash flows", "operating activities",
        "investing activities", "financing activities",
    ],
}


def _keyword_fallback(pages: list[str], stype: str) -> tuple[int, int] | None:
    """Scan full page text for keyword matches; return (start, end) or None."""
    keywords = _FALLBACK_KEYWORDS.get(stype, [])
    matching: list[int] = []
    for i, page in enumerate(pages):
        page_lower = page.lower()
        if sum(1 for kw in keywords if kw in page_lower) >= 2:
            matching.append(i)
    if not matching:
        return None
    return max(0, matching[0] - 1), min(len(pages) - 1, matching[-1] + 1)


def split_document(state: FinancialGraphState) -> dict:
    """
    Navigation call: scan first 500 chars/page so GPT-4o can locate each
    statement's page range.  Falls back to keyword search for any section
    that GPT-4o couldn't find (start_page == -1).
    """
    pages = state["raw_pages"]

    toc_text = "\n".join(
        f"[Page {i}]: {page[:500].strip()}"
        for i, page in enumerate(pages)
    )

    response = _client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SPLIT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Page previews:\n\n{toc_text}"},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    nav = json.loads(response.choices[0].message.content)

    company_name = nav.get("company_name", "")
    currency_unit = nav.get("currency_unit", "")

    # Build a dict keyed by statement_type from the AI response
    ai_sections: dict[str, dict] = {
        s["statement_type"]: s for s in nav.get("sections", [])
    }

    chunks: list[StatementChunk] = []
    for stype in ("balance_sheet", "profit_and_loss", "cash_flows"):
        section = ai_sections.get(stype, {})
        start_page = section.get("start_page", -1)
        end_page = section.get("end_page", -1)

        # Fix: check the raw values BEFORE applying max/min clamping
        if start_page == -1 or end_page == -1:
            # AI couldn't locate this section — try keyword fallback
            result = _keyword_fallback(pages, stype)
            if result is None:
                continue  # truly not found
            start_page, end_page = result

        start = max(0, start_page)
        end = min(len(pages) - 1, end_page)

        relevant_pages = pages[start : end + 1]
        raw_text = "\n\n--- PAGE BREAK ---\n\n".join(relevant_pages)
        chunks.append(
            StatementChunk(
                statement_type=stype,
                raw_text=raw_text,
                page_range=f"pages {start}-{end}",
            )
        )

    return {
        "statement_chunks": chunks,
        "company_name": company_name,
        "currency_unit": currency_unit,
    }


# ---------------------------------------------------------------------------
# Edge helpers — fan-out functions (return list[Send], not nodes themselves)
# ---------------------------------------------------------------------------

def fan_out_summaries(state: FinancialGraphState) -> list[Send]:
    """Dispatch one summarize_statement task per chunk in parallel."""
    return [
        Send(
            "summarize_statement",
            {"chunk": chunk, "currency_unit": state["currency_unit"]},
        )
        for chunk in state["statement_chunks"]
    ]


def fan_out_parsing(state: FinancialGraphState) -> list[Send]:
    """Dispatch one parse_statement task per chunk in parallel."""
    return [
        Send(
            "parse_statement",
            {"chunk": chunk, "currency_unit": state["currency_unit"]},
        )
        for chunk in state["statement_chunks"]
    ]


# ---------------------------------------------------------------------------
# Node 2 — summarize_statement  (receives per-Send private state)
# ---------------------------------------------------------------------------

def summarize_statement(state: dict) -> dict:
    """
    Summarise one statement chunk into a short digest + top key figures.
    Runs in parallel for all 3 statements via fan_out_summaries.
    Returns {"summaries": [StatementSummary]} — operator.add accumulates.
    """
    chunk: StatementChunk = state["chunk"]
    currency_unit: str = state.get("currency_unit", "")

    response = _client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SUMMARIZE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Currency unit: {currency_unit}\n\n"
                    f"Statement type: {chunk['statement_type']}\n\n"
                    f"{chunk['raw_text']}"
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    result = json.loads(response.choices[0].message.content)

    summary = StatementSummary(
        statement_type=chunk["statement_type"],
        summary_text=result.get("summary_text", ""),
        key_figures=result.get("key_figures", {}),
    )
    return {"summaries": [summary]}


# ---------------------------------------------------------------------------
# Node 3 — parse_statement  (receives per-Send private state)
# ---------------------------------------------------------------------------

_STATEMENT_LABELS = {
    "balance_sheet": "Standalone Balance Sheet",
    "profit_and_loss": "Standalone Statement of Profit and Loss",
    "cash_flows": "Standalone Statement of Cash Flows",
}


def parse_statement(state: dict) -> dict:
    """
    Full structured extraction of one statement scoped to its own pages only.
    Runs in parallel for all 3 statements via fan_out_parsing.
    Returns {"parsed_statements": [ParsedStatement]} — operator.add accumulates.
    """
    chunk: StatementChunk = state["chunk"]
    currency_unit: str = state.get("currency_unit", "")
    stype = chunk["statement_type"]
    label = _STATEMENT_LABELS.get(stype, stype)
    schema = _SCHEMA_FOR.get(stype, {"type": "json_object"})

    system_prompt = PARSE_SYSTEM_PROMPT_TEMPLATE.format(
        statement_label=label,
        currency_unit=currency_unit,
    )

    response = _client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Extract the {label} from:\n\n{chunk['raw_text']}"
                ),
            },
        ],
        response_format=schema,
        temperature=0,
    )
    data = json.loads(response.choices[0].message.content)

    parsed = ParsedStatement(statement_type=stype, data=data)
    return {"parsed_statements": [parsed]}


# ---------------------------------------------------------------------------
# Node 4 — build_kpis
# ---------------------------------------------------------------------------

_KPI_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "kpi_summary",
        "strict": False,
        "schema": {
            "type": "object",
            "properties": {
                "kpis": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "value": {"type": "string"},
                            "delta": {"type": "string"},
                            "delta_color": {"type": "string"},
                        },
                        "required": ["name", "value", "delta", "delta_color"],
                    },
                }
            },
            "required": ["kpis"],
        },
    },
}


def build_kpis(state: FinancialGraphState) -> dict:
    """
    Assembles full statements dict from the 3 parsed results, then extracts 8 KPIs.
    Runs after both parallel fan-outs (summarise + parse) have converged.
    """
    company_name = state.get("company_name", "the company")
    currency_unit = state.get("currency_unit", "")

    full_statements: dict = {
        "company_name": company_name,
        "currency_unit": currency_unit,
    }
    for ps in state.get("parsed_statements", []):
        full_statements[ps["statement_type"]] = ps["data"]

    prompt = (
        f"Given these financial statements for {company_name} ({currency_unit}):\n\n"
        f"{json.dumps(full_statements, indent=2)}\n\n"
        "Select exactly 8 of the most important KPIs that a CFO would put on an executive one-pager.\n"
        "For each KPI:\n"
        "- name: short display label (e.g. 'Total Revenue', 'Net Profit', 'Total Assets')\n"
        "- value: formatted value for current year with commas (e.g. '808,030')\n"
        "- delta: YoY percentage change as a string (e.g. '+17.3%', '-11.2%')\n"
        "- delta_color: 'normal' if positive delta is good, 'inverse' if positive delta is bad\n\n"
        "Return exactly 8 KPIs."
    )

    response = _client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format=_KPI_SCHEMA,
        temperature=0,
    )
    data = json.loads(response.choices[0].message.content)
    return {"kpis": data.get("kpis", [])}


# ---------------------------------------------------------------------------
# Node 5 — route_query
# ---------------------------------------------------------------------------

_ROUTER_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "query_routing",
        "strict": False,
        "schema": {
            "type": "object",
            "properties": {
                "selected_statements": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["balance_sheet", "profit_and_loss", "cash_flows"],
                    },
                },
                "needs_chart": {"type": "boolean"},
            },
            "required": ["selected_statements", "needs_chart"],
        },
    },
}


def route_query(state: FinancialGraphState) -> dict:
    """
    Reads the lightweight summaries to decide which 1-3 statements are needed.
    Much cheaper than passing full JSON — only summaries + key figures go to LLM.
    """
    summaries = state.get("summaries", [])
    query = state.get("current_query", "")

    summaries_context = "\n\n".join(
        f"[{s['statement_type']}]\n"
        f"Summary: {s['summary_text']}\n"
        f"Key figures: {json.dumps(s['key_figures'])}"
        for s in summaries
    )

    system = ROUTER_SYSTEM_PROMPT.format(summaries_context=summaries_context)

    response = _client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": query},
        ],
        response_format=_ROUTER_SCHEMA,
        temperature=0,
    )
    result = json.loads(response.choices[0].message.content)

    selected = result.get("selected_statements", [])
    # Fallback: if router returned nothing, use all three
    if not selected:
        selected = ["balance_sheet", "profit_and_loss", "cash_flows"]

    return {"selected_statements": selected}


# ---------------------------------------------------------------------------
# Node 6 — generate_answer
# ---------------------------------------------------------------------------

def generate_answer(state: FinancialGraphState) -> dict:
    """
    Two sub-calls:
      1. Chart routing — structured output, decides if & what chart to render.
      2. Text answer — grounded in only the selected statements' JSON.
    On retry, the validation critique is appended to the system prompt.
    """
    company_name = state.get("company_name", "the company")
    currency_unit = state.get("currency_unit", "")
    query = state.get("current_query", "")
    selected = state.get("selected_statements", [])
    parsed = state.get("parsed_statements", [])
    chat_history = state.get("chat_history", [])
    validation = state.get("validation")
    retry_count = state.get("retry_count", 0)

    # Build data context from only the selected statements
    selected_data: dict = {
        "company_name": company_name,
        "currency_unit": currency_unit,
    }
    for ps in parsed:
        if ps["statement_type"] in selected:
            selected_data[ps["statement_type"]] = ps["data"]
    selected_data_json = json.dumps(selected_data, indent=2)

    # --- Sub-call 1: chart routing ---
    chart_routing_messages = [
        {
            "role": "system",
            "content": CHART_ROUTING_SYSTEM_PROMPT
            + f"\n\nfinancial_data:\n{selected_data_json}",
        }
    ] + [{"role": m["role"], "content": m["content"]} for m in chat_history[-4:]]

    routing_resp = _client.chat.completions.create(
        model="gpt-4o",
        messages=chart_routing_messages,
        response_format=CHART_ROUTING_SCHEMA,
        temperature=0,
        max_tokens=2000,
    )
    routing = json.loads(routing_resp.choices[0].message.content)
    chart_spec = routing.get("chart_spec") if routing.get("needs_chart") else None

    # --- Sub-call 2: text answer ---
    retry_instruction = ""
    if retry_count > 0 and validation and not validation["is_valid"]:
        retry_instruction = (
            f"IMPORTANT — your previous answer was flagged as incorrect for this reason:\n"
            f"{validation['critique']}\n\n"
            "Please correct these specific issues in your new answer."
        )

    answer_system = ANSWER_SYSTEM_PROMPT_TEMPLATE.format(
        company_name=company_name,
        currency_unit=currency_unit,
        selected_data_json=selected_data_json,
        retry_instruction=retry_instruction,
    )

    messages_for_answer = [{"role": "system", "content": answer_system}] + [
        {"role": m["role"], "content": m["content"]} for m in chat_history
    ]

    answer_resp = _client.chat.completions.create(
        model="gpt-4o",
        messages=messages_for_answer,
        temperature=0.3,
    )
    answer_text = answer_resp.choices[0].message.content or ""

    return {
        "answer_text": answer_text,
        "chart_spec": chart_spec,
        "retry_count": retry_count,
    }


# ---------------------------------------------------------------------------
# Node 7 — validate_answer
# ---------------------------------------------------------------------------

_VALIDATOR_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "validation_result",
        "strict": False,
        "schema": {
            "type": "object",
            "properties": {
                "is_valid": {"type": "boolean"},
                "critique": {"type": "string"},
            },
            "required": ["is_valid", "critique"],
        },
    },
}


def validate_answer(state: FinancialGraphState) -> dict:
    """
    Self-critique: checks the generated answer for factual grounding against
    the selected statements' data. If invalid, increments retry_count.
    """
    query = state.get("current_query", "")
    answer = state.get("answer_text", "")
    selected = state.get("selected_statements", [])
    parsed = state.get("parsed_statements", [])
    retry_count = state.get("retry_count", 0)

    selected_data: dict = {}
    for ps in parsed:
        if ps["statement_type"] in selected:
            selected_data[ps["statement_type"]] = ps["data"]

    validation_prompt = (
        f"User query: {query}\n\n"
        f"Financial data used:\n{json.dumps(selected_data, indent=2)}\n\n"
        f"Generated answer:\n{answer}"
    )

    response = _client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": VALIDATOR_SYSTEM_PROMPT},
            {"role": "user", "content": validation_prompt},
        ],
        response_format=_VALIDATOR_SCHEMA,
        temperature=0,
    )
    result = json.loads(response.choices[0].message.content)

    new_retry_count = retry_count + (0 if result.get("is_valid", True) else 1)

    validation = ValidationResult(
        is_valid=result.get("is_valid", True),
        critique=result.get("critique", ""),
        retry_count=new_retry_count,
    )
    return {"validation": validation, "retry_count": new_retry_count}


# ---------------------------------------------------------------------------
# Conditional edge — should_retry
# ---------------------------------------------------------------------------

def should_retry(state: FinancialGraphState) -> str:
    """
    After validate_answer: route back to generate_answer if invalid and
    under the retry cap (2), otherwise END.
    """
    validation = state.get("validation")
    retry_count = state.get("retry_count", 0)

    if validation and not validation["is_valid"] and retry_count < 2:
        return "retry"
    return "done"
