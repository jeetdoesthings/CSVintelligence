# CSV Intelligence AI

**Chat with your CSV — a natural-language tabular data analytics workspace with verified, deterministic calculations.**

Repository: [https://github.com/jeetdoesthings/CSVintelligence](https://github.com/jeetdoesthings/CSVintelligence)  
Built for **PS 91: Chat-with-your-CSV Tool [Model Making]** (Unit: Transformers & LLMs, Practical Builds & Scenarios).  
Class: **LY AIA 2** | Department of Artificial Intelligence & Data Science.

---

## Why this is different from "just ask an LLM"

A general-purpose LLM is good at natural language interpretation and unreliable at exact multi-row dataset arithmetic. This project separates the two jobs:

1. **Interpret** the user question into an intermediate structured JSON Analysis Plan.
2. **Validate** that plan against the active dataset schema and a strict allowlist.
3. **Execute** only trusted, compiled pandas/NumPy operations locally.
4. **Explain** the exact columns, filters, aggregation, row counts, and formula used.

There is no `eval()`, no unrestricted code execution, no arbitrary SQL generation, and no model-hallucinated numbers presented as answers. If a question is ambiguous or unsupported, the app asks for clarification instead of guessing. An optional OpenAI-compatible LLM can enhance complex linguistic interpretation, but its output still passes through the same validator and deterministic executor.

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/jeetdoesthings/CSVintelligence.git
cd CSVintelligence

# Set up virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

Open <http://localhost:8501> in your browser. The built-in synthetic retail dataset loads automatically, making the application immediately ready for testing and demonstration.

---

## Optional LLM Interpretation

The deterministic engine works 100% offline with zero keys and zero network dependencies. To enable LLM-assisted question interpretation:

```bash
cp .env.example .env
# Edit .env and set your API credentials
```

Supported environment variables:

| Variable | Purpose | Default |
|---|---|---|
| `OPENAI_API_KEY` | API key for OpenAI / Gemini / local compatible provider | unset |
| `OPENAI_BASE_URL` | OpenAI-compatible chat-completions endpoint | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | Model used for plan generation | `gpt-4o-mini` |
| `CSVINTEL_DISABLE_LLM` | Set to `1` to enforce strict offline local-only mode | unset |

*Privacy note:* Only the question, column names/types, and up to 3 non-sensitive sample values are sent. Raw CSV rows never leave your local machine.

---

## What is in the Application

| Page / Feature | What it does |
|---|---|
| **Overview** | Dynamic KPI cards, trend chart, category breakdown, distribution, and quick query box |
| **AI Analyst** | Main natural-language interface: suggested questions, verified answers, smart Plotly charts, and explainability audit trail |
| **Data Explorer** | Inferred schema inspector, real-time search, sorting, filtering, and paginated tabular preview |
| **Insights** | Automatic statistical observations, outlier detection (IQR), and correlation analysis |
| **Evaluation** | Real in-app benchmark executing 34 test cases against independent calculations |
| **How It Works** | Comprehensive architecture documentation, safety boundaries, and technology map |
| **History** | Persistent query history with dataset context indicators and one-click recall |
| **Demo Mode** | Simplified presentation view with click-to-run demo sequence for evaluations and juries |

The app ships with **11 ready-to-use business datasets** (Retail, E-commerce, SaaS, Healthcare, Banking, HR, Marketing, Logistics, Real Estate, Streaming, and Crypto). Any custom CSV up to 50 MB can also be uploaded via drag-and-drop.

---

## Repository Guide

```text
├── app.py                           # Main Streamlit web application (Light Mode UI)
├── requirements.txt                 # Application dependencies
├── sample_retail_sales_2024.csv     # 800-row demo retail dataset
├── CSV_Intelligence_AI_Report.pdf   # Official 10-page academic project report (PDF)
├── PROJECT_REPORT.md                # 10-page academic project report (Markdown)
├── DEMO_SCRIPT.md                   # Step-by-step 3-5 minute live presentation script
├── JURY_PREPARATION.md              # 20+ Q&A technical defense documentation
├── README.md                        # Project documentation and quick start
├── guide.md                         # Architecture and implementation notes
├── .env.example                     # Template for optional LLM configuration
├── .streamlit/                      # Streamlit configuration (theme & layout)
├── csvintel/                        # Core UI-independent analytics package
│   ├── loader.py                    # Delimiter sniffing & dataset ingestion
│   ├── schema.py                    # Schema profiling & data type inference
│   ├── planner.py                   # Natural-language heuristic query planning
│   ├── validator.py                 # Query plan allowlist validation
│   ├── executor.py                  # Deterministic pandas calculation engine
│   ├── charts.py                    # Smart Plotly chart generation
│   ├── insights.py                  # Automated statistical insight generation
│   ├── llm.py                       # Optional OpenAI/Gemini integration layer
│   ├── text.py                      # Text normalization and formatting
│   └── evaluation.py                # In-app benchmark runner
├── datasets/                        # 10 business domain test datasets
├── scripts/                         # Multi-dataset verification test harness
└── tests/                           # 49 automated unit tests
```

---

## Automated Verification & Testing

```bash
# Run unit test suite (49 tests)
python3 -m unittest discover -s tests

# Run comprehensive 11-dataset verification suite (132 test cases)
python3 scripts/test_all_datasets.py
```

- **Unit tests:** 49 / 49 passed (100%)
- **Cross-dataset benchmark:** 132 / 132 passed (100% across all 11 business domains)
- **In-app evaluation benchmark:** 34 / 34 passed (100%)

---

## Limitations

- Operates on single tabular CSV files; relational multi-table `JOIN` across distinct files is not yet supported.
- Vectorized operations run in system RAM; files larger than 1–2 GB may require chunking or out-of-core engines.
- Compound questions with multiple nested sub-queries are limited to two sequential filters.
- The external LLM integration is optional; when offline, the system relies on its robust heuristic parser.
