"""Strict validation of structured analysis plans.

No generated code, SQL or expressions reach the executor. Only whitelisted
intents, aggregations, chart types and existing columns are accepted.
"""

from __future__ import annotations

from typing import Any

from .schema import DatasetProfile
from .text import humanize


class PlanValidationError(Exception):
    pass


ALLOWED_INTENTS = {
    "aggregate",
    "group_aggregation",
    "ranking",
    "time_series",
    "distribution",
    "outliers",
    "correlation",
    "column_profile",
    "dataset_overview",
    "row_count",
    "column_count",
    "schema",
    "list_numeric",
    "list_categorical",
    "missing",
    "duplicates",
    "unique_count",
    "meta",
    "clarification",
}

ALLOWED_AGGREGATIONS = {"sum", "mean", "median", "min", "max", "count", "std", "var", "nunique", "range"}
ALLOWED_CHARTS = {"kpi", "bar", "line", "pie", "scatter", "histogram", "box", "table", "none"}
ALLOWED_SORTS = {"asc", "desc", None}
ALLOWED_FREQUENCIES = {"D", "W", "M", "Q", "Y"}
ALLOWED_FILTER_OPS = {"==", "!=", ">", ">=", "<", "<=", "year==", "contains"}
NON_NUMERIC_AGGREGATIONS = {"count", "nunique"}

MAX_LIMIT = 1000


def _check_columns(plan: dict[str, Any], profile: DatasetProfile) -> None:
    valid = set(profile.all_columns)
    numeric = set(profile.numeric_columns)
    dates = set(profile.date_columns)

    metric = plan.get("metric")
    if metric is not None and metric not in valid:
        raise PlanValidationError(f"Unknown metric column: {metric}")
    metric_2 = plan.get("metric_2")
    if metric_2 is not None and metric_2 not in valid:
        raise PlanValidationError(f"Unknown second metric column: {metric_2}")
    group = plan.get("group")
    if group is not None and group not in valid:
        raise PlanValidationError(f"Unknown grouping column: {group}")
    date_col = plan.get("date_column")
    if date_col is not None and date_col not in valid:
        raise PlanValidationError(f"Unknown date column: {date_col}")

    intent = plan.get("intent")
    aggregation = plan.get("aggregation")
    if intent in ("aggregate", "group_aggregation", "ranking", "time_series", "distribution", "column_profile"):
        if metric and aggregation and aggregation not in NON_NUMERIC_AGGREGATIONS and metric not in numeric:
            # Numeric-looking object columns are accepted; executor coerces them.
            cp = profile.column(metric)
            if cp is None or cp.kind != "numeric":
                raise PlanValidationError(f"Column '{metric}' is not numeric and cannot be {aggregation}ed.")
    if intent == "correlation":
        if not metric or not metric_2:
            raise PlanValidationError("Correlation needs two numeric columns.")
        if metric not in numeric or metric_2 not in numeric:
            raise PlanValidationError("Correlation columns must be numeric.")
        if metric == metric_2:
            raise PlanValidationError("Correlation needs two different columns.")
    if intent == "time_series":
        if not date_col or date_col not in dates:
            raise PlanValidationError("Time-series analysis needs a valid date column.")
        if not plan.get("frequency"):
            raise PlanValidationError("Time-series analysis needs a frequency.")
    if intent == "unique_count" and not (metric or group):
        raise PlanValidationError("Unique-count needs a column.")

    for f in plan.get("filters") or []:
        if not isinstance(f, dict):
            raise PlanValidationError("Malformed filter entry.")
        col = f.get("column")
        op = f.get("op")
        if col not in valid:
            raise PlanValidationError(f"Filter references unknown column: {col}")
        if op not in ALLOWED_FILTER_OPS:
            raise PlanValidationError(f"Unsupported filter operator: {op}")
        if "value" not in f:
            raise PlanValidationError("Filter is missing a value.")
        value = f["value"]
        if isinstance(value, str) and len(value) > 200:
            raise PlanValidationError("Filter value is too long.")
        cp = profile.column(col)
        if cp and cp.kind == "numeric" and op not in ("==", "!=", ">", ">=", "<", "<=", "contains"):
            raise PlanValidationError(f"Invalid numeric filter operator: {op}")


def validate_plan(plan: dict[str, Any], profile: DatasetProfile) -> dict[str, Any]:
    if not isinstance(plan, dict):
        raise PlanValidationError("Plan must be an object.")
    intent = plan.get("intent")
    if intent not in ALLOWED_INTENTS:
        raise PlanValidationError(f"Unsupported intent: {intent}")
    if plan.get("chart") not in ALLOWED_CHARTS:
        raise PlanValidationError(f"Unsupported chart type: {plan.get('chart')}")
    aggregation = plan.get("aggregation")
    if aggregation is not None and aggregation not in ALLOWED_AGGREGATIONS:
        raise PlanValidationError(f"Unsupported aggregation: {aggregation}")
    if plan.get("sort") not in ALLOWED_SORTS:
        raise PlanValidationError(f"Unsupported sort direction: {plan.get('sort')}")
    frequency = plan.get("frequency")
    if frequency is not None and frequency not in ALLOWED_FREQUENCIES:
        raise PlanValidationError(f"Unsupported frequency: {frequency}")
    limit = plan.get("limit")
    if limit is not None:
        if not isinstance(limit, int) or isinstance(limit, bool):
            raise PlanValidationError("Limit must be an integer.")
        if limit < 1 or limit > MAX_LIMIT:
            raise PlanValidationError(f"Limit must be between 1 and {MAX_LIMIT}.")
    filters = plan.get("filters", [])
    if filters is None:
        filters = []
    if not isinstance(filters, list):
        raise PlanValidationError("Filters must be a list.")
    if len(filters) > 4:
        raise PlanValidationError("Too many filters.")

    _check_columns(plan, profile)

    if intent in ("aggregate", "group_aggregation", "ranking", "time_series") and not aggregation:
        raise PlanValidationError("This intent requires an aggregation.")
    if intent in ("group_aggregation", "ranking") and not plan.get("group"):
        raise PlanValidationError("This intent requires a grouping column.")
    if intent in ("aggregate", "distribution", "outliers") and not plan.get("metric"):
        raise PlanValidationError("This intent requires a metric column.")

    # Normalise and clamp trusted fields.
    plan["limit"] = limit
    plan["filters"] = filters
    plan["sort"] = plan.get("sort")
    return plan


def describe_validation(plan: dict[str, Any]) -> str:
    """Human-readable summary used by the explainability panel."""
    parts = [f"Intent: {str(plan.get('intent')).replace('_', ' ')}"]
    if plan.get("metric"):
        parts.append(f"Metric: {humanize(plan['metric'])}")
    if plan.get("group"):
        parts.append(f"Group: {humanize(plan['group'])}")
    if plan.get("date_column"):
        parts.append(f"Date: {humanize(plan['date_column'])}")
    if plan.get("aggregation"):
        parts.append(f"Aggregation: {plan['aggregation'].upper()}")
    if plan.get("filters"):
        parts.append("Filters: " + "; ".join(f.get("label", "") for f in plan["filters"]))
    return " | ".join(parts)
