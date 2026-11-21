# CSV Intelligence AI

**Chat with your CSV — a natural-language analytics workspace with verified, deterministic calculations.**

Built for **PS 91: Chat-with-your-CSV Tool**. Upload a CSV, ask a question in plain English, and get an answer, supporting metrics, a chart, the detected analysis plan and the exact method used. The language layer only interprets the question; every number is calculated locally with pandas.

---

## Why this is different from "just ask an LLM"

A general-purpose LLM is good at language and unreliable at exact dataset arithmetic. This project separates the two jobs:

1. **Interpret** the question into a structured JSON plan.
2. **Validate** that plan against the active schema and a strict allowlist.
3. **Execute** only trusted pandas operations.
4. **Explain** which columns, filters, aggregation and rows produced the answer.

There is no `eval()`, no generated Python/SQL execution, and no model-generated number presented as a result. If the question is ambiguous or unsupported, the app asks for clarification instead of guessing. An optional OpenAI-compatible LLM can improve interpretation, but its output still goes through the same validator and deterministic executor.

---

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open <http://localhost:8501>. The built-in synthetic retail dataset loads automatically, so the app is demo-ready without an upload.

The project was last verified with **Python 3.9.6**, Streamlit 1.50.0, pandas 2.3.3, Plotly 7.1.0 and NumPy 2.0.2.

### Optional LLM interpretation

The deterministic engine works with no key and no network. To enable LLM-assisted question interpretation:

```bash
cp .env.example .env
# edit .env and set OPENAI_API_KEY
```

Supported settings:

| Variable | Purpose | Default |
|---|---|---|
| `OPENAI_API_KEY` | Enables the optional interpretation layer | unset |
| `OPENAI_BASE_URL` | Any OpenAI-compatible chat-completions endpoint | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | Model used for plan generation | `gpt-4o-mini` |
| `CSVINTEL_DISABLE_LLM` | Set to `1` to force local-only mode | unset |

Only the question, column names/types, cardinality and up to three sample values per column are sent. The full CSV is never sent. The model returns a plan, not an answer or code. Invalid plans, timeouts, rate limits, missing keys and network failures fall back to the rule-based interpreter and are labelled in the UI. Streamlit secrets (`OPENAI_API_KEY`, etc.) are also read at runtime.

---

## What is in the app

| Page | What it does |
|---|---|
| **Overview** | Dataset KPIs, trend, group comparison, distribution, strongest numeric relationship, insights and a quick question box |
| **AI Analyst** | Core chat experience: schema-aware suggestions, validated plan, answer, metrics, chart, result table, exports and an explainability panel |
| **Data Explorer** | Inferred schema, column inspector, search, categorical filter, sort, pagination and CSV exports |
| **Insights** | Deterministic, evidence-backed observations generated from the active dataset |
| **Evaluation** | Runs the real 34-case benchmark live and shows per-case evidence |
| **How It Works** | Architecture, safety boundaries, technology stack, code map and limitations |
| **History** | Session query trail with dataset identity; older results are explicitly labelled when they belong to another dataset |
| **Demo Mode** | Guided live demonstration with one-click analyses and a presenter run sheet |

The app ships with **11 datasets**: one deterministic synthetic retail demo (800 rows) plus 10 multi-industry CSVs in `datasets/`. Any CSV can be uploaded; delimiter, quoting and encoding are detected, duplicate headers are repaired, and clear errors are shown for empty or header-only files.

---

## Question types the engine supports

- Dataset overview, schema, row/column counts, numeric/categorical/date column lists
- Totals, averages, medians, minimum, maximum, standard deviation, variance, range and counts
- Grouped comparisons and rankings, including top-N and "which group has the highest …"
- Time-series trends with daily, weekly, monthly, quarterly or yearly resampling
- Distribution histograms, IQR outlier scans and Pearson correlation
- Missing-value and duplicate-row checks
- Unique-value counts and column profiles
- Row-count questions such as "How many transactions are there?"
- Count-based group questions such as "Which country has the most shipments?"
- Single categorical or numeric filters and year filters
- Clarification and safe conversational responses for ambiguous, off-topic or invalid input

Example questions:

```text
Give me an overview of this dataset.
What is the total revenue?
Which category has the highest total profit?
Compare revenue across regions.
Show monthly revenue trends.
Are there any unusual values in revenue?
What is the average discount percent?
Correlation between revenue and profit
What is the total foobar?
```

The last example is intentional: it demonstrates that the system refuses to silently substitute a different metric.

---

## Architecture

```text
CSV upload / built-in dataset
        │
        ▼
csvintel.loader      parse bytes or path, detect delimiter/encoding, repair headers, infer dates
        │
        ▼
csvintel.schema      infer numeric/date/categorical/text/id, profile missingness and cardinality
        │
        ▼
csvintel.planner     normalize question, classify intent, match columns, extract filters,
        │            build a structured JSON plan (or ask for clarification)
        │
        ├── optional csvintel.llm ──► structured plan from an OpenAI-compatible API
        │                               (schema-only payload, no CSV rows, no code)
        ▼
csvintel.validator   allowlist intents/aggregations/charts/operators, reject unknown columns,
        │            wrong types, unsafe limits and malformed filters
        ▼
csvintel.executor    deterministic pandas: filter → aggregate/group/resample/correlate
        │            → format answer, metrics, evidence, chart specification
        ▼
csvintel.charts      chart specification + result table → Plotly figure
csvintel.insights    independent deterministic observations for the Insights page
        │
        ▼
app.py               Streamlit pages, session state, exports and presentation
```

Key modules:

| Module | Responsibility |
|---|---|
| `csvintel/loader.py` | CSV bytes/path parsing, delimiter/encoding detection, duplicate headers, date inference |
| `csvintel/schema.py` | Type inference and dataset profiling |
| `csvintel/text.py` | Normalization, synonyms, fuzzy matching, formatting, concept detection |
| `csvintel/planner.py` | Intent classification and structured plan generation |
| `csvintel/validator.py` | Whitelist and schema validation |
| `csvintel/executor.py` | Deterministic calculations, answer formatting and `AnalysisResult` |
| `csvintel/charts.py` | Chart specification to Plotly figure |
| `csvintel/insights.py` | Evidence-backed automatic insights |
| `csvintel/evaluation.py` | 34-case live benchmark with independently calculated expectations |
| `csvintel/llm.py` | Optional LLM plan proposal with schema-only context |

The structured plan is deliberately small and inspectable: `intent`, `metric`, `metric_2`, `group`, `date_column`, `aggregation`, `sort`, `limit`, `frequency`, `filters`, `chart`, `confidence` and `interpretation`.

---

## Trust, privacy and safety

- **Deterministic calculations.** The executor is a fixed set of pandas operations, not a generated program.
- **No model code execution.** No `eval()`, `exec()`, generated SQL or unrestricted expressions.
- **Schema validation before execution.** Unknown columns, unsupported aggregations, invalid filter operators, malformed plans and unreasonable limits are rejected.
- **No silent metric substitution.** Unknown or ambiguous metrics return a clarification with candidate columns.
- **CSV content is data.** Cell values that look like instructions are treated as text, never as prompts.
- **Local by default.** CSVs stay in session memory. With no API key, no data leaves the machine.
- **Explicit LLM boundary.** If enabled, only metadata and a few sample values are sent; the whole CSV is not.
- **Honest labels.** The result card distinguishes rule-based, LLM-assisted, clarification, error and conversational responses.
- **Session-scoped history.** Queries are stored in Streamlit session state only and disappear when the session ends or history is cleared.

---

## Verification

### Automated tests

```bash
python -m unittest discover -s tests -v
```

**47 tests pass** in the current workspace. They cover:

- parsing, delimiter/encoding detection, duplicate headers, empty/header-only rejection
- type inference, missingness and duplicate profiling
- NL variants for totals, averages, rankings, filters, trends and comparisons
- ambiguous metrics, unknown metrics, exact-column preference and prompt-injection resilience
- validator rejection of unknown columns, non-numeric metrics, bad operators, code-like intents and bad limits
- executor correctness against independently computed pandas values
- count-based row and group questions
- time words inside column names not forcing a trend
- chart construction, insights and the built-in benchmark

### Live benchmark

The **Evaluation** page executes 34 real questions through the same planner, validator and executor used by the app. Expected values are calculated independently with pandas, not copied from the engine. Current result:

**34 / 34 cases passed (100%)** across Basic (8), Grouped (5), Ranking (3), Time series (3), Data quality (4), Statistical (3), Filtering (2) and Invalid input (6).

The invalid-input cases require a clarification or safe response, never a fabricated number. This is a small project benchmark, not a claim of general accuracy on arbitrary CSVs or languages.

### Runtime check

```bash
streamlit run app.py --server.headless true
```

The app was also exercised with Streamlit's `AppTest` across every page, including running an analysis, switching chart type and running the demo. No runtime exceptions were observed.

---

## Repository guide

```text
app.py                          Streamlit presentation layer
csvintel/                       UI-independent analytics engine
tests/test_engine.py            unit and integration tests
sample_retail_sales_2024.csv    deterministic demo dataset (800 rows)
datasets/                       10 additional example CSVs
scripts/generate_sample_data.py deterministic demo data generator
README.md                       this file
JURY_PREPARATION.md             pitch, likely questions and evidence
DEMO_SCRIPT.md                  click-by-click live demonstration
guide.md                        deeper architecture and extension notes
.env.example                    optional LLM configuration template
```

Useful commands:

```bash
# regenerate the demo dataset
python scripts/generate_sample_data.py

# run tests
python -m unittest discover -s tests -v

# start the app
streamlit run app.py

# force local-only mode even if a key exists
CSVINTEL_DISABLE_LLM=1 streamlit run app.py
```

---

## Limitations

- The rule-based interpreter covers common analytical intents, not arbitrary English. Complex multi-condition boolean logic is limited; at most two filters are applied for clarity.
- Multi-series time comparisons (for example, monthly revenue by region in one chart) are not supported.
- Statistical analysis is descriptive: Pearson correlation and IQR outliers. There is no significance testing, regression or causal inference.
- Currency and percent formatting is name-based heuristics. Ambiguous column names can be formatted imperfectly.
- The LLM layer requires an external provider and is optional; when unavailable the deterministic engine remains fully functional.
- The local prototype limits uploads to 50 MB and keeps data in memory.
- The benchmark is tied to the built-in synthetic dataset and is evidence of tested behavior on that dataset, not a universal accuracy guarantee.
