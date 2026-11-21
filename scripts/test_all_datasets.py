import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import numpy as np

from csvintel.loader import read_csv_path
from csvintel.schema import profile_dataset, is_numeric_col, is_date_col, classify_column
from csvintel.planner import build_plan, primary_metric, primary_group, primary_date
from csvintel.validator import validate_plan
from csvintel.executor import execute_plan

print("=" * 70)
print("COMPREHENSIVE AUTOMATED VERIFICATION SUITE ACROSS ALL 11 DATASETS")
print("=" * 70)

datasets_to_test = [
    ("Retail Demo", "sample_retail_sales_2024.csv"),
    ("01 - E-Commerce", "datasets/01_ecommerce_orders.csv"),
    ("02 - SaaS", "datasets/02_saas_subscriptions.csv"),
    ("03 - Healthcare", "datasets/03_healthcare_admissions.csv"),
    ("04 - Finance", "datasets/04_finance_banking_transactions.csv"),
    ("05 - HR Workforce", "datasets/05_hr_workforce_salaries.csv"),
    ("06 - Marketing", "datasets/06_digital_marketing_campaigns.csv"),
    ("07 - Logistics", "datasets/07_supply_chain_logistics.csv"),
    ("08 - Real Estate", "datasets/08_real_estate_property_sales.csv"),
    ("09 - Streaming", "datasets/09_streaming_media_viewership.csv"),
    ("10 - Crypto Market", "datasets/10_cryptocurrency_market_daily.csv")
]

total_tests = 0
passed_tests = 0

for label, filepath in datasets_to_test:
    print(f"\n📂 Testing Dataset: [{label}] -> {filepath}")
    assert os.path.exists(filepath), f"File {filepath} does not exist!"

    df, report = read_csv_path(filepath)
    num_rows, num_cols = len(df), len(df.columns)
    print(f"   Loaded: {num_rows:,} rows, {num_cols} columns")

    # 1. Test Schema Type Inference
    profile = profile_dataset(df, name=label)
    schema_types = {}
    try:
        for c in df.columns:
            kind = classify_column(c, df[c])
            schema_types[c] = kind
        print(f"   ✓ Schema inference passed ({len(schema_types)} columns classified without error)")
        passed_tests += 1
    except Exception as e:
        print(f"   ❌ FAILED Schema inference: {e}")
    total_tests += 1

    primary_num = primary_metric(profile) or (profile.numeric_columns[0] if profile.numeric_columns else None)
    primary_cat = primary_group(profile) or (profile.categorical_columns[0] if profile.categorical_columns else None)
    has_date = bool(profile.date_columns)

    if not primary_num:
        print(f"   ⚠️ Skipping numerical queries for {label}: no numeric columns found")
        continue

    # Test Queries Array
    queries = [
        ("Total / Sum", f"What is the total {primary_num}?"),
        ("Average / Mean", f"What is the average {primary_num}?"),
        ("Min / Max", f"What is the maximum {primary_num}?"),
        ("Outlier Detection", f"Are there any unusual values in {primary_num}?"),
        ("Missing Values Check", "Are there any missing values?"),
        ("Row Count", "How many records are there?"),
        ("Safe Fallback (Unsupported)", "What is the weather on Jupiter?"),
        ("Safe Clarification (Unknown Column)", "What is the total unknown_xyz_column?")
    ]

    if primary_cat:
        queries.extend([
            ("Ranking / Top", f"Which {primary_cat} has the highest {primary_num}?"),
            ("Comparison / Group-by", f"Compare {primary_num} across {primary_cat}"),
        ])

    if has_date:
        queries.append(("Time-Series Trend", f"Show monthly {primary_num} trends"))

    for q_type, q_text in queries:
        total_tests += 1
        try:
            plan = build_plan(q_text, df, profile)
            validate_plan(plan, profile)
            result = execute_plan(plan, df, profile)

            headline = result.answer
            details = result.detail
            formula = result.formula

            # Validation assertions
            assert headline is not None and len(headline) > 5, "Headline must not be empty"
            assert details is not None, "Details must not be empty"

            if q_type == "Safe Fallback (Unsupported)":
                assert result.intent in ("meta", "clarification"), f"Expected meta/clarification intent, got: {result.intent}"
                assert any(w in headline.lower() for w in ["outside", "not match", "could not", "scope", "clarif"]), f"Unexpected fallback message: {headline}"
                assert "$" not in headline, "Safe fallback must not fabricate dollar amounts"
            elif q_type == "Safe Clarification (Unknown Column)":
                assert result.intent == "clarification", f"Unknown column must return clarification, got: {result.intent}"
            elif q_type == "Total / Sum":
                expected_sum = df[primary_num].sum()
                val = result.metrics.get("Value", 0)
                assert np.isclose(val, expected_sum, rtol=1e-3) or np.isclose(val, expected_sum, atol=1e-2), f"Sum query {val} must match actual sum {expected_sum}"
            elif q_type == "Average / Mean":
                expected_mean = df[primary_num].mean()
                val = result.metrics.get("Value", 0)
                assert np.isclose(val, expected_mean, rtol=1e-3) or np.isclose(val, expected_mean, atol=1e-2), f"Mean query {val} must match actual mean {expected_mean}"
            elif q_type == "Row Count":
                val = result.metrics.get("Rows", result.metrics.get("Records", 0))
                assert val == num_rows, f"Row count {val} must match {num_rows}"

            passed_tests += 1
            print(f"   ✓ [{q_type}]: \"{q_text}\" -> PASSED")
        except Exception as e:
            print(f"   ❌ [{q_type}]: \"{q_text}\" -> FAILED with error: {e}")

print("\n" + "=" * 70)
print(f"VERIFICATION RESULTS: {passed_tests} / {total_tests} TESTS PASSED ({(passed_tests/total_tests)*100:.1f}%)")
print("=" * 70)

if passed_tests == total_tests:
    print("✨ ALL QUERIES, SCHEMAS, AND DATASETS PASSED WITH 100% SUCCESS! ✨\n")
    sys.exit(0)
else:
    sys.exit(1)
