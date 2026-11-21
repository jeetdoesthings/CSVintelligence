# Jury Preparation — CSV Intelligence AI

This is the comprehensive jury defense and examination preparation document for **PS 91: Chat-with-your-CSV Tool [Model Making]** (Unit: Transformers & LLMs, Practical Builds & Scenarios). It details the pitch, architecture, mathematical evidence, technical mechanics, honest boundaries, and 20+ direct technical answers to jury questions.

---

## 1. The 45-Second Pitch

> “CSV Intelligence AI lets a non-technical user upload an unfamiliar CSV spreadsheet and ask questions in plain English to immediately extract verified mathematical answers, KPI metrics, and charts. The core challenge in Generative AI for data analysis is not sounding smart; it is being right. General LLMs frequently hallucinate multi-row aggregations, invent values, or generate risky code. We solved this with a decoupled 4-stage pipeline: Language Understanding maps the question to an intermediate JSON Analysis Plan; a Strict Validator enforces an allowlist of supported operations and checks column schemas; a Deterministic Executor computes the exact numbers locally with pandas without `eval()` or unconstrained code execution; and an Explainability Layer surfaces the exact pandas formula, filter criteria, and rows analyzed. If the question is ambiguous or unsupported, the system asks for clarification instead of guessing.”

---

## 2. Problem and Solution

### Problem
Business users and analysts have tabular CSV data but often lack the Python, pandas, or SQL expertise needed to query it. Conversely, feeding raw CSV data directly to general-purpose LLMs suffers from:
1. **Mathematical hallucinations:** Autoregressive language models predict tokens statistically rather than executing rigorous dataset arithmetic.
2. **Security vulnerabilities:** Naive text-to-code implementations use `eval()` or `exec()`, exposing systems to code injection or accidental file damage.
3. **Data privacy egress:** Uploading entire proprietary datasets to external cloud APIs compromises privacy and breaches confidentiality.
4. **Opaque answers:** LLM-generated prose cannot be audited for mathematical provenance.

### Solution: Constrained Natural-Language Analytics
A 4-stage decoupled analytics engine:
1. **Interpret:** Translate the question into a structured JSON Analysis Plan using either the local rule-based planner or an optional OpenAI-compatible LLM.
2. **Validate:** Enforce schema conformity and operation allowlists before any execution.
3. **Calculate:** Pure, deterministic pandas execution on local machine memory.
4. **Explain & Audit:** Show the exact columns, filters, row counts, aggregations, and formula behind every calculation.
5. **Safely Refuse:** Ask for clarification when queries are ambiguous, off-topic, or reference nonexistent columns.

---

## 3. Architecture & Technical Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                      USER UPLOADS CSV                       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              CSV PARSER & LOADER (loader.py)                │
│  - Detects delimiter (, ; \t |), quote chars, encoding      │
│  - Repaires duplicate headers automatically                 │
│  - Infers ISO / common date formats                         │
│  - Enforces 50 MB safety limit & non-empty validation       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│          SCHEMA PROFILER & VALIDATOR (schema.py)            │
│  - Classifies: numeric, date, categorical, text, boolean, ID│
│  - Calculates missing cells %, duplicate rows, cardinality  │
│  - Computes quantiles, IQR, ranges, and sample values       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│            USER ENTERS NATURAL-LANGUAGE QUESTION            │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│           INTERPRETATION LAYER (planner.py / llm.py)        │
│  - Normalizes text, tokenizes, removes stopwords            │
│  - Detects analytical intent (sum, mean, rank, trend, etc.) │
│  - Fuzzy-matches columns using aliases, synonyms & concepts │
│  - Extracts comparison filters, top-N limits, frequencies   │
│  - OPTIONAL LLM: Proposes plan via OpenAI-compatible API    │
│    (Receives ONLY schema metadata + 3 samples; never CSV)   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│            STRUCTURED ANALYSIS PLAN (JSON Plan)             │
│  { intent, metric, group, aggregation, sort, limit, filters }│
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              PLAN VALIDATOR (validator.py)                  │
│  - Strict allowlist: verifies intent, aggregation, sort     │
│  - Validates that columns actually exist in active dataset  │
│  - Verifies data-type compatibility (metric must be numeric) │
│  - Blocks unknown operators, dangerous payloads, bad limits │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│          DETERMINISTIC EXECUTOR (executor.py)               │
│  - Applies filters locally using pandas boolean indexing    │
│  - Executes groupby, resample, agg, corr, IQR without eval()│
│  - Formats answer, KPI metrics, and supporting result table │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│       VISUALIZATION & EXPLAINABILITY (charts.py, app.py)    │
│  - Dark Plotly charts: bar, line, donut, histogram, scatter │
│  - Formula & Step-by-step audit trail ("How it works")      │
│  - One-click exports: Answer (.txt), Table (.csv, .json),PNG│
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 20 Direct Jury Questions and Answers

### 1. What problem does this project solve?
> “It allows business users, researchers, and non-technical stakeholders to query and explore tabular CSV datasets using natural English without needing Python, pandas, or SQL expertise, while eliminating the mathematical hallucinations and security vulnerabilities of general LLMs.”

### 2. Why did you choose this problem?
> “Tabular data in CSV format is ubiquitous across every industry, but data analysis bottlenecks occur because non-technical users depend on developers or data teams for simple aggregations and trends. Conventional LLM chatbots try to solve this by generating raw code or hallucinating numbers, which is neither reliable nor safe. This project bridges that gap with guaranteed mathematical accuracy.”

### 3. What is the role of Generative AI?
> “Generative AI serves as the **semantic interpretation layer**. It understands linguistic nuance, synonymy, intent, and conversational phrasing, and translates the user's intent into a structured, validated JSON analysis plan. It does **not** perform calculation arithmetic; computation is delegated entirely to deterministic pandas algorithms.”

### 4. Is this a chatbot?
> “No. It is an **interactive natural-language analytics workspace**. While it has a query interface, it outputs structured KPI metric cards, interactive Plotly visualizations, downloadable supporting data tables, and an execution audit trail rather than conversational prose.”

### 5. How is a natural-language question converted into a query?
> “Through a 3-step compilation:
> 1. Normalization: Tokenization, punctuation stripping, synonym replacement, and entity recognition.
> 2. Intent & Column Matching: Fuzzy-matching question tokens against dataset column profiles, synonyms, and analytical keywords (e.g. ‘total’ → `sum`, ‘highest’ → `ranking`).
> 3. Plan Synthesis: Creating a constrained JSON object specifying `{intent, metric, group, aggregation, sort, limit, filters}`.”

### 6. What is intent classification?
> “Intent classification is determining the computational objective behind the user's question. We categorize questions into specific analytical types: `aggregate`, `group_aggregation`, `ranking`, `time_series`, `distribution`, `outliers`, `correlation`, `row_count`, `column_count`, `schema`, `missing`, `duplicates`, and `clarification`.”

### 7. How do you identify dataset columns?
> “The system generates column profiles containing normalized names, token variants, domain concepts (e.g., ‘revenue’ relates to sales, turnover, price), and data types. When a user asks a question, candidate columns are scored based on exact matching, token overlap, and fuzzy Levenshtein ratio. If two columns match with similar confidence, the system refuses to guess and asks for clarification.”

### 8. What is pandas?
> “pandas is Python’s industry-standard, high-performance open-source data manipulation and analysis library. In this application, pandas is our deterministic execution engine that performs in-memory filtering, grouping, date resampling, sorting, and statistical calculations.”

### 9. Why not directly ask the LLM for the answer?
> “Because LLMs are probabilistic sequence predictors, not deterministic calculators. When given a 1,000-row CSV in context, LLMs frequently skip rows, miscalculate sums, suffer attention degradation over long context windows, and hallucinate plausible-sounding numbers. Furthermore, sending an entire dataset violates data privacy.”

### 10. How do you reduce hallucinations?
> “By enforcing a complete architectural separation between language interpretation and calculation. The language model only outputs a JSON plan; every number presented in the UI is directly computed by pandas from the raw dataset rows. If a question is unsupported or ambiguous, the model returns a clarification rather than fabricating a result.”

### 11. How do you prevent unsafe query execution?
> “We completely ban `eval()`, `exec()`, and unrestricted Python or SQL generation. The only code executed is pre-written, audited pandas routines. Every JSON plan must pass `validator.py`, which checks each field against strict allowlists of intents, aggregations, chart types, and existing column names.”

### 12. What happens when a question is invalid?
> “When a question cannot be mapped to an analytical operation or references unknown columns (e.g., ‘What is the total foobar?’), the engine returns intent `clarification`. It politely explains what was missing, lists the available numeric and categorical columns, and suggests a valid alternative question.”

### 13. What happens when a dataset contains missing values?
> “During loading and profiling, missing cells are detected, counted, and reported. In calculations, pandas explicitly excludes `NaN` values from aggregations (such as mean and sum) to avoid silent errors. The Data Explorer and Insights pages highlight the exact columns and percentages affected by missing data.”

### 14. How does chart selection work?
> “Chart selection is deterministic based on the analytical intent and data dimensions:
> - Date + Metric → Line chart (`px.line`)
> - Categorical Group + Metric → Vertical or Horizontal Bar chart (`px.bar`)
> - Distribution of Single Metric → Histogram (`px.histogram`) or Box plot (`go.Box`)
> - Two Numeric Metrics → Scatter plot (`px.scatter`)
> - Top categories composition → Donut chart (`px.pie`)
> - Single Scalar Result → KPI Metric card
> Users can also toggle alternative compatible chart types in the UI.”

### 15. How is the accuracy of the application evaluated?
> “Through two automated test layers:
> 1. An automated test suite of **49 unit tests** (`tests/test_engine.py`) verifying loaders, schema classifiers, planners, validators, and executors.
> 2. A live **34-case verification benchmark** (`csvintel/evaluation.py`) running against independent pandas ground truth calculations across 8 categories with 100% pass rate.
> 3. An automated cross-dataset suite (`scripts/test_all_datasets.py`) running **132 automated tests across all 11 business datasets** with 100% success.”

### 16. What are the current limitations?
> “1. Single-table analysis (relational joins across multiple CSVs are not supported).
> 2. In-memory file size limit capped at 50 MB for responsive browser execution.
> 3. English-centric linguistic matching.
> 4. Max two simultaneous filter predicates per natural-language question.
> 5. Descriptive and exploratory statistics only; no automated hypothesis testing or causal inference.”

### 17. What happens if the dataset changes?
> “When the user uploads a new CSV or switches to another built-in dataset, the application wipes the active profile, parses the new file, re-infers column types, updates KPI cards and charts, and refreshes the suggested questions. Previous query results are tagged with their dataset origin to prevent stale data confusion.”

### 18. Does the model get trained on the uploaded data?
> “No. The application performs zero model training or fine-tuning. By default, with the deterministic engine, zero data leaves the user’s local machine. When the optional LLM mode is enabled, only column names, types, and up to 3 sample values are sent as prompt context for plan synthesis. The full dataset is never transmitted.”

### 19. What is the role of structured output?
> “Structured JSON output enforces a machine-verifiable contract between the natural-language layer and the execution engine. Because the output is constrained to a predefined JSON schema, our Python validator can programmatically verify every column and aggregation before a single line of pandas code runs.”

### 20. What improvements would you make in the future?
> “1. Multi-table SQL/relational joins using DuckDB or SQLite for complex relational schemas.
> 2. Semantic vector embeddings for column matching on massive schemas with thousands of columns.
> 3. Support for Excel (.xlsx), Parquet, and direct database connections (PostgreSQL/BigQuery).
> 4. Exportable PDF and PowerPoint analytical slide decks generated automatically from session findings.”

---

## 5. Live Demonstration Run Sheet (5 Minutes)

| Time | Action | Screen / Feature | What to Say |
|---|---|---|---|
| **0:00 - 0:45** | Introduce project & problem | Overview Page | “This is CSV Intelligence AI for PS 91. It provides verified tabular analytics with zero hallucinated math by separating question interpretation from deterministic pandas calculation.” |
| **0:45 - 1:30** | Run primary aggregation query | AI Analyst Page: *“Which category has the highest total profit?”* | “The engine identified Category as the group, Profit as the metric, and SUM as the aggregation. The result is calculated locally in milliseconds.” |
| **1:30 - 2:15** | Open explainability audit trail | Click *“How this analysis works”* | “Here is the verified execution audit trail: exact pandas formula, detected JSON plan, rows analyzed, and allowlist validation badge.” |
| **2:15 - 3:00** | Run time-series trend & chart toggle | AI Analyst Page: *“Show monthly revenue trends.”* | “It detected the date column, resampled monthly, and computed trend movement and peak period. We can toggle between chart representations instantly.” |
| **3:00 - 3:45** | Demonstrate refusal to hallucinate | Ask: *“What is the total foobar?”* | “Instead of inventing numbers or hallucinating a column, it flags the ambiguity, lists valid numeric columns, and guides the user.” |
| **3:45 - 4:30** | Run live evaluation benchmark | Evaluation Page | “Here is our live 34-case verification benchmark running against pandas ground truth. 34 of 34 cases pass with 100% precision.” |
| **4:30 - 5:00** | Conclusion & trust boundary | How It Works Page | “Zero eval(), zero code execution risks, local data privacy by default, and optional bounded LLM integration. Ready for your questions.” |

---

## 6. Pre-Jury Verification Checklist

- [x] `python -m unittest discover tests -v` → 49 passing tests.
- [x] `python scripts/test_all_datasets.py` → 132/132 tests passing across all 11 datasets.
- [x] Benchmark verification: 34/34 cases pass in `csvintel/evaluation.py`.
- [x] Streamlit app starts cleanly with `streamlit run app.py`.
- [x] All 8 navigation views render correctly (Overview, AI Analyst, Data Explorer, Insights, Evaluation, How It Works, History, Demo Mode).
- [x] Local offline deterministic mode functions with zero keys.
- [x] Optional LLM configuration drawer connects cleanly to OpenAI/Ollama endpoints.
