# PRD — Logistics Analytics Copilot

## Original problem
Coding assignment: build an AI analytics copilot for one logistics client using mock_logistics_data.csv (400 orders, 2025). It needs a dashboard (descriptive), a natural-language Q&A (diagnostic), and forecast + stock recommendation (predictive/prescriptive). AI only interprets and routes; all numbers are computed by code; every answer is explainable. Plus a README and a public deployment. User (Indonesian) wanted the simplest spec that is explainable with their CV stack (Python/Pandas, REST API, Text-to-SQL bot, Looker/Power BI, regression).

## Architecture
- FastAPI backend. `analytics/`:
  - `data.py`: CSV read-only in memory, metric definitions, reference date 2025-12-31
  - `query_tool.py`: Pydantic QueryPlan → pandas
  - `forecast_tool.py`: linear regression vs MA3 chosen by backtest MAE, safety stock 1.65·σ·√h
  - `dashboard.py`
  - `ai_router.py`: Gemini function calling, single-turn, validation-retry loop, SSE
- React frontend: 3 tabs (Dashboard, Ask the Data, Forecast), Recharts, dark "control room" UI
- Gemini via the user's own GEMINI_API_KEY (secret). Model `gemini-3.1-flash-lite-preview`. ASK_AI_SUMMARY=false → 1 LLM call per question.
- No auth, no DB used.

## Implemented (2026-06)
- Dashboard: 5 KPIs, 4 charts, date/carrier/region filters
- Ask: example chips, status pipeline, auto chart (kpi/line/multi_line/donut/bar), data table + CSV, explain panel (raw AI args vs validated plan), honest decline + suggestions, session history (localStorage), in-memory cache, quota/503 handling, key redacted in logs
- Forecast: category/SKU/all, horizon 1–12, SKU→category fallback, band, stock recommendation, method explanation
- README (setup, architecture, AI approach, assumptions, limitations, AI-use disclosure), unit tests (backend/tests/test_tools.py)

## Backlog
- P1: follow-up questions with context; period comparison; deploy public URL
- P2: route lead time, promo impact, backtest chart, seasonal models, per-warehouse forecast
- P3: dataset upload, saved questions, delay-rate alerts
