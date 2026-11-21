# CSV Intelligence AI — Architecture and Implementation Guide

This document describes the implementation that is actually in this repository. It is intentionally narrower and more concrete than a product pitch: the app is a local Streamlit prototype for natural-language analysis of tabular CSVs, with deterministic execution and optional LLM-assisted interpretation.

For the demo pitch and likely jury questions, see `JURY_PREPARATION.md`. For the live walkthrough, see `DEMO_SCRIPT.md`.

---

## 1. Problem framing

Non-technical users often know what they want to ask about a CSV but not how to write the pandas, SQL or chart configuration. Letting a general LLM answer directly is risky: language models can invent values, silently pick the wrong column, or produce code that is unsafe or non-reproducible.

The design goal is therefore split responsibility:

- **Language understanding** turns a question into a small structured plan.
- **Validation** checks that the plan only uses existing columns and supported operations.
- **Deterministic execution** calculates the result from the data.
- **Explainability** shows the plan, filters, rows and formula behind the result.

The result is a system that can say “I am not sure” and can prove how it got an answer.

---

## 2. Runtime stack

| Layer | Technology |
|---|---|
| UI | Streamlit 1.50.0 |
| Data | pandas 2.3.3 |
| Numeric helpers | NumPy 2.0.2 |
| Charts | Plotly 7.1.0 |
| Optional interpretation | OpenAI-compatible chat completions over `urllib` |
| Tests | Python standard-library `unittest` |
| Runtime | Python 3.9.6 in the verified environment |

No database, backend service, JavaScript build step or external analytics service is required.

---

## 3. End-to-end flow

```text
CSV file (upload or repository path)
  │
  ├─ loader.py
  │    decode bytes, sniff delimiter, parse, repair duplicate headers,
  │    infer date columns, report warnings
  │
  ├─ schema.py
  │    infer numeric / date / categorical / text / boolean / identifier,
  │    profile missingness, cardinality, ranges, quartiles, samples
  │
  ├─ planner.py
  │    normalize question, detect intent, match columns, extract filters,
  │    quantify confidence, build structured plan or clarification
  │
  ├─ (optional) llm.py
  │    send question + schema metadata to an OpenAI-compatible API,
  │    receive a JSON plan, then run the same validation
  │
  ├─ validator.py
  │    reject unknown intents, columns, aggregations, charts, sort values,
  │    frequencies, filter operators, malformed values and unsafe limits
  │
  ├─ executor.py
  │    apply filters, execute trusted pandas operations, format the answer,
  │    metrics, result table, chart specification and explanation
  │
  ├─ charts.py
  │    turn the chart specification and table into a dark Plotly figure
  │
  └─ app.py
       render answer, metrics, table, chart, exports, history and demo pages
```

The analytics engine has no Streamlit imports. It can be called from the UI, tests or another presentation layer.

---

## 4. Dataset loading and profiling

`csvintel/loader.py` handles:

- CSV bytes and filesystem paths
- delimiter detection (`csv.Sniffer` with sensible fallbacks)
- UTF-8/UTF-8-SIG, then Latin-1 fallback
- duplicate header repair (`revenue`, `revenue_2`, …)
- empty and header-only file rejection
- date-column inference only when parsing is sufficiently successful
- structured load reports used by the UI

`csvintel/schema.py` builds a `DatasetProfile` containing:

- row and column counts
- inferred kind per column: numeric, date, categorical, text, boolean or identifier
- missing cells, duplicate rows and duplicate percentage
- per-column unique counts, missing percentage, sample values and top values
- numeric summaries (min, mean, median, max, quartiles)
- primary metric, primary grouping and primary date helpers

The inference is heuristic. It does not know the business meaning of a column; that is why the planner distinguishes explicit matches from weak token overlap and asks for clarification when a choice is ambiguous.

---

## 5. The structured plan

A plan is a plain dictionary. A typical grouped ranking looks like this:

```json
{
  "intent": "ranking",
  "metric": "profit",
  "metric_2": null,
  "group": "category",
  "date_column": null,
  "aggregation": "sum",
  "sort": "desc",
  "limit": 1,
  "frequency": null,
  "filters": [],
  "chart": "bar",
  "confidence": 0.9,
  "interpretation": ["Detected intent: ranking.", "Metric: Profit.", "Grouping column: Category.", "Aggregation: SUM."],
  "source": "rules"
}
```

Allowed intents:

```text
aggregate, group_aggregation, ranking, time_series, distribution, outliers,
correlation, column_profile, dataset_overview, row_count, column_count,
schema, list_numeric, list_categorical, missing, duplicates, unique_count,
meta, clarification
```

Allowed aggregations:

```text
sum, mean, median, min, max, count, std, var, nunique, range
```

The plan is the central contract. The UI displays it, the validator checks it, and the executor interprets it. The LLM layer may propose one, but cannot bypass these steps.

---

## 6. Rule-based interpretation

`csvintel/planner.py` processes questions in a deliberate order so that specific intents win over generic ones:

1. empty / conversational / off-topic guards
2. dataset overview
3. schema and metadata intents
4. missing values, duplicates, unique counts
5. simple row-count questions
6. correlation
7. outliers
8. distribution
9. time series
10. grouped comparison and ranking
11. whole-dataset aggregation
12. single-column profile
13. clarification fallback

Column matching is handled by `csvintel/text.py`:

- normalization (case, punctuation, underscores, hyphens)
- tokenization and singular/plural handling
- exact phrase matching
- synonyms and business concepts (revenue/sales/turnover, price, cost, profit, etc.)
- fuzzy token comparison for longer words
- generic-token suppression so words like `total`, `value`, `monthly` do not by themselves match a column

Ambiguity is surfaced rather than hidden. If two numeric columns match equally well, the planner returns a clarification with candidate columns. If a phrase such as “annual salary” contains a time word that is actually part of a column name, the question is not misclassified as a trend.

Count semantics are explicit:

- “How many transactions are there?” → `row_count`
- “Which country has the most shipments?” → grouped `count`, with no numeric metric
- “Show monthly admission trends.” → time series `count` of records
- “Show monthly revenue trends.” → time series `sum` of the named revenue column

Every one of these is visible in the plan and explanation.

---

## 7. Optional LLM layer

`csvintel/llm.py` is optional. It is disabled unless `OPENAI_API_KEY` is set and `CSVINTEL_DISABLE_LLM` is not enabled.

Privacy boundary:

- the question is sent
- column names, inferred types, cardinality, missing counts and up to three sample values are sent
- the full CSV is not sent

The model is instructed to return JSON only, with the allowed plan schema. It is also told that dataset text is untrusted data and that it must not write code or SQL. The returned object is merged with defaults and passed to `validator.validate_plan`. Any failure mode falls back to the rule-based planner:

- no key
- disabled by environment
- network error
- timeout
- rate limit
- credentials rejected
- non-JSON response
- schema-invalid plan

The UI labels LLM-assisted results and shows validation warnings when a proposal was rejected. Because the executor is unchanged, an LLM-assisted result is still a deterministic pandas calculation.

The implementation uses `urllib` rather than a provider SDK, so no extra dependency is required and any OpenAI-compatible base URL can be used.

---

## 8. Validation and execution

`csvintel/validator.py` rejects:

- unknown intents, aggregations, charts, sort directions and frequencies
- unknown metric, group, date and filter columns
- non-numeric metrics for numeric aggregations
- correlation with fewer than two different numeric columns
- time series without a valid date column and frequency
- grouped/ranked plans without a grouping column
- malformed filters, unknown operators, overlong values and invalid operators for numeric columns
- non-integer, negative or excessive limits
- too many filters

`csvintel/executor.py` contains fixed implementations for:

- aggregate statistics
- grouped aggregation and grouped record counts
- rankings with sort and limit
- time-series resampling and record-count trends
- distributions and histograms
- Tukey 1.5×IQR outlier scans
- Pearson correlation
- column profiles
- data-quality checks
- dataset metadata summaries
- clarification and conversational responses

Filters support equality, inequality, numeric comparisons, year comparison and text containment. The executor does not evaluate expressions.

`AnalysisResult` carries the answer, detail, metrics, table, chart specification, plan, explanation, formula, records used, source, warnings and success state. This makes the result independently inspectable and exportable as CSV, JSON or plain text.

---

## 9. Charts and insights

`csvintel/charts.py` maps a small chart specification (`bar`, `line`, `pie`/donut, `scatter`, `histogram`, `box`, `table`, `none`) and a result table to a Plotly figure, using a consistent dark theme. The UI can switch a compatible bar result to a donut or line view without recomputing the data.

`csvintel/insights.py` generates deterministic observations such as:

- leading category by a metric
- concentration/share of the leader
- profit margin where revenue and profit exist
- monthly peak and movement
- missingness and duplicate warnings
- strongest descriptive correlation

Each insight includes its evidence labels. Correlation is described as association, not causation. Outliers are described as statistical flags, not errors or fraud.

---

## 10. UI composition

`app.py` is the presentation layer:

- dark, responsive Streamlit theme
- sidebar dataset selector and uploader
- optional LLM toggle, shown only when configured
- pages: Overview, AI Analyst, Data Explorer, Insights, Evaluation, How It Works, History, Demo Mode
- result exports and “How this analysis works” panel
- session history keyed by dataset identity, so stale results are not presented as current
- cached built-in dataset loading
- graceful dataset fallback

The UI never calculates the analytical answer itself; it calls `build_plan`, `validate_plan` and `execute_plan`.

---

## 11. Evaluation design

`csvintel/evaluation.py` contains 34 executable cases across eight categories:

| Category | Cases | What is checked |
|---|---:|---|
| Basic | 8 | totals, averages, counts, extrema, overview |
| Grouped | 5 | group sums, group counts, comparison |
| Ranking | 3 | top-N, highest/lowest |
| Time series | 3 | monthly trends, peak periods |
| Data quality | 4 | missing, duplicates, unique counts, schema |
| Statistical | 3 | outlier counts, correlation, distribution |
| Filtering | 2 | category and year filters |
| Invalid input | 6 | ambiguous, unknown and off-topic questions must clarify |

Expected values are calculated independently with pandas in the test definitions rather than being copied from engine output. Numeric comparisons use a small tolerance. The UI’s Evaluation page runs the real engine and displays every case.

Unit and integration tests live in `tests/test_engine.py` and run with:

```bash
python -m unittest discover -s tests -v
```

They cover loader edge cases, planner behavior, validator rejections, executor arithmetic, chart creation, insights, prompt-injection resilience and the benchmark.

---

## 12. How to extend safely

### Add a new intent

1. Add the intent to the planner’s classification logic.
2. Add it to `ALLOWED_INTENTS` in `validator.py`.
3. Add validation requirements (metric/group/date).
4. Implement one fixed executor function.
5. Add an `AnalysisResult` explanation and tests.
6. Add a benchmark case with an independent expected value.

### Add a new dataset

Place a CSV in `datasets/` and add an entry to `DATASET_OPTIONS` in `app.py` with a readable name, description and schema-aware sample questions. Test every sample question against the real engine before presenting it.

### Improve matching

Add synonyms or concepts in `csvintel/text.py`, but keep ambiguity handling. Prefer a clarification over a low-confidence guess.

### Add an LLM provider

Set `OPENAI_BASE_URL` and `OPENAI_MODEL` to any endpoint exposing an OpenAI-compatible `/chat/completions` API. Keep the plan-only contract and validate every response.

---

## 13. Known limitations

- Coverage is for common analytical questions, not open-ended reasoning.
- Multi-condition boolean queries and multi-series trends are not implemented.
- Matching is heuristic and English-centric.
- Statistical output is descriptive, not inferential.
- Formatting is name-based; a column such as “value” may be treated as currency when it is not.
- Very wide or very large datasets are beyond the prototype’s 50 MB in-memory scope.
- The benchmark measures this project on its synthetic dataset, not general-world accuracy.
- The optional LLM path depends on an external provider and remains optional by design.
