"""CSV Intelligence AI - deterministic natural-language analysis engine.

The UI is a thin Streamlit layer. Everything that interprets a question,
validates a plan and calculates a result lives in this package so it can be
tested without a browser.
"""

from .schema import (
    ColumnProfile,
    DatasetProfile,
    classify_column,
    is_date_col,
    is_numeric_col,
    profile_dataset,
)
from .planner import build_plan, primary_metric
from .validator import validate_plan, PlanValidationError
from .executor import execute_plan, AnalysisResult
from .insights import generate_insights
from .loader import parse_csv_bytes, read_csv_path, DatasetLoadError
from .evaluation import run_benchmark
from .llm import llm_config, propose_plan, test_connection

__all__ = [
    "ColumnProfile",
    "DatasetProfile",
    "classify_column",
    "is_date_col",
    "is_numeric_col",
    "profile_dataset",
    "build_plan",
    "primary_metric",
    "validate_plan",
    "PlanValidationError",
    "execute_plan",
    "AnalysisResult",
    "generate_insights",
    "parse_csv_bytes",
    "read_csv_path",
    "DatasetLoadError",
    "run_benchmark",
    "llm_config",
    "propose_plan",
    "test_connection",
]
