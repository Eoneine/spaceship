import json
import logging
from datetime import date
from typing import List, Optional

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env", override=True)

from fastapi import APIRouter, FastAPI, HTTPException, Query  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from pydantic import BaseModel, Field, ValidationError  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402
import os  # noqa: E402

from analytics import ai_router  # noqa: E402
from analytics.dashboard import build_dashboard  # noqa: E402
from analytics.data import DF, DIMENSION_VALUES, METRIC_DEFINITIONS, REFERENCE_DATE  # noqa: E402
from analytics.forecast_tool import ForecastRequest, run_forecast  # noqa: E402
from analytics.query_tool import QueryPlan, run_query  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(title="Logistics Analytics Copilot")
api = APIRouter(prefix="/api")
_ask_cache: dict = {}


class AskBody(BaseModel):
    question: str = Field(min_length=2, max_length=500)


@api.get("/")
async def root():
    return {"status": "ok"}


@api.get("/meta")
async def meta():
    sku_counts = DF.groupby("sku")["order_date"].apply(
        lambda s: s.dt.to_period("M").nunique()
    )
    return {
        "date_min": str(DF["order_date"].min().date()),
        "date_max": str(DF["order_date"].max().date()),
        "reference_date": str(REFERENCE_DATE),
        "rows": int(len(DF)),
        "carriers": DIMENSION_VALUES["carrier"],
        "regions": DIMENSION_VALUES["region"],
        "categories": DIMENSION_VALUES["product_category"],
        "skus": sorted(sku_counts.index.tolist()),
        "metric_definitions": METRIC_DEFINITIONS,
        "ai_available": ai_router.ai_available(),
        "examples": [
            "Show delayed orders by week for the last 3 months",
            "Which carrier has the highest delay rate?",
            "How many orders were delivered late last month?",
            "Average delivery time by region",
            "Top 5 destinations by order value",
            "Order volume by category in Q3",
            "Predict demand for PAPER for the next 4 months",
            "How much inventory should I plan for BOOK?",
        ],
    }


@api.get("/dashboard")
async def dashboard(
    start: Optional[date] = None,
    end: Optional[date] = None,
    carrier: List[str] = Query(default=[]),
    region: List[str] = Query(default=[]),
):
    return build_dashboard(start, end, carrier, region)


@api.post("/query")
async def query(plan: QueryPlan):
    return run_query(plan)


@api.post("/forecast")
async def forecast(body: dict):
    try:
        return run_forecast(ForecastRequest.model_validate(body))
    except ValidationError as e:
        raise HTTPException(422, detail=[x["msg"] for x in e.errors()])


@api.post("/ask")
async def ask(body: AskBody):
    key = " ".join(body.question.lower().split())

    async def gen():
        if key in _ask_cache:
            for ev in _ask_cache[key]:
                yield f"data: {json.dumps({**ev, 'cached': True}, default=str)}\n\n"
            return
        events = []
        async for ev in ai_router.ask(body.question):
            events.append(ev)
            yield f"data: {json.dumps(ev, default=str)}\n\n"
        if events and events[-1]["type"] == "done" and "warning" not in events[-1]:
            _ask_cache[key] = [e for e in events if e["type"] != "delta"]

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
