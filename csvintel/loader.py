"""CSV parsing with validation, delimiter detection and safe date inference."""

from __future__ import annotations

import csv
import io
import os
import re
from dataclasses import dataclass, field
from typing import BinaryIO

import pandas as pd

MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 MB
_DATE_NAME_HINTS = (
    "date",
    "time",
    "day",
    "month",
    "year",
    "period",
    "timestamp",
    "signup",
    "hire",
    "launch",
    "dispatch",
    "listing",
    "trade",
)


class DatasetLoadError(Exception):
    """Raised when an uploaded CSV cannot be parsed safely."""


@dataclass
class LoadReport:
    rows: int
    columns: int
    delimiter: str
    encoding: str
    duplicate_headers: list[str] = field(default_factory=list)
    renamed_headers: dict[str, str] = field(default_factory=dict)
    parsed_date_columns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "rows": self.rows,
            "columns": self.columns,
            "delimiter": self.delimiter,
            "encoding": self.encoding,
            "duplicate_headers": self.duplicate_headers,
            "renamed_headers": self.renamed_headers,
            "parsed_date_columns": self.parsed_date_columns,
            "warnings": self.warnings,
        }


def _decode(data: bytes) -> tuple[str, str]:
    if not data:
        raise DatasetLoadError("The uploaded file is empty.")
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = data.decode(encoding)
            if "\x00" in text:
                raise DatasetLoadError("The file appears to be binary, not a CSV.")
            return text, encoding
        except UnicodeDecodeError:
            continue
    raise DatasetLoadError("Could not decode the file. Please upload a UTF-8 CSV.")


def detect_delimiter(text: str) -> str:
    sample = "\n".join(text.splitlines()[:30])
    if not sample.strip():
        return ","
    candidates = [",", ";", "\t", "|"]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        if dialect.delimiter in candidates:
            return dialect.delimiter
    except csv.Error:
        pass
    # Fall back to the character with the most consistent per-line count.
    best, best_score = ",", -1.0
    lines = [ln for ln in sample.splitlines() if ln.strip()][:20]
    for delim in candidates:
        counts = [ln.count(delim) for ln in lines]
        if not counts or max(counts) == 0:
            continue
        mode = max(set(counts), key=counts.count)
        consistency = counts.count(mode) / len(counts)
        score = consistency * mode
        if score > best_score:
            best, best_score = delim, score
    return best


def _sanitize_headers(headers: list[str]) -> tuple[list[str], list[str], dict[str, str]]:
    cleaned: list[str] = []
    seen: dict[str, int] = {}
    duplicates: list[str] = []
    renamed: dict[str, str] = {}
    for idx, raw in enumerate(headers):
        name = re.sub(r"\s+", " ", str(raw).replace("\n", " ").replace("\r", " ")).strip()
        if not name:
            name = f"column_{idx + 1}"
        base = name
        if base in seen:
            if base not in duplicates:
                duplicates.append(base)
            seen[base] += 1
            name = f"{base}_{seen[base]}"
            renamed[base] = name
        else:
            seen[base] = 1
        cleaned.append(name)
    return cleaned, duplicates, renamed


def _parse_each_date_column(df: pd.DataFrame) -> pd.DataFrame:
    parsed: list[str] = []
    for col in df.columns:
        lname = str(col).lower()
        series = df[col]
        if pd.api.types.is_datetime64_any_dtype(series):
            parsed.append(str(col))
            continue
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
            continue
        hinted = any(h in lname for h in _DATE_NAME_HINTS)
        non_null = series.dropna().astype(str)
        if non_null.empty:
            continue
        # Avoid turning plain years such as 2024 into timestamps.
        if pd.to_numeric(non_null.head(50), errors="coerce").notna().mean() > 0.9:
            continue
        try:
            converted = pd.to_datetime(series, errors="coerce", format="mixed")
        except (TypeError, ValueError):
            converted = pd.to_datetime(series, errors="coerce")
        ratio = float(converted.notna().mean())
        if (hinted and ratio >= 0.6) or ratio >= 0.95:
            df[col] = converted
            parsed.append(str(col))
    return df


def parse_csv_bytes(data: bytes, name: str = "uploaded.csv") -> tuple[pd.DataFrame, LoadReport]:
    """Parse CSV bytes into a DataFrame without dropping any data rows."""
    if len(data) > MAX_FILE_BYTES:
        raise DatasetLoadError(
            f"File is {len(data) / (1024 * 1024):.1f} MB. The limit is 50 MB for this local prototype."
        )
    text, encoding = _decode(data)
    delimiter = detect_delimiter(text)
    warnings: list[str] = []

    try:
        # Read the header ourselves so duplicate/blank names can be reported.
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        raw_headers = next(reader)
    except StopIteration:
        raise DatasetLoadError("The CSV has no header row.")

    headers, duplicates, renamed = _sanitize_headers(raw_headers)
    if duplicates:
        warnings.append(
            "Duplicate headers were renamed to keep every column addressable: "
            + ", ".join(sorted(set(renamed.values())))
        )

    try:
        df = pd.read_csv(
            io.StringIO(text),
            sep=delimiter,
            header=0,
            skip_blank_lines=True,
            keep_default_na=True,
        )
    except Exception as exc:
        raise DatasetLoadError(f"CSV parsing failed: {exc}") from exc

    if df.empty and len(df.columns) == 0:
        raise DatasetLoadError("The CSV contains no readable columns.")
    if len(df) == 0:
        raise DatasetLoadError("The CSV contains headers but no data rows.")
    if len(df) > 1_000_000:
        warnings.append("Large dataset detected. Charts and previews are sampled for performance.")

    # pandas mangles duplicate headers on its own. Replace with our sanitized
    # names so the UI and the planner refer to the same schema.
    if len(df.columns) == len(headers):
        df.columns = headers
    elif df.columns.duplicated().any():
        df.columns = _sanitize_headers([str(c) for c in df.columns])[0]

    df = _parse_each_date_column(df)

    # Drop fully empty trailing rows only; never drop rows with data.
    df = df.dropna(how="all")
    if df.empty:
        raise DatasetLoadError("The CSV contains no rows with data.")

    report = LoadReport(
        rows=len(df),
        columns=len(df.columns),
        delimiter=delimiter,
        encoding=encoding,
        duplicate_headers=duplicates,
        renamed_headers=renamed,
        parsed_date_columns=[str(c) for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])],
        warnings=warnings,
    )
    _ = name
    return df, report


def read_csv_path(path: str, name: str | None = None) -> tuple[pd.DataFrame, LoadReport]:
    if not os.path.exists(path):
        raise DatasetLoadError(f"Dataset file not found: {path}")
    with open(path, "rb") as handle:
        data = handle.read()
    return parse_csv_bytes(data, name=name or os.path.basename(path))


def parse_uploaded_file(uploaded: BinaryIO, name: str | None = None) -> tuple[pd.DataFrame, LoadReport]:
    data = uploaded.read()
    if isinstance(data, str):
        data = data.encode("utf-8")
    return parse_csv_bytes(data, name=name or getattr(uploaded, "name", "uploaded.csv"))
