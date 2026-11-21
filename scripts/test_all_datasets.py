import os
import sys
sys.path.insert(0, os.path.abspath("."))
import glob
import pandas as pd
import numpy as np

# Import core analytical engine functions directly from app
from app import analyze_query, get_col_type_label, load_csv_file, is_numeric_col, is_date_col, DATASET_OPTIONS

print("=" * 70)
print("COMPREHENSIVE AUTOMATED VERIFICATION SUITE ACROSS ALL 10 DATASETS")
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
    
    df = load_csv_file(filepath)
    num_rows, num_cols = len(df), len(df.columns)
    print(f"   Loaded: {num_rows:,} rows, {num_cols} columns")
    
    # 1. Test Schema Type Inference (Crucial StringDtype test)
    schema_types = {}
    try:
        for c in df.columns:
            t = get_col_type_label(df[c])
            schema_types[c] = t
        print(f"   ✓ Schema inference passed ({len(schema_types)} columns classified without StringDtype error)")
        passed_tests += 1
    except Exception as e:
        print(f"   ❌ FAILED Schema inference: {e}")
    total_tests += 1

    # Numeric & categorical detection
    num_cols_list = [c for c in df.columns if is_numeric_col(df[c])]
    cat_cols_list = [c for c in df.columns if not is_numeric_col(df[c]) and not is_date_col(df[c])]
    date_cols_list = [c for c in df.columns if is_date_col(df[c])]
    
    primary_num = num_cols_list[0] if num_cols_list else "value"
    primary_cat = cat_cols_list[0] if cat_cols_list else "category"

    # Test Queries Array
    queries = [
        ("Total / Sum", f"What is the total {primary_num}?"),
        ("Average / Mean", f"What is the average {primary_num}?"),
        ("Min / Max", f"What is the maximum {primary_num}?"),
        ("Ranking / Top", f"Which {primary_cat} has the highest {primary_num}?"),
        ("Comparison / Group-by", f"Compare {primary_num} across {primary_cat}"),
        ("Outlier Detection", "Are there any unusual patterns in this dataset?"),
        ("Missing Values Check", "Are there any missing values?"),
        ("Row Count", "How many records are there?"),
        ("Safe Fallback (Unsupported)", "What is the weather on Jupiter?")
    ]
    
    if date_cols_list:
        queries.append(("Time-Series Trend", f"Show monthly {primary_num} trends"))

    for q_type, q_text in queries:
        total_tests += 1
        try:
            headline, details, evidence, formula, fig, res_df, *rest = analyze_query(q_text, df)
            
            # Validation assertions
            assert headline is not None and len(headline) > 5, "Headline must not be empty"
            assert details is not None, "Details must not be empty"
            assert formula is not None, "Formula must not be empty"
            
            if q_type == "Safe Fallback (Unsupported)":
                assert any(w in headline.lower() for w in ["couldn't match", "not recognized", "outside the scope"]), f"Unsupported query must return safe fallback, got: {headline}"
                assert "$" not in headline, "Safe fallback must not fabricate dollar amounts"
            elif q_type == "Total / Sum":
                expected_sum = df[primary_num].sum()
                assert f"{expected_sum:,.0f}" in headline or f"{expected_sum:,.2f}" in headline or f"{int(expected_sum):,}" in headline, f"Sum query must match actual sum: {expected_sum}"
            elif q_type == "Average / Mean":
                expected_mean = df[primary_num].mean()
                assert f"{expected_mean:,.0f}" in headline or f"{expected_mean:,.2f}" in headline or f"{int(expected_mean):,}" in headline, f"Mean query must match actual mean: {expected_mean}"
            elif q_type == "Row Count":
                assert f"{num_rows:,}" in headline, f"Row count must match: {num_rows}"

            passed_tests += 1
            print(f"   ✓ [{q_type}]: \"{q_text}\" -> PASSED")
        except Exception as e:
            print(f"   ❌ [{q_type}]: \"{q_text}\" -> FAILED with error: {e}")

print("\n" + "=" * 70)
print(f"VERIFICATION RESULTS: {passed_tests} / {total_tests} TESTS PASSED ({(passed_tests/total_tests)*100:.1f}%)")
print("=" * 70)

if passed_tests == total_tests:
    print("✨ ALL QUERIES, SCHEMAS, AND DATASETS PASSED WITH 100% SUCCESS! ✨\n")
    exit(0)
else:
    exit(1)
