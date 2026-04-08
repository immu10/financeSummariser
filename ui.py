import streamlit as st
import pandas as pd
from main import extract_text_by_page, build_plotly_figure
from graph import ingestion_graph, query_graph
from state import FinancialGraphState

st.set_page_config(
    page_title="FinSight AI",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Dark glassmorphism CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
  [data-testid="stAppViewContainer"] {
      background: linear-gradient(135deg, #0A0A0F 0%, #0D1117 60%, #0A0F1E 100%);
      min-height: 100vh;
  }
  [data-testid="stSidebar"] {
      background: rgba(13,17,23,0.95) !important;
      border-right: 1px solid rgba(0,204,136,0.15);
  }
  [data-testid="metric-container"] {
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      border: 1px solid rgba(0,204,136,0.25);
      border-radius: 14px;
      padding: 1.1rem 1.2rem;
      box-shadow: 0 4px 24px rgba(0,204,136,0.08), 0 1px 4px rgba(0,0,0,0.4);
      transition: box-shadow 0.2s;
  }
  [data-testid="metric-container"]:hover {
      box-shadow: 0 6px 32px rgba(0,204,136,0.18);
  }
  [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 1.5rem !important; }
  [data-testid="stMetricLabel"] { color: #9CA3AF !important; font-size: 0.8rem !important; letter-spacing: 0.05em; text-transform: uppercase; }
  [data-testid="stTabs"] button {
      color: #9CA3AF;
      font-weight: 500;
      font-size: 0.95rem;
      padding: 0.6rem 1.4rem;
      border-radius: 8px 8px 0 0;
      transition: color 0.2s;
  }
  [data-testid="stTabs"] button[aria-selected="true"] {
      color: #00CC88 !important;
      border-bottom: 2px solid #00CC88 !important;
  }
  [data-testid="stChatMessage"] {
      border-radius: 14px;
      margin: 0.4rem 0;
      border: 1px solid rgba(255,255,255,0.06);
  }
  [data-testid="stSidebar"] .stButton > button {
      background: linear-gradient(90deg, #00CC88, #0088FF);
      color: white;
      border: none;
      border-radius: 10px;
      padding: 0.6rem 1.5rem;
      font-weight: 700;
      font-size: 0.95rem;
      width: 100%;
      box-shadow: 0 4px 14px rgba(0,204,136,0.3);
      transition: opacity 0.2s;
  }
  [data-testid="stSidebar"] .stButton > button:hover { opacity: 0.88; }
  [data-testid="stExpander"] {
      border: 1px solid rgba(0,204,136,0.15);
      border-radius: 10px;
      margin-bottom: 0.5rem;
  }
  .stDataFrame { border-radius: 8px; overflow: hidden; }
  hr { border-color: rgba(255,255,255,0.06) !important; }
  body, p, span, div { color: #E0E0E0; }
  h1, h2, h3 { color: #FFFFFF; }

  /* Graph status badge */
  .graph-badge {
      display: inline-block;
      background: rgba(0,204,136,0.12);
      border: 1px solid rgba(0,204,136,0.3);
      border-radius: 6px;
      padding: 0.25rem 0.65rem;
      font-size: 0.75rem;
      color: #00CC88;
      margin-bottom: 0.5rem;
  }
  .retry-badge {
      display: inline-block;
      background: rgba(255,107,107,0.12);
      border: 1px solid rgba(255,107,107,0.3);
      border-radius: 6px;
      padding: 0.2rem 0.6rem;
      font-size: 0.72rem;
      color: #FF6B6B;
      margin-left: 0.5rem;
  }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
defaults = {
    "graph_state": None,      # Full FinancialGraphState after ingestion
    "ingestion_done": False,
    "company_name": "",
    "currency_unit": "",
    "kpis": [],
    "chat_history": [],       # Mirrors graph_state["chat_history"] for rendering
    "pages_count": 0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------------------------------------------------------------------
# Sidebar — upload + analyze
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## FinSight AI")
    st.markdown(
        "<p style='color:#9CA3AF;font-size:0.82rem;margin-top:-0.5rem'>"
        "LangGraph-powered financial intelligence"
        "</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<span class='graph-badge'>LangGraph · GPT-4o </span>",
        unsafe_allow_html=True,
    )
    st.divider()

    uploaded_file = st.file_uploader("Upload Annual Report PDF", type=["pdf"])

    if uploaded_file:
        if st.button("Analyze Report"):
            st.session_state.chat_history = []
            st.session_state.ingestion_done = False
            st.session_state.graph_state = None

            with st.spinner("Reading PDF pages..."):
                pages = extract_text_by_page(uploaded_file)
                st.session_state.pages_count = len(pages)

            # Build the initial graph state
            initial_state: FinancialGraphState = {
                "raw_pages": pages,
                "company_name": "",
                "currency_unit": "",
                "statement_chunks": [],
                "summaries": [],
                "parsed_statements": [],
                "kpis": [],
                "chat_history": [],
                "current_query": "",
                "selected_statements": [],
                "answer_text": "",
                "chart_spec": None,
                "validation": None,
                "retry_count": 0,
            }

            with st.spinner("Splitting document into statement sections..."):
                # The ingestion graph runs:
                #   split → [parallel: summarise×3 + parse×3] → build_kpis
                final_state = ingestion_graph.invoke(initial_state)

            st.session_state.graph_state = final_state
            st.session_state.company_name = final_state.get("company_name", "Company")
            st.session_state.currency_unit = final_state.get("currency_unit", "")
            st.session_state.kpis = final_state.get("kpis", [])
            st.session_state.ingestion_done = True
            st.success(
                f"{st.session_state.pages_count} pages · "
                f"{len(final_state.get('statement_chunks', []))} statements · "
                f"{len(final_state.get('summaries', []))} summaries"
            )

    if st.session_state.ingestion_done:
        st.divider()
        st.markdown(f"**{st.session_state.company_name}**")
        st.markdown(
            f"<p style='color:#9CA3AF;font-size:0.8rem'>{st.session_state.currency_unit}</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='color:#9CA3AF;font-size:0.8rem'>"
            f"{st.session_state.pages_count} pages | 3 statements extracted"
            f"</p>",
            unsafe_allow_html=True,
        )

        if st.session_state.chat_history:
            if st.button("Clear Chat"):
                # Reset chat in both session state and graph state
                st.session_state.chat_history = []
                if st.session_state.graph_state:
                    st.session_state.graph_state = {
                        **st.session_state.graph_state,
                        "chat_history": [],
                    }
                st.rerun()

    if not uploaded_file:
        st.markdown("""
        <div style='color:#6B7280;font-size:0.82rem;margin-top:1rem'>
        Upload an annual report PDF to extract:<br>
        • Standalone Balance Sheet<br>
        • Statement of Profit &amp; Loss<br>
        • Statement of Cash Flows<br><br>
        <b style='color:#9CA3AF'>How it works:</b><br>
        1. Document split into 3 sections<br>
        2. Each summarised independently<br>
        3. Queries routed to relevant section<br>
        4. Answers self-validated + retried
        </div>
        """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Main content — only shown after analysis
# ---------------------------------------------------------------------------
if not st.session_state.ingestion_done:
    st.markdown("""
    <div style='text-align:center;padding:5rem 2rem'>
      <h1 style='font-size:2.8rem;background:linear-gradient(90deg,#00CC88,#0088FF);
                 -webkit-background-clip:text;-webkit-text-fill-color:transparent'>
        FinSight AI
      </h1>
      <p style='color:#6B7280;font-size:1.1rem;margin-top:0.5rem'>
        Upload an annual report PDF in the sidebar to begin.
      </p>
      <p style='color:#4B5563;font-size:0.85rem;margin-top:1rem'>
        Powered by LangGraph · Parallel document processing · Self-validating answers
      </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Header
st.markdown(
    f"<h2 style='margin-bottom:0'>{st.session_state.company_name}</h2>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<p style='color:#9CA3AF;margin-top:0'>{st.session_state.currency_unit}</p>",
    unsafe_allow_html=True,
)

tab1, tab2, tab3, tab4 = st.tabs(
    ["  Dashboard  ", "  Financial Statements  ", "  Summaries  ", "  AI Chatbot  "]
)

# ---------------------------------------------------------------------------
# Tab 1 — Dashboard
# ---------------------------------------------------------------------------
with tab1:
    kpis = st.session_state.kpis

    if kpis:
        cols = st.columns(4, gap="medium")
        for col, kpi in zip(cols, kpis[:4]):
            with col:
                st.metric(
                    label=kpi["name"],
                    value=kpi["value"],
                    delta=kpi["delta"],
                    delta_color=kpi.get("delta_color", "normal"),
                    border=True,
                )

        st.markdown("<div style='margin-top:0.8rem'></div>", unsafe_allow_html=True)

        cols2 = st.columns(4, gap="medium")
        for col, kpi in zip(cols2, kpis[4:8]):
            with col:
                st.metric(
                    label=kpi["name"],
                    value=kpi["value"],
                    delta=kpi["delta"],
                    delta_color=kpi.get("delta_color", "normal"),
                    border=True,
                )

    st.divider()

    # Auto-generate 2 dashboard charts from parsed statement data
    graph_state = st.session_state.graph_state
    parsed = graph_state.get("parsed_statements", []) if graph_state else []
    parsed_by_type = {p["statement_type"]: p["data"] for p in parsed}

    col_c1, col_c2 = st.columns(2, gap="large")

    with col_c1:
        try:
            pl = parsed_by_type.get("profit_and_loss", {})
            period_cur = pl.get("period_current", "Current")
            period_pri = pl.get("period_prior", "Prior")
            highlights = [
                item
                for section in pl.get("sections", [])
                for item in section.get("line_items", [])
                if item.get("is_subtotal") and item["current_value"] != 0
            ]
            if highlights:
                labels = [h["label"] for h in highlights[:6]]
                chart_spec = {
                    "chart_type": "bar",
                    "title": "P&L Key Figures",
                    "x_label": "",
                    "y_label": st.session_state.currency_unit,
                    "show_legend": True,
                    "annotations": [],
                    "data_series": [
                        {"name": period_cur, "x": labels, "y": [h["current_value"] for h in highlights[:6]], "color": "#00CC88"},
                        {"name": period_pri, "x": labels, "y": [h["prior_value"] for h in highlights[:6]], "color": "#0088FF"},
                    ],
                }
                st.plotly_chart(build_plotly_figure(chart_spec), use_container_width=True)
        except Exception:
            st.info("P&L chart will appear after analysis.")

    with col_c2:
        try:
            cf = parsed_by_type.get("cash_flows", {})
            period_cur = cf.get("period_current", "Current")
            cf_labels, cf_values = [], []
            for section in cf.get("sections", []):
                subtotals = [i for i in section.get("line_items", []) if i.get("is_subtotal")]
                if subtotals:
                    cf_labels.append(section["section_name"])
                    cf_values.append(subtotals[-1]["current_value"])
            if cf_labels:
                chart_spec = {
                    "chart_type": "waterfall",
                    "title": f"Cash Flow Breakdown — {period_cur}",
                    "x_label": "",
                    "y_label": st.session_state.currency_unit,
                    "show_legend": False,
                    "annotations": [],
                    "data_series": [{"name": "Cash Flow", "x": cf_labels, "y": cf_values}],
                }
                st.plotly_chart(build_plotly_figure(chart_spec), use_container_width=True)
        except Exception:
            st.info("Cash flow chart will appear after analysis.")

# ---------------------------------------------------------------------------
# Tab 2 — Financial Statements
# ---------------------------------------------------------------------------
with tab2:
    parsed_by_type = {}
    if st.session_state.graph_state:
        for p in st.session_state.graph_state.get("parsed_statements", []):
            parsed_by_type[p["statement_type"]] = p["data"]

    statement_configs = [
        {
            "key": "balance_sheet",
            "label": "Standalone Balance Sheet",
            "date_fields": ("as_of_date_current", "as_of_date_prior"),
            "date_label": "As of",
        },
        {
            "key": "profit_and_loss",
            "label": "Standalone Statement of Profit and Loss",
            "date_fields": ("period_current", "period_prior"),
            "date_label": "Period",
        },
        {
            "key": "cash_flows",
            "label": "Standalone Statement of Cash Flows",
            "date_fields": ("period_current", "period_prior"),
            "date_label": "Period",
        },
    ]

    for cfg in statement_configs:
        stmt = parsed_by_type.get(cfg["key"], {})
        date_cur = stmt.get(cfg["date_fields"][0], "Current Year")
        date_pri = stmt.get(cfg["date_fields"][1], "Prior Year")

        with st.expander(f"**{cfg['label']}**", expanded=False):
            st.caption(f"{cfg['date_label']}: {date_cur} vs {date_pri}")

            rows = []
            for section in stmt.get("sections", []):
                rows.append({
                    "Item": f"\u2014\u2014  {section['section_name'].upper()}  \u2014\u2014",
                    "Current Year": "",
                    "Prior Year": "",
                })
                for item in section.get("line_items", []):
                    rows.append({
                        "Item": ("  " if not item.get("is_subtotal") else "") + item["label"],
                        "Current Year": f"{item['current_value']:,.0f}" if item["current_value"] != 0 else "-",
                        "Prior Year": f"{item['prior_value']:,.0f}" if item["prior_value"] != 0 else "-",
                    })

            if rows:
                df = pd.DataFrame(rows)[["Item", "Current Year", "Prior Year"]]
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    height=min(600, 36 * len(rows) + 40),
                )
            else:
                st.warning("No data extracted for this statement.")

# ---------------------------------------------------------------------------
# Tab 3 — Summaries (new: shows the LangGraph summaries + key figures)
# ---------------------------------------------------------------------------
with tab3:
    summaries = []
    if st.session_state.graph_state:
        summaries = st.session_state.graph_state.get("summaries", [])

    if not summaries:
        st.info("Summaries will appear after analysis.")
    else:
        _labels = {
            "balance_sheet": "Balance Sheet",
            "profit_and_loss": "Profit & Loss",
            "cash_flows": "Cash Flows",
        }
        for summary in summaries:
            stype = summary["statement_type"]
            with st.expander(f"**{_labels.get(stype, stype)}**", expanded=True):
                st.markdown(
                    f"<p style='color:#D1D5DB;line-height:1.7'>{summary['summary_text']}</p>",
                    unsafe_allow_html=True,
                )
                kf = summary.get("key_figures", {})
                if kf:
                    st.markdown("**Key figures**")
                    kf_cols = st.columns(min(len(kf), 3))
                    for idx, (label, value) in enumerate(kf.items()):
                        with kf_cols[idx % len(kf_cols)]:
                            st.metric(label=label, value=f"{value:,.0f}" if isinstance(value, (int, float)) else value)

# ---------------------------------------------------------------------------
# Tab 4 — AI Chatbot (was Tab 3)
# ---------------------------------------------------------------------------
with tab4:
    st.markdown(
        "<p style='color:#9CA3AF;font-size:0.9rem;margin-bottom:1rem'>"
        "Queries are routed to the relevant statement(s). "
        "Every answer is validated and retried if needed."
        "</p>",
        unsafe_allow_html=True,
    )

    # Render existing chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            if msg.get("chart_spec"):
                try:
                    st.plotly_chart(
                        build_plotly_figure(msg["chart_spec"]),
                        use_container_width=True,
                    )
                except Exception:
                    pass
            st.write(msg["content"])
            # Show which statements were used and if retried
            if msg["role"] == "assistant":
                meta_parts = []
                if msg.get("selected_statements"):
                    meta_parts.append("Used: " + ", ".join(msg["selected_statements"]))
                if msg.get("retry_count", 0) > 0:
                    meta_parts.append(f"Retried {msg['retry_count']}x")
                if meta_parts:
                    st.markdown(
                        f"<p style='color:#4B5563;font-size:0.72rem;margin-top:0.3rem'>"
                        f"{' · '.join(meta_parts)}</p>",
                        unsafe_allow_html=True,
                    )

    # Chat input
    if prompt := st.chat_input("Ask about revenue, profits, cash flow, trends, comparisons..."):
        with st.chat_message("user"):
            st.write(prompt)

        current_state = st.session_state.graph_state
        updated_history = (current_state.get("chat_history") or []) + [
            {"role": "user", "content": prompt, "chart_spec": None}
        ]

        query_input = {
            **current_state,
            "current_query": prompt,
            "chat_history": updated_history,
            "answer_text": "",
            "chart_spec": None,
            "validation": None,
            "retry_count": 0,
        }

        with st.chat_message("assistant"):
            with st.spinner("Routing query · generating answer · validating..."):
                result_state = query_graph.invoke(query_input)

            chart_spec = result_state.get("chart_spec")
            answer = result_state.get("answer_text", "")
            selected = result_state.get("selected_statements", [])
            retry_count = result_state.get("retry_count", 0)
            validation = result_state.get("validation")

            if chart_spec:
                try:
                    st.plotly_chart(
                        build_plotly_figure(chart_spec),
                        use_container_width=True,
                    )
                except Exception as e:
                    st.warning(f"Chart could not be rendered: {e}")
                    chart_spec = None

            st.write(answer)

            # Metadata line
            meta_parts = []
            if selected:
                meta_parts.append("Used: " + ", ".join(selected))
            if retry_count > 0:
                meta_parts.append(f"Retried {retry_count}x")
            if validation and validation.get("is_valid"):
                meta_parts.append("Validated")
            if meta_parts:
                st.markdown(
                    f"<p style='color:#4B5563;font-size:0.72rem;margin-top:0.3rem'>"
                    f"{' · '.join(meta_parts)}</p>",
                    unsafe_allow_html=True,
                )

        # Update graph state and chat history
        new_history = updated_history + [{
            "role": "assistant",
            "content": answer,
            "chart_spec": chart_spec,
            "selected_statements": selected,
            "retry_count": retry_count,
        }]

        st.session_state.graph_state = {**result_state, "chat_history": new_history}
        st.session_state.chat_history = new_history
        st.rerun()
