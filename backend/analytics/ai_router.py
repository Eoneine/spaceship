"""AI layer: Gemini only interprets the question and picks a tool + structured arguments.
All numbers come from query_tool / forecast_tool."""

import asyncio
import json
import logging
import os
import re
import uuid
from typing import AsyncIterator

from emergentintegrations.llm.chat import (
    ChatError,
    LlmChat,
    StreamDone,
    TextDelta,
    ToolCallReady,
    UserMessage,
)
from pydantic import ValidationError

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


def ai_available() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


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


SUMMARY_ENABLED = os.environ.get("ASK_AI_SUMMARY", "false").lower() == "true"


def _redact(text: str) -> str:
    return re.sub(r"key=[\w-]+", "key=***", text).replace(
        os.environ.get("GEMINI_API_KEY", "@@"), "***"
    )


def _provider_error(e: Exception) -> dict:
    msg = str(e)
    log.error("gemini call failed: %s", _redact(msg)[:300])
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
        return {
            "type": "error",
            "code": "ai_quota",
            "message": "Gemini quota exceeded for this API key. Try again later; Dashboard and Forecast still work.",
        }
    return {
        "type": "error",
        "code": "ai_error",
        "message": "AI unavailable right now. Try again or use the Dashboard/Forecast tabs.",
    }


def _chat(system: str, tools: bool):
    chat = LlmChat(
        api_key=os.environ["GEMINI_API_KEY"],
        session_id=str(uuid.uuid4()),
        system_message=system,
    ).with_model("gemini", os.environ["GEMINI_MODEL"])
    return chat.with_tools(TOOLS, tool_choice="auto") if tools else chat


SUMMARY_PROMPT = (
    "You summarise computed logistics analytics results. Reply in 1-2 plain sentences using ONLY "
    "numbers present in the RESULT. Mention the period. No markdown, no speculation."
)


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
            async for ev in _chat(SYSTEM_PROMPT, True).stream_message(
                UserMessage(text=text)
            ):
                if isinstance(ev, TextDelta):
                    out.append(ev.content)
                elif isinstance(ev, ToolCallReady):
                    calls.append(ev.tool_call)
                elif isinstance(ev, StreamDone):
                    break
            break
        except ChatError as e:
            if attempt or not (
                "503" in str(e)
                or "overloaded" in str(e).lower()
                or "high demand" in str(e).lower()
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
            "message": "AI unavailable: no Gemini API key configured. Dashboard and Forecast still work.",
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
    except ChatError as e:  # provider errors, quota, network
        yield _provider_error(e)
        return
    if not SUMMARY_ENABLED:
        yield {"type": "done", "answer": result["headline"]}
        return
    try:
        parts = []
        prompt = f"QUESTION: {question}\nRESULT: {_compact(result)}"
        async for ev in _chat(SUMMARY_PROMPT, False).stream_message(
            UserMessage(text=prompt)
        ):
            if isinstance(ev, TextDelta):
                parts.append(ev.content)
                yield {"type": "delta", "text": ev.content}
            elif isinstance(ev, StreamDone):
                break
        yield {"type": "done", "answer": "".join(parts).strip() or result["headline"]}
    except ChatError as e:
        log.error("summary failed: %s", _redact(str(e))[:300])
        yield {
            "type": "done",
            "answer": result["headline"],
            "warning": "AI summary unavailable; showing computed headline.",
        }
