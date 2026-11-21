# Logistics Analytics Copilot

A web app for one logistics client. It has a KPI dashboard, a plain-English "Ask the Data" box and a demand forecast with a stock recommendation. All of it runs on `mock_logistics_data.csv` (400 orders, 2025).

**Core principle:** the AI (Gemini) only *interprets* the question and *routes* it to a tool with structured arguments. Every number, chart and forecast is computed by deterministic Python/Pandas code, and every answer shows how it was computed.

---

## 1. Setup

### Stack
- **Frontend:** React 19, Tailwind, shadcn/ui, Recharts
- **Backend:** Python, FastAPI, Pandas, NumPy
- **AI:** Google Gemini (Flash) through function calling, using the `emergentintegrations`/LiteLLM wrapper
- **Data:** `backend/data/mock_logistics_data.csv`. It is loaded once into memory and treated as read-only, so there is no DB for analytics.

### Run locally
```bash
# backend
cd backend
pip install -r requirements.txt
cp .env.example .env   # then fill GEMINI_API_KEY
uvicorn server:app --host 0.0.0.0 --port 8001

# frontend
cd frontend
yarn install
echo "REACT_APP_BACKEND_URL=http://localhost:8001" > .env
yarn start
```

### Environment variables
| Var | Where | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | backend | Google AI Studio key. If it is missing, Ask shows "AI unavailable", and Dashboard and Forecast keep working. |
| `GEMINI_MODEL` | backend | Gemini model id, e.g. `gemini-3.1-flash-lite-preview` (fast, generous free quota; any Gemini model with function calling works) |
| `ASK_AI_SUMMARY` | backend | `false` (default): one Gemini call per question; the answer text is the code-generated headline. `true`: a second call rewrites it in natural language (numbers still only from the result). |
| `CORS_ORIGINS` | backend | Allowed origins (`*` for demo) |
| `REACT_APP_BACKEND_URL` | frontend | Base URL of the API |

Secrets are never committed. `.env` files are git-ignored.

### Tests
```bash
cd backend && pytest tests -q
```
The tests check KPI values against the raw CSV. They also cover relative date resolution, filter validation (unknown values and illegal metrics are rejected), weekly series completeness, the SKU→category forecast fallback, and excluding canceled orders from demand.

---

## 2. Architecture

```
            ┌──────────── React (3 tabs) ────────────┐
            │ Dashboard │ Ask the Data │ Forecast     │
            └─────┬───────────┬──────────────┬───────┘
     GET /api/dashboard   POST /api/ask (SSE)   POST /api/forecast
            │              │                    │
            │      ┌───────▼────────┐           │
            │      │  AI router     │  Gemini: interpret + pick tool
            │      │ (ai_router.py) │  -> structured JSON args only
            │      └───────┬────────┘
            │       Pydantic validation (QueryPlan / ForecastRequest)
            │              │  invalid -> error sent back to AI to fix (max 3 rounds)
     ┌──────▼──────────────▼────────────────────▼──────┐
     │  Computation layer (pure Python / Pandas)       │
     │  query_tool.py · forecast_tool.py · dashboard.py│
     └──────────────────────┬──────────────────────────┘
                     data.py (CSV, read-only, in memory)
```

The three layers are kept separate on purpose:
- **AI interpretation:** `analytics/ai_router.py`. It holds the system prompt and the tool schemas, and drives the tool loop.
- **Data computation:** `analytics/query_tool.py`, `analytics/forecast_tool.py` and `analytics/dashboard.py`. None of these import any AI code.
- **Business logic and definitions:** `analytics/data.py`. It holds the metric definitions, the reference date and the shared filters.

### Ask flow (data flow)
1. The user asks: *"Show delayed orders by week for the last 3 months"*.
2. Gemini receives the question, the dataset schema and the allowed values. It must call exactly one tool:
   - `run_query(metric, group_by, time_grain, time_range, filters, sort, limit)`
   - `run_forecast(target_type, target, horizon_months)`
   - `decline_question(reason, kind, suggestions)`
3. The backend validates the arguments with Pydantic:
   - Enums are enforced.
   - Filter values are matched case-insensitively to real dataset values. Unknown values are rejected and the allowed list goes back to the AI.
4. The tool computes the result with Pandas and returns:
   - rows and columns
   - a chart spec (chosen by code from the shape of the result)
   - a deterministic `headline`
   - the resolved date range
   - the metric definition and the number of rows scanned
5. The answer sentence is the deterministic headline from code. With `ASK_AI_SUMMARY=true`, Gemini gets a compact result in a second single-turn call and rewrites it as 1–2 sentences, told to use only those numbers; the code headline is still shown under it so the wording can be checked. A quota or provider error is shown as such and never becomes a fabricated answer.
6. The response streams as Server-Sent Events: `status → tool → result → answer`. The UI shows these steps as a pipeline.

### Key design decisions and tradeoffs
- **No AI-generated SQL.** The AI fills a small, typed query plan, which keeps the set of possible queries small and checkable. The tradeoff is that only questions the plan can express are supported (see Limitations). For this assignment that is correct and safe.
- **Pandas in memory instead of a database.** 400 rows load instantly. Postgres would add operational weight and no correctness benefit. In production, the same `QueryPlan` could be compiled to parameterised SQL.
- **The chart type is chosen by code, not by the AI:**
  - a single value → KPI card
  - a time series → line
  - time × dimension → multi-line
  - a small additive breakdown (≤6 groups) → donut
  - anything else → horizontal bar
- **Caching:** identical questions (normalised) are replayed from an in-memory cache, with no second AI call.
- **Query history:** each session's questions are kept in localStorage. Clicking one restores its full result.

---

## 3. AI approach

### How questions are interpreted
The system prompt gives Gemini:
- the schema and the allowed values (carriers, regions, statuses, categories, warehouses, origins)
- the metric definitions
- explicit mapping rules, e.g. "late" → `delayed_count`, "Q3" → `preset=quarter, quarter=3`, "top 5" → `limit=5, sort=desc`, "inventory / stock planning" → `run_forecast`

### How tools are selected
| Intent | Tool |
|---|---|
| Counts, rates, averages, sums, breakdowns, trends | `run_query` |
| Future demand, predictions, how much stock to plan | `run_forecast` |
| Causes not in the data (weather), years other than 2025, writing data, chit-chat, unclear questions | `decline_question` → "not supported" with suggested questions |

Guardrails:
- If the model answers with text and no tool call, the reply is shown as "needs a clearer question". It is never shown as a data answer.
- Invalid arguments get a structured validation error back, and the model may correct them up to 3 times. Rejected attempts are shown in the explainability panel.
- If the provider fails after the computation has finished, the code-generated headline is shown instead of the AI summary.

### Explainability (shown for every answer)
- The tool used, the resolved time range and the reference date
- Active filters, the metric with its definition, and the dimensions
- The **raw AI tool arguments**, shown next to the **validated, executed plan** (JSON)
- Rows matched, the result row count and the reason for the chart choice
- A data table with CSV download

---

## 4. Forecasting method
- **Demand** = the sum of `quantity` per order month, with canceled orders excluded.
- **Level:** product category, or total demand. A SKU is forecast on its own only if it has demand in at least 6 of 12 months. Otherwise the tool falls back to the SKU's category and says so. In this dataset no SKU has enough history, because there are 355 SKUs across 400 orders.
- **Two candidate models:**
  - linear regression on month index
  - a 3-month moving average
- **Model selection:** a rolling one-step-ahead back-test from month 4 onwards. Each month is predicted only from the months before it, and the model with the lower MAE is used.
- **Range:** forecast ± 1.65 × σ, where σ is the standard deviation of the back-test errors.
- **Safety stock** = 1.65 × σ × √horizon, which gives roughly a 95% service level.
- **Recommended stock** = forecast total + safety stock.

---

## 5. Assumptions, limitations and unsupported queries

**Assumptions**
- **"Today" is 2025-12-31,** the end of the dataset, not the real calendar date. So:
  - "last month" = November 2025
  - "this month" = December 2025
  - "last 3 months" = Oct 1 to Dec 31
  - weeks start on Monday
- **Status-based metrics:**
  - delayed = status `delayed`; delivered = status `delivered`
  - on-time rate = delivered / (delivered + delayed). `exception`, `in_transit` and `canceled` count in total orders but not in the rates.
  - "Delivered late" = status `delayed`, because the dataset has no promised delivery date.
- **Delivery time** = `delivery_date − order_date` in days, only for orders that have a `delivery_date` (delivered, delayed and exception).

**Limitations**
- There is one query per question and no follow-up context ("now only for DHL").
- There are no period-over-period comparisons in a single answer, and no route-level (origin→destination) metric.
- The data is too short and sparse for seasonality. Forecasts of a few units per month are indicative only.

**Unsupported, answered with an honest "not supported" message:**
- causal "why" questions (weather, traffic)
- data that is not in the CSV (costs, SLA dates, customer satisfaction)
- years other than 2025
- any request to modify data

---

## 6. Future improvements
1. Follow-up questions with conversation context, and period comparisons (this month vs last month).
2. More plan shapes: route lead times, and promo impact on volume.
3. Showing the forecast back-test on screen, plus exponential smoothing or seasonal models and forecasts per warehouse.
4. Moving to Postgres, compiling `QueryPlan` → parameterised SQL, and supporting uploads of new datasets (read-only).
5. Alerts when a carrier's delay rate crosses a threshold, and saved/shared questions.

---

## 7. AI usage disclosure
AI tools were used while building this project:
- an AI coding assistant (Emergent) helped write and scaffold the code and this README
- design guidelines were generated with an AI design helper

The architecture, metric definitions, assumptions and forecasting choices were reviewed and are explained above. At runtime, Gemini is used only for question routing, as described in section 3.
