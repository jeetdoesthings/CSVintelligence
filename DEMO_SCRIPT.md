# Live Demo Script — CSV Intelligence AI

**Target length:** 5–7 minutes  
**Default dataset:** OmniTech Retail Sales 2024 (800 synthetic rows)  
**Starting page:** Demo Mode after a reset, or Overview for a more exploratory opening

The demo uses the real engine. Do not use pre-recorded answers, and do not describe the synthetic data as real company data.

---

## A. Pre-flight (do this 5 minutes before)

```bash
cd /Users/jeet/Desktop/GENAIPRESENTATION2
source .venv/bin/activate

# 1. Verify the engine
python -m unittest discover -s tests -v
# Expected: Ran 47 tests ... OK

# 2. Start the app
streamlit run app.py
```

Open <http://localhost:8501>.

Before the jury enters:

- [ ] Confirm the sidebar says **OmniTech Retail Sales 2024 (Synthetic Demo)**.
- [ ] Confirm the LLM toggle is **off** unless you have configured a key and want to show it.
- [ ] Confirm the footer or sidebar shows **800 rows · 12 cols**.
- [ ] Open **Demo Mode** and press **Reset demo**.
- [ ] Close noisy browser tabs and notifications.
- [ ] Keep this file and `JURY_PREPARATION.md` accessible on another device.

If port 8501 is busy:

```bash
streamlit run app.py --server.port 8503
```

---

## B. Opening — 30 seconds

**On screen:** Overview page.

**Say:**

> “This is CSV Intelligence AI. A user can upload a CSV and ask questions in plain English. The dataset on screen is an 800-row synthetic retail dataset with orders, products, regions, revenue, cost and profit. The app has already parsed it, inferred column types and profiled the data.”
>
> “The key design choice is that the language model does not calculate the answer. It only helps interpret the question. All numbers are computed locally with deterministic pandas operations, and the user can inspect the plan.”

Point to the KPI strip and one chart. Do not read every number.

---

## C. Demo step 1 — Ranking (60–90 seconds)

**Go to:** AI Analyst.

**Ask:**

```text
Which category has the highest total profit?
```

**Expected result shape:** Category `Computing` has the highest Profit at about `$155,440` (the exact value should match the live result).

**Say:**

> “The system chose the category column as the grouping, profit as the metric, and SUM as the aggregation. It sorted the groups and returned the top one.”

Open **How this analysis works** under the result.

**Say:**

> “This is the actual structured plan: intent, metric, group, aggregation, filters. This is the formula and the number of rows analysed. There is no opaque model arithmetic here.”

Point out the source label: **Verified deterministic calculation**.

**If asked to prove it:** open the result table and show that the winning group has the highest summed profit.

---

## D. Demo step 2 — Comparison and chart (45–60 seconds)

**Ask:**

```text
Compare revenue across regions.
```

**Expected result shape:** Revenue by five regions; North America leads at about `$303,860`, about 32% of the total.

**Say:**

> “Now it detected a grouped comparison. It summed revenue for each region and calculated each group’s share of the total.”

Switch the **Chart view** from **Bar** to **Donut**.

**Say:**

> “The chart is just a view of the same verified result table; switching it does not recompute or change the values.”

Switch back to **Bar** if time allows.

---

## E. Demo step 3 — Time series (45–60 seconds)

**Ask:**

```text
Show monthly revenue trends.
```

**Expected result shape:** Peak monthly Revenue in `2024-12` at about `$108,527`, with monthly periods and a first-to-last movement.

**Say:**

> “It detected the order date column, resampled it monthly, summed revenue per month and compared the first and last period. The plan shows the date column and frequency.”

Point to the peak period, movement and row count.

---

## F. Demo step 4 — Safety/refusal (30–45 seconds)

**Ask:**

```text
What is the total foobar?
```

**Expected result:** A clarification card, not a number. It should state that the metric could not be confidently identified and list numeric columns.

**Say:**

> “This is the most important behaviour. It does not silently pick a column and invent an answer. It refuses to guess. That is the difference between a demo and a usable analytical tool.”

You can also ask:

```text
What is the total?
```

It should clarify as well.

---

## G. Demo step 5 — Evaluation (60–90 seconds)

**Go to:** Evaluation.

**Say:**

> “The project includes an executable benchmark, not just screenshots. These 34 cases run through the exact same planner, validator and executor used by the chat page.”

Press **Run 34-case benchmark**.

Expected result: **34 / 34 passed, 100%** on this benchmark, with category breakdowns and individual results.

**Say:**

> “The expected values are calculated independently with pandas in the benchmark definition. Invalid-input cases must return a clarification or safe response, never a number. This is a 34-case project benchmark, not a claim of universal accuracy.”

Optional: point to the failure detail expander and say, “If a case failed, it would be shown here. The app does not hide failures.”

---

## H. Demo step 6 — Explorer and upload (optional, 45 seconds)

Only if time and the jury seems interested.

**Go to:** Data Explorer.

Show:

- inferred schema table
- search box
- column filter
- pagination
- download buttons

**Say:**

> “The same parsed dataset is fully inspectable. The user is not forced to trust only the chat answer.”

To demonstrate upload, use:

```text
datasets/03_healthcare_admissions.csv
```

Then ask:

```text
What is the total bill amount?
```

This is optional. Do not upload during a timed final unless you have rehearsed it.

---

## I. Close — 30 seconds

**Say:**

> “The pipeline is interpret, validate, execute, explain. The optional LLM layer only proposes a plan; it cannot run code, and it cannot bypass validation. The app is local by default, works without a key, and every result is exportable with its plan and method.”
>
> “The honest scope is a 34-case benchmark and 47 automated tests on this implementation. It handles common analytical questions on a single CSV; it is not a general-purpose reasoning engine. That trade-off is deliberate: we chose auditability and exact arithmetic over unconstrained generation.”

---

## J. Exact fallback questions

If a query clarifies unexpectedly, do not argue with the UI. Use one of these explicit variants:

| Goal | Fallback question |
|---|---|
| Total | `What is the total revenue?` |
| Average | `What is the average profit?` |
| Grouped | `Compare revenue across regions.` |
| Ranking | `Which category has the highest total profit?` |
| Trend | `Show monthly revenue trends.` |
| Outliers | `Are there any unusual values in revenue?` |
| Missing | `Are there any missing values?` |
| Row count | `How many records are there?` |
| Safe refusal | `What is the total foobar?` |

---

## K. Demo Mode shortcut

If you prefer a single screen:

1. Open **Demo Mode**.
2. Press **Reset demo**.
3. Use the numbered buttons:
   - `1 · Dataset overview`
   - `2 · Ranking`
   - `3 · Comparison`
   - `4 · Time series`
   - `5 · Anomalies`
4. Open **Presenter run sheet** for the built-in prompts.

Demo Mode runs the same real analyses as AI Analyst. It does not contain stored answers.

---

## L. Post-demo questions

Use `JURY_PREPARATION.md` for the full Q&A. The three most likely:

1. **“Where is the AI?”** → Optional LLM proposes a validated plan; calculations stay deterministic.
2. **“How do you prevent hallucination?”** → Clarification on ambiguity, schema validation, fixed executor, no generated code.
3. **“Is 100% real?”** → 34/34 on this benchmark, with independent expected values; 47 tests pass; not a universal accuracy claim.

---

## M. Emergency reset

If the app state becomes confusing:

1. Press **Reset demo** in Demo Mode.
2. If the browser is stuck, refresh the page. Built-in data reloads; session history is intentionally lost.
3. If the server died, restart:

```bash
streamlit run app.py
```

4. If a browser cache issue persists, use a private window.

The demo does not depend on network access unless you intentionally enable the optional LLM.
