### This is a token heavy version of the fin_stat repo in my github
this was made just to meet a course project requirment as the other wasnt finished in time

# FinSight AI 📊

**LangGraph-Powered Financial Intelligence System**

FinSight AI is an advanced financial document analysis platform that automatically extracts, parses, and analyzes financial statements from annual report PDFs using LangGraph state machines and GPT-4o. It provides intelligent chat capabilities with self-validating answers, automatic chart generation, and comprehensive financial insights.

---

## 🌟 Key Features

### 🤖 **Intelligent Document Processing**
- **Automatic statement detection** — Identifies and extracts Balance Sheet, Profit & Loss, and Cash Flow statements
- **Parallel processing** — Simultaneous extraction of all three statements for maximum efficiency
- **Smart page navigation** — AI-powered detection of statement boundaries across multi-page documents

### 📊 **Interactive Financial Analysis**
- **AI Chatbot** — Ask questions about revenue, profits, trends, ratios, and more
- **Smart routing** — Queries automatically directed to relevant statements
- **Self-validating answers** — Every response is fact-checked against source data with automatic retry (up to 2x)
- **Intelligent chart generation** — Automatic visualization when comparisons or trends are discussed

### 📈 **Executive Dashboard**
- **8 Key Performance Indicators** — Auto-selected most important metrics with YoY changes
- **Interactive visualizations** — P&L comparisons and cash flow waterfall charts
- **Statement summaries** — Natural language digests with key figures
- **Full statement explorer** — Complete line-by-line data tables

### 🎨 **Modern UI**
- **Dark glassmorphism design** — Beautiful, responsive Streamlit interface
- **Real-time processing** — Live feedback on document analysis progress
- **Persistent chat history** — Track conversation context throughout your session
- **Metadata transparency** — See which statements were used and if answers were retried

---

## 🏗️ Architecture

FinSight AI uses **LangGraph** to orchestrate two sophisticated state machines:

### 1️⃣ **Ingestion Graph** (Document Processing)

```
     START
       │
       ▼
  split_document  ──────────────────────────────────────┐
       │                                                 │
       │ Send×3                                    Send×3│
       ▼                                                 ▼
  summarize_statement                         parse_statement
  (runs 3× in parallel)                       (runs 3× in parallel)
       │   │   │                                   │   │   │
       └───┴───┘                                   └───┴───┘
           │                                           │
           └─────────────────┬─────────────────────────┘
                             ▼
                        build_kpis
                             │
                            END
```

**Graph Flow:**
1. **split_document** — Fast navigation pass using first 300 chars/page to identify statement boundaries
2. **Fan-out (parallel)**:
   - **summarize_statement** (3×) — Generate 3-5 sentence summary + top 6 figures for each statement
   - **parse_statement** (3×) — Full structured extraction of all line items with current/prior year values
3. **build_kpis** — Analyzes all parsed data to select 8 executive KPIs with YoY deltas

**Key Design Principles:**
- Uses `operator.add` reducers on state arrays to accumulate parallel results
- Cheap navigation pass before expensive extraction
- Each statement processed independently for maximum parallelism

---

### 2️⃣ **Query Graph** (Chat & Analysis)

```
     START
       │
       ▼
   route_query
       │
       ▼
  generate_answer  ◄──────────────┐
       │                          │
       ▼                          │ "retry" (max 2×)
  validate_answer  ───────────────┘
       │ "done"
      END
```

**Graph Flow:**
1. **route_query** — Analyzes query using lightweight summaries to select 1-3 relevant statements
2. **generate_answer** — Two-phase generation:
   - **Chart routing** — Decides if visualization would help and generates spec
   - **Text answer** — Grounded response using only selected financial data
3. **validate_answer** — Self-critique against source data; flags hallucinations or errors
4. **Conditional edge** — Retry if invalid (max 2 retries), otherwise complete

**Intelligent Features:**
- **Context-aware routing** — Only loads relevant statements (saves tokens)
- **Retry with critique** — Failed validations trigger regeneration with explicit feedback
- **Chart intelligence** — Automatically generates bar/line/pie/waterfall charts for visual queries

---

## � Complete Data Flow: AI-Powered End-to-End

### **Zero Hard-Coded Financial Data**

Every financial number, KPI, line item, and summary you see in FinSight AI is **100% AI-generated** from your uploaded PDF. There is no test data, no placeholders, no mock values.

### **Data Extraction Pipeline**

```
┌─────────────────────┐
│   PDF Upload        │
│  (Annual Report)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│  PyMuPDF: Raw Text Extraction           │
│  • Extract text page by page             │
│  • Preserve layout and structure         │
└──────────┬──────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│  GPT-4o: split_document                  │
│  • Scans first 300 chars per page        │
│  • Identifies statement page ranges      │
│  • Extracts company name & currency      │
│  • Fallback: keyword search if AI fails  │
└──────────┬───────────────────────────────┘
           │
           ├──────────────────────┬────────────────────────┐
           ▼                      ▼                        ▼
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
│ GPT-4o: summarize    │ │ GPT-4o: summarize    │ │ GPT-4o: summarize    │
│ Balance Sheet        │ │ Profit & Loss        │ │ Cash Flows           │
│ • 3-5 sentence text  │ │ • 3-5 sentence text  │ │ • 3-5 sentence text  │
│ • Top 6 key figures  │ │ • Top 6 key figures  │ │ • Top 6 key figures  │
└──────────────────────┘ └──────────────────────┘ └──────────────────────┘
           │                      │                        │
           ├──────────────────────┴────────────────────────┘
           │
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
│ GPT-4o: parse        │ │ GPT-4o: parse        │ │ GPT-4o: parse        │
│ Balance Sheet        │ │ Profit & Loss        │ │ Cash Flows           │
│ • ALL line items     │ │ • ALL line items     │ │ • ALL line items     │
│ • Current year vals  │ │ • Current year vals  │ │ • Current year vals  │
│ • Prior year vals    │ │ • Prior year vals    │ │ • Prior year vals    │
│ • Section hierarchy  │ │ • Section hierarchy  │ │ • Section hierarchy  │
└──────────────────────┘ └──────────────────────┘ └──────────────────────┘
           │                      │                        │
           └──────────────────────┬────────────────────────┘
                                  ▼
                    ┌─────────────────────────────┐
                    │  GPT-4o: build_kpis         │
                    │  • Analyzes ALL parsed data │
                    │  • Selects 8 top metrics    │
                    │  • Calculates YoY changes   │
                    │  • Assigns delta colors     │
                    └─────────────┬───────────────┘
                                  │
                                  ▼
                    ┌──────────────────────────────┐
                    │  Display in Streamlit UI     │
                    │  • Dashboard: 8 KPI cards    │
                    │  • Statements: Full tables   │
                    │  • Summaries: Natural text   │
                    │  • Chat: Q&A with data       │
                    └──────────────────────────────┘
```

### **What Gets AI-Generated**

| Data Type | Source | AI Model | Example |
|-----------|--------|----------|---------|
| **Company Name** | PDF header/title | GPT-4o | "Reliance Industries Limited" |
| **Currency Unit** | Document metadata | GPT-4o | "INR in Crores" |
| **Statement Sections** | Page content | GPT-4o | Balance Sheet: pages 45-47 |
| **Summaries** | Full statement text | GPT-4o | "Total assets increased by 8.5% to ₹1.2M crores..." |
| **Key Figures** | Summaries | GPT-4o | {"Total Revenue": 808030, "Net Profit": 72533} |
| **Parsed Line Items** | Full statement text | GPT-4o | 150+ line items per statement with current/prior values |
| **KPIs** | All parsed data | GPT-4o | 8 metrics auto-selected (Revenue, Profit, Assets, etc.) |
| **YoY Changes** | Current vs prior | GPT-4o | "+17.3%", "-5.2%" |
| **Chat Answers** | Query + selected data | GPT-4o | "Revenue grew from ₹688,052 to ₹808,030..." |
| **Charts** | Query intent | GPT-4o | Bar chart: Revenue vs Expenses (2 years) |

### **What Is Hard-Coded**

Only **presentation elements** are hard-coded:

- **UI Styling**: Colors (#00CC88, #0088FF), fonts (Inter), spacing
- **Display Labels**: "Balance Sheet", "Current Year", "Prior Year"
- **Prompts**: Instructions that guide AI behavior (~2000 words)
- **JSON Schemas**: Structure definitions for validation
- **Fallback Keywords**: Emergency search terms if AI navigation fails

**Critical Point**: Numbers like `808030` or `72533` appearing in the codebase are **examples in documentation/prompts only** — they are NOT shown to users. All displayed values come from your PDF.

### **Data Persistence**

```python
# Before upload:
st.session_state.kpis = []                    # Empty
st.session_state.summaries = []                # Empty
st.session_state.parsed_statements = []        # Empty

# After ingestion_graph runs:
st.session_state.kpis = [                      # AI-generated from YOUR PDF
    {"name": "Total Revenue", "value": "808,030", "delta": "+17.3%"},
    # ... 7 more KPIs selected by GPT-4o
]
st.session_state.summaries = [                 # AI-generated summaries
    {"statement_type": "balance_sheet", "summary_text": "...", "key_figures": {...}},
    # ... 2 more summaries
]
st.session_state.parsed_statements = [         # AI-parsed data
    {"statement_type": "balance_sheet", "data": {150+ line items}},
    # ... 2 more statements
]
```

If PDF upload fails or AI extraction fails, you see:
- Empty dashboard with placeholder text
- "Summaries will appear after analysis"
- No fallback data displayed

### **Quality Assurance**

Every AI-generated answer goes through validation:

1. **Generate Answer** → GPT-4o creates response with citations
2. **Validate Answer** → Separate GPT-4o call checks:
   - Are all cited numbers present in source data?
   - Are calculations correct?
   - Does answer actually address the question?
3. **Retry if Invalid** → If validation fails, regenerate with critique (max 2×)
4. **Display with Metadata** → Show which statements used + retry count

This ensures **100% data fidelity** — no hallucinated numbers, no made-up figures.

---

## �🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Orchestration** | [LangGraph 0.2+](https://github.com/langchain-ai/langgraph) | State machine workflows with parallel execution |
| **LLM** | OpenAI GPT-4o | Text extraction, summarization, analysis, validation |
| **UI Framework** | [Streamlit 1.44+](https://streamlit.io/) | Interactive web interface |
| **PDF Processing** | [PyMuPDF (fitz) 1.25+](https://pymupdf.readthedocs.io/) | Fast PDF text extraction |
| **Visualization** | [Plotly 5.24+](https://plotly.com/) | Interactive charts (bar, line, pie, waterfall) |
| **Data Handling** | Pandas 2.0+ | Tabular data processing |
| **Type Safety** | Pydantic 2.7+ | State validation & schema enforcement |
| **Configuration** | python-dotenv 1.0+ | Environment variable management |

---

## 📦 Installation

### Prerequisites
- **Python 3.10+** (recommended: 3.11)
- **OpenAI API Key** with GPT-4o access
- **Git** (optional, for cloning)

### Setup Steps

1. **Clone or download the repository:**
```bash
git clone <your-repo-url>
```

2. **Create a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables:**
   
   Create a `.env` file in the project root:
```bash
OPENAI_API_KEY=sk-your-api-key-here
```

5. **Verify installation:**
```bash
streamlit --version
python -c "import langgraph; print('LangGraph version:', langgraph.__version__)"
```

---

## 🚀 Usage

### Starting the Application

```bash
streamlit run main.py
```

The app will open in your browser at `http://localhost:8501`.

---

### Workflow

#### **Step 1: Upload PDF**
1. Click **"Upload Annual Report PDF"** in the sidebar
2. Select a PDF containing Indian annual report financial statements
3. Click **"Analyze Report"**

**What happens:**
- PDF pages are extracted using PyMuPDF
- Document is split into 3 statement sections
- Parallel summarization + parsing begins (6 AI calls simultaneously)
- KPIs are computed from parsed data
- Process completes in ~15-30 seconds

---

#### **Step 2: Explore Dashboard**
Navigate through four tabs:

**📊 Dashboard:**
- 8 executive KPIs with YoY changes
- P&L comparison chart (current vs prior year)
- Cash flow waterfall breakdown

**📄 Financial Statements:**
- Full line-by-line data for all three statements
- Expandable sections with current/prior year columns
- Preserves hierarchical structure

**📝 Summaries:**
- Natural language summaries (3-5 sentences each)
- Top 6 key figures per statement
- Quick overview without diving into raw data

**💬 AI Chatbot:**
- Interactive question-answering
- Automatic chart generation for visual queries
- Full transparency on which statements were used

---

#### **Step 3: Ask Questions**
Example queries:

```
💡 "What was the revenue growth from last year?"
💡 "Compare operating profit margin to net profit margin"
💡 "Show me the breakdown of total assets"
💡 "Did cash from operations increase or decrease?"
💡 "What's the debt-to-equity ratio?"
💡 "Plot revenue vs expenses for both years"
```

**Query Processing:**
1. Router analyzes your question using summaries
2. Selects relevant statements (1, 2, or all 3)
3. Generates answer + optional chart
4. Validates response against source data
5. Retries if validation fails (max 2×)
6. Displays result with metadata

**Metadata shown:**
- Which statements were used
- Number of retries (if any)
- Validation status

---

## 📁 Project Structure

```
immu/
│
├── main.py              # Shared utilities (PDF extraction, chart building, OpenAI client)
├── state.py             # TypedDict definitions for graph state + sub-types
├── nodes.py             # All 7 node functions + edge helpers + prompts + schemas
├── graph.py             # LangGraph definitions (ingestion_graph, query_graph)
├── ui.py                # Streamlit interface with 4 tabs + chat logic
│
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (OPENAI_API_KEY) — not in repo
├── data/                # Sample PDFs for testing
│   └── Annual_Report_FY25-152-157.pdf
│
└── README.md            # This file
```

---

## 🔍 Detailed Component Breakdown

### **main.py** — Shared Utilities
```python
# OpenAI client initialization
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# PDF extraction
extract_text_by_page(file_obj) -> list[str]

# Chart rendering with custom dark theme
build_plotly_figure(chart_spec: dict) -> go.Figure
```

**Responsibilities:**
- Single source of OpenAI client (imported by nodes.py and ui.py)
- PDF → list of page text strings
- Chart spec dict → styled Plotly figure

---

### **state.py** — Type Definitions

**Core State: `FinancialGraphState`**
```python
{
    # Ingestion
    "raw_pages": list[str],              # PDF text by page
    "company_name": str,                 # Extracted from document
    "currency_unit": str,                # e.g. "INR in millions"
    
    # Split
    "statement_chunks": list[StatementChunk],
    
    # Parallel accumulation (operator.add)
    "summaries": list[StatementSummary],
    "parsed_statements": list[ParsedStatement],
    
    # KPIs
    "kpis": list[dict],
    
    # Chat
    "chat_history": list[dict],
    "current_query": str,
    "selected_statements": list[str],
    
    # Answer
    "answer_text": str,
    "chart_spec": Optional[dict],
    
    # Validation
    "validation": Optional[ValidationResult],
    "retry_count": int,
}
```

**Sub-types:**
- **StatementChunk** — Raw text + statement type + page range
- **StatementSummary** — 3-5 sentence summary + key figures dict
- **ParsedStatement** — Full structured JSON (matches schema)
- **ValidationResult** — is_valid + critique + retry_count

---

### **nodes.py** — Graph Logic (600+ lines)

**7 Node Functions:**

| Node | Purpose | Input | Output | Model Calls |
|------|---------|-------|--------|-------------|
| `split_document` | Find statement page ranges | raw_pages | statement_chunks, company_name, currency_unit | 1× (navigation) |
| `summarize_statement` | 3-5 sentence summary + top 6 figures | chunk (private state) | summaries[] | 1× per statement |
| `parse_statement` | Full structured extraction | chunk (private state) | parsed_statements[] | 1× per statement |
| `build_kpis` | Select 8 executive metrics | parsed_statements | kpis[] | 1× |
| `route_query` | Decide which statements needed | current_query, summaries | selected_statements[] | 1× |
| `generate_answer` | Text + chart generation | current_query, selected data | answer_text, chart_spec | 2× (routing + answer) |
| `validate_answer` | Check for hallucinations | answer, financial data | validation, retry_count | 1× |

**Edge Helpers:**
- `fan_out_summaries()` → returns `list[Send]` to dispatch 3 parallel summarizations
- `fan_out_parsing()` → returns `list[Send]` to dispatch 3 parallel parsings
- `should_retry()` → conditional edge: "retry" if invalid + under cap, else "done"

**Key Prompts:**
- `SPLIT_SYSTEM_PROMPT` — Navigation instructions for finding statements
- `SUMMARIZE_SYSTEM_PROMPT` — Rules for summary + key figures
- `PARSE_SYSTEM_PROMPT_TEMPLATE` — Structured extraction guidelines
- `ROUTER_SYSTEM_PROMPT` — Statement selection logic
- `ANSWER_SYSTEM_PROMPT_TEMPLATE` — Grounded response generation
- `CHART_ROUTING_SYSTEM_PROMPT` — When to visualize
- `VALIDATOR_SYSTEM_PROMPT` — Fact-checking criteria

**JSON Schemas:**
- `BALANCE_SHEET_SCHEMA`, `PL_SCHEMA`, `CF_SCHEMA` — Structured output formats
- `CHART_ROUTING_SCHEMA` — Chart spec structure
- `_ROUTER_SCHEMA`, `_VALIDATOR_SCHEMA`, `_KPI_SCHEMA` — Other outputs

---

### **graph.py** — LangGraph Definitions

**Exports two compiled graphs:**

```python
ingestion_graph = _build_ingestion_graph()
query_graph = _build_query_graph()
```

**Ingestion Graph Builder:**
```python
builder.add_node("split_document", split_document)
builder.add_node("summarize_statement", summarize_statement)
builder.add_node("parse_statement", parse_statement)
builder.add_node("build_kpis", build_kpis)

builder.add_edge(START, "split_document")
builder.add_conditional_edges("split_document", fan_out_summaries, ["summarize_statement"])
builder.add_conditional_edges("split_document", fan_out_parsing, ["parse_statement"])
builder.add_edge("summarize_statement", "build_kpis")
builder.add_edge("parse_statement", "build_kpis")
builder.add_edge("build_kpis", END)
```

**Query Graph Builder:**
```python
builder.add_node("route_query", route_query)
builder.add_node("generate_answer", generate_answer)
builder.add_node("validate_answer", validate_answer)

builder.add_edge(START, "route_query")
builder.add_edge("route_query", "generate_answer")
builder.add_edge("generate_answer", "validate_answer")
builder.add_conditional_edges("validate_answer", should_retry, {
    "retry": "generate_answer",
    "done": END,
})
```

---

### **ui.py** — Streamlit Interface (550+ lines)

**Structure:**
1. **Config & CSS** — Dark glassmorphism styling
2. **Session State** — Persistent graph_state, chat_history, KPIs
3. **Sidebar** — Upload + Analyze + metadata display
4. **Main Content** — 4 tabs accessible after ingestion
5. **Chat Logic** — Input → query_graph.invoke() → display results

**Session State Variables:**
- `graph_state` — Full FinancialGraphState after ingestion
- `ingestion_done` — Boolean flag
- `company_name`, `currency_unit`, `kpis` — Extracted metadata
- `chat_history` — Mirrors graph state for UI rendering
- `pages_count` — Number of PDF pages processed

**Tab 1 — Dashboard:**
- Renders 8 KPIs in 2 rows of 4 columns
- Auto-generates P&L comparison chart
- Auto-generates cash flow waterfall

**Tab 2 — Financial Statements:**
- 3 expandable sections (one per statement)
- Pandas DataFrames with hierarchical line items
- Preserves subtotals/totals formatting

**Tab 3 — Summaries:**
- Natural language summaries from `summarize_statement` nodes
- Key figures displayed as metrics
- Quick overview without raw data

**Tab 4 — AI Chatbot:**
- Renders chat_history with charts inline
- Shows metadata (statements used, retry count, validation status)
- Chat input → query_graph → update state → st.rerun()

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Required
OPENAI_API_KEY=sk-your-openai-api-key-here

# Optional customizations
# MODEL_NAME=gpt-4o  # Default model
# MAX_RETRIES=2      # Default validation retry limit
```

---

### Customization Points

**Modify prompts** (in `nodes.py`):
- Adjust `SPLIT_SYSTEM_PROMPT` for different document formats
- Tweak `SUMMARIZE_SYSTEM_PROMPT` for longer/shorter summaries
- Customize `ANSWER_SYSTEM_PROMPT_TEMPLATE` for different tone

**Adjust schemas** (in `nodes.py`):
- Extend `_SINGLE_STATEMENT_SCHEMA_ITEMS` to capture more fields
- Add new chart types to `CHART_ROUTING_SCHEMA`

**UI styling** (in `ui.py`):
- Modify CSS in `st.markdown()` block for colors/fonts
- Change `COLORS` array in `main.py` for chart palette

**Graph behavior** (in `graph.py`):
- Change retry limit in `should_retry()` conditional
- Add new nodes or edges for extended workflows

---

## 🔬 Technical Deep Dive

### Why LangGraph?

**Traditional Approach Problems:**
- Sequential processing → slow (3 statements × 2 calls = 6× longer)
- Monolithic prompts → high token cost
- No structured retry logic → unreliable answers
- Tight coupling between extraction and analysis

**LangGraph Advantages:**
1. **Parallel execution** — `Send()` dispatches enable 3× simultaneous calls
2. **State management** — `operator.add` reducers accumulate parallel results
3. **Conditional routing** — Self-validation with automatic retry loops
4. **Modular design** — Each node is independently testable
5. **Transparency** — Full state inspection at every step

---

### Prompt Engineering Strategy

**Navigation-first extraction:**
- Cheap 1st pass with 300 chars/page → reduces extraction cost
- Only process relevant pages for each statement

**Two-phase answer generation:**
- Chart routing as separate structured call → clean separation
- Text answer with explicit financial_data context → no hallucinations

**Retry with critique:**
- Validation failure → regenerate with explicit critique
- Max 2 retries → prevents infinite loops
- Retry instruction appended to system prompt

---

### Parallel Processing Architecture

**Fan-out pattern:**
```python
def fan_out_summaries(state):
    return [
        Send("summarize_statement", {"chunk": chunk, ...})
        for chunk in state["statement_chunks"]
    ]
```

**How it works:**
1. `split_document` returns 3 chunks
2. Conditional edge calls `fan_out_summaries()`
3. Returns 3× `Send()` objects
4. LangGraph executes all 3 simultaneously
5. `operator.add` on `state["summaries"]` accumulates results
6. `build_kpis` waits for all 3 before firing

**Result:** 6 parallel AI calls (3 summaries + 3 parses) instead of 6 sequential → ~5× faster

---

### Self-Validation Mechanism

**Validator criteria:**
1. All numbers in answer present in financial_data?
2. Any numbers clearly wrong (10× off, wrong sign)?
3. Does answer address the actual question?
4. Any ungrounded claims?

**Retry flow:**
```
generate_answer → validate_answer
                      │
                      ├─ is_valid=True → END
                      │
                      └─ is_valid=False + retry_count < 2
                            → back to generate_answer with critique
```

**Critique forwarding:**
```python
if retry_count > 0 and not validation["is_valid"]:
    retry_instruction = f"Previous answer flagged: {validation['critique']}\n\n"
                        f"Please correct these specific issues."
```

---

## 🚧 Known Limitations & Future Enhancements

### Current Limitations

1. **Document format specificity**
   - Optimized for Indian annual reports with "Standalone" statements
   - May require prompt tuning for international formats

2. **Single PDF at a time**
   - No multi-document comparison or portfolio analysis

3. **Memory constraints**
   - Full parsed statements held in session state (~2-3 MB per document)
   - Could be optimized with database storage

4. **Chart types**
   - Limited to 5 types (bar, line, pie, waterfall, horizontal_bar)
   - No heatmaps, scatter plots, or advanced visualizations

---

### Potential Enhancements

**🔮 Multi-document analysis:**
- Compare multiple years of reports
- Portfolio-level KPI aggregation
- Peer company benchmarking

**📊 Advanced visualizations:**
- Trend analysis over 5+ years
- Ratio breakdown heatmaps
- Interactive drill-down charts

**🧠 Enhanced intelligence:**
- Predictive analytics (forecast next year)
- Anomaly detection in line items
- Industry-standard ratio benchmarking

**💾 Persistence layer:**
- PostgreSQL storage for parsed statements
- Query history tracking
- Export to Excel/CSV

**🌐 API interface:**
- RESTful API for programmatic access
- Batch processing endpoint
- Webhook integrations

**🔒 Security & compliance:**
- User authentication
- Role-based access control
- Audit logging

---

## 🧪 Testing

### Sample Test Cases

**1. Revenue Growth Query:**
```
Query: "What was the revenue growth from last year?"
Expected: Cites exact revenue figures from P&L, calculates YoY %
```

**2. Multi-statement Query:**
```
Query: "Calculate the debt-to-equity ratio"
Expected: Uses balance sheet data, shows calculation steps
```

**3. Visualization Request:**
```
Query: "Show me a comparison of current vs prior year expenses"
Expected: Generates bar chart + text explanation
```

**4. Validation Trigger:**
```
Scenario: Answer with incorrect number
Expected: Validator fails → retry with critique → corrected answer
```

---

### Manual Testing Checklist

- [ ] Upload a valid PDF → Analysis completes without errors
- [ ] Dashboard tab shows 8 KPIs with proper formatting
- [ ] Statements tab displays all 3 sections with data
- [ ] Summaries tab shows natural language summaries
- [ ] Chat responds to revenue questions using P&L
- [ ] Chat responds to asset questions using balance sheet
- [ ] Chart generated for "show me" queries
- [ ] Validation retry visible in metadata (try intentionally vague query)
- [ ] Clear chat resets conversation
- [ ] Re-upload new PDF resets all state

---

## 📖 Dependencies Reference

```txt
openai>=1.0.0          # GPT-4o API access
streamlit>=1.44.0      # Web UI framework
PyMuPDF>=1.25.0        # PDF text extraction (import as 'fitz')
plotly>=5.24.0         # Interactive chart library
pandas>=2.0.0          # DataFrame manipulation
python-dotenv>=1.0.0   # .env file loading
langgraph>=0.2.0       # State machine orchestration
pydantic>=2.7.4        # Type validation
```

**Version Notes:**
- LangGraph 0.2+ required for `Send()` API
- Streamlit 1.44+ required for `st.chat_message()` and tabs
- OpenAI SDK 1.0+ uses new client API

---

## 🤝 Contributing

Contributions are welcome! Areas of interest:

1. **Document format adapters** — Support for non-Indian formats, SEC filings, etc.
2. **Additional chart types** — Implement scatter, heatmap, gauge, etc.
3. **Performance optimization** — Reduce token usage, faster parsing
4. **Test suite** — Unit tests for node functions, integration tests for graphs
5. **Documentation** — Tutorial videos, example queries, troubleshooting guide

**Development Setup:**
```bash
git checkout -b feature/your-feature-name
# Make changes
# Test thoroughly
git commit -m "feat: add X feature"
# Submit pull request
```

---

## 📝 License

This project is provided as-is for educational and research purposes. 

**Note:** Usage of OpenAI's API is subject to [OpenAI's Terms of Service](https://openai.com/policies/terms-of-use) and usage pricing.

---

## 🙏 Acknowledgments

- **LangGraph team** — For the amazing state machine framework
- **OpenAI** — For GPT-4o's powerful extraction and analysis capabilities
- **Streamlit** — For making beautiful UIs simple
- **PyMuPDF** — For fast and reliable PDF processing

---

## 📞 Support & Contact

**Issues:** Open a GitHub issue for bug reports or feature requests

**Questions:** Use GitHub Discussions for general questions and ideas

**Documentation:** See inline code comments for implementation details

---

## 🎯 Quick Start Summary

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
echo "OPENAI_API_KEY=sk-your-key-here" > .env

# 3. Run the app
streamlit run ui.py

# 4. Upload a PDF and start analyzing!
```

---

**Built with ❤️ using LangGraph, GPT-4o, and Streamlit**

---

## 📊 Example Output

### Dashboard View
```
Total Revenue        Net Profit          Total Assets        EBITDA
808,030             72,533              1,234,567           123,456
↑ +17.3%            ↑ +12.8%            ↑ +8.5%             ↑ +15.2%
```

### Chat Example
```
User: "What was the revenue growth from last year?"