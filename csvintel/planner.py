"""Question -> structured analysis plan.

This module performs intent classification and column matching. It never
executes anything: it only produces a JSON-serialisable plan that the
validator and executor can check.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from .schema import (
    CATEGORICAL,
    DATE,
    ID,
    NUMERIC,
    TEXT,
    DatasetProfile,
)
from .text import (
    CORRELATION_TOKENS,
    DISTRIBUTION_TOKENS,
    FAREWELL_WORDS,
    GREETING_WORDS,
    GROUP_TRIGGERS,
    MISSING_TOKENS,
    OFF_TOPIC,
    OUTLIER_TOKENS,
    OVERVIEW_TOKENS,
    POLITE_WORDS,
    RANK_TOKENS,
    SCHEMA_TOKENS,
    TIME_TOKENS,
    column_match_score,
    contains_any,
    concept_for_column,
    contains_phrase,
    detect_aggregation,
    detect_direction,
    extract_frequency,
    extract_limit,
    humanize,
    is_currency_column,
    normalize,
    normalize_question,
    singular,
    tokenize,
)

_PREFERRED_METRIC_HINTS = (
    "revenue_generated",
    "monthly_recurring_revenue",
    "total_bill_amount",
    "transaction_amount",
    "annual_salary",
    "annual_contract_value",
    "revenue",
    "sales",
    "profit",
    "amount",
    "spend",
    "bill",
    "salary",
    "mrr",
    "freight_cost",
    "sale_price",
    "close_price",
    "unit_price",
    "price",
    "volume",
    "quantity",
    "units_sold",
    "score",
    "rating",
    "age",
    "days",
    "discount",
)

_PRIMARY_GROUP_NAMES = (
    "category",
    "region",
    "segment",
    "customer_segment",
    "department",
    "platform",
    "plan_tier",
    "transport_mode",
    "merchant_category",
    "property_type",
    "genre",
    "device_type",
    "city",
    "destination_country",
    "product",
    "product_name",
    "asset_name",
    "ticker_symbol",
)

_GROUP_TRIGGER_PHRASES = (
    "by ",
    "per ",
    "across ",
    "compare ",
    "comparison",
    "breakdown",
    "split ",
    "for each ",
    "grouped ",
    "divided ",
)

_META_ANALYTIC_MARKERS = (
    "total",
    "sum",
    "average",
    "mean",
    "median",
    "highest",
    "lowest",
    "top",
    "bottom",
    "trend",
    "monthly",
    "compare",
    "by",
    "outlier",
    "missing",
    "unique",
    "distribution",
    "correlation",
    "count",
    "rows",
    "records",
    "columns",
    "revenue",
    "profit",
    "cost",
    "amount",
    "sales",
)


_ROW_COUNT_ENTITIES = {
    "row", "record", "entry", "order", "transaction", "shipment", "admission",
    "signup", "session", "visit", "customer", "user", "employee", "property",
    "campaign", "product", "event", "loan", "student", "patient", "ticket",
}

_TIME_WORDS = {"monthly", "weekly", "daily", "yearly", "annual", "quarterly"}
_STRONG_TIME_PHRASES = (
    "trend", "trends", "over time", "timeline", "progression", "seasonality",
    "by month", "per month", "by year", "per year", "by week", "per week",
    "by day", "per day", "by quarter", "per quarter", "time series",
)


def _time_signal(text: str, profile: DatasetProfile) -> bool:
    """Detect a genuine time-series request.

    A word like "annual" inside "annual_salary" describes the column, not the
    requested operation, so it must not turn a total or grouping into a trend.
    """
    if any(contains_phrase(text, p) for p in _STRONG_TIME_PHRASES):
        return True
    time_words = [w for w in _TIME_WORDS if contains_phrase(text, w)]
    if not time_words:
        return False
    # A time word is a real signal only when it is not simply part of a column
    # that the question explicitly names (e.g. "annual_salary" or
    # "monthly_recurring_revenue").
    named = [
        cp.name
        for cp in profile.column_profiles
        if column_match_score(text, cp.name, cp.kind) >= 60
    ]
    if named and all(any(contains_phrase(normalize(col), w) for col in named) for w in time_words):
        return False
    return True


def _mentions_row_entity(text: str) -> bool:
    tokens = {singular(t) for t in tokenize(text)}
    return any(singular(entity) in tokens for entity in _ROW_COUNT_ENTITIES)


def _row_count_request(text: str) -> bool:
    if not re.search(r"\bhow many\b", text):
        return False
    return _mentions_row_entity(text)


def primary_metric(profile: DatasetProfile) -> str | None:
    numeric = profile.numeric_columns
    if not numeric:
        return None
    normalized = {c: normalize(c) for c in numeric}
    for hint in _PREFERRED_METRIC_HINTS:
        for col, ncol in normalized.items():
            if ncol == hint:
                return col
    for hint in _PREFERRED_METRIC_HINTS:
        for col, ncol in normalized.items():
            if contains_phrase(ncol, hint):
                return col
    return numeric[0]


def primary_group(profile: DatasetProfile) -> str | None:
    candidates = [c for c in profile.column_profiles if c.kind in (CATEGORICAL, DATE) and c.name not in profile.id_columns]
    if not candidates:
        return None
    for hint in _PRIMARY_GROUP_NAMES:
        for c in candidates:
            if normalize(c.name) == hint:
                return c.name
    scored: list[tuple[float, str]] = []
    for c in candidates:
        if c.unique < 2:
            continue
        if c.unique <= 50:
            score = 40 - c.unique * 0.2
        elif c.unique <= max(100, profile.rows // 5):
            score = 18
        else:
            score = 4
        if c.kind == DATE:
            score -= 12
        scored.append((score, c.name))
    if not scored:
        return None
    scored.sort(reverse=True)
    return scored[0][1]


def primary_date(profile: DatasetProfile) -> str | None:
    dates = profile.date_columns
    return dates[0] if dates else None


def _rank_columns(
    text: str,
    profile: DatasetProfile,
    kinds: tuple[str, ...],
    exclude: set[str] | None = None,
) -> list[tuple[float, str]]:
    exclude = exclude or set()
    out: list[tuple[float, str]] = []
    for cp in profile.column_profiles:
        if cp.kind not in kinds or cp.name in exclude:
            continue
        score = column_match_score(text, cp.name, cp.kind)
        out.append((score, cp.name))
    out.sort(key=lambda item: (-item[0], item[1]))
    return out


def _preference_bonus(text: str, column: str) -> float:
    ncol = normalize(column)
    bonus = 0.0
    if contains_phrase(text, "revenue") and "revenue" in ncol:
        bonus += 6
        if ncol == "revenue":
            bonus += 3
        if "generated" in ncol and "generated" not in text:
            bonus -= 2
    if contains_phrase(text, "profit") and "profit" in ncol:
        bonus += 6
    if contains_phrase(text, "sales") and ncol in {"revenue", "sales"}:
        bonus += 5
    if contains_phrase(text, "price"):
        if ncol == "close_price" and not any(contains_phrase(text, p) for p in ("open", "high", "low")):
            bonus += 6
        elif ncol in {"sale_price", "list_price", "unit_price"}:
            bonus += 2
    if contains_phrase(text, "cost") and ncol == "cost":
        bonus += 5
    if contains_phrase(text, "discount") and "discount" in ncol:
        bonus += 5
    return bonus


def _choose_metric(
    text: str,
    profile: DatasetProfile,
    exclude: set[str] | None = None,
    required: bool = False,
) -> tuple[str | None, list[tuple[float, str]], bool]:
    ranked = _rank_columns(text, profile, (NUMERIC,), exclude)
    ranked = [(score + _preference_bonus(text, col), col) for score, col in ranked]
    ranked.sort(key=lambda item: (-item[0], item[1]))
    explicit = [(s, c) for s, c in ranked if s >= 34]
    if explicit:
        top_score, top_col = explicit[0]
        ambiguous = len(explicit) > 1 and (top_score - explicit[1][0]) < 6
        if not ambiguous:
            return top_col, ranked, False
        # A dataset column whose exact name appears in the question wins even
        # when a synonym of another column also matches.
        exact = [c for _, c in explicit if contains_phrase(text, normalize(c)) and len(normalize(c).split()) >= 1]
        if len(exact) == 1:
            return exact[0], ranked, False
        return None, ranked, True
    if required:
        return None, ranked, False
    return primary_metric(profile), ranked, False


def _choose_group(text: str, profile: DatasetProfile, exclude: set[str] | None = None) -> tuple[str | None, list[tuple[float, str]], bool]:
    ranked = _rank_columns(text, profile, (CATEGORICAL, DATE), exclude)
    # Phrase-level disambiguation: "product categories" means category, not product.
    if "product categor" in text:
        ranked = [(score + (40 if "categor" in col.lower() else 0), col) for score, col in ranked]
        ranked.sort(key=lambda item: (-item[0], item[1]))
    explicit = [(s, c) for s, c in ranked if s >= 34]
    if explicit:
        top_score, top_col = explicit[0]
        ambiguous = len(explicit) > 1 and (top_score - explicit[1][0]) < 6
        if ambiguous:
            exact = [c for _, c in explicit if contains_phrase(text, normalize(c))]
            if len(exact) == 1:
                return exact[0], ranked, False
            return None, ranked, True
        return top_col, ranked, False
    return None, ranked, False


def _extract_filters(text: str, df: pd.DataFrame, profile: DatasetProfile) -> list[dict[str, Any]]:
    filters: list[dict[str, Any]] = []
    numeric_cols = set(profile.numeric_columns)
    all_cols = set(profile.all_columns)

    # 1) Explicit comparisons: revenue > 100, discount >= 10%
    for m in re.finditer(r"([a-z][a-z0-9 ]{1,40}?)\s*(>=|<=|>|<|=)\s*([0-9]+(?:\.[0-9]+)?)\s*%?", text):
        phrase = m.group(1).strip()
        op = m.group(2)
        value = float(m.group(3))
        best_col, best_score = None, 0.0
        for col in numeric_cols:
            score = column_match_score(phrase, col, NUMERIC)
            if score > best_score:
                best_col, best_score = col, score
        if best_col and best_score >= 30:
            filters.append({"column": best_col, "op": op, "value": value, "label": f"{humanize(best_col)} {op} {value:g}"})

    # 2) "where region is Europe" / "for category = Furniture"
    for m in re.finditer(r"(?:where|for|with)\s+([a-z][a-z0-9 ]{1,35}?)\s+(?:is|equals|=|of)\s+([a-z0-9][a-z0-9 &\.\-]{1,35})", text):
        col_phrase, value_phrase = m.group(1).strip(), m.group(2).strip()
        col, score = _best_col_for_phrase(col_phrase, profile)
        if col and score >= 30:
            actual = _find_actual_value(df[col], value_phrase)
            if actual is not None:
                filters.append({"column": col, "op": "==", "value": actual, "label": f"{humanize(col)} = {actual}"})

    # 3) Categorical values introduced by in/for/within/from.
    for cp in profile.column_profiles:
        if cp.kind not in (CATEGORICAL,) or cp.unique > 100 or cp.unique < 1:
            continue
        try:
            values = df[cp.name].dropna().astype(str).unique()[:100]
        except Exception:
            continue
        for value in values:
            if len(str(value).strip()) < 2:
                continue
            val_text = normalize(str(value))
            if len(val_text) < 2:
                continue
            pattern = rf"\b(?:in|for|within|from|where)\s+{re.escape(val_text)}\b"
            if re.search(pattern, text):
                if not any(f["column"] == cp.name for f in filters):
                    filters.append({"column": cp.name, "op": "==", "value": str(value), "label": f"{humanize(cp.name)} = {value}"})

    # 4) Year filters ("in 2024", "during 2023")
    for date_col in profile.date_columns:
        years = pd.to_datetime(df[date_col], errors="coerce").dt.year.dropna().astype(int).unique()
        for year in years:
            if re.search(rf"\b(?:in|during|for)\s+{year}\b", text):
                if not any(f["column"] == date_col for f in filters):
                    filters.append({"column": date_col, "op": "year==", "value": int(year), "label": f"Year = {year}"})

    # De-duplicate while keeping order and cap at two filters for clarity.
    seen = set()
    unique: list[dict[str, Any]] = []
    for f in filters:
        key = (f["column"], f["op"], str(f["value"]))
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique[:2]


def _best_col_for_phrase(phrase: str, profile: DatasetProfile) -> tuple[str | None, float]:
    best, best_score = None, 0.0
    for cp in profile.column_profiles:
        score = column_match_score(phrase, cp.name, cp.kind)
        if score > best_score:
            best, best_score = cp.name, score
    return best, best_score


def _find_actual_value(series: pd.Series, phrase: str) -> str | None:
    phrase_n = normalize(phrase)
    try:
        values = series.dropna().astype(str).unique()
    except Exception:
        return None
    for value in values:
        if normalize(value) == phrase_n:
            return str(value)
    for value in values:
        if phrase_n and phrase_n in normalize(value):
            return str(value)
    return None


def _has_analytical_signal(text: str, profile: DatasetProfile) -> bool:
    if any(contains_phrase(text, w) for w in _META_ANALYTIC_MARKERS):
        return True
    for cp in profile.column_profiles:
        if column_match_score(text, cp.name, cp.kind) >= 34:
            return True
    return False


def _meta_plan(kind: str, question: str) -> dict[str, Any]:
    return {
        "version": 1,
        "question": question,
        "intent": "meta",
        "meta_type": kind,
        "metric": None,
        "group": None,
        "date_column": None,
        "aggregation": None,
        "sort": None,
        "limit": None,
        "frequency": None,
        "filters": [],
        "chart": "none",
        "confidence": 1.0,
        "interpretation": [],
        "candidates": {},
        "source": "rules",
        "notes": [],
    }


def _clarification(
    question: str,
    reason: str,
    profile: DatasetProfile,
    metrics: list[tuple[float, str]] | None = None,
    groups: list[tuple[float, str]] | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "version": 1,
        "question": question,
        "intent": "clarification",
        "metric": None,
        "group": None,
        "date_column": None,
        "aggregation": None,
        "sort": None,
        "limit": None,
        "frequency": None,
        "filters": [],
        "chart": "none",
        "confidence": 0.0,
        "interpretation": [],
        "candidates": {
            "reason": reason,
            "metrics": [c for _, c in (metrics or [])[:8]],
            "groups": [c for _, c in (groups or [])[:8]],
            "numeric_columns": profile.numeric_columns,
            "categorical_columns": profile.categorical_columns,
        },
        "source": "rules",
        "notes": notes or [],
    }


def explain_plan(plan: dict[str, Any]) -> list[str]:
    """Public helper used by the UI and external-plan adapters."""
    return _steps(plan)


def _steps(plan: dict[str, Any]) -> list[str]:
    intent = plan.get("intent")
    steps: list[str] = []
    if intent == "aggregate":
        steps.append(f"Detected an aggregate statistic over the numeric column '{plan.get('metric')}'.")
        steps.append(f"Applied {str(plan.get('aggregation')).upper()} to {plan.get('metric')}.")
    elif intent in ("group_aggregation", "ranking"):
        steps.append(f"Detected a grouped analysis by '{plan.get('group')}'.")
        steps.append(f"Applied {str(plan.get('aggregation')).upper()} to the metric '{plan.get('metric') or 'row count'}' for each group.")
        if plan.get("sort"):
            steps.append(f"Sorted groups in {'descending' if plan.get('sort') == 'desc' else 'ascending'} order.")
        if plan.get("limit"):
            steps.append(f"Kept the top {plan.get('limit')} group(s) as requested.")
    elif intent == "time_series":
        steps.append(f"Detected a time-based question using the date column '{plan.get('date_column')}'.")
        steps.append(f"Resampled dates by {plan.get('frequency')} and aggregated '{plan.get('metric')}' with {str(plan.get('aggregation')).upper()}.")
    elif intent == "outliers":
        steps.append(f"Selected '{plan.get('metric')}' and computed Tukey's 1.5x IQR fences.")
        steps.append("Flagged values outside the fences as potential statistical outliers (not proof of error or fraud).")
    elif intent == "correlation":
        steps.append(f"Selected numeric columns '{plan.get('metric')}' and '{plan.get('metric_2')}'.")
        steps.append("Computed the Pearson correlation coefficient on complete pairs.")
    elif intent == "distribution":
        steps.append(f"Selected '{plan.get('metric')}' and binned the values into a histogram.")
    elif intent in ("missing", "duplicates", "dataset_overview", "row_count", "column_count", "schema", "list_numeric", "list_categorical"):
        steps.append("Inspected dataset metadata only; no row values were modified.")
    if plan.get("filters"):
        steps.append("Applied filters: " + ", ".join(f.get("label", "") for f in plan["filters"]) + ".")
    steps.append("Executed deterministic pandas operations locally against the active dataset.")
    return steps


def _build_plan_core(question: str, df: pd.DataFrame, profile: DatasetProfile) -> dict[str, Any]:
    """Convert a natural-language question into a validated plan candidate."""
    nq = normalize_question(question)
    text = nq.text
    raw = str(question or "")

    if not text or not nq.tokens:
        return _meta_plan("empty", raw)

    # Meta intents are only returned when there is no analytical signal.
    analytical = _has_analytical_signal(text, profile)
    if not analytical:
        if any(contains_phrase(text, w) for w in GREETING_WORDS):
            return _meta_plan("greeting", raw)
        if any(contains_phrase(text, w) for w in POLITE_WORDS):
            return _meta_plan("polite", raw)
        if any(contains_phrase(text, w) for w in FAREWELL_WORDS):
            return _meta_plan("farewell", raw)
        if any(contains_phrase(text, w) for w in ("help", "what can you do", "who are you", "how does this work", "how to use", "capabilities")):
            return _meta_plan("help", raw)
        if any(contains_phrase(text, w) for w in OFF_TOPIC):
            return _meta_plan("off_topic", raw)

    # Dataset-level overview.
    if any(contains_phrase(text, w) for w in OVERVIEW_TOKENS) or (
        "summarize" in text or "summarise" in text or "overview" in text
    ):
        return _finish(raw, "dataset_overview", chart="kpi")

    # Schema / metadata intents.
    if any(contains_phrase(text, w) for w in ("how many columns", "number of columns", "column count")):
        return _finish(raw, "column_count", chart="kpi")

    if contains_phrase(text, "numeric columns") or contains_phrase(text, "numeric fields"):
        return _finish(raw, "list_numeric", chart="table")
    if contains_phrase(text, "categorical columns") or contains_phrase(text, "text columns") or contains_phrase(text, "date columns"):
        return _finish(raw, "list_categorical", chart="table")
    if any(contains_phrase(text, w) for w in SCHEMA_TOKENS) and not any(
        contains_phrase(text, w) for w in ("average", "total", "sum", "profit", "revenue", "amount", "sales")
    ):
        return _finish(raw, "schema", chart="table")
    if contains_phrase(text, "duplicate"):
        return _finish(raw, "duplicates", chart="kpi")
    if any(contains_phrase(text, w) for w in MISSING_TOKENS):
        return _finish(raw, "missing", chart="bar")
    if contains_phrase(text, "how many unique") or contains_phrase(text, "number of unique") or contains_phrase(text, "distinct values count"):
        col, ranked, ambiguous = _choose_group(text, profile)
        if ambiguous or not col:
            return _clarification(raw, "I need one column to count unique values for.", profile, groups=ranked)
        p = _finish(raw, "unique_count", metric=None, group=col, chart="kpi")
        p["metric"] = col
        p["interpretation"] = [f"Counted distinct non-null values in '{col}'."]
        return p

    # Simple row-count questions ("How many transactions are there?").
    early_group_trigger = any(contains_phrase(text, w) for w in _GROUP_TRIGGER_PHRASES)
    if _row_count_request(text) and not early_group_trigger and not any(
        contains_phrase(text, w) for w in ("total", "sum", "average", "mean", "median", "minimum", "maximum")
    ):
        return _finish(raw, "row_count", chart="kpi")

    # Correlation.
    if any(contains_phrase(text, w) for w in CORRELATION_TOKENS):
        numeric_ranked = _rank_columns(text, profile, (NUMERIC,))
        mentioned = [c for s, c in numeric_ranked if s >= 34]
        if len(mentioned) >= 2:
            first, second = mentioned[0], mentioned[1]
        elif len(mentioned) == 1:
            first = mentioned[0]
            second = _strongest_partner(first, df, profile)
        elif len(profile.numeric_columns) >= 2:
            first, second = _strongest_pair(df, profile)
        else:
            return _clarification(raw, "Correlation needs at least two numeric columns.", profile, metrics=numeric_ranked)
        p = _finish(raw, "correlation", metric=first, metric_2=second, chart="scatter")
        p["interpretation"] = [f"Computed Pearson correlation between '{first}' and '{second}'."]
        return p

    # Outliers.
    if any(contains_phrase(text, w) for w in OUTLIER_TOKENS):
        col, ranked, ambiguous = _choose_metric(text, profile, required=False)
        if ambiguous:
            return _clarification(raw, "Several numeric columns match. Which metric should I check for outliers?", profile, metrics=ranked)
        if not col:
            return _clarification(raw, "I could not identify a numeric column for outlier detection.", profile, metrics=ranked)
        p = _finish(raw, "outliers", metric=col, chart="box")
        return p

    # Distribution.
    if any(contains_phrase(text, w) for w in DISTRIBUTION_TOKENS):
        col, ranked, ambiguous = _choose_metric(text, profile, required=False)
        if ambiguous:
            return _clarification(raw, "Several numeric columns match. Which distribution should I show?", profile, metrics=ranked)
        if not col:
            return _clarification(raw, "I could not identify a numeric column for the distribution.", profile, metrics=ranked)
        return _finish(raw, "distribution", metric=col, chart="histogram")

    freq = extract_frequency(text)
    time_signal = _time_signal(text, profile)
    date_col, date_ranked, date_ambiguous = _choose_group(text, profile, exclude=set(profile.numeric_columns))
    date_matches = [c for c in profile.date_columns if (date_col == c)]
    if time_signal:
        actual_date = date_col if date_matches else primary_date(profile)
        if actual_date is None:
            return _clarification(raw, "This dataset has no date column I can use for a time-series analysis.", profile)
        metric, metric_ranked, ambiguous = _choose_metric(text, profile, required=True)
        if ambiguous:
            return _clarification(raw, "Several metrics match. Which metric should the trend use?", profile, metrics=metric_ranked)
        aggregation = detect_aggregation(text)
        if aggregation is None:
            point_metric = concept_for_column(metric or "") in ("price", "score", "rating", "age", "discount", "roi")
            aggregation = "mean" if point_metric else "sum"
        if not metric:
            # No numeric metric was named: count matching records per period.
            # This is explicit in the answer rather than silently summing a
            # different column.
            metric = None
            aggregation = "count"
        freq = freq or "M"
        p = _finish(
            raw,
            "time_series",
            metric=metric,
            date_column=actual_date,
            frequency=freq,
            aggregation=aggregation,
            sort="asc",
            chart="line",
        )
        if metric is None:
            p["interpretation"].append("No numeric metric was named; counts records per period.")
        return p

    # Grouped / ranking analysis.
    group_trigger = any(contains_phrase(text, w) for w in _GROUP_TRIGGER_PHRASES)
    rank_hit = any(contains_phrase(text, w) for w in RANK_TOKENS)
    group_col, group_ranked, group_ambiguous = _choose_group(text, profile)
    metric_col, metric_ranked, metric_ambiguous = _choose_metric(text, profile, required=False)
    explicit_metric = bool(metric_col) and any(s >= 34 for s, c in metric_ranked if c == metric_col) and not metric_ambiguous

    if group_ambiguous and (group_trigger or rank_hit):
        return _clarification(raw, "Several categorical columns match. Which grouping should I use?", profile, metrics=metric_ranked, groups=group_ranked)

    should_group = bool(group_trigger and group_col) or bool(rank_hit and group_col and contains_phrase(text, "which"))
    # "Top products by revenue" has no "by <group>" unless candidate matched.
    if contains_phrase(text, "top") or contains_phrase(text, "bottom"):
        if group_col:
            should_group = True

    if should_group and group_col:
        aggregation = detect_aggregation(text)
        if aggregation in ("min", "max") and not any(
            contains_phrase(text, w) for w in ("minimum", "maximum", "min", "max", "highest", "lowest", "best", "worst")
        ):
            aggregation = "sum"
        if aggregation is None:
            if contains_phrase(text, "most frequently") or contains_phrase(text, "frequency"):
                aggregation = "count"
            elif contains_phrase(text, "average") or contains_phrase(text, "mean"):
                aggregation = "mean"
            else:
                aggregation = "sum"
        # "Which country has the most shipments?" asks for a COUNT of rows,
        # not a sum of whichever numeric column happens to be primary.
        entity_count = (
            not explicit_metric
            and (
                (rank_hit and _mentions_row_entity(text))
                or ("how many" in text)
            )
        )
        if entity_count:
            aggregation = "count"
            metric_col = None
        # "Highest/lowest" usually describes the ranking direction, not the
        # aggregation. For grouped questions the default comparison is SUM,
        # except for naturally point-in-time metrics such as price or rating.
        if aggregation in ("min", "max"):
            explicit_extreme = any(contains_phrase(text, w) for w in ("maximum", "minimum", " min ", " max "))
            concept = concept_for_column(metric_col or "")
            point_metric = concept in ("price", "score", "age", "discount", "days", "roi")
            if not explicit_extreme and not point_metric:
                aggregation = "sum"
        if metric_ambiguous and aggregation != "count":
            return _clarification(raw, "Several numeric metrics match. Which metric should I aggregate?", profile, metrics=metric_ranked, groups=group_ranked)
        if aggregation == "count" and not explicit_metric:
            metric_col = None
        if metric_col is None and aggregation != "count":
            return _clarification(raw, "I found the grouping column but no numeric metric to aggregate. Please name the metric.", profile, metrics=metric_ranked, groups=group_ranked)
        direction = detect_direction(text) or "desc"
        if aggregation == "min" and direction == "desc":
            direction = "asc"
        if aggregation == "max" and direction == "asc":
            direction = "desc"
        limit = extract_limit(text, default=None)
        if limit is None and any(contains_phrase(text, w) for w in ("top", "bottom")):
            limit = 5
        if limit is None and contains_phrase(text, "which"):
            limit = 1
        intent = "ranking" if (rank_hit or limit) else "group_aggregation"
        p = _finish(
            raw,
            intent,
            metric=metric_col,
            group=group_col,
            aggregation=aggregation,
            sort=direction,
            limit=limit,
            chart="bar",
        )
        p["candidates"]["metrics"] = [c for _, c in metric_ranked[:8]]
        p["candidates"]["groups"] = [c for _, c in group_ranked[:8]]
        return p

    if group_trigger and not group_col:
        return _clarification(
            raw,
            "I detected a grouped question but could not confidently identify the grouping column.",
            profile,
            metrics=metric_ranked,
            groups=group_ranked,
        )
    if group_ambiguous and group_trigger:
        return _clarification(raw, "Several columns could be the grouping column.", profile, metrics=metric_ranked, groups=group_ranked)

    # Row count without a group.
    if any(
        contains_phrase(text, w)
        for w in ("how many rows", "how many records", "row count", "record count", "number of rows", "total records", "total rows", "how many entries")
    ):
        return _finish(raw, "row_count", chart="kpi")

    # Aggregation over the whole dataset.
    aggregation = detect_aggregation(text)
    if aggregation:
        explicit_ser = _choose_metric(text, profile, required=True)
        agg_metric, agg_ranked, agg_ambiguous = explicit_ser
        if agg_ambiguous:
            return _clarification(raw, "Several numeric metrics match. Which one should I use?", profile, metrics=agg_ranked)
        if agg_metric is None:
            if aggregation == "count" and not metric_ranked:
                return _finish(raw, "row_count", chart="kpi")
            return _clarification(
                raw,
                "I could not confidently identify the metric in your question. Please name a numeric column.",
                profile,
                metrics=agg_ranked or metric_ranked,
            )
        p = _finish(raw, "aggregate", metric=agg_metric, aggregation=aggregation, chart="kpi")
        return p

    # A single mentioned column: profile it instead of guessing an operation.
    if metric_col and not metric_ambiguous and _explicitly_mentioned(text, metric_col):
        return _finish(raw, "column_profile", metric=metric_col, chart="histogram")
    if group_col and not group_ambiguous and _explicitly_mentioned(text, group_col) and not group_trigger:
        return _finish(raw, "column_profile", metric=group_col, chart="bar")

    return _clarification(
        raw,
        "I could not map that question to a supported analytical operation.",
        profile,
        metrics=metric_ranked,
        groups=group_ranked,
    )


def build_plan(question: str, df: pd.DataFrame, profile: DatasetProfile) -> dict[str, Any]:
    """Public entry point: classify, match columns, then attach filters."""
    plan = _build_plan_core(question, df, profile)
    text = normalize_question(question).text
    if plan.get("intent") not in ("meta", "clarification"):
        plan["filters"] = _extract_filters(text, df, profile)
        plan["steps"] = _steps(plan)
        if plan["filters"]:
            plan["interpretation"].append(
                "Filters applied: " + ", ".join(f.get("label", "") for f in plan["filters"]) + "."
            )
    plan.setdefault("steps", [])
    return plan


def _explicitly_mentioned(text: str, column: str) -> bool:
    return column_match_score(text, column, "") >= 60


def _finish(
    question: str,
    intent: str,
    metric: str | None = None,
    group: str | None = None,
    date_column: str | None = None,
    aggregation: str | None = None,
    sort: str | None = None,
    limit: int | None = None,
    frequency: str | None = None,
    chart: str = "table",
    **extra: Any,
) -> dict[str, Any]:
    plan: dict[str, Any] = {
        "version": 1,
        "question": question,
        "intent": intent,
        "metric": metric,
        "metric_2": extra.get("metric_2"),
        "group": group,
        "date_column": date_column,
        "aggregation": aggregation,
        "sort": sort,
        "limit": limit,
        "frequency": frequency,
        "filters": extra.get("filters", []),
        "chart": chart,
        "confidence": 0.9,
        "interpretation": [],
        "candidates": {},
        "source": "rules",
        "notes": [],
    }
    plan["interpretation"] = [f"Detected intent: {intent.replace('_', ' ')}."]
    if metric:
        plan["interpretation"].append(f"Metric: {humanize(metric)}.")
    if group:
        plan["interpretation"].append(f"Grouping column: {humanize(group)}.")
    if date_column:
        plan["interpretation"].append(f"Date column: {humanize(date_column)}.")
    if aggregation:
        plan["interpretation"].append(f"Aggregation: {aggregation.upper()}.")
    plan["steps"] = _steps(plan)
    return plan


def _strongest_partner(column: str, df: pd.DataFrame, profile: DatasetProfile) -> str:
    best, best_corr = None, -2.0
    try:
        base = pd.to_numeric(df[column], errors="coerce")
    except Exception:
        base = pd.Series(dtype=float)
    for other in profile.numeric_columns:
        if other == column:
            continue
        try:
            corr = base.corr(pd.to_numeric(df[other], errors="coerce"))
        except Exception:
            continue
        if pd.notna(corr) and abs(float(corr)) > best_corr:
            best, best_corr = other, abs(float(corr))
    return best or (profile.numeric_columns[0] if profile.numeric_columns else column)


def _strongest_pair(df: pd.DataFrame, profile: DatasetProfile) -> tuple[str, str]:
    best = (profile.numeric_columns[0], profile.numeric_columns[1])
    best_corr = -1.0
    cols = profile.numeric_columns
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            try:
                corr = pd.to_numeric(df[cols[i]], errors="coerce").corr(pd.to_numeric(df[cols[j]], errors="coerce"))
            except Exception:
                continue
            if pd.notna(corr) and abs(float(corr)) > best_corr:
                best, best_corr = (cols[i], cols[j]), abs(float(corr))
    return best


def suggest_questions(profile: DatasetProfile, limit: int = 8) -> list[str]:
    """Schema-aware example questions. Generated from columns, not hardcoded data."""
    metric = primary_metric(profile)
    group = primary_group(profile)
    date = primary_date(profile)
    out: list[str] = []
    if profile.rows:
        out.append("Give me an overview of this dataset.")
    if metric and group:
        out.append(f"Which {humanize(group).lower()} has the highest {humanize(metric).lower()}?")
        out.append(f"Compare {humanize(metric).lower()} across {humanize(group).lower()}.")
    if metric:
        out.append(f"What is the total {humanize(metric).lower()}?")
        out.append(f"What is the average {humanize(metric).lower()}?")
    if date and metric:
        out.append(f"Show monthly {humanize(metric).lower()} trends.")
    if profile.numeric_columns:
        out.append("Are there any unusual values in this dataset?")
    out.append("Are there any missing values?")
    out.append("How many records are there?")
    # Unique while preserving order.
    seen = set()
    result = []
    for q in out:
        if q not in seen:
            seen.add(q)
            result.append(q)
    return result[:limit]
