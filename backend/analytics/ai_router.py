"""AI layer: LLM only interprets the question and picks a tool + structured arguments.
All numbers come from query_tool / forecast_tool."""

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from types import SimpleNamespace
from typing import AsyncIterator

from dotenv import load_dotenv
from openai import APIError, OpenAI, RateLimitError
from pydantic import ValidationError

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

from .data import DIMENSION_VALUES, METRIC_DEFINITIONS, REFERENCE_DATE
from .forecast_tool import ForecastRequest, run_forecast
from .query_tool import QueryPlan, run_query

log = logging.getLogger(__name__)
MAX_TOOL_ROUNDS = 3

SUGGESTIONS = [
    "Which carrier has the highest delay rate?",
    "Show delayed orders by week for the last 3 months",
    "Average delivery time by region",
    "Predict demand for PAPER for the next 4 months",
]

_list = lambda k: ", ".join(DIMENSION_VALUES[k])  # noqa: E731

SYSTEM_PROMPT = f"""You are the routing layer of a logistics analytics app. You NEVER compute or invent numbers.
For every user question call EXACTLY ONE tool:
- run_query: descriptive/diagnostic questions (counts, rates, averages, sums, breakdowns, trends).
- run_forecast: future demand, predictions, inventory / stock planning.
- decline_question: anything the dataset cannot answer (causes like weather, data not in the dataset,
  years other than 2025, writing/changing data, general chit-chat) or a question too ambiguous to map.

Dataset: one client's 400 orders, order dates 2025-01-01 to 2025-12-30. Read-only.
Columns: order_date, delivery_date, carrier, origin_city, destination_city, status, sku, product_category,
quantity, order_value_usd, is_promo, region, warehouse, client_id.
Allowed values:
- carrier: {_list("carrier")}
- region: {_list("region")}
- status: {_list("status")}
- product_category: {_list("product_category")}
- warehouse: {_list("warehouse")}
- origin_city: {_list("origin_city")}
Metric definitions: {json.dumps(METRIC_DEFINITIONS)}

Rules:
- Today's reference date is {REFERENCE_DATE} (end of dataset). "last month" = preset last_month (November 2025),
  "this month" = December 2025, "last 3 months" = last_n_months n=3, "Q3" = preset quarter, quarter=3,
  "in March" = preset month, month=3. No time words = preset all.
- "late"/"delayed" = metric delayed_count (or delay_rate for rates). "on time" = on_time_rate.
- "volume"/"how many orders" = order_count. "revenue"/"value" = total_order_value. "units"/"demand so far" = total_quantity.
- "by week/month/day/quarter" or "trend"/"over time" -> time_grain. "by carrier/region/..." -> group_by.
- "Top N" -> limit N with sort desc; "bottom/lowest N" -> sort asc.
- destination cities look like "Leeds, UK"; a city name prefix is fine.
- For forecasts: target_type category with a product_category, sku for codes like PAPER-0197, all for total demand.
  Default horizon 3 months if not given.
- Never answer with numbers yourself; always call a tool.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_query",
            "description": "Aggregate the logistics orders. Returns computed rows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "enum": list(METRIC_DEFINITIONS)},
                    "group_by": {
                        "type": "string",
                        "enum": [
                            "none",
                            "carrier",
                            "region",
                            "status",
                            "product_category",
                            "warehouse",
                            "destination_city",
                            "origin_city",
                            "client_id",
                            "is_promo",
                        ],
                    },
                    "time_grain": {
                        "type": "string",
                        "enum": ["none", "day", "week", "month", "quarter"],
                    },
                    "time_range": {
                        "type": "object",
                        "properties": {
                            "preset": {
                                "type": "string",
                                "enum": [
                                    "all",
                                    "last_n_days",
                                    "last_n_weeks",
                                    "last_n_months",
                                    "last_month",
                                    "this_month",
                                    "quarter",
                                    "month",
                                    "custom",
                                ],
                            },
                            "n": {"type": "integer"},
                            "quarter": {"type": "integer"},
                            "month": {"type": "integer"},
                            "start": {
                                "type": "string",
                                "description": "YYYY-MM-DD, preset custom only",
                            },
                            "end": {
                                "type": "string",
                                "description": "YYYY-MM-DD, preset custom only",
                            },
                        },
                        "required": ["preset"],
                    },
                    "filters": {
                        "type": "object",
                        "properties": {
                            k: {"type": "array", "items": {"type": "string"}}
                            for k in [
                                "carriers",
                                "regions",
                                "statuses",
                                "categories",
                                "warehouses",
                                "destination_cities",
                                "origin_cities",
                                "client_ids",
                            ]
                        }
                        | {"is_promo": {"type": "boolean"}},
                    },
                    "sort": {"type": "string", "enum": ["desc", "asc"]},
                    "limit": {"type": "integer"},
                },
                "required": ["metric"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_forecast",
            "description": "Forecast monthly demand (units) and recommend inventory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_type": {
                        "type": "string",
                        "enum": ["category", "sku", "all"],
                    },
                    "target": {
                        "type": "string",
                        "description": "Category (e.g. PAPER) or SKU (e.g. PAPER-0197)",
                    },
                    "horizon_months": {"type": "integer", "description": "1-12"},
                },
                "required": ["target_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "decline_question",
            "description": "Use when the question cannot be answered from this dataset or is too ambiguous.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Short, honest reason"},
                    "kind": {"type": "string", "enum": ["unsupported", "ambiguous"]},
                    "suggestions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "1-3 supported questions the user could ask instead",
                    },
                },
                "required": ["reason", "kind"],
            },
        },
    },
]


DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "anthropic/claude-sonnet-4"


def ai_available() -> bool:
    load_dotenv(ENV_PATH, override=True)
    return bool(os.environ.get("LLM_API_KEY", "").strip())


def _execute(name: str, args: dict) -> dict:
    if name == "run_query":
        return run_query(QueryPlan.model_validate(args))
    return run_forecast(ForecastRequest.model_validate(args))


def _compact(result: dict) -> str:
    """What the model sees after computation (rows capped)."""
    keep = {
        k: result[k]
        for k in (
            "tool",
            "headline",
            "resolved",
            "metric_label",
            "note",
            "recommendation",
            "method_label",
            "forecast",
        )
        if k in result
    }
    if "rows" in result:
        keep["rows"] = result["rows"][:25]
        keep["row_count"] = len(result["rows"])
    return json.dumps(keep, default=str)


def _summary_enabled() -> bool:
    load_dotenv(ENV_PATH, override=True)
    return os.environ.get("ASK_AI_SUMMARY", "false").lower() == "true"


def _redact(text: str) -> str:
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    redacted = re.sub(r"key=[\w-]+", "key=***", text)
    return redacted.replace(api_key, "***") if api_key else redacted


def _provider_error(e: Exception) -> dict:
    msg = str(e)
    log.error("llm call failed: %s", _redact(msg)[:300])
    if (
        isinstance(e, RateLimitError)
        or "429" in msg
        or "quota" in msg.lower()
        or "rate limit" in msg.lower()
        or "credit" in msg.lower()
    ):
        return {
            "type": "error",
            "code": "ai_quota",
            "message": "AI quota or rate limit exceeded for this API key. Try again later; Dashboard and Forecast still work.",
        }
    return {
        "type": "error",
        "code": "ai_error",
        "message": "AI unavailable right now. Try again or use the Dashboard/Forecast tabs.",
    }


def _model() -> str:
    load_dotenv(ENV_PATH, override=True)
    return os.environ.get("LLM_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _client() -> OpenAI:
    load_dotenv(ENV_PATH, override=True)
    base_url = os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
    headers = {}
    if site_url := os.environ.get("OPENROUTER_SITE_URL", "").strip():
        headers["HTTP-Referer"] = site_url
    if app_name := os.environ.get("OPENROUTER_APP_NAME", "").strip():
        headers["X-Title"] = app_name
    return OpenAI(
        base_url=base_url,
        api_key=os.environ["LLM_API_KEY"].strip(),
        default_headers=headers or None,
    )


SUMMARY_PROMPT = (
    "You summarise computed logistics analytics results. Reply in 1-2 plain sentences using ONLY "
    "numbers present in the RESULT. Mention the period. No markdown, no speculation."
)


def _route_completion(model: str, text: str):
    client = _client()
    return client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        tools=TOOLS,
        tool_choice="auto",
    )


def _summary_stream(model: str, prompt: str) -> list[str]:
    client = _client()
    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": prompt},
        ],
        stream=True,
    )
    chunks: list[str] = []
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            chunks.append(chunk.choices[0].delta.content)
    return chunks


async def _route(question: str, attempts: list):
    """Single-turn routing call; previous invalid attempts are fed back in the prompt."""
    text = question
    if attempts:
        text += (
            "\n\nYour previous tool arguments were rejected:\n"
            + "\n".join(f"- {json.dumps(a['args'])} -> {a['error']}" for a in attempts)
            + "\nCall the tool again with fixed arguments."
        )
    calls, out = [], []
    for attempt in range(2):
        try:
            resp = await asyncio.to_thread(_route_completion, _model(), text)
            msg = resp.choices[0].message if resp.choices else None
            if msg and msg.tool_calls:
                for tc in msg.tool_calls:
                    raw_args = tc.function.arguments or "{}"
                    try:
                        parsed = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
                    except json.JSONDecodeError:
                        parsed = {}
                    calls.append(SimpleNamespace(name=tc.function.name, arguments=parsed))
            if msg and msg.content:
                out.append(msg.content)
            break
        except APIError as e:
            if attempt or not (
                "502" in str(e)
                or "503" in str(e)
                or "overloaded" in str(e).lower()
                or "high demand" in str(e).lower()
                or "unavailable" in str(e).lower()
            ):
                raise
            calls, out = [], []
            await asyncio.sleep(1.5)
    return calls, "".join(out).strip()


async def ask(question: str) -> AsyncIterator[dict]:
    if not ai_available():
        yield {
            "type": "error",
            "code": "ai_unavailable",
            "message": "AI unavailable: no LLM API key configured. Dashboard and Forecast still work.",
        }
        return
    yield {"type": "status", "step": "interpreting"}
    result, attempts = None, []
    try:
        for _ in range(MAX_TOOL_ROUNDS):
            calls, text = await _route(question, attempts)
            if not calls:
                yield {
                    "type": "unsupported",
                    "kind": "ambiguous",
                    "suggestions": SUGGESTIONS,
                    "reason": text
                    or "I could not map this question to a supported query.",
                }
                return
            tc = calls[0]
            if tc.name == "decline_question":
                a = tc.arguments
                yield {
                    "type": "unsupported",
                    "kind": a.get("kind", "unsupported"),
                    "reason": a.get("reason", "Not supported by this dataset."),
                    "suggestions": a.get("suggestions") or SUGGESTIONS,
                    "tool_args": a,
                }
                return
            yield {"type": "tool", "name": tc.name, "args": tc.arguments}
            yield {"type": "status", "step": "computing"}
            try:
                result = _execute(tc.name, tc.arguments)
                break
            except ValidationError as e:
                err = "; ".join(
                    f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()
                )
                attempts.append({"args": tc.arguments, "error": err})
                yield {"type": "validation_error", "error": err}
                yield {"type": "status", "step": "interpreting"}
        if not result:
            yield {
                "type": "unsupported",
                "kind": "ambiguous",
                "suggestions": SUGGESTIONS,
                "reason": "I could not build a valid query for this question after several attempts.",
            }
            return
        result["ai_tool_args"] = tc.arguments
        result["validation_attempts"] = attempts
        yield {"type": "result", "result": result}
        yield {"type": "status", "step": "summarizing"}
    except (APIError, Exception) as e:  # provider errors, quota, network
        yield _provider_error(e)
        return
    if not _summary_enabled():
        yield {"type": "done", "answer": result["headline"]}
        return
    try:
        parts = []
        prompt = f"QUESTION: {question}\nRESULT: {_compact(result)}"
        chunks = await asyncio.to_thread(_summary_stream, _model(), prompt)
        for text_chunk in chunks:
            parts.append(text_chunk)
            yield {"type": "delta", "text": text_chunk}
        yield {"type": "done", "answer": "".join(parts).strip() or result["headline"]}
    except (APIError, Exception) as e:
        log.error("summary failed: %s", _redact(str(e))[:300])
        yield {
            "type": "done",
            "answer": result["headline"],
            "warning": "AI summary unavailable; showing computed headline.",
        }
