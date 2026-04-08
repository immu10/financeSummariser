"""
main.py — Shared helpers used by both nodes.py and ui.py.

Kept here:
  - OpenAI client initialisation
  - extract_text_by_page()   PDF → list of page strings
  - build_plotly_figure()    chart_spec dict → Plotly Figure

Everything else (extraction, KPI, chat, prompts, schemas) lives in nodes.py.
"""
import fitz
import os
from dotenv import load_dotenv
from openai import OpenAI
import plotly.graph_objects as go

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

def extract_text_by_page(file_obj) -> list[str]:
    """Extract text per page from a PDF file object using PyMuPDF."""
    doc = fitz.open(stream=file_obj.read(), filetype="pdf")
    return [page.get_text() for page in doc]


# ---------------------------------------------------------------------------
# Chart rendering
# ---------------------------------------------------------------------------

def build_plotly_figure(chart_spec: dict):
    """Convert an AI chart_spec dict into an interactive Plotly figure."""
    COLORS = ["#00CC88", "#0088FF", "#FF6B6B", "#FFD93D", "#C77DFF", "#FF9A3C", "#00D4FF"]

    LAYOUT_BASE = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(20,20,35,0.9)",
        font=dict(color="#E0E0E0", family="Inter, system-ui, sans-serif", size=13),
        title=dict(
            text=chart_spec.get("title", ""),
            font=dict(size=18, color="#FFFFFF"),
            x=0.5,
            xanchor="center",
        ),
        xaxis=dict(
            title=chart_spec.get("x_label", ""),
            gridcolor="rgba(255,255,255,0.08)",
            showline=True,
            linecolor="rgba(255,255,255,0.2)",
        ),
        yaxis=dict(
            title=chart_spec.get("y_label", ""),
            gridcolor="rgba(255,255,255,0.08)",
            showline=True,
            linecolor="rgba(255,255,255,0.2)",
        ),
        showlegend=chart_spec.get("show_legend", True),
        legend=dict(
            bgcolor="rgba(0,0,0,0.3)",
            bordercolor="rgba(255,255,255,0.1)",
            borderwidth=1,
        ),
        margin=dict(l=60, r=30, t=70, b=60),
        hoverlabel=dict(
            bgcolor="rgba(0,0,0,0.8)",
            bordercolor="#00CC88",
            font_color="white",
        ),
    )

    chart_type = chart_spec.get("chart_type", "bar")
    series = chart_spec.get("data_series", [])
    fig = go.Figure()

    if chart_type == "bar":
        for i, s in enumerate(series):
            fig.add_trace(
                go.Bar(
                    x=s["x"],
                    y=s["y"],
                    name=s["name"],
                    marker=dict(
                        color=s.get("color", COLORS[i % len(COLORS)]),
                        line=dict(color="rgba(255,255,255,0.1)", width=1),
                    ),
                    hovertemplate="<b>%{x}</b><br>%{y:,.0f}<extra>%{fullData.name}</extra>",
                )
            )
        fig.update_layout(barmode="group", **LAYOUT_BASE)

    elif chart_type == "horizontal_bar":
        for i, s in enumerate(series):
            fig.add_trace(
                go.Bar(
                    x=s["y"],
                    y=s["x"],
                    orientation="h",
                    name=s["name"],
                    marker=dict(color=s.get("color", COLORS[i % len(COLORS)])),
                    hovertemplate="<b>%{y}</b><br>%{x:,.0f}<extra>%{fullData.name}</extra>",
                )
            )
        fig.update_layout(barmode="group", **LAYOUT_BASE)

    elif chart_type == "line":
        for i, s in enumerate(series):
            fig.add_trace(
                go.Scatter(
                    x=s["x"],
                    y=s["y"],
                    name=s["name"],
                    mode="lines+markers",
                    line=dict(width=3, color=s.get("color", COLORS[i % len(COLORS)])),
                    marker=dict(size=9, symbol="circle"),
                    hovertemplate="<b>%{x}</b><br>%{y:,.0f}<extra>%{fullData.name}</extra>",
                )
            )
        fig.update_layout(**LAYOUT_BASE)

    elif chart_type == "pie":
        s = series[0]
        fig.add_trace(
            go.Pie(
                labels=s["x"],
                values=s["y"],
                name=s["name"],
                hole=0.42,
                marker=dict(colors=COLORS, line=dict(color="#0A0A0F", width=2)),
                textinfo="label+percent",
                textfont=dict(size=12),
                hovertemplate="<b>%{label}</b><br>%{value:,.0f}<br>%{percent}<extra></extra>",
            )
        )
        layout = {k: v for k, v in LAYOUT_BASE.items() if k not in ("xaxis", "yaxis")}
        fig.update_layout(**layout)

    elif chart_type == "waterfall":
        s = series[0]
        measures = ["relative"] * len(s["x"])
        if measures:
            measures[-1] = "total"
        fig.add_trace(
            go.Waterfall(
                x=s["x"],
                y=s["y"],
                measure=measures,
                name=s["name"],
                connector=dict(line=dict(color="rgba(200,200,200,0.3)", width=1)),
                increasing=dict(marker=dict(color="#00CC88")),
                decreasing=dict(marker=dict(color="#FF6B6B")),
                totals=dict(marker=dict(color="#0088FF")),
                hovertemplate="<b>%{x}</b><br>%{y:,.0f}<extra></extra>",
            )
        )
        fig.update_layout(**LAYOUT_BASE)

    # Annotations
    annotations = []
    for ann in chart_spec.get("annotations", []):
        annotations.append(
            dict(
                x=ann["x"],
                y=ann["y"],
                text=ann["text"],
                showarrow=True,
                arrowhead=2,
                arrowcolor="#00CC88",
                bgcolor="rgba(0,0,0,0.7)",
                bordercolor="#00CC88",
                borderwidth=1,
                font=dict(color="white", size=11),
                ax=0,
                ay=-35,
            )
        )
    if annotations:
        fig.update_layout(annotations=annotations)

    return fig
