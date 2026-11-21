# Jury Preparation — CSV Intelligence AI

This is the working preparation document for PS 91. It separates the **pitch**, the **evidence**, and the **honest limits**. Do not claim accuracy on arbitrary tables beyond what has been tested.

---

## 1. The 45-second pitch

> “CSV Intelligence AI lets a non-technical user upload a spreadsheet and ask a question in plain English. The hard part is not sounding smart; it is being right. So we separated interpretation from calculation. The language layer turns the question into a small JSON analysis plan. A validator checks every column and operation. Then trusted pandas code calculates the answer locally. The user sees the answer, chart, supporting table, and the exact plan and formula behind it. If the question is ambiguous, the system asks a clarifying question instead of inventing a number. It runs with no API key by default, and has an optional LLM interpretation layer that still cannot bypass validation.”

---

## 2. Problem and solution

### Problem

Business users have CSV data but not always the pandas/SQL skills to query it. Directly asking a general LLM is unreliable for exact numbers and often produces opaque or unsafe code.

### Solution

A constrained natural-language analytics engine:

1. **Understand** the question as a structured plan.
2. **Validate** the plan against the actual schema and an operation allowlist.
3. **Calculate** deterministically with pandas.
4. **Explain** what was selected, filtered and computed.
5. **Refuse** to guess when the request is ambiguous or unsupported.

The “AI” is in the interpretation layer. The numbers come from the data, not from a model.

---

## 3. What to show — evidence, not adjectives

| Claim | Evidence to open live |
|---|---|
| Plain-English questions work | AI Analyst → ask 2–3 questions |
| Answers are calculated, not generated | Open “How this analysis works” and show metric, group, aggregation, filters, formula |
| It refuses to guess | Ask “What is the total foobar?” → clarification with column hints |
| Grouped analysis is correct | “Compare revenue across regions.” → chart + table + plan |
| Time analysis is real | “Show monthly revenue trends.” → monthly periods, peak, movement |
| Statistical checks exist | “Are there any unusual values in revenue?” → IQR fences and outlier percentage |
| Evaluation is live | Evaluation → run the 34-case benchmark |
| Tests exist outside the UI | `python -m unittest discover -s tests -v` → 47 tests |
| Privacy is real by default | No key needed; sidebar shows deterministic engine active; data stays local |
| LLM is optional and bounded | Explain plan-only call, schema-only payload, validator, fallback |
| Exports work | Download result CSV/JSON and answer text |

---

## 4. Live demonstration outline

Full click-by-click instructions are in `DEMO_SCRIPT.md`. Use this as the spoken structure.

1. **Open on Overview.** “The app has profiled 800 synthetic retail orders across 12 columns. These KPIs, charts and insights are generated from the data, not typed in.”
2. **Ask “Which category has the highest total profit?”** “The system identified Category as the group, Profit as the metric, and SUM as the aggregation.”
3. **Open the explainability panel.** “This is the actual plan and formula. There is no hidden model arithmetic.”
4. **Ask “Compare revenue across regions.”** Switch to donut and back. “Charts are visualisations of the same verified result table.”
5. **Ask “Show monthly revenue trends.”** “It detected the date column, resampled monthly and computed the peak and movement.”
6. **Ask “What is the total foobar?”** “This is the important one. It does not silently pick a column. It asks for clarification.”
7. **Run the Evaluation page.** “34 cases run against the real engine with independently calculated expected values. Current run: 34 of 34.”
8. **Close with the trust boundary.** “Local by default, no generated code, optional LLM only for interpretation.”

Keep the demo under 5–7 minutes. Do not narrate every pixel.

---

## 5. Likely jury questions and strong answers

### “Where is the AI? This looks like rules.”

> “The default interpreter is rule-based because reliability matters more than novelty for exact numbers. The optional AI layer is real: if an OpenAI-compatible key is configured, the app sends the question plus schema metadata, receives a JSON plan and validates it. But the AI never calculates the answer. We deliberately made the deterministic path the default so the demo works offline and so an LLM failure cannot corrupt a result.”

Follow-up: show `csvintel/llm.py`, the `propose_plan` function, and the fallback path in `run_analysis`.

### “Why not just let ChatGPT answer?”

> “Because language models are not reliable calculators of exact dataset statistics, and we cannot audit an answer that appears as prose. Our contract is interpret → validate → execute. That gives reproducibility: the same data and plan produce the same number. It also prevents prompt injection in cell values from becoming code execution.”

### “How do you prevent hallucinations?”

> “Three boundaries. First, unsupported or ambiguous questions return clarification, not a number. Second, the validator rejects unknown columns and operations. Third, the executor is a fixed set of pandas operations; it does not run model-generated code. The answer is formatted from computed values. We also label the result source in the UI.”

### “Show me the evaluation. Is 100% real?”

> “It is real for this 34-case benchmark on the built-in dataset. The page runs the actual planner, validator and executor live. Expected values are independently calculated in pandas. It is not a claim of 100% accuracy on every CSV or every phrasing. The invalid-input cases check that the system refuses to guess.”

Be precise: that is **34 of 34 on this benchmark**, plus **47 automated tests** in the current environment. Do not say “100% accurate AI.”

### “What happens if the LLM returns bad JSON or hallucinated columns?”

> “The plan fails validation and the app falls back to the rule-based interpreter with a warning. The executor never sees an invalid plan. Network failures, missing keys, rate limits and timeouts follow the same fallback path.”

### “Can the LLM see my data?”

> “Only if the user configures a key and enables the toggle. Even then, only the question, schema metadata and up to three sample values per column are sent. The full CSV is not. With no key, the app is local-only; the CSV remains in session memory.”

### “What about prompt injection from a CSV cell?”

> “Cell content is data. It is not concatenated into an instructions prompt for the execution path. The optional LLM prompt explicitly marks schema values as untrusted and tells the model to ignore instruction-like text. More importantly, the model only returns a plan that must pass a schema allowlist, and it cannot execute code.”

### “How do you handle ambiguous questions?”

> “The matcher scores exact names, synonyms and partial tokens. If two metrics or two groups match closely, the planner returns a clarification with candidate columns. For example, a dataset with both `revenue` and `revenue_generated` will not silently choose one for a vague ‘sales’ question.”

### “What about large files, joins or multiple CSVs?”

> “This prototype handles a single CSV, capped at 50 MB, in memory. Joins, multi-file semantic models and distributed execution are out of scope. The engine boundary is modular, so those could be added later, but I am not claiming them now.”

### “What statistical methods do you use?”

> “Descriptive statistics: sums, means, medians, standard deviation, variance, range, Pearson correlation, histogram binning and Tukey’s 1.5×IQR outlier fences. We do not do significance testing, regression or causal inference.”

### “Why is the chart sometimes a bar when I asked for a trend?”

> “The planner selects a chart suited to the intent. Bar charts are for comparisons and rankings; line charts are for time series; histograms for distributions; scatter for correlation. For compatible bar results the UI lets the user switch to a donut or line view without recomputing values.”

### “What did you personally build?”

Use a truthful answer based on the repository:

> “I rebuilt the original monolithic Streamlit analyzer into a UI-independent `csvintel` engine, added schema profiling, a structured plan contract, strict validation, deterministic execution, chart/insight modules, a 34-case live benchmark, an optional LLM plan layer, a new presentation UI, 47 automated tests and the documentation/demo material.”

Do not claim every line was written without assistance; describe ownership of the design and the verified result.

---

## 6. Technical talking points if asked to go deeper

### Plan schema

The model/planner outputs intent, metric, optional second metric, group, date column, aggregation, sort, limit, frequency, filters, chart, confidence and interpretation. The validator only accepts known intents, aggregations, chart types, sort values, frequencies and filter operators. Unknown columns are rejected.

### Execution

The executor applies filters, coerces numeric columns, drops invalid values explicitly, groups/resamples, and returns an `AnalysisResult`. Empty results and invalid numeric input are handled explicitly; no fabricated fallback value is shown.

### Explainability

Every result carries:

- the answer and detail text
- supporting metrics
- result table
- chart specification
- detected plan
- execution steps
- formula or method
- source label (rule-based, LLM-assisted, clarification, error)
- row count analysed

### Optional LLM

`csvintel/llm.py` uses `urllib` to call an OpenAI-compatible `/chat/completions` endpoint. It requests JSON and sets temperature 0. It sends schema metadata only. The response is parsed, defaults are merged, and `validate_plan` runs before `execute_plan`. If anything fails, the deterministic path is used.

### Testing

`tests/test_engine.py` uses `unittest` only. The benchmark's expected values are computed independently. The current verification run is **47 tests passing** and **34/34 benchmark cases passing**.

---

## 7. Known limitations to state proactively

Stating limitations increases credibility:

- Common analytical intents only; not arbitrary open-ended reasoning.
- At most two filters for clarity.
- Single CSV, in-memory, 50 MB prototype limit.
- No multi-series trend (for example, monthly revenue by region in one chart).
- Descriptive statistics only; no significance tests or causal claims.
- Currency/percent formatting is name-based and can be imperfect for unusual column names.
- English-centric matching.
- The 34-case benchmark is evidence for this dataset, not a universal accuracy guarantee.
- The optional LLM requires an external provider; the app remains usable without it.

---

## 8. Failure drill

If something goes wrong live:

| Problem | Recovery |
|---|---|
| App state looks stale | Use **Demo Mode → Reset demo** |
| Wrong dataset selected | Sidebar dataset selector → retail demo |
| LLM/network slow | Leave LLM toggle off; deterministic engine is complete |
| A question clarifies instead of answering | Treat it as a trust feature and ask a more explicit question, e.g. “total revenue” |
| Benchmark shows a failure | Say it is a live result; open the failure detail and explain that the system does not hide failures |
| Browser refresh loses history | History is session-only by design; rerun one query |
| Streamlit port in use | `streamlit run app.py --server.port 8503` |

---

## 9. Pre-jury checklist

- [ ] `python -m unittest discover -s tests -v` → 47 passing
- [ ] `streamlit run app.py` opens cleanly
- [ ] Overview, AI Analyst, Data Explorer, Insights, Evaluation, How It Works, History, Demo Mode each load
- [ ] Ask one aggregate, one ranking, one trend and one invalid question
- [ ] Run the Evaluation page once
- [ ] Toggle a chart type
- [ ] Confirm the LLM toggle is off unless you intentionally configured a key
- [ ] Reset Demo Mode before presenting
- [ ] Close other heavy apps if the laptop is slow
- [ ] Have `DEMO_SCRIPT.md` open on a second screen or phone

---

## 10. Closing statement

> “The contribution is not that we generated more text. It is that we made natural-language analysis auditable. The question becomes a plan, the plan is validated, the calculation is deterministic, and the evidence is on screen. That is what makes the result usable in a business or academic setting.”
