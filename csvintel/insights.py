"""Deterministic, explainable dataset insights. No causal claims, no LLM."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .executor import _num
from .planner import primary_date, primary_group, primary_metric
from .schema import DatasetProfile
from .text import format_value, humanize, is_currency_column


def generate_insights(df: pd.DataFrame, profile: DatasetProfile, limit: int = 12) -> list[dict[str, Any]]:
    insights: list[dict[str, Any]] = []
    metric = primary_metric(profile)
    group = primary_group(profile)
    date_col = primary_date(profile)

    insights.append(
        {
            "title": "Dataset composition",
            "detail": (
                f"{profile.rows:,} records × {profile.columns} columns. "
                f"{len(profile.numeric_columns)} numeric, {len(profile.categorical_columns)} categorical, "
                f"{len(profile.date_columns)} date."
            ),
            "kind": "overview",
            "evidence": ["len(df)", "schema type inference"],
        }
    )

    if metric and group:
        try:
            series = _num(df[metric]).groupby(df[group]).sum().sort_values(ascending=False)
            series = series.dropna()
            if len(series):
                total = float(series.sum())
                top_name, top_value = str(series.index[0]), float(series.iloc[0])
                low_name, low_value = str(series.index[-1]), float(series.iloc[-1])
                share = (top_value / total * 100) if total else 0.0
                insights.append(
                    {
                        "title": f"{humanize(group)} leader",
                        "detail": (
                            f"{top_name} has the highest total {humanize(metric)} at {format_value(top_value, metric)} "
                            f"({share:.1f}% of the grouped total)."
                        ),
                        "kind": "category",
                        "metric": metric,
                        "value": top_value,
                        "share": round(share, 2),
                        "evidence": [f"groupby({group}).sum({metric})"],
                    }
                )
                insights.append(
                    {
                        "title": f"Lowest {humanize(group)}",
                        "detail": f"{low_name} has the lowest total {humanize(metric)} at {format_value(low_value, metric)}.",
                        "kind": "category",
                        "metric": metric,
                        "value": low_value,
                        "evidence": [f"groupby({group}).sum({metric})"],
                    }
                )
                if share >= 50 and len(series) > 1:
                    insights.append(
                        {
                            "title": "Concentration risk signal",
                            "detail": (
                                f"{top_name} contributes {share:.1f}% of total {humanize(metric)}. "
                                "This is a concentration observation, not a causal explanation."
                            ),
                            "kind": "concentration",
                            "metric": metric,
                            "value": round(share, 2),
                            "evidence": ["share = top group / grouped total"],
                        }
                    )
        except Exception:
            pass

    if metric and date_col:
        try:
            work = pd.DataFrame(
                {
                    "period": pd.to_datetime(df[date_col], errors="coerce").dt.to_period("M"),
                    "value": _num(df[metric]),
                }
            ).dropna()
            if len(work):
                agg = work.groupby("period")["value"].sum().sort_index()
                if len(agg) >= 2:
                    first, last = float(agg.iloc[0]), float(agg.iloc[-1])
                    change = ((last - first) / abs(first) * 100) if first else 0.0
                    direction = "increased" if change > 1 else ("decreased" if change < -1 else "stayed broadly flat")
                    peak_period = str(agg.idxmax())
                    insights.append(
                        {
                            "title": "Time trend",
                            "detail": (
                                f"Monthly {humanize(metric)} {direction} {change:+.1f}% from "
                                f"{agg.index[0]} to {agg.index[-1]}. Peak month: {peak_period}."
                            ),
                            "kind": "trend",
                            "metric": metric,
                            "value": round(change, 2),
                            "evidence": [f"monthly sum({metric}); first vs last period"],
                        }
                    )
        except Exception:
            pass

    if profile.missing_cells:
        worst = max(profile.column_profiles, key=lambda c: c.missing)
        insights.append(
            {
                "title": "Missing data",
                "detail": (
                    f"{profile.missing_cells:,} cells are missing. The most affected column is "
                    f"{humanize(worst.name)} ({worst.missing:,} missing, {worst.missing_pct:.1f}%)."
                ),
                "kind": "quality",
                "value": profile.missing_cells,
                "evidence": ["df.isna().sum()"],
            }
        )
    else:
        insights.append(
            {
                "title": "Data completeness",
                "detail": "No missing cells were detected in the active dataset.",
                "kind": "quality",
                "value": 0,
                "evidence": ["df.isna().sum().sum() == 0"],
            }
        )

    if profile.duplicate_rows:
        insights.append(
            {
                "title": "Duplicate rows",
                "detail": f"{profile.duplicate_rows:,} fully duplicated row(s) were found ({profile.duplicate_rows / max(profile.rows, 1) * 100:.2f}% of rows).",
                "kind": "quality",
                "value": profile.duplicate_rows,
                "evidence": ["df.duplicated().sum()"],
            }
        )

    if metric:
        try:
            values = _num(df[metric]).replace([np.inf, -np.inf], np.nan).dropna()
            if len(values) > 3:
                q1, q3 = np.percentile(values, [25, 75])
                iqr = q3 - q1
                count = int(((values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr)).sum())
                if count:
                    insights.append(
                        {
                            "title": "Potential outliers",
                            "detail": (
                                f"{count:,} value(s) in {humanize(metric)} fall outside Tukey's 1.5×IQR fences. "
                                "These are statistical flags, not confirmed errors."
                            ),
                            "kind": "outlier",
                            "metric": metric,
                            "value": count,
                            "evidence": [f"IQR scan on {metric}"],
                        }
                    )
        except Exception:
            pass

    # Strongest numeric correlation.
    numeric = profile.numeric_columns
    if len(numeric) >= 2:
        best = None
        best_r = 0.0
        for i in range(min(len(numeric), 8)):
            for j in range(i + 1, min(len(numeric), 8)):
                try:
                    r = _num(df[numeric[i]]).corr(_num(df[numeric[j]]))
                except Exception:
                    continue
                if pd.notna(r) and abs(float(r)) > abs(best_r):
                    best, best_r = (numeric[i], numeric[j]), float(r)
        if best and abs(best_r) >= 0.5:
            strength = "strong" if abs(best_r) >= 0.7 else "moderate"
            relation = "positive" if best_r > 0 else "negative"
            insights.append(
                {
                    "title": "Numeric relationship",
                    "detail": (
                        f"{humanize(best[0])} and {humanize(best[1])} show a {strength} {relation} "
                        f"Pearson correlation (r = {best_r:.3f}). Correlation does not imply causation."
                    ),
                    "kind": "correlation",
                    "value": round(best_r, 3),
                    "evidence": [f"corr({best[0]}, {best[1]})"],
                }
            )

    if profile.categorical_columns:
        try:
            col = profile.categorical_columns[0]
            vc = df[col].astype(str).value_counts()
            if len(vc):
                top_value = str(vc.index[0])
                insights.append(
                    {
                        "title": "Most common category",
                        "detail": (
                            f"The most frequent value in {humanize(col)} is '{top_value}' "
                            f"with {int(vc.iloc[0]):,} records ({vc.iloc[0] / max(len(df), 1) * 100:.1f}%)."
                        ),
                        "kind": "distribution",
                        "value": int(vc.iloc[0]),
                        "evidence": [f"value_counts({col})"],
                    }
                )
        except Exception:
            pass

    if metric:
        currency = is_currency_column(metric)
        insights.append(
            {
                "title": "Primary metric range",
                "detail": (
                    f"{humanize(metric)} ranges from {format_value(_num(df[metric]).min(), metric)} to "
                    f"{format_value(_num(df[metric]).max(), metric)}. "
                    f"The dataset is {'currency-denominated' if currency else 'numeric'}."
                ),
                "kind": "distribution",
                "metric": metric,
                "evidence": [f"min/max({metric})"],
            }
        )

    return insights[:limit]
