"""Schema inference and dataset profiling.

Types are inferred conservatively. We never silently drop rows or rewrite
values; date columns are the only values the loader converts, and only when
the conversion is unambiguous.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

NUMERIC = "numeric"
DATE = "date"
CATEGORICAL = "categorical"
TEXT = "text"
BOOLEAN = "boolean"
ID = "id"

_DATE_NAME_HINTS = (
    "date",
    "time",
    "day",
    "month",
    "year",
    "period",
    "timestamp",
    "created_at",
    "updated_at",
    "signup",
    "hire",
    "launch",
    "dispatch",
    "listing",
    "trade",
)
_ID_NAME_HINTS = ("id", "uuid", "code", "number", "no")
_NUMERIC_NAME_HINTS = (
    "revenue",
    "sales",
    "profit",
    "cost",
    "price",
    "amount",
    "salary",
    "spend",
    "mrr",
    "bill",
    "volume",
    "quantity",
    "units",
    "discount",
    "score",
    "rating",
    "age",
    "days",
    "seats",
    "fee",
    "tax",
    "total",
    "value",
    "count",
    "roas",
    "percent",
    "rate",
)


def is_numeric_col(series: pd.Series) -> bool:
    try:
        return pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)
    except Exception:
        return False


def is_date_col(series: pd.Series) -> bool:
    try:
        return pd.api.types.is_datetime64_any_dtype(series)
    except Exception:
        return False


def _looks_like_date(series: pd.Series, name: str) -> bool:
    if is_date_col(series):
        return True
    if is_numeric_col(series) or pd.api.types.is_bool_dtype(series):
        return False
    lname = str(name).lower()
    hinted = any(h in lname for h in _DATE_NAME_HINTS)
    sample = series.dropna().astype(str).head(40)
    if sample.empty:
        return False
    # Pure numeric strings (e.g. a year column) should not become timestamps.
    numeric_ratio = pd.to_numeric(sample, errors="coerce").notna().mean()
    if numeric_ratio > 0.9:
        return False
    try:
        parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
    except (TypeError, ValueError):
        parsed = pd.to_datetime(sample, errors="coerce")
    ratio = float(parsed.notna().mean())
    if hinted and ratio >= 0.6:
        return True
    # Unhinted columns need a very strong signal.
    separators = sample.str.contains(r"[-/]", regex=True).mean()
    return ratio >= 0.88 and separators >= 0.6


def classify_column(name: str, series: pd.Series) -> str:
    """Infer a practical analytical type for one column."""
    lname = str(name).strip().lower()
    if is_date_col(series) or _looks_like_date(series, name):
        return DATE
    if is_numeric_col(series):
        # Identifier-looking numeric columns are still numeric, but flagged as ID
        # only when the name is unmistakable.
        if lname in {"id", "_id"} or lname.endswith("_id") or lname.endswith("id"):
            return ID
        return NUMERIC
    if pd.api.types.is_bool_dtype(series):
        return BOOLEAN
    non_null = series.dropna()
    if non_null.empty:
        return CATEGORICAL
    if lname in {"id", "_id", "uuid"} or lname.endswith("_id") or lname.endswith("id"):
        return ID
    unique = non_null.nunique()
    ratio = unique / max(len(non_null), 1)
    avg_len = float(non_null.astype(str).str.len().mean())
    if unique > 60 and ratio > 0.9 and avg_len > 24:
        return TEXT
    if hinted_numeric_name(lname) and len(non_null) > 0:
        coerced = pd.to_numeric(non_null.astype(str).str.replace(r"[,$%]", "", regex=True), errors="coerce")
        if coerced.notna().mean() >= 0.9:
            # Keep the original values. The executor coerces on demand.
            return NUMERIC
    return CATEGORICAL


def hinted_numeric_name(name: str) -> bool:
    return any(h in name for h in _NUMERIC_NAME_HINTS)


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    kind: str
    non_null: int
    missing: int
    missing_pct: float
    unique: int
    sample: list[str] = field(default_factory=list)
    top_values: list[tuple[str, int]] = field(default_factory=list)
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    q1: float | None = None
    q3: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "dtype": self.dtype,
            "kind": self.kind,
            "non_null": self.non_null,
            "missing": self.missing,
            "missing_pct": round(self.missing_pct, 2),
            "unique": self.unique,
            "sample": self.sample,
            "top_values": self.top_values,
            "min": self.min,
            "max": self.max,
            "mean": self.mean,
            "median": self.median,
            "std": self.std,
            "q1": self.q1,
            "q3": self.q3,
        }


@dataclass
class DatasetProfile:
    rows: int
    columns: int
    missing_cells: int
    duplicate_rows: int
    memory_bytes: int
    column_profiles: list[ColumnProfile]
    warnings: list[str] = field(default_factory=list)
    name: str = "dataset"

    @property
    def all_columns(self) -> list[str]:
        return [c.name for c in self.column_profiles]

    @property
    def numeric_columns(self) -> list[str]:
        return [c.name for c in self.column_profiles if c.kind == NUMERIC]

    @property
    def categorical_columns(self) -> list[str]:
        return [c.name for c in self.column_profiles if c.kind in (CATEGORICAL, BOOLEAN)]

    @property
    def date_columns(self) -> list[str]:
        return [c.name for c in self.column_profiles if c.kind == DATE]

    @property
    def id_columns(self) -> list[str]:
        return [c.name for c in self.column_profiles if c.kind == ID]

    def column(self, name: str) -> ColumnProfile | None:
        for c in self.column_profiles:
            if c.name == name:
                return c
        return None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "rows": self.rows,
            "columns": self.columns,
            "missing_cells": self.missing_cells,
            "duplicate_rows": self.duplicate_rows,
            "memory_bytes": self.memory_bytes,
            "numeric_columns": self.numeric_columns,
            "categorical_columns": self.categorical_columns,
            "date_columns": self.date_columns,
            "id_columns": self.id_columns,
            "column_profiles": [c.as_dict() for c in self.column_profiles],
            "warnings": self.warnings,
        }


def _numeric_series(df: pd.DataFrame, name: str) -> pd.Series:
    series = df[name]
    if is_numeric_col(series):
        return series
    return pd.to_numeric(
        series.astype(str).str.replace(r"[,$%]", "", regex=True).str.strip(),
        errors="coerce",
    )


def profile_dataset(df: pd.DataFrame, name: str = "dataset", warnings: list[str] | None = None) -> DatasetProfile:
    cols: list[ColumnProfile] = []
    for col in df.columns:
        series = df[col]
        kind = classify_column(str(col), series)
        non_null = int(series.notna().sum())
        missing = int(series.isna().sum())
        missing_pct = (missing / len(df) * 100.0) if len(df) else 0.0
        try:
            unique = int(series.nunique(dropna=True))
        except Exception:
            unique = 0
        sample: list[str] = []
        for value in series.dropna().head(3):
            text = str(value)
            sample.append(text[:80])
        top_values: list[tuple[str, int]] = []
        if kind in (CATEGORICAL, BOOLEAN, ID):
            try:
                vc = series.astype(str).value_counts().head(8)
                top_values = [(str(k), int(v)) for k, v in vc.items()]
            except Exception:
                top_values = []

        cp = ColumnProfile(
            name=str(col),
            dtype=str(series.dtype),
            kind=kind,
            non_null=non_null,
            missing=missing,
            missing_pct=missing_pct,
            unique=unique,
            sample=sample,
            top_values=top_values,
        )
        if kind == NUMERIC:
            numeric = _numeric_series(df, str(col)).replace([np.inf, -np.inf], np.nan).dropna()
            if not numeric.empty:
                cp.min = float(numeric.min())
                cp.max = float(numeric.max())
                cp.mean = float(numeric.mean())
                cp.median = float(numeric.median())
                cp.std = float(numeric.std()) if len(numeric) > 1 else 0.0
                cp.q1 = float(numeric.quantile(0.25))
                cp.q3 = float(numeric.quantile(0.75))
        cols.append(cp)

    dupes = int(df.duplicated().sum()) if len(df) else 0
    mem = int(df.memory_usage(deep=True).sum()) if len(df) else 0
    return DatasetProfile(
        rows=len(df),
        columns=len(df.columns),
        missing_cells=int(df.isna().sum().sum()) if len(df) else 0,
        duplicate_rows=dupes,
        memory_bytes=mem,
        column_profiles=cols,
        warnings=warnings or [],
        name=name,
    )
