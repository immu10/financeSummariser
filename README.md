This was a college course project (LLMs).

# FinSight AI

> LangGraph-powered financial intelligence for annual reports.

FinSight AI turns a company's annual report PDF into an interactive financial dashboard and a grounded, self-validating chatbot. Upload a report, and the app locates the three core financial statements, parses them into structured data, surfaces executive KPIs, and answers free-form questions with auto-generated charts.

---

## Overview

The app is built around **two LangGraph state graphs**:

- **Ingestion graph** — runs once per PDF upload. It locates the Standalone Balance Sheet, Profit & Loss, and Cash Flow statements, then summarises and parses all three **in parallel**, and finally distills 8 executive KPIs.
- **Query graph** — runs once per chat message. It routes the question to only the relevant statement(s), generates an answer (plus an optional chart), and **self-validates** the answer against the source data — retrying up to twice if the answer is ungrounded or wrong.

Key design choices:

- **Parallel fan-out** — summarisation and parsing of all 3 statements run concurrently via LangGraph `Send`, with `operator.add` reducers accumulating results.
- **Cheap routing** — the query router reads only lightweight summaries + key figures (not full statement JSON) to decide which statements are relevant.
- **Self-correcting answers** — a validator node audits each answer for fabricated numbers and off-topic responses, feeding its critique back into a retry loop.
- **AI-driven charts** — a routing layer decides if a chart helps and emits a structured `chart_spec` rendered with Plotly.
- **Keyword fallback** — if GPT-4o can't locate a statement, a keyword scan finds it.

---

## Architecture

```
                          ┌──────────────────────────┐
                          │   Streamlit UI (ui.py)    │
                          │  upload · dashboard · chat │
                          └────────────┬─────────────┘
                                       │
                  ┌────────────────────┴────────────────────┐
                  │                                          │
       PDF upload │                            chat message  │
                  ▼                                          ▼
   ╔══════════════════════════════╗          ╔══════════════════════════════╗
   ║      INGESTION GRAPH         ║          ║        QUERY GRAPH           ║
   ║      (runs once/PDF)         ║          ║      (runs once/message)     ║
   ╟──────────────────────────────╢          ╟──────────────────────────────╢
   ║                              ║          ║                              ║
   ║          START               ║          ║          START               ║
   ║            │                 ║          ║            │                 ║
   ║            ▼                 ║          ║            ▼                 ║
   ║      split_document          ║          ║       route_query            ║
   ║   (locate 3 statements)      ║          ║  (pick relevant statements)  ║
   ║         ╱      ╲             ║          ║            │                 ║
   ║  Send×3╱        ╲Send×3      ║          ║            ▼                 ║
   ║       ▼          ▼           ║          ║     generate_answer ◄──────┐ ║
   ║  summarize_   parse_         ║          ║   (answer + chart_spec)    │ ║
   ║  statement    statement      ║          ║            │               │ ║
   ║  (×3 ‖)       (×3 ‖)         ║          ║            ▼        "retry" │ ║
   ║       ╲          ╱           ║          ║     validate_answer ───────┘ ║
   ║        ╲        ╱            ║          ║   (audit vs source data)     ║
   ║         ▼      ▼             ║          ║            │  "done"         ║
   ║       build_kpis             ║          ║            ▼  (max 2 retries)║
   ║   (8 executive KPIs)         ║          ║           END                ║
   ║            │                 ║          ║                              ║
   ║           END                ║          ╚══════════════════════════════╝
   ╚══════════════════════════════╝
            │                                          │
            ▼                                          ▼
   raw_pages → chunks → summaries          answer_text + chart_spec
   + parsed_statements + kpis              (rendered in chat)

                         ┌─────────────────────────┐
                         │   OpenAI GPT-4o          │
                         │ (structured JSON output) │
                         └─────────────────────────┘
                    every node calls the LLM via main.py client
```

### File layout

| File | Responsibility |
|------|----------------|
| `ui.py` | Streamlit front-end — upload, KPI dashboard, statement tables, summaries, chatbot |
| `graph.py` | Defines & compiles the two LangGraph graphs (`ingestion_graph`, `query_graph`) |
| `nodes.py` | All node functions, fan-out edge helpers, prompts, and JSON schemas |
| `state.py` | `FinancialGraphState` TypedDict + sub-types (chunks, summaries, parsed, validation) |
| `main.py` | Shared helpers — OpenAI client, PDF text extraction, Plotly chart builder |

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Orchestration | [LangGraph](https://langchain-ai.github.io/langgraph/) `>=0.2.0` | State-graph workflows, parallel fan-out (`Send`), conditional retry edges |
| LLM | OpenAI **GPT-4o** (`openai>=1.0.0`) | Document navigation, parsing, summarisation, routing, answering, validation |
| UI | [Streamlit](https://streamlit.io/) `>=1.44.0` | Web app — dashboard, tabs, chat interface |
| PDF parsing | [PyMuPDF](https://pymupdf.readthedocs.io/) (`fitz`) `>=1.25.0` | Per-page text extraction from annual reports |
| Charts | [Plotly](https://plotly.com/python/) `>=5.24.0` | Interactive bar / line / pie / waterfall charts |
| Data | [pandas](https://pandas.pydata.org/) `>=2.0.0` | Statement tables in the UI |
| Validation | [Pydantic](https://docs.pydantic.dev/) `>=2.7.4` | Type models (via LangGraph) |
| Config | [python-dotenv](https://pypi.org/project/python-dotenv/) `>=1.0.0` | Loads `OPENAI_API_KEY` from `.env` |
| Language | Python 3.12 | — |

---

## Getting Started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure your API key

Create a `.env` file in the project root:

```
OPENAI_API_KEY=sk-...
```

### 3. Run the app

```bash
streamlit run ui.py
```

or

```bash
python main.py
```

Then open the local URL Streamlit prints, upload an annual report PDF in the sidebar, and click **Analyze Report**.

---

## How It Works (end to end)

1. **Upload** — PyMuPDF extracts text page by page.
2. **Split** — GPT-4o reads a preview of each page to locate the 3 statements' page ranges (with a keyword fallback).
3. **Parallel processing** — each statement is summarised (short digest + key figures) and parsed (full structured line items) at the same time.
4. **KPIs** — GPT-4o distills 8 CFO-level KPIs from the parsed statements.
5. **Dashboard** — KPIs, auto-generated P&L and cash-flow charts, full statement tables, and summaries.
6. **Chat** — each question is routed to the relevant statement(s), answered with citations and an optional chart, then validated and retried if the answer isn't grounded in the data.

---

> **Note:** This app is tuned for **Indian annual reports** (standalone statements, INR units). Prompts reference Indian reporting conventions but generalise to most annual-report formats.

---

## Tags

`#LLM` · `#PDF-parsing` · `#LangGraph` · `#financial-analysis`
