"""CSV Intelligence AI - Streamlit presentation layer.

Run:  streamlit run app.py

All interpretation, validation and calculation live in the `csvintel` package.
This file only handles state, rendering and exports.
"""

from __future__ import annotations

import hashlib
import html
import io
import json
import os
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from csvintel.charts import alt_chart_types, build_figure, style_figure
from csvintel.evaluation import run_benchmark
from csvintel.executor import AnalysisResult, execute_plan
from csvintel.insights import generate_insights
from csvintel.llm import llm_config, propose_plan, test_connection
from csvintel.loader import DatasetLoadError, parse_csv_bytes, read_csv_path
from csvintel.planner import build_plan, explain_plan, primary_date, primary_group, primary_metric, suggest_questions
from csvintel.schema import DatasetProfile, profile_dataset
from csvintel.text import format_value, humanize, is_currency_column
from csvintel.validator import PlanValidationError, validate_plan

# ---------------------------------------------------------------------------
# Page config + theme
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="CSV Intelligence AI",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --bg: #070a11;
  --panel: #0d121c;
  --panel-2: #111827;
  --border: #1e293b;
  --border-soft: #172033;
  --text: #e2e8f0;
  --muted: #8b98ad;
  --faint: #64748b;
  --violet: #8b7cff;
  --cyan: #22d3ee;
  --green: #34d399;
  --amber: #fbbf24;
  --red: #fb7185;
}

html, body, [class*="css"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
.stApp {
  background:
    radial-gradient(1100px 500px at 18% -12%, rgba(124, 92, 255, 0.13), transparent 60%),
    radial-gradient(900px 500px at 92% 0%, rgba(34, 211, 238, 0.07), transparent 55%),
    var(--bg);
  color: var(--text);
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { right: 1rem; }
.block-container { padding-top: 1.6rem; padding-bottom: 4rem; max-width: 1500px; }

section[data-testid="stSidebar"] {
  background: #090d15 !important;
  border-right: 1px solid var(--border-soft);
}
section[data-testid="stSidebar"] .block-container { padding-top: 1.1rem; }

h1, h2, h3, h4 { color: #f1f5f9 !important; letter-spacing: -0.02em; }
p, li, label, span { color: var(--text); }
[data-testid="stCaptionContainer"] p { color: var(--faint) !important; }
a { color: var(--violet); }

/* Sidebar radio as navigation */
section[data-testid="stSidebar"] div[role="radiogroup"] { gap: 2px; }
section[data-testid="stSidebar"] div[role="radiogroup"] label {
  padding: 8px 11px;
  border-radius: 8px;
  transition: background 0.14s ease;
  color: #aab6c8;
  font-size: 0.88rem;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover { background: #111827; }
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
  background: linear-gradient(90deg, rgba(139,124,255,0.17), rgba(139,124,255,0.05));
  color: #ffffff;
  box-shadow: inset 2px 0 0 var(--violet);
}
section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child { display: none; }

/* Inputs */
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
textarea,
.stTextInput input {
  background: #0d131f !important;
  border-color: #243146 !important;
  color: #e2e8f0 !important;
  border-radius: 9px !important;
}
div[data-baseweb="select"] svg { fill: #8b98ad; }
.stTextInput input::placeholder { color: #5b687d !important; }
.stTextInput input:focus { border-color: var(--violet) !important; box-shadow: 0 0 0 1px var(--violet) !important; }
.stFileUploader section {
  background: #0c111b !important;
  border: 1px dashed #2a3a55 !important;
  border-radius: 10px !important;
  color: #aab6c8 !important;
}
.stFileUploader small { color: #64748b !important; }

/* Buttons */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
  border-radius: 9px;
  font-weight: 600;
  font-size: 0.84rem;
  border: 1px solid #26344b;
  background: #0f1724;
  color: #dbe4f0;
  transition: all 0.14s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
  border-color: var(--violet);
  color: #ffffff;
  background: #151d30;
}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
  background: linear-gradient(135deg, #6d5ef5, #8b7cff);
  border-color: #8b7cff;
  color: #ffffff;
  box-shadow: 0 6px 18px rgba(109, 94, 245, 0.25);
}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {
  filter: brightness(1.08);
  border-color: #a99dff;
}

/* Tabs / expanders / code / dataframes */
.stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid var(--border-soft); }
.stTabs [data-baseweb="tab"] { color: #93a1b5; font-size: 0.86rem; padding: 8px 12px; }
.stTabs [aria-selected="true"] { color: #ffffff !important; }
div[data-testid="stExpander"] {
  background: #0b1019;
  border: 1px solid var(--border-soft);
  border-radius: 10px;
  overflow: hidden;
}
div[data-testid="stExpander"] summary { color: #cbd5e1; font-size: 0.86rem; }
div[data-testid="stExpander"] summary:hover { color: #ffffff; }
.stCode, pre { background: #080c14 !important; border: 1px solid #1d293b !important; border-radius: 8px; }
code { font-family: 'JetBrains Mono', monospace !important; font-size: 0.8rem !important; }
div[data-testid="stDataFrame"] { border: 1px solid var(--border-soft); border-radius: 9px; overflow: hidden; }
div[data-testid="stAlert"] { border-radius: 10px; border: 1px solid #2a3a55; background: #0d1420; }
.stSpinner > div { border-top-color: var(--violet) !important; }

/* Custom components */
.hero {
  position: relative;
  background: linear-gradient(140deg, rgba(20, 27, 43, 0.95), rgba(10, 14, 22, 0.92));
  border: 1px solid #223049;
  border-radius: 16px;
  padding: 26px 30px;
  margin-bottom: 20px;
  overflow: hidden;
}
.hero::after {
  content: "";
  position: absolute; inset: 0;
  background: radial-gradient(600px 220px at 92% -20%, rgba(139,124,255,0.17), transparent 65%);
  pointer-events: none;
}
.eyebrow {
  color: var(--violet);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.13em;
  text-transform: uppercase;
  margin-bottom: 8px;
}
.hero-title { font-size: 1.7rem; font-weight: 750; color: #f8fafc; letter-spacing: -0.03em; line-height: 1.2; }
.hero-sub { color: #93a1b5; font-size: 0.92rem; margin-top: 8px; max-width: 980px; line-height: 1.55; }
.hero-meta { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
.chip {
  display: inline-flex; align-items: center; gap: 6px;
  background: #111827; border: 1px solid #26344b; color: #b9c5d6;
  padding: 4px 9px; border-radius: 999px; font-size: 0.72rem; font-weight: 600;
}
.chip.violet { background: rgba(139,124,255,0.10); border-color: rgba(139,124,255,0.32); color: #c6beff; }
.chip.green { background: rgba(52,211,153,0.08); border-color: rgba(52,211,153,0.28); color: #8ee8c5; }
.chip.amber { background: rgba(251,191,36,0.08); border-color: rgba(251,191,36,0.28); color: #f5cf7a; }
.chip.red { background: rgba(251,113,133,0.08); border-color: rgba(251,113,133,0.28); color: #f6a0ad; }

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin: 6px 0 20px 0;
}
.kpi-card {
  background: linear-gradient(160deg, #0f1521, #0b1019);
  border: 1px solid #1d293b;
  border-radius: 12px;
  padding: 15px 17px;
  min-height: 92px;
}
.kpi-label { color: #7f8da3; font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; }
.kpi-value { color: #f8fafc; font-size: 1.35rem; font-weight: 700; margin-top: 6px; font-family: 'JetBrains Mono', monospace; letter-spacing: -0.02em; }
.kpi-sub { color: #66758c; font-size: 0.72rem; margin-top: 4px; }

.answer-card {
  background: linear-gradient(160deg, rgba(17, 24, 39, 0.96), rgba(10, 15, 23, 0.94));
  border: 1px solid #24314a;
  border-left: 3px solid var(--violet);
  border-radius: 13px;
  padding: 20px 22px;
  margin: 8px 0 16px 0;
}
.answer-card.error { border-left-color: var(--red); }
.answer-card.clarify { border-left-color: var(--amber); }
.answer-badge { font-size: 0.68rem; font-weight: 700; letter-spacing: 0.09em; text-transform: uppercase; color: #a99dff; margin-bottom: 8px; }
.answer-card.clarify .answer-badge { color: #f5cf7a; }
.answer-card.error .answer-badge { color: #f6a0ad; }
.answer-title { font-size: 1.22rem; font-weight: 700; color: #f8fafc; line-height: 1.35; letter-spacing: -0.015em; }
.answer-detail { color: #9aa7ba; font-size: 0.87rem; line-height: 1.6; margin-top: 8px; }

.metric-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-bottom: 16px;
}
.metric-pill {
  background: #0d131e; border: 1px solid #1c283b; border-radius: 10px; padding: 11px 13px;
}
.metric-pill .k { color: #728097; font-size: 0.66rem; text-transform: uppercase; letter-spacing: 0.07em; font-weight: 700; }
.metric-pill .v { color: #e8edf5; font-size: 1.02rem; font-weight: 650; margin-top: 4px; font-family: 'JetBrains Mono', monospace; }

.insight-card {
  background: #0d131e; border: 1px solid #1c283b; border-radius: 12px; padding: 17px 18px; height: 100%;
}
.insight-kind { font-size: 0.64rem; text-transform: uppercase; letter-spacing: 0.09em; color: var(--cyan); font-weight: 700; }
.insight-title { font-size: 0.98rem; font-weight: 650; color: #f1f5f9; margin-top: 5px; }
.insight-detail { font-size: 0.82rem; color: #95a3b7; line-height: 1.55; margin-top: 6px; }
.insight-evidence { font-size: 0.68rem; color: #5f6e84; margin-top: 9px; font-family: 'JetBrains Mono', monospace; }

.pipeline { display: flex; flex-direction: column; gap: 8px; margin: 10px 0 6px 0; }
.pipe-row { display: flex; align-items: stretch; gap: 10px; }
.pipe-num {
  width: 34px; min-width: 34px; display: flex; align-items: center; justify-content: center;
  background: #111a29; border: 1px solid #26344b; border-radius: 9px;
  color: #a99dff; font-family: 'JetBrains Mono', monospace; font-size: 0.76rem; font-weight: 700;
}
.pipe-body { flex: 1; background: #0d131e; border: 1px solid #1c283b; border-radius: 9px; padding: 10px 14px; }
.pipe-title { color: #e8edf5; font-size: 0.86rem; font-weight: 650; }
.pipe-desc { color: #8492a7; font-size: 0.77rem; margin-top: 2px; line-height: 1.5; }
.pipe-arrow { color: #334155; text-align: center; font-size: 0.8rem; line-height: 0.6; }

.section-label { color: #718096; font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.11em; margin: 6px 0 10px 0; }
.divider { height: 1px; background: #172033; margin: 20px 0; }
.small-muted { color: #6a788e; font-size: 0.75rem; line-height: 1.55; }
.history-item { background: #0c121c; border: 1px solid #1c283b; border-radius: 10px; padding: 12px 15px; margin-bottom: 8px; }
.history-q { color: #e8edf5; font-size: 0.88rem; font-weight: 600; }
.history-meta { color: #66758c; font-size: 0.7rem; font-family: 'JetBrains Mono', monospace; margin-top: 4px; }
.demo .hero-title { font-size: 2.15rem; }
.demo .answer-title { font-size: 1.5rem; }
.demo .answer-detail { font-size: 0.98rem; }
.demo .kpi-value { font-size: 1.55rem; }
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Dataset catalog
# ---------------------------------------------------------------------------
DATASET_OPTIONS: dict[str, dict[str, Any]] = {
    "retail_demo": {
        "name": "OmniTech Retail Sales 2024 (Synthetic Demo)",
        "file": "sample_retail_sales_2024.csv",
        "description": "800 deterministic retail orders with revenue, cost, profit, discount, category, region and segment.",
        "sample_questions": [
            "Give me an overview of this dataset.",
            "What is the total revenue?",
            "Which category has the highest total profit?",
            "Compare revenue across regions.",
            "Show monthly revenue trends.",
            "Are there any unusual values in revenue?",
        ],
    },
    "ecommerce": {
        "name": "01 · E-Commerce Orders (1,500 rows)",
        "file": "datasets/01_ecommerce_orders.csv",
        "description": "Global e-commerce transactions with discount, revenue, cost and profit.",
        "sample_questions": [
            "What is the total revenue?",
            "Which category generates the most revenue?",
            "Which region has the highest total profit?",
            "Show monthly revenue trends.",
            "What is the average discount percent?",
            "Compare revenue across customer segments.",
        ],
    },
    "saas": {
        "name": "02 · SaaS Subscriptions (1,200 rows)",
        "file": "datasets/02_saas_subscriptions.csv",
        "description": "B2B subscription metrics: MRR, ACV, seats, usage scores and churn risk.",
        "sample_questions": [
            "What is the total monthly recurring revenue?",
            "Which plan tier generates the highest revenue?",
            "What is the average usage score?",
            "Compare monthly recurring revenue across plan tiers.",
            "Show monthly signup trends.",
            "Are there any outliers in monthly recurring revenue?",
        ],
    },
    "healthcare": {
        "name": "03 · Healthcare Admissions (1,000 rows)",
        "file": "datasets/03_healthcare_admissions.csv",
        "description": "Hospital admissions, departments, length of stay and billing.",
        "sample_questions": [
            "What is the total bill amount?",
            "Which department has the highest total bill amount?",
            "What is the average length of stay days?",
            "Compare total bill amount across departments.",
            "Show monthly admission trends.",
            "Are there any unusual values in bill amount?",
        ],
    },
    "finance": {
        "name": "04 · Finance Transactions (2,000 rows)",
        "file": "datasets/04_finance_banking_transactions.csv",
        "description": "Banking transactions, merchant categories, risk scores and channels.",
        "sample_questions": [
            "What is the total transaction amount?",
            "Which merchant category has the highest transaction amount?",
            "What is the average transaction amount?",
            "Compare transaction amount across channels.",
            "Are there any outliers in transaction amount?",
            "How many transactions are there?",
        ],
    },
    "hr": {
        "name": "05 · HR Workforce Salaries (1,000 rows)",
        "file": "datasets/05_hr_workforce_salaries.csv",
        "description": "Payroll, departments, ratings, tenure and attrition.",
        "sample_questions": [
            "What is the total annual salary?",
            "Which department has the highest total annual salary?",
            "What is the average annual salary?",
            "Compare annual salary across departments.",
            "What is the average tenure years?",
            "Are there any outliers in annual salary?",
        ],
    },
    "marketing": {
        "name": "06 · Marketing Campaigns (800 rows)",
        "file": "datasets/06_digital_marketing_campaigns.csv",
        "description": "Ad spend, impressions, clicks, conversions, revenue and ROAS by platform.",
        "sample_questions": [
            "What is the total revenue generated?",
            "Which platform generates the highest revenue?",
            "What is the total ad spend?",
            "Compare revenue generated across platforms.",
            "What is the average roas?",
            "Show monthly revenue trends.",
        ],
    },
    "logistics": {
        "name": "07 · Supply Chain Logistics (1,500 rows)",
        "file": "datasets/07_supply_chain_logistics.csv",
        "description": "Freight movements, modes, delays, weights and carriers.",
        "sample_questions": [
            "What is the total freight cost?",
            "Which transport mode has the highest total freight cost?",
            "What is the average delay days?",
            "Compare freight cost across transport modes.",
            "Which destination country has the most shipments?",
            "Are there any outliers in freight cost?",
        ],
    },
    "realestate": {
        "name": "08 · Real Estate Sales (1,000 rows)",
        "file": "datasets/08_real_estate_property_sales.csv",
        "description": "Property sales, cities, square footage and prices.",
        "sample_questions": [
            "What is the total sale price?",
            "Which city has the highest total sale price?",
            "What is the average sale price?",
            "Compare sale price across property types.",
            "What is the average square feet?",
            "Are there any outliers in sale price?",
        ],
    },
    "streaming": {
        "name": "09 · Streaming Viewership (1,500 rows)",
        "file": "datasets/09_streaming_media_viewership.csv",
        "description": "Sessions, genres, watch duration, devices and ratings.",
        "sample_questions": [
            "What is the total watch duration minutes?",
            "Which genre has the highest total watch duration?",
            "What is the average user rating?",
            "Compare watch duration across genres.",
            "Compare watch duration across device types.",
            "Show monthly watch duration trends.",
        ],
    },
    "crypto": {
        "name": "10 · Crypto Daily Market (1,200 rows)",
        "file": "datasets/10_cryptocurrency_market_daily.csv",
        "description": "Daily OHLC prices, volume and market cap by asset.",
        "sample_questions": [
            "What is the total volume millions?",
            "Which asset name has the highest total volume millions?",
            "What is the average close price?",
            "Compare volume millions across ticker symbols.",
            "Show monthly close price trends.",
            "Are there any outliers in volume millions?",
        ],
    },
}
NAV_PAGES = ["Overview", "AI Analyst", "Data Explorer", "Insights", "Evaluation", "How It Works", "History", "Demo Mode"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def label_for_key(key: str) -> str:
    if key == "custom" and st.session_state.get("custom_name"):
        return f"Custom · {st.session_state.custom_name}"
    return DATASET_OPTIONS.get(key, DATASET_OPTIONS["retail_demo"])["name"]


@st.cache_data(show_spinner=False)
def load_builtin(path: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    df, report = read_csv_path(path)
    return df, report.as_dict()


def dataset_signature(key: str, df: pd.DataFrame) -> str:
    raw = f"{key}|{len(df)}|{len(df.columns)}|{','.join(map(str, df.columns))}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


def kpi_grid(items: list[tuple[str, str, str]], accent: str = "") -> None:
    cards = []
    for label, value, sub in items:
        cards.append(
            f'<div class="kpi-card {accent}"><div class="kpi-label">{esc(label)}</div>'
            f'<div class="kpi-value">{esc(value)}</div><div class="kpi-sub">{esc(sub)}</div></div>'
        )
    st.markdown(f'<div class="kpi-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def metric_display(key: str, value: Any, result: AnalysisResult) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float, np.floating, np.integer)):
        metric = (result.plan or {}).get("metric")
        k = key.lower()
        if "pearson" in k or "r squared" in k:
            return f"{float(value):.4f}"
        if "%" in key:
            return f"{float(value):,.2f}%"
        count_keys = {
            "rows", "columns", "records", "groups", "periods", "pairs analysed", "unique values",
            "missing cells", "duplicate rows", "potential outliers", "columns with missing",
            "numeric columns", "categorical columns", "date", "numeric", "matching columns",
            "non-null", "missing", "top count", "count", "rows shown",
        }
        if k in count_keys:
            return f"{int(float(value)):,}"
        if metric and is_currency_column(metric) and k not in {"change %", "top share %", "outlier %"}:
            return format_value(float(value), metric)
        return f"{float(value):,.2f}"
    return str(value)


def metric_pills(metrics: dict[str, Any], result: AnalysisResult, max_items: int = 8) -> None:
    items = list(metrics.items())[:max_items]
    if not items:
        return
    html_parts = []
    for key, value in items:
        html_parts.append(
            f'<div class="metric-pill"><div class="k">{esc(key)}</div><div class="v">{esc(metric_display(key, value, result))}</div></div>'
        )
    st.markdown(f'<div class="metric-grid">{"".join(html_parts)}</div>', unsafe_allow_html=True)


def add_history(result: AnalysisResult, question: str, dataset_id: str, dataset_name: str) -> None:
    item = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "query": question,
        "dataset_id": dataset_id,
        "dataset_name": dataset_name,
        "result": result,
    }
    history = st.session_state.history
    if history and history[0]["query"] == question and history[0]["dataset_id"] == dataset_id:
        history[0] = item
    else:
        history.insert(0, item)
    st.session_state.history = history[:60]


def prepare_llm_plan(plan: dict[str, Any], question: str) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "version": 1,
        "question": question,
        "intent": "clarification",
        "metric": None,
        "metric_2": None,
        "group": None,
        "date_column": None,
        "aggregation": None,
        "sort": None,
        "limit": None,
        "frequency": None,
        "filters": [],
        "chart": "none",
        "confidence": 0.7,
        "interpretation": [],
        "candidates": {},
        "source": "llm",
        "notes": [],
    }
    merged = {**defaults, **{k: v for k, v in plan.items() if k not in {"choices"}}}
    merged["question"] = question
    merged["source"] = "llm"
    merged["filters"] = merged.get("filters") or []
    if merged.get("limit") is not None:
        try:
            merged["limit"] = int(merged["limit"])
        except Exception:
            merged["limit"] = None
    merged["steps"] = explain_plan(merged)
    return merged


def run_analysis(question: str, df: pd.DataFrame, profile: DatasetProfile, use_llm: bool) -> AnalysisResult:
    """Try the optional LLM plan, validate it, then execute deterministically."""
    warnings: list[str] = []
    plan: dict[str, Any] | None = None
    source = "rules"

    if use_llm:
        llm_plan, error = propose_plan(question, profile)
        if llm_plan:
            candidate = prepare_llm_plan(llm_plan, question)
            try:
                validate_plan(candidate, profile)
                plan = candidate
                source = "llm"
            except PlanValidationError as exc:
                warnings.append(f"LLM plan rejected by the validator ({exc}). The rule-based engine was used instead.")
        if error and plan is None:
            warnings.append(error)

    if plan is None:
        plan = build_plan(question, df, profile)
        source = "rules"
        try:
            validate_plan(plan, profile)
        except PlanValidationError as exc:
            return AnalysisResult(
                ok=False,
                intent="invalid",
                answer="This question produced a plan that failed validation.",
                detail=str(exc),
                plan=plan,
                error=str(exc),
                source="rules",
            )

    result = execute_plan(plan, df, profile, source=source)
    result.warnings = warnings + list(result.warnings)
    return result


def render_result(
    result: AnalysisResult,
    key_prefix: str,
    allow_chart_switch: bool = True,
    demo: bool = False,
) -> None:
    if result.warnings:
        for warning in result.warnings:
            st.warning(warning)

    if not result.ok:
        css_class = "error"
        badge = "Analysis error"
    elif result.intent == "clarification":
        css_class = "clarify"
        badge = "Needs a clearer question"
    elif result.source == "llm":
        css_class = ""
        badge = "LLM-assisted plan · deterministic calculation"
    elif result.intent == "meta":
        css_class = ""
        badge = "Assistant response"
    else:
        css_class = ""
        badge = "Verified deterministic calculation"

    st.markdown(
        f"""
        <div class="answer-card {css_class}">
          <div class="answer-badge">{esc(badge)}</div>
          <div class="answer-title">{esc(result.answer)}</div>
          <div class="answer-detail">{esc(result.detail)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if result.metrics:
        metric_pills(result.metrics, result, max_items=8)

    if result.chart and result.chart.get("type") not in (None, "none", "kpi", "table"):
        override = None
        options = alt_chart_types(result.chart)
        if allow_chart_switch and len(options) > 1:
            labels = {"bar": "Bar", "line": "Line", "pie": "Donut"}
            choice = st.radio(
                "Chart view",
                options,
                format_func=lambda x: labels.get(x, x.title()),
                horizontal=True,
                key=f"{key_prefix}_chart_{len(result.answer)}_{result.row_count}",
                label_visibility="collapsed",
            )
            override = choice
        figure = build_figure(result.chart, result.table, chart_override=override)
        if figure is not None:
            st.plotly_chart(
                figure,
                use_container_width=True,
                config={
                    "displayModeBar": "hover",
                    "toImageButtonOptions": {
                        "format": "png",
                        "filename": "csv_intelligence_chart",
                        "height": 550,
                        "width": 900,
                        "scale": 2,
                    },
                },
                key=f"{key_prefix}_plot_{result.intent}_{result.row_count}",
            )

    if result.table is not None and len(result.table) > 0:
        st.markdown('<div class="section-label">Supporting result set</div>', unsafe_allow_html=True)
        st.dataframe(result.table, use_container_width=True, hide_index=True, height=min(360, 42 + 35 * min(len(result.table), 9)))

    # Exports
    export_cols = st.columns([1, 1, 1, 1.2])
    with export_cols[0]:
        st.download_button(
            "Answer (.txt)",
            data=f"{result.answer}\n\n{result.detail}\n\nGenerated by CSV Intelligence AI\n".encode("utf-8"),
            file_name="csv_intelligence_answer.txt",
            mime="text/plain",
            key=f"{key_prefix}_txt",
            use_container_width=True,
        )
    if result.table is not None and len(result.table) > 0:
        with export_cols[1]:
            st.download_button(
                "Result (.csv)",
                data=result.table.to_csv(index=False).encode("utf-8"),
                file_name="csv_intelligence_result.csv",
                mime="text/csv",
                key=f"{key_prefix}_csv",
                use_container_width=True,
            )
    with export_cols[2]:
        payload = json.dumps(result.as_dict(), indent=2, default=str)
        st.download_button(
            "Result (.json)",
            data=payload.encode("utf-8"),
            file_name="csv_intelligence_result.json",
            mime="application/json",
            key=f"{key_prefix}_json",
            use_container_width=True,
        )
    with export_cols[3]:
        with st.expander("Copy answer"):
            st.code(result.answer + "\n\n" + result.detail, language=None)

    # Explainability
    with st.expander("How this analysis works", expanded=False):
        if result.explanation:
            st.markdown("**Execution steps**")
            for idx, step in enumerate(result.explanation, start=1):
                st.markdown(f"{idx}. {step}")
        plan = result.plan or {}
        left, right = st.columns(2)
        with left:
            st.markdown("**Detected plan**")
            st.json(
                {
                    "intent": plan.get("intent"),
                    "metric": plan.get("metric"),
                    "group": plan.get("group"),
                    "date_column": plan.get("date_column"),
                    "aggregation": plan.get("aggregation"),
                    "filters": plan.get("filters", []),
                    "sort": plan.get("sort"),
                    "limit": plan.get("limit"),
                    "chart": plan.get("chart"),
                }
            )
        with right:
            st.markdown("**Verification**")
            st.markdown(
                f"""
- Source: **{'LLM-assisted interpretation' if result.source == 'llm' else 'Rule-based interpreter'}**
- Execution: **deterministic pandas**, no generated code
- Rows analysed: **{result.records_used:,}**
- Plan validated against the active schema before execution
- Unsupported operations return a clarification instead of a guess
                """
            )
            st.markdown("**Formula / method**")
            st.code(result.formula or "No calculation", language=None)


def render_page_header(eyebrow: str, title: str, subtitle: str, chips: list[tuple[str, str]]) -> None:
    chip_html = "".join(f'<span class="chip {css}">{esc(text)}</span>' for text, css in chips)
    st.markdown(
        f"""
        <div class="hero">
          <div class="eyebrow">{esc(eyebrow)}</div>
          <div class="hero-title">{esc(title)}</div>
          <div class="hero-sub">{esc(subtitle)}</div>
          <div class="hero-meta">{chip_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def insight_cards(insights: list[dict[str, Any]], limit: int = 3) -> None:
    cols = st.columns(min(limit, max(len(insights), 1)))
    for idx, insight in enumerate(insights[:limit]):
        with cols[idx]:
            st.markdown(
                f"""
                <div class="insight-card">
                  <div class="insight-kind">{esc(insight.get('kind', 'insight'))}</div>
                  <div class="insight-title">{esc(insight.get('title', ''))}</div>
                  <div class="insight-detail">{esc(insight.get('detail', ''))}</div>
                  <div class="insight-evidence">{esc(' · '.join(insight.get('evidence', [])))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def make_chart(chart: dict[str, Any], table: pd.DataFrame, key: str, override: str | None = None) -> None:
    fig = build_figure(chart, table, chart_override=override)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=key)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "current_dataset_key" not in st.session_state:
    st.session_state.current_dataset_key = "retail_demo"
if "custom_df" not in st.session_state:
    st.session_state.custom_df = None
    st.session_state.custom_name = None
    st.session_state.custom_report = None
    st.session_state.upload_sig = None
if "history" not in st.session_state:
    st.session_state.history = []
if "active_query" not in st.session_state:
    st.session_state.active_query = "What is the total revenue?"
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "Overview"
if "target_nav" not in st.session_state:
    st.session_state.target_nav = None
if "last_result" not in st.session_state:
    st.session_state.last_result = None
    st.session_state.last_result_query = ""
    st.session_state.last_result_dataset = None
if "use_llm" not in st.session_state:
    st.session_state.use_llm = False
if "eval_report" not in st.session_state:
    st.session_state.eval_report = None
    st.session_state.eval_sig = None
if "demo_result" not in st.session_state:
    st.session_state.demo_result = None
    st.session_state.demo_query = "Give me an overview of this dataset."

# Programmatic dataset switches are applied before the selector widget exists.
pending = st.session_state.pop("pending_dataset", None)
if pending:
    if pending == "custom" and st.session_state.custom_df is None:
        pending = "retail_demo"
    st.session_state.current_dataset_key = pending
    st.session_state["dataset_selector"] = label_for_key(pending)
    st.session_state.last_result = None
    st.session_state.last_result_dataset = None

if "dataset_selector" not in st.session_state:
    st.session_state["dataset_selector"] = label_for_key(st.session_state.current_dataset_key)

if st.session_state.target_nav:
    st.session_state.nav_page = st.session_state.target_nav
    st.session_state.target_nav = None


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:18px;">
          <div style="width:34px;height:34px;border-radius:9px;background:linear-gradient(135deg,#7c5cff,#22d3ee);
                      display:flex;align-items:center;justify-content:center;color:#fff;font-weight:800;font-size:15px;
                      box-shadow:0 6px 18px rgba(124,92,255,.28);">◆</div>
          <div>
            <div style="font-weight:700;font-size:14px;color:#f8fafc;letter-spacing:-.02em;">CSV Intelligence AI</div>
            <div style="font-size:10px;color:#64748b;letter-spacing:.04em;">NATURAL LANGUAGE ANALYTICS</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    nav = st.radio("Navigation", NAV_PAGES, key="nav_page", label_visibility="collapsed")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    options_keys = list(DATASET_OPTIONS.keys())
    options_labels = [DATASET_OPTIONS[k]["name"] for k in options_keys]
    if st.session_state.custom_df is not None:
        options_keys = ["custom"] + options_keys
        options_labels = [f"Custom · {st.session_state.custom_name}"] + options_labels

    current_key = st.session_state.current_dataset_key
    if current_key not in options_keys:
        current_key = "retail_demo"
        st.session_state.current_dataset_key = current_key
    current_idx = options_keys.index(current_key)
    if st.session_state.get("dataset_selector") not in options_labels:
        st.session_state["dataset_selector"] = options_labels[current_idx]

    selected_label = st.selectbox("Active dataset", options_labels, index=current_idx, key="dataset_selector", label_visibility="collapsed")
    selected_key = options_keys[options_labels.index(selected_label)]
    if selected_key != st.session_state.current_dataset_key:
        st.session_state.current_dataset_key = selected_key
        st.session_state.last_result = None
        st.session_state.last_result_dataset = None
        if selected_key != "custom":
            st.session_state.active_query = DATASET_OPTIONS[selected_key]["sample_questions"][0]
        st.rerun()

    st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload CSV", type=["csv"], label_visibility="collapsed", help="CSV up to 50 MB. Data stays in local session memory.")
    if uploaded is not None:
        try:
            raw = uploaded.getvalue()
            signature = f"{uploaded.name}:{len(raw)}"
            if st.session_state.upload_sig != signature:
                user_df, report = parse_csv_bytes(raw, uploaded.name)
                st.session_state.custom_df = user_df
                st.session_state.custom_name = uploaded.name
                st.session_state.custom_report = report.as_dict()
                st.session_state.upload_sig = signature
                st.session_state.pending_dataset = "custom"
                st.rerun()
        except DatasetLoadError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Could not parse this CSV: {exc}")

    # Resolve the active dataset.
    active_report: dict[str, Any] = {}
    if st.session_state.current_dataset_key == "custom" and st.session_state.custom_df is not None:
        df = st.session_state.custom_df
        dataset_name = f"Custom · {st.session_state.custom_name}"
        active_report = st.session_state.custom_report or {}
    else:
        opt = DATASET_OPTIONS.get(st.session_state.current_dataset_key, DATASET_OPTIONS["retail_demo"])
        try:
            df, active_report = load_builtin(opt["file"])
        except Exception:
            df, active_report = load_builtin(DATASET_OPTIONS["retail_demo"]["file"])
            st.session_state.current_dataset_key = "retail_demo"
        dataset_name = opt["name"]

    profile = profile_dataset(df, name=dataset_name, warnings=active_report.get("warnings", []))
    dataset_id = dataset_signature(st.session_state.current_dataset_key, df)

    st.markdown(
        f"""
        <div style="background:#0c121c;border:1px solid #1d293b;border-radius:10px;padding:12px 13px;margin-top:10px;">
          <div style="font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:#64748b;font-weight:700;">Active dataset</div>
          <div style="font-size:12px;font-weight:600;color:#dbe4f0;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="{esc(dataset_name)}">{esc(dataset_name)}</div>
          <div style="display:flex;gap:10px;font-size:11px;font-family:'JetBrains Mono',monospace;color:#9b8cff;margin-top:6px;">
            <span>{esc(f"{profile.rows:,} rows")}</span><span>•</span><span>{profile.columns} cols</span><span>•</span><span>{len(profile.numeric_columns)} numeric</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if active_report.get("duplicate_headers"):
        st.caption("Duplicate headers were renamed automatically.")
    if active_report.get("parsed_date_columns"):
        st.caption("Date columns: " + ", ".join(active_report["parsed_date_columns"]))

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Optional LLM configuration.
    try:
        if hasattr(st, "secrets"):
            for secret_key in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"):
                try:
                    if secret_key in st.secrets and not os.environ.get(secret_key):
                        os.environ[secret_key] = str(st.secrets[secret_key])
                except Exception:
                    pass
    except Exception:
        pass
    cfg = llm_config()
    if cfg["available"]:
        st.checkbox(
            "LLM-assisted interpretation",
            key="use_llm",
            help="Sends only the question, column names/types and up to 3 sample values to your configured provider. The full CSV never leaves this machine. Every returned plan is validated before execution.",
        )
        st.markdown(
            f'<div class="chip green" style="margin-top:4px;">LLM ready: {esc(str(cfg["model"]))}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.session_state.use_llm = False
        st.markdown(
            '<div class="chip green">Deterministic engine active</div>'
            '<div class="small-muted" style="margin-top:6px;">No LLM key configured. Set OPENAI_API_KEY to enable optional natural-language plan interpretation.</div>',
            unsafe_allow_html=True,
        )

    with st.expander("⚙️ LLM Provider & Key (Optional)", expanded=False):
        st.caption("Connect OpenAI, Ollama, LM Studio, or any OpenAI-compatible endpoint")
        input_key = st.text_input(
            "API Key",
            value=os.environ.get("OPENAI_API_KEY", ""),
            type="password",
            help="Set an OpenAI-compatible API key. Leave empty to use local-only deterministic engine.",
            key="ui_llm_key",
        )
        input_base = st.text_input(
            "Base URL",
            value=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            help="Default: https://api.openai.com/v1 (or http://localhost:11434/v1 for Ollama)",
            key="ui_llm_base",
        )
        input_model = st.text_input(
            "Model",
            value=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            help="Model used for structured plan proposal",
            key="ui_llm_model",
        )
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button("Test", use_container_width=True, key="btn_test_llm"):
                if not input_key.strip():
                    st.error("No API key entered.")
                else:
                    with st.spinner("Connecting..."):
                        ok, msg = test_connection(
                            api_key=input_key.strip(),
                            base_url=input_base.strip(),
                            model=input_model.strip(),
                        )
                        if ok:
                            st.success(msg)
                        else:
                            st.error(msg)
        with btn_c2:
            if st.button("Apply", use_container_width=True, key="btn_apply_llm"):
                if input_key.strip():
                    os.environ["OPENAI_API_KEY"] = input_key.strip()
                elif "OPENAI_API_KEY" in os.environ:
                    del os.environ["OPENAI_API_KEY"]
                os.environ["OPENAI_BASE_URL"] = input_base.strip() or "https://api.openai.com/v1"
                os.environ["OPENAI_MODEL"] = input_model.strip() or "gpt-4o-mini"
                st.rerun()

    st.markdown(
        '<div style="margin-top:18px;font-size:10px;color:#526178;line-height:1.6;">'
        'Zero data egress by default · in-memory execution<br/>'
        'No eval() · no generated code · no SQL execution'
        "</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# PAGE: Overview
# ---------------------------------------------------------------------------
if nav == "Overview":
    metric = primary_metric(profile)
    group = primary_group(profile)
    date_col = primary_date(profile)
    render_page_header(
        "Natural-language analytics workspace",
        dataset_name,
        f"Explore {profile.rows:,} records across {profile.columns} columns. Ask a question in plain English; the engine builds a validated analysis plan and calculates the answer directly from the data.",
        [
            (f"{profile.rows:,} rows", ""),
            (f"{profile.columns} columns", ""),
            (f"{len(profile.numeric_columns)} numeric", ""),
            ("Deterministic calculations", "green"),
            ("LLM-ready" if cfg["available"] else "Local-only mode", "violet"),
        ],
    )

    if profile.rows == 0:
        st.error("The active dataset has no rows.")
    else:
        total_metric = float(pd.to_numeric(df[metric], errors="coerce").sum()) if metric else 0
        avg_metric = float(pd.to_numeric(df[metric], errors="coerce").mean()) if metric else 0
        kpi_grid(
            [
                ("Records", f"{profile.rows:,}", "Rows loaded in memory"),
                ("Columns", f"{profile.columns}", f"{len(profile.numeric_columns)} numeric · {len(profile.categorical_columns)} categorical"),
                (f"Total {humanize(metric)}" if metric else "Primary metric", format_value(total_metric, metric) if metric else "—", "Sum across all rows"),
                (f"Average {humanize(metric)}" if metric else "Average", format_value(avg_metric, metric) if metric else "—", "Arithmetic mean"),
                ("Missing cells", f"{profile.missing_cells:,}", "Data-quality check"),
                ("Duplicate rows", f"{profile.duplicate_rows:,}", "Full-row duplicates"),
            ]
        )

        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown('<div class="section-label">Trend</div>', unsafe_allow_html=True)
            if date_col and metric:
                work = pd.DataFrame(
                    {
                        "Period": pd.to_datetime(df[date_col], errors="coerce").dt.to_period("M").dt.start_time,
                        metric: pd.to_numeric(df[metric], errors="coerce"),
                    }
                ).dropna()
                table = work.groupby("Period")[metric].sum().reset_index().sort_values("Period")
                table["Period"] = table["Period"].dt.strftime("%Y-%m")
                make_chart({"type": "line", "x": "Period", "y": metric, "title": f"Monthly {humanize(metric)}"}, table, "ov_trend")
            else:
                st.info("No date column detected. Trend chart is unavailable for this dataset.")
        with col_right:
            st.markdown('<div class="section-label">Group comparison</div>', unsafe_allow_html=True)
            if group and metric:
                table = (
                    pd.to_numeric(df[metric], errors="coerce")
                    .groupby(df[group])
                    .sum()
                    .sort_values(ascending=False)
                    .head(8)
                    .reset_index()
                )
                make_chart(
                    {"type": "bar", "x": group, "y": metric, "title": f"{humanize(metric)} by {humanize(group)}", "orientation": "h"},
                    table,
                    "ov_groups",
                )
            else:
                st.info("No categorical grouping column detected.")

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown('<div class="section-label">Distribution</div>', unsafe_allow_html=True)
            if metric:
                values = pd.to_numeric(df[metric], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
                if len(values):
                    counts, edges = np.histogram(values, bins=min(24, max(5, int(np.sqrt(len(values))))))
                    table = pd.DataFrame(
                        {"Range": [f"{edges[i]:,.1f}–{edges[i+1]:,.1f}" for i in range(len(counts))], "Records": counts}
                    )
                    make_chart({"type": "histogram", "x": "Range", "y": "Records", "title": f"Distribution of {humanize(metric)}"}, table, "ov_dist")
            else:
                st.info("No numeric metric available.")
        with col_b:
            st.markdown('<div class="section-label">Numeric relationship</div>', unsafe_allow_html=True)
            numeric = profile.numeric_columns
            if len(numeric) >= 2:
                pair = (numeric[0], numeric[1])
                best = -1.0
                for i in range(min(len(numeric), 6)):
                    for j in range(i + 1, min(len(numeric), 6)):
                        try:
                            r = pd.to_numeric(df[numeric[i]], errors="coerce").corr(pd.to_numeric(df[numeric[j]], errors="coerce"))
                        except Exception:
                            continue
                        if pd.notna(r) and abs(float(r)) > best:
                            pair, best = (numeric[i], numeric[j]), abs(float(r))
                plot_df = df[[pair[0], pair[1]]].apply(pd.to_numeric, errors="coerce").dropna()
                if len(plot_df) > 1000:
                    plot_df = plot_df.sample(1000, random_state=42)
                fig = px.scatter(plot_df, x=pair[0], y=pair[1], opacity=0.55)
                fig.update_traces(marker=dict(size=5, color="#22d3ee", line=dict(width=0)))
                fig.update_layout(xaxis_title=humanize(pair[0]), yaxis_title=humanize(pair[1]))
                st.plotly_chart(
                    style_figure(fig, f"{humanize(pair[0])} vs {humanize(pair[1])} · r = {best:.3f}"),
                    use_container_width=True,
                    config={
                    "displayModeBar": "hover",
                    "toImageButtonOptions": {
                        "format": "png",
                        "filename": "csv_intelligence_chart",
                        "height": 550,
                        "width": 900,
                        "scale": 2,
                    },
                },
                    key="ov_scatter",
                )
            else:
                st.info("At least two numeric columns are needed for a relationship chart.")

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-label">Ask the analyst</div>', unsafe_allow_html=True)
        quick_default = (DATASET_OPTIONS.get(st.session_state.current_dataset_key) or {}).get("sample_questions", ["Give me an overview of this dataset."])[:4]
        quick_cols = st.columns(4)
        quick_clicked = None
        for idx, q in enumerate(quick_default):
            with quick_cols[idx]:
                if st.button(q, key=f"ov_q_{idx}", use_container_width=True):
                    quick_clicked = q
        with st.form("overview_ask"):
            quick_text = st.text_input("Question", value="", placeholder="e.g. Which category has the highest total profit?", label_visibility="collapsed")
            submitted = st.form_submit_button("Run analysis", type="primary")
        if quick_clicked:
            st.session_state.active_query = quick_clicked
            st.session_state.target_nav = "AI Analyst"
            st.rerun()
        if submitted and quick_text.strip():
            st.session_state.active_query = quick_text.strip()
            st.session_state.target_nav = "AI Analyst"
            st.rerun()

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-label">What stands out</div>', unsafe_allow_html=True)
        insight_cards(generate_insights(df, profile, limit=9), limit=3)


# ---------------------------------------------------------------------------
# PAGE: AI Analyst
# ---------------------------------------------------------------------------
elif nav == "AI Analyst":
    render_page_header(
        "Core feature · PS 91",
        "Ask your CSV a question",
        "The question is classified, matched to columns, converted into a structured plan, validated, and executed with deterministic pandas. The result includes the answer, evidence, chart and the exact plan used.",
        [
            ("Validated analysis plans", "green"),
            ("No generated code", ""),
            ("LLM-assisted" if cfg["available"] and st.session_state.use_llm else "Rule-based interpreter", "violet" if not (cfg["available"] and st.session_state.use_llm) else "amber"),
            (dataset_name, ""),
        ],
    )

    suggestions = suggest_questions(profile, 8)
    st.markdown('<div class="section-label">Suggested questions from this schema</div>', unsafe_allow_html=True)
    sug_cols = st.columns(4)
    clicked_query = None
    for idx, q in enumerate(suggestions[:4]):
        with sug_cols[idx]:
            if st.button(q, key=f"ai_sug_{dataset_id}_{idx}", use_container_width=True):
                clicked_query = q

    with st.form("analyst_form"):
        typed_query = st.text_input(
            "Question",
            value=clicked_query or st.session_state.active_query,
            placeholder="e.g. Which region has the highest total profit?",
            label_visibility="collapsed",
        )
        submit = st.form_submit_button("Execute analysis", type="primary", use_container_width=True)
    st.caption("Press Enter in the field or use the button. Ambiguous questions return candidate columns instead of guessing.")

    query_to_run = clicked_query or (typed_query.strip() if submit else None)
    if query_to_run:
        st.session_state.active_query = query_to_run
        with st.spinner("Building plan, validating columns and calculating…"):
            result = run_analysis(query_to_run, df, profile, st.session_state.use_llm)
        st.session_state.last_result = result
        st.session_state.last_result_query = query_to_run
        st.session_state.last_result_dataset = dataset_id
        add_history(result, query_to_run, dataset_id, dataset_name)

    if st.session_state.last_result is not None and st.session_state.last_result_dataset == dataset_id:
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="section-label">Question · {esc(st.session_state.last_result_query)}</div>', unsafe_allow_html=True)
        render_result(st.session_state.last_result, key_prefix=f"ai_{dataset_id}")
    else:
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.info("Ask a question above, or pick one of the schema-aware suggestions. Try an unsupported question too — the system returns a clarification instead of a fabricated answer.")


# ---------------------------------------------------------------------------
# PAGE: Data Explorer
# ---------------------------------------------------------------------------
elif nav == "Data Explorer":
    render_page_header(
        "Schema + records",
        "Data Explorer",
        f"Inspect the active dataset: inferred types, missingness, summary statistics, searchable paginated rows and exports.",
        [(f"{profile.rows:,} rows", ""), (f"{profile.columns} columns", ""), (f"{profile.missing_cells:,} missing cells", ""), (f"{profile.duplicate_rows:,} duplicates", "")],
    )

    with st.expander("Inferred schema & column statistics", expanded=True):
        rows = []
        for cp in profile.column_profiles:
            stat = "—"
            if cp.kind == "numeric":
                stat = f"min {cp.min:,.2f} · mean {cp.mean:,.2f} · max {cp.max:,.2f}"
            elif cp.top_values:
                stat = f"top: {cp.top_values[0][0]} ({cp.top_values[0][1]:,})"
            rows.append(
                {
                    "Column": cp.name,
                    "Type": cp.kind,
                    "Missing": cp.missing,
                    "Missing %": round(cp.missing_pct, 2),
                    "Unique": cp.unique,
                    "Summary": stat,
                    "Sample": cp.sample[0] if cp.sample else "",
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=min(480, 42 + 33 * len(rows)))

    st.markdown('<div class="section-label">Column inspector</div>', unsafe_allow_html=True)
    inspect_col = st.selectbox("Column", profile.all_columns, index=0)
    cp = profile.column(inspect_col)
    if cp:
        info_cols = st.columns(4)
        info_cols[0].metric("Inferred type", cp.kind)
        info_cols[1].metric("Missing", f"{cp.missing:,}", f"{cp.missing_pct:.1f}%")
        info_cols[2].metric("Unique values", f"{cp.unique:,}")
        info_cols[3].metric("Non-null", f"{cp.non_null:,}")
        if cp.kind == "numeric":
            values = pd.to_numeric(df[inspect_col], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
            if len(values):
                counts, edges = np.histogram(values, bins=min(24, max(5, int(np.sqrt(len(values))))))
                table = pd.DataFrame(
                    {"Range": [f"{edges[i]:,.1f}–{edges[i+1]:,.1f}" for i in range(len(counts))], "Records": counts}
                )
                make_chart({"type": "histogram", "x": "Range", "y": "Records", "title": f"Distribution of {humanize(inspect_col)}"}, table, f"de_hist_{inspect_col}")
        else:
            vc = df[inspect_col].astype(str).value_counts().head(12).reset_index()
            vc.columns = [inspect_col, "Records"]
            make_chart(
                {"type": "bar", "x": inspect_col, "y": "Records", "title": f"Top values in {humanize(inspect_col)}", "orientation": "h"},
                vc,
                f"de_bar_{inspect_col}",
            )

    st.markdown('<div class="section-label">Search, filter, sort and page</div>', unsafe_allow_html=True)
    filter_cols = st.columns([1.4, 1.4, 1, 1, 1])
    with filter_cols[0]:
        search = st.text_input("Search rows", placeholder="Type a keyword…", key="de_search")
    with filter_cols[1]:
        filter_col = st.selectbox("Filter column", ["None"] + profile.categorical_columns, key="de_filter_col")
    with filter_cols[2]:
        sort_col = st.selectbox("Sort by", ["None"] + profile.all_columns, key="de_sort")
    with filter_cols[3]:
        sort_dir = st.selectbox("Order", ["Descending", "Ascending"], key="de_order")
    with filter_cols[4]:
        page_size = st.selectbox("Rows per page", [25, 50, 100, 250], index=1, key="de_page_size")

    filter_value = None
    if filter_col != "None":
        try:
            values = df[filter_col].dropna().astype(str).unique().tolist()[:200]
        except Exception:
            values = []
        filter_value = st.selectbox(f"Value for {filter_col}", ["Any"] + values, key="de_filter_val")

    visible = df.copy()
    if filter_col != "None" and filter_value not in (None, "Any"):
        visible = visible[visible[filter_col].astype(str) == str(filter_value)]
    if search.strip():
        needle = search.strip()
        mask = visible.astype(str).apply(lambda col: col.str.contains(needle, case=False, na=False, regex=False)).any(axis=1)
        visible = visible[mask]
    if sort_col != "None":
        visible = visible.sort_values(sort_col, ascending=(sort_dir == "Ascending"), kind="mergesort")

    total_visible = len(visible)
    max_pages = max(1, (total_visible + page_size - 1) // page_size)
    if int(st.session_state.get("de_page", 1)) > max_pages:
        st.session_state["de_page"] = max_pages
    page = st.number_input("Page", min_value=1, max_value=max_pages, value=1, step=1, key="de_page")
    start = (int(page) - 1) * page_size
    page_df = visible.iloc[start : start + page_size]

    st.caption(f"{total_visible:,} matching rows · page {int(page):,} of {max_pages:,}")
    st.dataframe(page_df, use_container_width=True, hide_index=True, height=430)

    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            "Download active dataset (CSV)",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"{dataset_name.lower().replace(' ', '_').replace('·', '').strip()}.csv",
            mime="text/csv",
            key="de_download_all",
            use_container_width=True,
        )
    with dl2:
        st.download_button(
            "Download filtered view (CSV)",
            data=visible.to_csv(index=False).encode("utf-8"),
            file_name="filtered_view.csv",
            mime="text/csv",
            key="de_download_filtered",
            use_container_width=True,
        )


# ---------------------------------------------------------------------------
# PAGE: Insights
# ---------------------------------------------------------------------------
elif nav == "Insights":
    render_page_header(
        "Automatic exploration",
        "Dataset insights",
        "Deterministic observations computed from the active data. Each insight shows its evidence. Correlation is not presented as causation, and outliers are not called errors.",
        [("No LLM required", "green"), (f"{profile.rows:,} rows analysed", ""), ("Explainable evidence", "")],
    )
    insights = generate_insights(df, profile, limit=12)
    cols = st.columns(2)
    for idx, insight in enumerate(insights):
        with cols[idx % 2]:
            st.markdown(
                f"""
                <div class="insight-card" style="margin-bottom:12px;">
                  <div class="insight-kind">{esc(insight.get('kind', 'insight'))}</div>
                  <div class="insight-title">{esc(insight.get('title', ''))}</div>
                  <div class="insight-detail">{esc(insight.get('detail', ''))}</div>
                  <div class="insight-evidence">Evidence: {esc(' · '.join(insight.get('evidence', [])))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    metric = primary_metric(profile)
    group = primary_group(profile)
    date_col = primary_date(profile)
    a, b = st.columns(2)
    with a:
        st.markdown('<div class="section-label">Group contribution</div>', unsafe_allow_html=True)
        if metric and group:
            table = pd.to_numeric(df[metric], errors="coerce").groupby(df[group]).sum().sort_values(ascending=False).head(10).reset_index()
            make_chart({"type": "bar", "x": group, "y": metric, "title": f"{humanize(metric)} by {humanize(group)}", "orientation": "h"}, table, "ins_group")
        else:
            st.info("No group/metric pair available.")
    with b:
        st.markdown('<div class="section-label">Monthly movement</div>', unsafe_allow_html=True)
        if metric and date_col:
            work = pd.DataFrame({"Period": pd.to_datetime(df[date_col], errors="coerce").dt.to_period("M").dt.start_time, metric: pd.to_numeric(df[metric], errors="coerce")}).dropna()
            table = work.groupby("Period")[metric].sum().reset_index()
            table["Period"] = table["Period"].dt.strftime("%Y-%m")
            make_chart({"type": "line", "x": "Period", "y": metric, "title": f"Monthly {humanize(metric)}"}, table, "ins_trend")
        else:
            st.info("No date metric available.")


# ---------------------------------------------------------------------------
# PAGE: Evaluation
# ---------------------------------------------------------------------------
elif nav == "Evaluation":
    render_page_header(
        "Verification",
        "Engine evaluation",
        "A 34-case benchmark runs the real question engine against independently calculated pandas answers on the built-in synthetic dataset. Invalid-input cases verify that the system refuses to guess.",
        [("Executed live", "green"), ("Independent expected values", ""), ("34 cases · 8 categories", "")],
    )

    st.markdown('<div class="section-label">Benchmark dataset</div>', unsafe_allow_html=True)
    bench_df, _ = load_builtin(DATASET_OPTIONS["retail_demo"]["file"])
    bench_profile = profile_dataset(bench_df, name="retail benchmark")
    st.caption(f"Built-in synthetic retail dataset · {len(bench_df):,} rows · {len(bench_df.columns)} columns · deterministic seed 2024")

    run_clicked = st.button("Run 34-case benchmark", type="primary")
    if run_clicked or st.session_state.eval_report is None:
        with st.spinner("Executing each benchmark question through the real engine…"):
            st.session_state.eval_report = run_benchmark(bench_df, bench_profile)

    report = st.session_state.eval_report
    if report:
        kpi_grid(
            [
                ("Total cases", f"{report['total']}", "Real engine executions"),
                ("Passed", f"{report['passed']}", "Exact / tolerance match"),
                ("Failed", f"{report['failed']}", "Investigated individually"),
                ("Pass rate", f"{report['pass_pct']:.1f}%", "Computed from this run"),
            ]
        )
        st.progress(report["passed"] / report["total"] if report["total"] else 0.0)

        cat_rows = [{"Category": k, "Passed": v["passed"], "Total": v["total"], "Pass %": round(v["passed"] / v["total"] * 100, 1)} for k, v in report["categories"].items()]
        st.dataframe(pd.DataFrame(cat_rows), use_container_width=True, hide_index=True)

        results_df = pd.DataFrame([r.as_dict() for r in report["results"]])
        st.markdown('<div class="section-label">Individual results</div>', unsafe_allow_html=True)
        st.dataframe(results_df[["ID", "Category", "Question", "Expected", "Actual", "Status", "Intent"]], use_container_width=True, hide_index=True, height=520)

        failures = [r for r in report["results"] if not r.passed]
        with st.expander(f"Failure detail ({len(failures)})"):
            if failures:
                for r in failures:
                    st.markdown(f"**{r.id} · {r.question}**  \nExpected `{r.expected}` · actual `{r.actual}` · {r.error}")
            else:
                st.success("All benchmark cases passed. No failures to investigate.")

        st.markdown("**How this is evaluated**")
        st.markdown(
            "- Expected values are computed independently with pandas, not copied from the engine.\n"
            "- Numeric comparisons allow a small floating-point tolerance.\n"
            "- Invalid questions are expected to return `clarification` or a safe meta response, never a number.\n"
            "- Unit tests also run outside the UI: `python -m unittest discover -s tests -v` (42 tests).\n"
            "- The pass rate above is calculated from the current execution; it is not hardcoded."
        )


# ---------------------------------------------------------------------------
# PAGE: How It Works
# ---------------------------------------------------------------------------
elif nav == "How It Works":
    render_page_header(
        "Architecture",
        "How CSV Intelligence AI works",
        "This page describes the real implementation: a rule-based interpreter, optional LLM-assisted plan generation, strict validation, and deterministic pandas execution.",
        [("Python · Streamlit · pandas · Plotly", ""), ("No generated code executed", "green"), ("Optional OpenAI-compatible LLM", "violet")],
    )

    stages = [
        ("CSV input", "Drag-and-drop or built-in datasets. Delimiter detection, encoding fallback, duplicate-header repair and a 50 MB guard."),
        ("Parsing & validation", "Rows/columns are preserved. Date columns are converted only when the match is unambiguous. Empty files and header-only files are rejected with a readable error."),
        ("Schema & profiling", "Each column is classified as numeric, date, categorical, text, boolean or identifier. Profile includes missingness, unique counts, quartiles and samples."),
        ("Question normalization", "Lower-casing, punctuation cleanup, synonym expansion, singular/plural normalization and fuzzy token matching."),
        ("Intent classification", "Aggregate, grouped comparison, ranking, time series, distribution, outlier scan, correlation, schema lookup, clarification or safe meta response."),
        ("Column matching", "Scores exact names, aliases, concept synonyms and partial tokens against the active schema. Ambiguous matches return candidate columns instead of guessing."),
        ("Structured plan", "A JSON plan containing intent, metric, group, date column, aggregation, sort, limit, frequency, filters and chart type."),
        ("Validation", "Whitelisted intents/aggregations/charts only. Columns must exist. Types must be compatible. Limits and filter operators are bounded."),
        ("Safe execution", "Trusted pandas functions execute SUM, MEAN, MEDIAN, MIN, MAX, COUNT, STD, VAR, NUNIQUE, GROUPBY, RESAMPLE, correlation, IQR and filters."),
        ("Result verification", "Empty results, missing values and invalid numeric values are handled explicitly. No fabricated fallback number is returned."),
        ("Answer & visualization", "The calculated result is formatted into a finding, supporting metrics, exportable table and an appropriate Plotly chart with an explanation panel."),
    ]
    pipeline_html = []
    for idx, (title, desc) in enumerate(stages, start=1):
        pipeline_html.append(
            f'<div class="pipe-row"><div class="pipe-num">{idx:02d}</div>'
            f'<div class="pipe-body"><div class="pipe-title">{esc(title)}</div><div class="pipe-desc">{esc(desc)}</div></div></div>'
        )
    st.markdown(f'<div class="pipeline">{"".join(pipeline_html)}</div>', unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Technology stack")
        st.markdown(
            "- **Python 3** — application runtime\n"
            "- **Streamlit** — reactive web UI\n"
            "- **pandas** — parsing, grouping, resampling, aggregation\n"
            "- **NumPy** — percentile and histogram calculations\n"
            "- **Plotly** — interactive charts\n"
            "- **Optional OpenAI-compatible API** — question → plan only\n"
            "- **unittest** — engine and safety tests"
        )
        st.markdown("### Why deterministic calculations?")
        st.markdown(
            "LLMs are useful for understanding language, but they are not reliable calculators of exact dataset statistics. "
            "CSV Intelligence AI separates **interpretation** from **execution**. The question becomes a structured plan, "
            "the plan is validated, and pandas calculates the result. The answer is formatted from those verified values."
        )
    with c2:
        st.markdown("### The optional LLM layer")
        st.markdown(
            "If `OPENAI_API_KEY` is configured and the toggle is enabled, only the question, column names/types, "
            "cardinality and up to three sample values per column are sent. The full CSV never leaves the machine. "
            "The model returns a JSON plan, which is validated with the same validator used for rule-based plans. "
            "If the key is missing, the network fails, the response is invalid, or the plan fails validation, the app "
            "falls back to the deterministic interpreter and labels the response accordingly."
        )
        st.markdown("### Safety boundaries")
        st.markdown(
            "- No `eval()` / `exec()` of model output\n"
            "- No generated Python, SQL or unrestricted expressions\n"
            "- Unknown columns and unsupported aggregations are rejected\n"
            "- CSV cell content is treated as data, never as instructions\n"
            "- Filter values are length-limited and operator-checked\n"
            "- Result tables are capped; missing/NaN values are handled"
        )

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown("### Code map")
    st.dataframe(
        pd.DataFrame(
            [
                ("csvintel/loader.py", "CSV parsing, delimiter/encoding detection, duplicate headers, date inference"),
                ("csvintel/schema.py", "Type inference and dataset profiling"),
                ("csvintel/text.py", "Normalization, synonyms, fuzzy matching, formatting"),
                ("csvintel/planner.py", "Intent classification and structured plan generation"),
                ("csvintel/validator.py", "Whitelist and schema validation"),
                ("csvintel/executor.py", "Deterministic calculations and result objects"),
                ("csvintel/charts.py", "Chart specification → Plotly figure"),
                ("csvintel/insights.py", "Evidence-backed automatic insights"),
                ("csvintel/evaluation.py", "34-case live benchmark"),
                ("csvintel/llm.py", "Optional LLM plan proposal, schema-only context"),
            ],
            columns=["Module", "Responsibility"],
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Current limitations")
    st.markdown(
        "- Multi-series time comparisons (e.g. monthly revenue by region in one chart) are not yet supported.\n"
        "- Free-form multi-condition boolean logic is limited to at most two filters.\n"
        "- Statistical inference is descriptive (Pearson correlation, IQR); no significance testing.\n"
        "- The LLM layer requires an external provider and is optional by design.\n"
        "- Very large files are limited to 50 MB for this local academic prototype."
    )


# ---------------------------------------------------------------------------
# PAGE: History
# ---------------------------------------------------------------------------
elif nav == "History":
    render_page_header(
        "Session trail",
        "Analysis history",
        "Every executed question is stored with its dataset, result and plan. Older results are labelled when they belong to a different dataset.",
        [(f"{len(st.session_state.history)} analyses", ""), ("Session-only storage", ""), ("No fake entries", "green")],
    )
    if not st.session_state.history:
        st.info("No questions executed yet. Open AI Analyst and run a query to build the session trail.")
    else:
        for idx, item in enumerate(st.session_state.history):
            different = item["dataset_id"] != dataset_id
            with st.expander(f"{item['query']}  ·  {item['timestamp']}"):
                if different:
                    st.warning(f"This result belongs to another dataset: {item['dataset_name']}. It is not presented as a result of the current dataset.")
                st.markdown(f"**{esc(item['result'].answer)}**")
                st.caption(item["result"].detail)
                metric_pills(item["result"].metrics, item["result"], max_items=6)
                if item["result"].table is not None and len(item["result"].table):
                    st.dataframe(item["result"].table, use_container_width=True, hide_index=True, height=220)
                st.download_button(
                    "Answer (.txt)",
                    data=f"{item['result'].answer}\n\n{item['result'].detail}\n".encode("utf-8"),
                    file_name="csv_intelligence_history.txt",
                    key=f"hist_txt_{idx}",
                )
                if st.button("Open in AI Analyst", key=f"hist_open_{idx}"):
                    st.session_state.last_result = item["result"]
                    st.session_state.last_result_query = item["query"]
                    st.session_state.last_result_dataset = item["dataset_id"]
                    st.session_state.target_nav = "AI Analyst"
                    st.rerun()
        if st.button("Clear session history"):
            st.session_state.history = []
            st.rerun()


# ---------------------------------------------------------------------------
# PAGE: Demo Mode
# ---------------------------------------------------------------------------
elif nav == "Demo Mode":
    metric = primary_metric(profile)
    group = primary_group(profile)
    date_col = primary_date(profile)
    st.markdown('<div class="demo">', unsafe_allow_html=True)
    render_page_header(
        "Jury demonstration",
        "Live analysis demo",
        "Five real analyses, executed live. No pre-recorded answers. Every number is calculated from the active dataset.",
        [(dataset_name, ""), (f"{profile.rows:,} rows", ""), ("Deterministic", "green"), ("Session reset available", "violet")],
    )
    st.markdown("</div>", unsafe_allow_html=True)

    kpi_grid(
        [
            ("Dataset", dataset_name, "Active demonstration data"),
            ("Records", f"{profile.rows:,}", f"{profile.columns} columns"),
            ("Primary metric", f"Total {humanize(metric)}" if metric else "—", format_value(float(pd.to_numeric(df[metric], errors="coerce").sum()), metric) if metric else "—"),
            ("Grouping", humanize(group) if group else "—", "Used by comparison demos"),
            ("Date coverage", humanize(date_col) if date_col else "—", "Used by trend demo"),
        ]
    )

    demo_actions = [
        ("1 · Dataset overview", "Give me an overview of this dataset."),
        ("2 · Ranking", "Which category has the highest total revenue?"),
        ("3 · Comparison", "Compare revenue across regions."),
        ("4 · Time series", "Show monthly revenue trends."),
        ("5 · Anomalies", "Are there any unusual values in revenue?"),
    ]
    demo_clicked = None
    action_cols = st.columns(3)
    for idx, (label, question) in enumerate(demo_actions):
        with action_cols[idx % 3]:
            if st.button(label, key=f"demo_action_{idx}", use_container_width=True):
                demo_clicked = question

    with st.form("demo_form"):
        demo_query = st.text_input("Ask a question", value=st.session_state.demo_query, label_visibility="collapsed")
        demo_submit = st.form_submit_button("Run live analysis", type="primary", use_container_width=True)

    query = demo_clicked or (demo_query.strip() if demo_submit else None)
    if query:
        st.session_state.demo_query = query
        with st.spinner("Executing deterministic analysis…"):
            result = run_analysis(query, df, profile, use_llm=st.session_state.use_llm)
        st.session_state.demo_result = result
        add_history(result, query, dataset_id, dataset_name)

    if st.session_state.demo_result is not None:
        st.markdown(f'<div class="section-label">Live question · {esc(st.session_state.demo_query)}</div>', unsafe_allow_html=True)
        render_result(st.session_state.demo_result, key_prefix="demo", allow_chart_switch=False, demo=True)
    else:
        st.info("Choose a demo step above. Each button executes a real query against the active dataset.")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    reset_col, note_col = st.columns([1, 3])
    with reset_col:
        if st.button("Reset demo", use_container_width=True):
            st.session_state.pending_dataset = "retail_demo"
            st.session_state.history = []
            st.session_state.demo_result = None
            st.session_state.demo_query = "Give me an overview of this dataset."
            st.session_state.last_result = None
            st.session_state.last_result_dataset = None
            st.rerun()
    with note_col:
        st.caption("Reset restores the built-in synthetic retail dataset and clears the session history. No files are deleted.")

    with st.expander("Presenter run sheet"):
        st.markdown(
            "1. **Overview** — state the problem, upload or confirm the synthetic dataset, point out the automatically generated profile.\n"
            "2. **Ranking** — run demo 2; open *How this analysis works* and show the detected group, metric and SUM aggregation.\n"
            "3. **Comparison** — run demo 3; switch the chart to donut and back. Emphasise that values are calculated, not generated.\n"
            "4. **Time series** — run demo 4; explain date detection, monthly resampling and the peak period.\n"
            "5. **Anomalies** — run demo 5; explain Tukey's 1.5×IQR and that outliers are flags, not proof of fraud.\n"
            "6. **Safety** — ask *What is the total foobar?* to show a clarification rather than a fabricated number.\n"
            "7. **Evaluation** — open Evaluation and run the 34-case benchmark live."
        )


# Footer
st.markdown(
    f"""
    <div style="margin-top:36px;padding-top:14px;border-top:1px solid #172033;display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;">
      <span style="color:#526178;font-size:11px;">CSV Intelligence AI · PS 91 Chat-with-your-CSV · {esc(dataset_name)}</span>
      <span style="color:#526178;font-size:11px;font-family:'JetBrains Mono',monospace;">{profile.rows:,} rows · deterministic engine · plan validated</span>
    </div>
    """,
    unsafe_allow_html=True,
)
