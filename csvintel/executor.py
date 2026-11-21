"""Deterministic, whitelisted execution of validated analysis plans."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .planner import primary_date, primary_group, primary_metric, suggest_questions
from .schema import DatasetProfile, is_numeric_col
from .text import (
    format_value,
    humanize,
    is_currency_column,
    is_percent_column,
    normalize,
)
from .validator import PlanValidationError, validate_plan

MAX_TABLE_ROWS = 5000
MAX_SCATTER_POINTS = 1200


@dataclass
class AnalysisResult:
    ok: bool
    intent: str
    answer: str
    detail: str
    metrics: dict[str, Any] = field(default_factory=dict)
    table: pd.DataFrame | None = None
    chart: dict[str, Any] | None = None
    plan: dict[str, Any] | None = None
    explanation: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    records_used: int = 0
    formula: str = ""
    error: str | None = None
    source: str = "rules"

    @property
    def row_count(self) -> int:
        return 0 if self.table is None else len(self.table)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "intent": self.intent,
            "answer": self.answer,
            "detail": self.detail,
            "metrics": self.metrics,
            "table": None if self.table is None else self.table.to_dict(orient="records"),
            "chart": self.chart,
            "plan": self.plan,
            "explanation": self.explanation,
            "warnings": self.warnings,
            "records_used": self.records_used,
            "formula": self.formula,
            "error": self.error,
            "source": self.source,
        }


def _num(series: pd.Series) -> pd.Series:
    if is_numeric_col(series):
        return pd.to_numeric(series, errors="coerce")
    return pd.to_numeric(
        series.astype(str).str.replace(r"[,$%]", "", regex=True).str.strip(),
        errors="coerce",
    )


def _clean_number(value: Any) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _apply_filters(df: pd.DataFrame, plan: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    filters = plan.get("filters") or []
    if not filters:
        return df, []
    out = df.copy()
    labels: list[str] = []
    for f in filters:
        col, op, value = f["column"], f["op"], f["value"]
        if col not in out.columns:
            continue
        series = out[col]
        if op == "year==":
            try:
                out = out[pd.to_datetime(out[col], errors="coerce").dt.year == int(value)]
            except Exception:
                continue
        elif op == "contains":
            out = out[series.astype(str).str.contains(str(value), case=False, na=False, regex=False)]
        elif op in (">", ">=", "<", "<=", "==", "!="):
            if is_numeric_col(series):
                numeric = _num(series)
                if op == ">":
                    out = out[numeric > float(value)]
                elif op == ">=":
                    out = out[numeric >= float(value)]
                elif op == "<":
                    out = out[numeric < float(value)]
                elif op == "<=":
                    out = out[numeric <= float(value)]
                elif op == "==":
                    out = out[numeric == float(value)]
                elif op == "!=":
                    out = out[numeric != float(value)]
            else:
                text_series = series.astype(str).str.strip().str.lower()
                target = normalize(str(value))
                if op == "==":
                    out = out[text_series == target]
                elif op == "!=":
                    out = out[text_series != target]
                else:
                    continue
        labels.append(f.get("label", f"{col} {op} {value}"))
    return out, labels


def _filter_note(labels: list[str]) -> str:
    return (" Filters applied: " + "; ".join(labels) + ".") if labels else ""


def _chart(kind: str, **kwargs: Any) -> dict[str, Any]:
    return {"type": kind, **kwargs}


def _base_result(plan: dict[str, Any], profile: DatasetProfile, source: str) -> AnalysisResult:
    return AnalysisResult(
        ok=True,
        intent=str(plan.get("intent")),
        answer="",
        detail="",
        plan=plan,
        explanation=list(plan.get("steps") or []),
        records_used=profile.rows,
        source=source,
    )


def execute_plan(
    plan: dict[str, Any],
    df: pd.DataFrame,
    profile: DatasetProfile,
    source: str = "rules",
) -> AnalysisResult:
    """Validate and execute a plan. Never evaluates generated code."""
    try:
        validate_plan(plan, profile)
    except PlanValidationError as exc:
        return AnalysisResult(
            ok=False,
            intent=str(plan.get("intent", "invalid")),
            answer="I could not run that analysis safely.",
            detail=str(exc),
            plan=plan,
            error=str(exc),
            source=source,
        )

    try:
        return _dispatch(plan, df, profile, source)
    except Exception as exc:  # last-resort guard: never crash the UI
        return AnalysisResult(
            ok=False,
            intent=str(plan.get("intent", "error")),
            answer="The analysis could not be completed.",
            detail=f"Internal calculation error: {type(exc).__name__}: {exc}",
            plan=plan,
            error=str(exc),
            source=source,
        )


def _dispatch(plan: dict[str, Any], df: pd.DataFrame, profile: DatasetProfile, source: str) -> AnalysisResult:
    intent = plan["intent"]
    if intent == "meta":
        return _execute_meta(plan, df, profile, source)
    if intent == "clarification":
        return _execute_clarification(plan, profile, source)
    if intent == "dataset_overview":
        return _dataset_overview(plan, df, profile, source)
    if intent == "schema":
        return _schema(plan, df, profile, source)
    if intent == "list_numeric":
        return _list_columns(plan, profile, source, numeric=True)
    if intent == "list_categorical":
        return _list_columns(plan, profile, source, numeric=False)
    if intent == "row_count":
        return _row_count(plan, df, profile, source)
    if intent == "column_count":
        return _column_count(plan, df, profile, source)
    if intent == "missing":
        return _missing(plan, df, profile, source)
    if intent == "duplicates":
        return _duplicates(plan, df, profile, source)
    if intent == "unique_count":
        return _unique_count(plan, df, profile, source)
    if intent == "aggregate":
        return _aggregate(plan, df, profile, source)
    if intent in ("group_aggregation", "ranking"):
        return _grouped(plan, df, profile, source)
    if intent == "time_series":
        return _time_series(plan, df, profile, source)
    if intent == "distribution":
        return _distribution(plan, df, profile, source)
    if intent == "outliers":
        return _outliers(plan, df, profile, source)
    if intent == "correlation":
        return _correlation(plan, df, profile, source)
    if intent == "column_profile":
        return _column_profile(plan, df, profile, source)
    raise PlanValidationError(f"Unhandled intent: {intent}")


# ---------------------------------------------------------------------------
# Meta and clarification
# ---------------------------------------------------------------------------
def _execute_meta(plan: dict[str, Any], df: pd.DataFrame, profile: DatasetProfile, source: str) -> AnalysisResult:
    result = _base_result(plan, profile, source)
    metric = primary_metric(profile)
    group = primary_group(profile)
    kind = plan.get("meta_type")
    if kind == "empty":
        result.answer = "Please enter a question about your dataset."
        result.detail = "Ask about totals, averages, rankings, monthly trends, missing values or outliers."
    elif kind == "greeting":
        result.answer = "Hello. I am your CSV analyst."
        result.detail = (
            f"I am connected to {profile.rows:,} records across {profile.columns} columns. "
            "Ask a question in plain English and I will compute the answer directly from the data."
        )
    elif kind == "polite":
        result.answer = "You're welcome."
        result.detail = "Ask another question whenever you are ready."
    elif kind == "farewell":
        result.answer = "Session closed. Your data stays local."
        result.detail = "The active dataset remains in memory for this session; history is kept until you clear it."
    elif kind == "help":
        result.answer = "I turn plain-English questions into validated pandas operations."
        result.detail = (
            "I can compute totals, averages, medians, spread, grouped comparisons, rankings, time trends, "
            "correlations, distributions, outliers, missing-value counts and dataset summaries. "
            "Every calculation runs deterministically on the active CSV."
        )
    else:
        result.answer = "That question is outside this dataset's scope."
        result.detail = "I only analyse the active tabular dataset. Try a question about its columns, totals, groups or trends."
        result.explanation = ["Off-topic guardrail triggered before any calculation."]
    result.metrics = {
        "Rows": f"{profile.rows:,}",
        "Columns": profile.columns,
        "Suggested question": suggest_questions(profile, 1)[0] if suggest_questions(profile, 1) else "",
    }
    result.chart = _chart("none")
    result.formula = "No data operation executed (conversational response)."
    if metric and group:
        result.explanation.append(f"Available example: which {humanize(group).lower()} has the highest {humanize(metric).lower()}?")
    return result


def _execute_clarification(plan: dict[str, Any], profile: DatasetProfile, source: str) -> AnalysisResult:
    result = _base_result(plan, profile, source)
    reason = (plan.get("candidates") or {}).get("reason") or "I need a clearer question."
    numeric = profile.numeric_columns
    groups = profile.categorical_columns
    result.answer = reason
    hints = []
    if numeric:
        hints.append("Numeric columns: " + ", ".join(humanize(c) for c in numeric[:8]) + ".")
    if groups:
        hints.append("Grouping columns: " + ", ".join(humanize(c) for c in groups[:8]) + ".")
    hints.append("Try: 'What is the total " + humanize(numeric[0]).lower() + "?'" if numeric else "Try: 'How many records are there?'")
    result.detail = " ".join(hints)
    result.metrics = {"Rows": f"{profile.rows:,}", "Numeric columns": len(numeric), "Grouping columns": len(groups)}
    result.chart = _chart("none")
    result.formula = "No calculation performed: the question was ambiguous or unsupported."
    result.explanation = [
        "The question could not be mapped to a high-confidence structured plan.",
        "No guess was made and no data was modified.",
        "Clarification candidates were generated from the active schema.",
    ]
    return result


# ---------------------------------------------------------------------------
# Dataset metadata
# ---------------------------------------------------------------------------
def _dataset_overview(plan: dict[str, Any], df: pd.DataFrame, profile: DatasetProfile, source: str) -> AnalysisResult:
    result = _base_result(plan, profile, source)
    metric = primary_metric(profile)
    group = primary_group(profile)
    total_metric = _clean_number(_num(df[metric]).sum()) if metric else None
    leader, leader_value = None, None
    if metric and group:
        try:
            agg = _num(df[metric]).groupby(df[group]).sum().sort_values(ascending=False)
            if len(agg):
                leader, leader_value = str(agg.index[0]), _clean_number(agg.iloc[0])
        except Exception:
            pass
    result.answer = f"Dataset contains {profile.rows:,} records across {profile.columns} columns."
    detail_parts = [
        f"{len(profile.numeric_columns)} numeric, {len(profile.categorical_columns)} categorical and {len(profile.date_columns)} date columns.",
        f"{profile.missing_cells:,} missing cells and {profile.duplicate_rows:,} duplicate rows.",
    ]
    if metric:
        detail_parts.append(f"Primary metric is {humanize(metric)} (total {format_value(total_metric, metric)}).")
    if leader:
        detail_parts.append(f"{humanize(group)} leader is {leader} at {format_value(leader_value, metric)}.")
    result.detail = " ".join(detail_parts)
    result.metrics = {
        "Rows": profile.rows,
        "Columns": profile.columns,
        "Missing cells": profile.missing_cells,
        "Duplicate rows": profile.duplicate_rows,
        "Numeric columns": len(profile.numeric_columns),
        "Categorical columns": len(profile.categorical_columns),
    }
    if metric:
        result.metrics[f"Total {humanize(metric)}"] = total_metric
    if leader:
        result.metrics[f"Leading {humanize(group)}"] = leader
    rows = [
        {
            "Column": cp.name,
            "Type": cp.kind,
            "Missing": cp.missing,
            "Unique": cp.unique,
            "Sample": cp.sample[0] if cp.sample else "",
        }
        for cp in profile.column_profiles
    ]
    result.table = pd.DataFrame(rows)
    result.chart = _chart("none")
    result.formula = "Schema profiling + deterministic aggregates over all rows."
    result.explanation = [
        f"Read row/column counts from the DataFrame shape: {profile.rows:,} x {profile.columns}.",
        "Classified columns by dtype and value heuristics.",
        "Computed totals, category leadership and data-quality counts.",
    ]
    return result


def _schema(plan: dict[str, Any], df: pd.DataFrame, profile: DatasetProfile, source: str) -> AnalysisResult:
    result = _base_result(plan, profile, source)
    rows = []
    for cp in profile.column_profiles:
        rows.append(
            {
                "Column": cp.name,
                "Type": cp.kind,
                "Dtype": cp.dtype,
                "Non-null": cp.non_null,
                "Missing": cp.missing,
                "Unique": cp.unique,
            }
        )
    result.table = pd.DataFrame(rows)
    result.answer = f"The dataset has {profile.columns} columns."
    result.detail = "Numeric: " + (", ".join(profile.numeric_columns) or "none") + ". Categorical: " + (", ".join(profile.categorical_columns) or "none") + "."
    result.metrics = {
        "Numeric": len(profile.numeric_columns),
        "Categorical": len(profile.categorical_columns),
        "Date": len(profile.date_columns),
    }
    result.chart = _chart("table")
    result.formula = "df.dtypes + value-based type inference."
    return result


def _list_columns(plan: dict[str, Any], profile: DatasetProfile, source: str, numeric: bool) -> AnalysisResult:
    result = _base_result(plan, profile, source)
    names = profile.numeric_columns if numeric else (profile.categorical_columns + profile.date_columns)
    label = "numeric" if numeric else "categorical and date"
    rows = []
    for name in names:
        cp = profile.column(name)
        rows.append({"Column": name, "Type": cp.kind if cp else "", "Unique": cp.unique if cp else "", "Sample": cp.sample[0] if cp and cp.sample else ""})
    result.table = pd.DataFrame(rows)
    result.answer = f"{len(names)} {label} column(s) found."
    result.detail = ", ".join(humanize(n) for n in names) if names else "No matching columns."
    result.metrics = {"Matching columns": len(names)}
    result.chart = _chart("table")
    result.formula = "Schema inspection only."
    return result


def _row_count(plan: dict[str, Any], df: pd.DataFrame, profile: DatasetProfile, source: str) -> AnalysisResult:
    result = _base_result(plan, profile, source)
    result.answer = f"The dataset contains {profile.rows:,} records."
    result.detail = f"Each record spans {profile.columns} columns. {profile.missing_cells:,} cells are missing and {profile.duplicate_rows:,} fully duplicated rows were found."
    result.metrics = {"Rows": profile.rows, "Columns": profile.columns}
    result.chart = _chart("kpi")
    result.formula = "len(df)"
    return result


def _column_count(plan: dict[str, Any], df: pd.DataFrame, profile: DatasetProfile, source: str) -> AnalysisResult:
    result = _base_result(plan, profile, source)
    result.answer = f"The dataset has {profile.columns} columns."
    result.detail = f"{len(profile.numeric_columns)} numeric, {len(profile.categorical_columns)} categorical, {len(profile.date_columns)} date."
    result.metrics = {"Columns": profile.columns, "Rows": profile.rows}
    result.chart = _chart("kpi")
    result.formula = "len(df.columns)"
    return result


def _missing(plan: dict[str, Any], df: pd.DataFrame, profile: DatasetProfile, source: str) -> AnalysisResult:
    result = _base_result(plan, profile, source)
    counts = df.isna().sum()
    table = pd.DataFrame(
        {
            "Column": counts.index,
            "Missing": counts.values,
            "Missing %": (counts.values / max(len(df), 1) * 100).round(2),
        }
    ).sort_values("Missing", ascending=False)
    total = int(counts.sum())
    total_cells = max(profile.rows * profile.columns, 1)
    completeness = (1 - total / total_cells) * 100
    result.answer = (
        "No missing values were detected."
        if total == 0
        else f"{total:,} missing cells were detected across {int((counts > 0).sum())} column(s)."
    )
    result.detail = f"Data completeness is {completeness:.2f}% ({total:,} missing out of {total_cells:,} cells)."
    result.metrics = {
        "Missing cells": total,
        "Completeness %": round(completeness, 2),
        "Columns with missing": int((counts > 0).sum()),
    }
    result.table = table
    result.chart = _chart("bar", x="Column", y="Missing", title="Missing values by column") if total else _chart("kpi")
    result.formula = "df.isna().sum()"
    return result


def _duplicates(plan: dict[str, Any], df: pd.DataFrame, profile: DatasetProfile, source: str) -> AnalysisResult:
    result = _base_result(plan, profile, source)
    mask = df.duplicated(keep="first")
    count = int(mask.sum())
    result.answer = f"{count:,} duplicate row(s) found." if count else "No duplicate rows were found."
    result.detail = f"Compared all {profile.columns} columns across {profile.rows:,} records. Duplicate rate: {count / max(profile.rows, 1) * 100:.2f}%."
    result.metrics = {"Duplicate rows": count, "Rows": profile.rows}
    result.table = df[mask].head(50).copy() if count else None
    result.chart = _chart("kpi")
    result.formula = "df.duplicated().sum()"
    return result


def _unique_count(plan: dict[str, Any], df: pd.DataFrame, profile: DatasetProfile, source: str) -> AnalysisResult:
    col = plan.get("metric") or plan.get("group")
    result = _base_result(plan, profile, source)
    if col not in df.columns:
        result.ok = False
        result.error = f"Unknown column: {col}"
        result.answer = "I could not identify the column to count."
        return result
    count = int(df[col].nunique(dropna=True))
    total = int(df[col].notna().sum())
    result.answer = f"'{humanize(col)}' has {count:,} unique values."
    result.detail = f"Based on {total:,} non-null records; {int(df[col].isna().sum()):,} values are missing."
    result.metrics = {"Unique values": count, "Non-null records": total, "Missing": int(df[col].isna().sum())}
    result.chart = _chart("kpi")
    result.formula = f"df['{col}'].nunique()"
    return result


# ---------------------------------------------------------------------------
# Aggregations
# ---------------------------------------------------------------------------
def _aggregate(plan: dict[str, Any], df: pd.DataFrame, profile: DatasetProfile, source: str) -> AnalysisResult:
    result = _base_result(plan, profile, source)
    filtered, labels = _apply_filters(df, plan)
    metric = plan["metric"]
    agg = plan["aggregation"]
    series = _num(filtered[metric])
    valid = series.dropna()
    if valid.empty:
        result.ok = False
        result.answer = f"No valid numeric values remain in '{humanize(metric)}'."
        result.detail = _filter_note(labels).strip() or "The column is empty or non-numeric."
        result.warnings.append("Empty aggregation input.")
        return result
    mapping = {
        "sum": valid.sum(),
        "mean": valid.mean(),
        "median": valid.median(),
        "min": valid.min(),
        "max": valid.max(),
        "std": valid.std() if len(valid) > 1 else 0.0,
        "var": valid.var() if len(valid) > 1 else 0.0,
        "count": valid.count(),
        "nunique": valid.nunique(),
        "range": valid.max() - valid.min(),
    }
    value = float(mapping[agg])
    value_display = format_value(value, metric)
    labels_text = {
        "sum": "Total",
        "mean": "Average",
        "median": "Median",
        "min": "Minimum",
        "max": "Maximum",
        "std": "Standard deviation of",
        "var": "Variance of",
        "count": "Count of",
        "nunique": "Unique values in",
        "range": "Range of",
    }[agg]
    result.answer = f"{labels_text} {humanize(metric)} is {value_display}."
    result.detail = (
        f"Calculated from {int(valid.count()):,} valid numeric records"
        f"{' out of ' + format(len(filtered), ',') + ' filtered rows' if labels else ''}. "
        f"Missing/non-numeric values were excluded. Range: {format_value(valid.min(), metric)} to {format_value(valid.max(), metric)}."
    )
    result.metrics = {
        "Value": value,
        "Records": int(valid.count()),
        "Missing excluded": int(series.isna().sum()),
        "Minimum": float(valid.min()),
        "Maximum": float(valid.max()),
    }
    result.chart = _chart("kpi")
    result.records_used = len(filtered)
    result.formula = f"df['{metric}'].{agg}()" + (" with filters" if labels else "")
    result.explanation.extend(
        [
            f"Selected numeric metric '{metric}'.",
            f"Applied {agg.upper()} over {int(valid.count()):,} non-null values.",
        ]
    )
    if labels:
        result.explanation.append("Applied filters: " + "; ".join(labels) + ".")
    _ = is_percent_column(metric)
    return result


def _grouped(plan: dict[str, Any], df: pd.DataFrame, profile: DatasetProfile, source: str) -> AnalysisResult:
    result = _base_result(plan, profile, source)
    filtered, labels = _apply_filters(df, plan)
    group = plan["group"]
    metric = plan.get("metric")
    agg = plan["aggregation"]
    if len(filtered) == 0:
        result.ok = False
        result.answer = "No rows matched the applied filters."
        result.detail = _filter_note(labels).strip()
        return result

    if agg == "count" and not metric:
        table = filtered.groupby(group, dropna=False).size().reset_index(name="Records")
        value_col = "Records"
        result.formula = f"df.groupby('{group}').size()"
    else:
        if metric not in filtered.columns:
            result.ok = False
            result.answer = "The metric column is unavailable."
            return result
        work = filtered[[group, metric]].copy()
        work[metric] = _num(work[metric])
        work = work.dropna(subset=[group, metric])
        if work.empty:
            result.ok = False
            result.answer = f"No valid '{humanize(metric)}' values exist for the groups."
            result.detail = "Grouping was aborted rather than returning a fabricated value."
            return result
        try:
            table = work.groupby(group)[metric].agg(agg).reset_index()
        except Exception:
            # Numeric-like text columns: coerce had already happened above.
            table = work.groupby(group)[metric].sum().reset_index()
            agg = "sum"
        value_col = metric
        result.formula = f"df.groupby('{group}')['{metric}'].{agg}()"

    ascending = plan.get("sort") == "asc"
    table = table.sort_values(value_col, ascending=ascending, kind="mergesort").reset_index(drop=True)
    total_groups = len(table)
    limit = plan.get("limit")
    shown = table.head(limit) if limit else table
    result.table = shown.reset_index(drop=True)
    result.records_used = len(filtered)

    if shown.empty:
        result.ok = False
        result.answer = "The grouped calculation returned no rows."
        return result

    top = shown.iloc[0]
    top_name = str(top[group])
    top_value = float(top[value_col])
    bottom = table.iloc[-1]
    bottom_name, bottom_value = str(bottom[group]), float(bottom[value_col])
    agg_label = agg.upper() if agg != "mean" else "AVERAGE"

    if agg in ("sum", "count"):
        total = float(table[value_col].sum())
        share = (top_value / total * 100) if total else 0.0
    else:
        total, share = None, None

    if plan["intent"] == "ranking" and (limit == 1 or contains_which(plan)):
        if metric:
            direction_word = "highest" if not ascending else "lowest"
            result.answer = f"{humanize(group)} '{top_name}' has the {direction_word} {humanize(value_col)} at {format_value(top_value, value_col)}."
        else:
            result.answer = f"{humanize(group)} '{top_name}' has the {'most' if not ascending else 'fewest'} records at {int(top_value):,}."
    elif plan["intent"] == "ranking" and limit:
        result.answer = (
            f"Top {len(shown)} {humanize(group)} by {humanize(value_col)}: "
            f"{top_name} leads with {format_value(top_value, value_col if metric else None)}."
        )
    else:
        result.answer = (
            f"{humanize(value_col)} is highest for {humanize(group)} '{top_name}' at "
            f"{format_value(top_value, value_col if metric else None)}"
            + (f" ({share:.1f}% of total)." if share is not None else ".")
        )

    detail = (
        f"{agg_label} calculated across {len(filtered):,} filtered records and {total_groups} groups. "
        f"Lowest group: '{bottom_name}' at {format_value(bottom_value, value_col if metric else None)}."
        + _filter_note(labels)
    )
    if share is not None:
        detail += f" The leading group accounts for {share:.1f}% of the aggregate total."

    result.detail = detail
    result.metrics = {
        "Groups": total_groups,
        "Metric": humanize(value_col) if metric else "Records",
        "Aggregation": agg_label,
        f"Top {humanize(group)}": top_name,
        "Top value": top_value,
        f"Lowest {humanize(group)}": bottom_name,
        "Lowest value": bottom_value,
    }
    if total is not None:
        result.metrics["Total"] = total
        result.metrics["Top share %"] = round(share or 0.0, 2)
    chart_rows = table.head(12).copy()
    try:
        chart_rows[group] = chart_rows[group].astype(str)
    except Exception:
        pass
    result.chart = _chart(
        "bar",
        x=group,
        y=value_col,
        title=f"{humanize(value_col)} by {humanize(group)}",
        orientation="h" if (plan["intent"] == "ranking" or total_groups > 8) else "v",
        data=chart_rows.to_dict(orient="records"),
    )
    result.explanation.extend(
        [
            f"Grouped {len(filtered):,} rows by '{group}'.",
            f"Aggregated '{value_col}' with {agg_label}.",
            f"Sorted {'ascending' if ascending else 'descending'}"
            + (f" and kept {limit} rows." if limit else " across all groups."),
        ]
    )
    return result


def contains_which(plan: dict[str, Any]) -> bool:
    return "which" in normalize(plan.get("question", ""))


# ---------------------------------------------------------------------------
# Time series
# ---------------------------------------------------------------------------
def _time_series(plan: dict[str, Any], df: pd.DataFrame, profile: DatasetProfile, source: str) -> AnalysisResult:
    result = _base_result(plan, profile, source)
    filtered, labels = _apply_filters(df, plan)
    date_col, metric, freq, agg = plan["date_column"], plan["metric"], plan["frequency"], plan["aggregation"]
    count_mode = metric is None and agg == "count"
    columns = [date_col] if count_mode else [date_col, metric]
    work = filtered[columns].copy()
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    if count_mode:
        work = work.dropna(subset=[date_col])
        value_col = "Records"
    else:
        work[metric] = _num(work[metric])
        work = work.dropna(subset=[date_col, metric])
        value_col = metric
    if work.empty:
        result.ok = False
        result.answer = "No valid dated records were available for the trend."
        result.detail = "Rows with missing or invalid dates were excluded."
        return result

    freq_label = {"D": "Daily", "W": "Weekly", "M": "Monthly", "Q": "Quarterly", "Y": "Yearly"}[freq]
    try:
        work["period"] = work[date_col].dt.to_period(freq)
        if count_mode:
            grouped = work.groupby("period").size().reset_index(name=value_col)
        else:
            grouped = work.groupby("period")[metric].agg(agg).reset_index()
    except Exception:
        work["period"] = work[date_col].dt.to_period("M")
        freq, freq_label = "M", "Monthly"
        if count_mode:
            grouped = work.groupby("period").size().reset_index(name=value_col)
        else:
            grouped = work.groupby("period")[metric].agg("sum").reset_index()
    grouped = grouped.sort_values("period").reset_index(drop=True)
    # Use period start timestamps as readable labels.
    try:
        grouped["Period"] = grouped["period"].dt.start_time
    except Exception:
        grouped["Period"] = grouped["period"].astype(str)
    grouped = grouped[["Period", value_col]]
    if len(grouped) > 500:
        grouped = grouped.tail(500)

    result.table = grouped
    result.records_used = len(work)
    peak_idx = grouped[value_col].idxmax()
    low_idx = grouped[value_col].idxmin()
    peak_period = _period_label(grouped.loc[peak_idx, "Period"], freq)
    peak_value = float(grouped.loc[peak_idx, value_col])
    low_period = _period_label(grouped.loc[low_idx, "Period"], freq)
    low_value = float(grouped.loc[low_idx, value_col])
    first = float(grouped.iloc[0][value_col])
    last = float(grouped.iloc[-1][value_col])
    change_pct = ((last - first) / abs(first) * 100) if first else None
    trend = "flat"
    if change_pct is not None:
        if change_pct > 1:
            trend = "rising"
        elif change_pct < -1:
            trend = "falling"

    if count_mode:
        result.answer = f"Peak {freq_label.lower()} record count was {int(peak_value):,} in {peak_period}."
    else:
        result.answer = f"Peak {freq_label.lower()} {humanize(metric)} was {format_value(peak_value, metric)} in {peak_period}."
    detail = f"{freq_label} {'COUNT' if count_mode else agg.upper()} across {len(grouped)} periods and {len(work):,} dated records."
    if change_pct is not None:
        detail += f" The series moved {change_pct:+.1f}% from {_period_label(grouped.iloc[0]['Period'], freq)} to {_period_label(grouped.iloc[-1]['Period'], freq)} ({trend})."
    result.detail = detail + _filter_note(labels)
    result.metrics = {
        "Periods": len(grouped),
        "Peak period": peak_period,
        "Peak value": peak_value,
        "Lowest period": low_period,
        "Lowest value": low_value,
        "First value": first,
        "Last value": last,
        "Trend": trend,
    }
    if change_pct is not None:
        result.metrics["Change %"] = round(change_pct, 2)
    result.chart = _chart(
        "line",
        x="Period",
        y=value_col,
        title=f"{freq_label} {'record count' if count_mode else humanize(metric)} trend",
    )
    if count_mode:
        result.formula = f"df.groupby(df['{date_col}'].dt.to_period('{freq}')).size()"
        result.explanation.extend(
            [
                f"Parsed '{date_col}' as dates and grouped into {freq_label.lower()} periods.",
                "No numeric metric was named, so matching rows were counted per period.",
                "Compared the first and last period to describe direction.",
            ]
        )
    else:
        result.formula = f"df.groupby(df['{date_col}'].dt.to_period('{freq}'))['{metric}'].{agg}()"
        result.explanation.extend(
            [
                f"Parsed '{date_col}' as dates and grouped into {freq_label.lower()} periods.",
                f"Aggregated '{metric}' with {agg.upper()}.",
                "Compared the first and last period to describe direction.",
            ]
        )
    return result


def _period_label(value: Any, freq: str) -> str:
    try:
        ts = pd.Timestamp(value)
        if freq == "Y":
            return str(ts.year)
        if freq == "Q":
            return f"{ts.year}-Q{ts.quarter}"
        if freq == "M":
            return ts.strftime("%Y-%m")
        return ts.strftime("%Y-%m-%d")
    except Exception:
        return str(value)


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------
def _distribution(plan: dict[str, Any], df: pd.DataFrame, profile: DatasetProfile, source: str) -> AnalysisResult:
    result = _base_result(plan, profile, source)
    filtered, labels = _apply_filters(df, plan)
    metric = plan["metric"]
    values = _num(filtered[metric]).replace([np.inf, -np.inf], np.nan).dropna()
    if values.empty:
        result.ok = False
        result.answer = f"No numeric values are available in '{humanize(metric)}'."
        return result
    bin_count = int(min(30, max(5, round(math.sqrt(len(values))))))
    counts, edges = np.histogram(values, bins=bin_count)
    table = pd.DataFrame(
        {
            "Bin": [f"{edges[i]:,.2f} – {edges[i + 1]:,.2f}" for i in range(len(counts))],
            "Count": counts,
        }
    )
    result.table = table
    result.records_used = len(values)
    result.metrics = {
        "Records": int(len(values)),
        "Mean": float(values.mean()),
        "Median": float(values.median()),
        "Std": float(values.std()) if len(values) > 1 else 0.0,
        "Min": float(values.min()),
        "Max": float(values.max()),
        "Skew": float(values.skew()) if len(values) > 2 else None,
    }
    result.answer = (
        f"{humanize(metric)} is centred at {format_value(values.mean(), metric)} "
        f"(median {format_value(values.median(), metric)})."
    )
    result.detail = (
        f"{len(values):,} valid values, standard deviation {format_value(values.std(), metric)}, "
        f"range {format_value(values.min(), metric)} to {format_value(values.max(), metric)}." + _filter_note(labels)
    )
    result.chart = _chart("histogram", x="Bin", y="Count", title=f"Distribution of {humanize(metric)}")
    result.formula = f"np.histogram(df['{metric}'].dropna(), bins={bin_count})"
    result.explanation.extend(
        [
            f"Selected numeric column '{metric}' and removed missing values.",
            f"Binned the values into {bin_count} equal-width intervals.",
            "Computed mean, median and standard deviation from the same series.",
        ]
    )
    return result


def _outliers(plan: dict[str, Any], df: pd.DataFrame, profile: DatasetProfile, source: str) -> AnalysisResult:
    result = _base_result(plan, profile, source)
    filtered, labels = _apply_filters(df, plan)
    metric = plan["metric"]
    values = _num(filtered[metric]).replace([np.inf, -np.inf], np.nan).dropna()
    if values.empty:
        result.ok = False
        result.answer = f"No numeric values are available in '{humanize(metric)}'."
        return result
    q1, q3 = np.percentile(values, [25, 75])
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    mask = (values < lower) | (values > upper)
    count = int(mask.sum())
    pct = count / len(values) * 100
    outlier_rows = filtered.loc[values[mask].index]
    keep = [metric]
    for col in profile.categorical_columns[:2]:
        if col not in keep:
            keep.append(col)
    result.table = outlier_rows[keep].head(50) if count else None
    result.records_used = len(values)
    result.metrics = {
        "Potential outliers": count,
        "Outlier %": round(pct, 2),
        "Q1": float(q1),
        "Q3": float(q3),
        "IQR": float(iqr),
        "Lower fence": float(lower),
        "Upper fence": float(upper),
    }
    if count:
        result.answer = (
            f"{count:,} potential outlier(s) detected in {humanize(metric)} "
            f"({pct:.2f}% of values) outside {format_value(lower, metric)} – {format_value(upper, metric)}."
        )
        result.detail = (
            f"Tukey's rule: Q1={format_value(q1, metric)}, Q3={format_value(q3, metric)}, IQR={format_value(iqr, metric)}. "
            "Values beyond 1.5 x IQR are flagged. This is a statistical signal, not proof of fraud or error." + _filter_note(labels)
        )
    else:
        result.answer = f"No values fall outside the 1.5 x IQR fences in {humanize(metric)}."
        result.detail = (
            f"Q1={format_value(q1, metric)}, Q3={format_value(q3, metric)}, IQR={format_value(iqr, metric)}. "
            "No statistical outliers were flagged." + _filter_note(labels)
        )
    sample = values.sample(min(len(values), 2000), random_state=42) if len(values) > 2000 else values
    result.chart = _chart("box", y=metric, title=f"Outlier scan: {humanize(metric)}", values=[float(v) for v in sample])
    result.formula = f"Q1, Q3 = df['{metric}'].quantile([.25, .75]); fences = Q1/Q3 ± 1.5*IQR"
    result.explanation.extend(
        [
            f"Selected numeric column '{metric}'.",
            "Computed quartiles and the interquartile range (IQR).",
            "Flagged values outside Q1 - 1.5*IQR and Q3 + 1.5*IQR.",
        ]
    )
    return result


def _correlation(plan: dict[str, Any], df: pd.DataFrame, profile: DatasetProfile, source: str) -> AnalysisResult:
    result = _base_result(plan, profile, source)
    filtered, labels = _apply_filters(df, plan)
    a, b = plan["metric"], plan["metric_2"]
    work = pd.DataFrame({"a": _num(filtered[a]), "b": _num(filtered[b])}).dropna()
    if len(work) < 2:
        result.ok = False
        result.answer = "Not enough complete pairs for a correlation."
        return result
    r = float(work["a"].corr(work["b"]))
    r = _clean_number(r)
    if r is None:
        result.ok = False
        result.answer = "Correlation could not be computed (constant or invalid values)."
        return result
    strength = "very weak"
    absr = abs(r)
    if absr >= 0.8:
        strength = "very strong"
    elif absr >= 0.6:
        strength = "strong"
    elif absr >= 0.4:
        strength = "moderate"
    elif absr >= 0.2:
        strength = "weak"
    direction = "positive" if r > 0 else ("negative" if r < 0 else "neutral")
    sample = work.sample(min(len(work), MAX_SCATTER_POINTS), random_state=42)
    result.table = sample.reset_index(drop=True)
    result.records_used = len(work)
    result.metrics = {
        "Pearson r": r,
        "R squared": r * r,
        "Pairs analysed": int(len(work)),
        "Strength": strength,
        "Direction": direction,
    }
    result.answer = f"{humanize(a)} and {humanize(b)} have a {strength} {direction} correlation (r = {r:.3f})."
    result.detail = (
        f"Pearson correlation computed on {len(work):,} complete pairs. "
        f"R² = {r * r:.3f}. Correlation does not imply causation." + _filter_note(labels)
    )
    result.chart = _chart("scatter", x="a", y="b", title=f"{humanize(a)} vs {humanize(b)}", x_label=humanize(a), y_label=humanize(b))
    result.formula = f"df['{a}'].corr(df['{b}'])"
    result.explanation.extend(
        [
            f"Selected numeric columns '{a}' and '{b}'.",
            f"Removed rows missing either value; {len(work):,} complete pairs remained.",
            "Computed Pearson correlation and R-squared.",
        ]
    )
    return result


def _column_profile(plan: dict[str, Any], df: pd.DataFrame, profile: DatasetProfile, source: str) -> AnalysisResult:
    result = _base_result(plan, profile, source)
    filtered, labels = _apply_filters(df, plan)
    col = plan.get("metric")
    if col not in filtered.columns:
        result.ok = False
        result.answer = "That column is not available."
        return result
    series = filtered[col]
    cp = profile.column(col)
    if cp and cp.kind == "numeric":
        values = _num(series).replace([np.inf, -np.inf], np.nan).dropna()
        if values.empty:
            result.ok = False
            result.answer = f"No numeric values in '{humanize(col)}'."
            return result
        result.answer = f"{humanize(col)}: mean {format_value(values.mean(), col)}, median {format_value(values.median(), col)}."
        result.detail = (
            f"{len(values):,} valid values; min {format_value(values.min(), col)}, max {format_value(values.max(), col)}, "
            f"standard deviation {format_value(values.std(), col)}." + _filter_note(labels)
        )
        result.metrics = {
            "Count": int(len(values)),
            "Mean": float(values.mean()),
            "Median": float(values.median()),
            "Min": float(values.min()),
            "Max": float(values.max()),
            "Std": float(values.std()) if len(values) > 1 else 0.0,
        }
        hist, edges = np.histogram(values, bins=min(20, max(5, int(math.sqrt(len(values))))))
        result.table = pd.DataFrame(
            {"Bin": [f"{edges[i]:,.2f} – {edges[i + 1]:,.2f}" for i in range(len(hist))], "Count": hist}
        )
        result.chart = _chart("histogram", x="Bin", y="Count", title=f"Distribution of {humanize(col)}")
        result.formula = f"df['{col}'].describe()"
    else:
        vc = series.astype(str).value_counts().head(20)
        total = int(series.notna().sum())
        result.table = pd.DataFrame(
            {
                col: vc.index,
                "Count": vc.values,
                "Percent": (vc.values / max(total, 1) * 100).round(2),
            }
        )
        top = vc.index[0] if len(vc) else None
        result.answer = (
            f"'{humanize(col)}' has {series.nunique(dropna=True):,} distinct values; most common is '{top}'."
            if top is not None
            else f"'{humanize(col)}' has no non-null values."
        )
        result.detail = f"Based on {total:,} non-null records; {int(series.isna().sum()):,} missing." + _filter_note(labels)
        result.metrics = {
            "Unique values": int(series.nunique(dropna=True)),
            "Non-null": total,
            "Missing": int(series.isna().sum()),
            "Top value": str(top) if top is not None else None,
        }
        if top is not None:
            result.metrics["Top count"] = int(vc.iloc[0])
        result.chart = _chart("bar", x=col, y="Count", title=f"Frequency of {humanize(col)}", orientation="h")
        result.formula = f"df['{col}'].value_counts()"
    result.records_used = len(filtered)
    result.explanation.extend(
        [
            f"Profiled column '{col}' as a {cp.kind if cp else 'column'}.",
            "Computed summary statistics or value frequencies from the active rows.",
        ]
    )
    return result
