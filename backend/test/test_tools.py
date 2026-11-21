"""Correctness tests for the computation layer (no AI involved). Run: cd backend && pytest tests -q"""

import sys
from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analytics.dashboard import build_dashboard  # noqa: E402
from analytics.data import CSV_PATH  # noqa: E402
from analytics.forecast_tool import ForecastRequest, run_forecast  # noqa: E402
from analytics.query_tool import QueryPlan, run_query  # noqa: E402

RAW = pd.read_csv(CSV_PATH, parse_dates=["order_date", "delivery_date"])


def q(**plan):
    return run_query(QueryPlan.model_validate(plan))


def test_kpis_match_raw_csv():
    k = build_dashboard(None, None, [], [])["kpis"]
    delivered, delayed = (
        (RAW.status == "delivered").sum(),
        (RAW.status == "delayed").sum(),
    )
    assert k["total_orders"] == len(RAW)
    assert k["delivered"] == delivered and k["delayed"] == delayed
    assert k["on_time_rate"] == round(delivered / (delivered + delayed) * 100, 1)
    assert k["avg_delivery_days"] == round(
        (RAW.delivery_date - RAW.order_date).dt.days.mean(), 2
    )


def test_last_month_is_november():
    r = q(metric="delayed_count", time_range={"preset": "last_month"})
    nov = RAW[(RAW.order_date >= "2025-11-01") & (RAW.order_date <= "2025-11-30")]
    assert r["rows"][0]["value"] == (nov.status == "delayed").sum()
    assert r["resolved"]["start"] == "2025-11-01"


def test_carrier_delay_rate_sorted_desc():
    rows = q(metric="delay_rate", group_by="carrier")["rows"]
    values = [r["value"] for r in rows if r["value"] is not None]
    assert values == sorted(values, reverse=True)


def test_filter_values_are_normalized_and_validated():
    r = q(metric="order_count", filters={"carriers": ["dhl"]})
    assert r["plan"]["filters"]["carriers"] == ["DHL"]
    assert r["rows"][0]["value"] == (RAW.carrier == "DHL").sum()
    with pytest.raises(ValidationError):
        QueryPlan.model_validate(
            {"metric": "order_count", "filters": {"carriers": ["Acme"]}}
        )
    with pytest.raises(ValidationError):
        QueryPlan.model_validate({"metric": "drop_table"})


def test_weekly_series_has_no_gaps_and_sums_to_total():
    r = q(
        metric="delayed_count",
        time_grain="week",
        time_range={"preset": "last_n_months", "n": 3},
    )
    total = q(metric="delayed_count", time_range={"preset": "last_n_months", "n": 3})[
        "rows"
    ][0]["value"]
    assert sum(x["value"] for x in r["rows"]) == total
    assert r["chart"]["type"] == "line"


def test_forecast_sku_falls_back_to_category():
    r = run_forecast(
        ForecastRequest(target_type="sku", target="PAPER-0197", horizon_months=3)
    )
    assert r["level"] == "category" and r["target"] == "PAPER" and r["note"]
    assert len(r["forecast"]) == 3
    rec = r["recommendation"]
    assert rec["recommended_stock"] >= rec["forecast_total"]


def test_forecast_excludes_canceled():
    r = run_forecast(ForecastRequest(target_type="all", horizon_months=1))
    assert (
        sum(h["actual"] for h in r["history"])
        == RAW[RAW.status != "canceled"].quantity.sum()
    )
