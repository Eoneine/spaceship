import json
import os

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")


@pytest.fixture(scope="module")
def s():
    return requests.Session()


# Meta endpoint
def test_meta(s):
    r = s.get(f"{BASE_URL}/api/meta", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["rows"] == 400
    assert d["reference_date"] == "2025-12-31"
    assert "DHL" in d["carriers"] and "GLS" in d["carriers"]
    assert "PAPER" in d["categories"] and "BOOK" in d["categories"]
    assert len(d["skus"]) > 0
    assert d["ai_available"] is True
    assert len(d["examples"]) == 8


# Dashboard KPIs
def test_dashboard_all(s):
    d = s.get(f"{BASE_URL}/api/dashboard", timeout=30).json()
    k = d["kpis"]
    assert k["total_orders"] == 400
    assert k["delivered"] == 304
    assert k["delayed"] == 55
    assert k["on_time_rate"] == 84.7
    assert round(k["avg_delivery_days"], 2) == 3.83
    assert len(d["monthly"]) == 12
    assert sum(m["orders"] for m in d["monthly"]) == 400
    assert d["by_carrier"] and d["by_region"]


def test_dashboard_dhl(s):
    d = s.get(f"{BASE_URL}/api/dashboard", params={"carrier": "DHL"}, timeout=30).json()
    assert d["kpis"]["total_orders"] == 63
    assert d["kpis"]["on_time_rate"] == 94.7
    assert all(c["carrier"] == "DHL" for c in d["by_carrier"])


def test_dashboard_date_range(s):
    d = s.get(
        f"{BASE_URL}/api/dashboard",
        params={"start": "2025-07-01", "end": "2025-09-30"},
        timeout=30,
    ).json()
    assert len(d["monthly"]) == 3
    assert d["kpis"]["total_orders"] == sum(m["orders"] for m in d["monthly"])


def test_dashboard_bad_date(s):
    r = s.get(f"{BASE_URL}/api/dashboard", params={"start": "notadate"}, timeout=30)
    assert r.status_code == 422


def test_dashboard_unknown_carrier_empty(s):
    r = s.get(f"{BASE_URL}/api/dashboard", params={"carrier": "Acme"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["kpis"]["total_orders"] == 0


# Query tool
def test_query_carrier_delay_rate(s):
    r = s.post(
        f"{BASE_URL}/api/query",
        json={"metric": "delay_rate", "group_by": "carrier"},
        timeout=30,
    )
    assert r.status_code == 200
    d = r.json()
    assert d["rows"][0]["carrier"] == "GLS"
    assert d["rows"][0]["value"] == 28.57 or round(d["rows"][0]["value"], 1) == 28.6


def test_query_last_month_delayed(s):
    r = s.post(
        f"{BASE_URL}/api/query",
        json={"metric": "delayed_count", "time_range": {"preset": "last_month"}},
        timeout=30,
    )
    d = r.json()
    assert d["rows"][0]["value"] == 4
    assert d["chart"]["type"] == "kpi"
    assert d["resolved"]["start"] == "2025-11-01"


def test_query_weekly_last3(s):
    r = s.post(
        f"{BASE_URL}/api/query",
        json={
            "metric": "delayed_count",
            "time_grain": "week",
            "time_range": {"preset": "last_n_months", "n": 3},
        },
        timeout=30,
    )
    d = r.json()
    assert d["chart"]["type"] == "line"
    assert sum(x["value"] for x in d["rows"]) == 10


def test_query_top5_destinations(s):
    r = s.post(
        f"{BASE_URL}/api/query",
        json={
            "metric": "total_order_value",
            "group_by": "destination_city",
            "limit": 5,
        },
        timeout=30,
    )
    d = r.json()
    assert len(d["rows"]) == 5
    vals = [x["value"] for x in d["rows"]]
    assert vals == sorted(vals, reverse=True)


def test_query_invalid_carrier(s):
    r = s.post(
        f"{BASE_URL}/api/query",
        json={"metric": "order_count", "filters": {"carriers": ["Acme"]}},
        timeout=30,
    )
    assert r.status_code == 422


def test_query_invalid_metric(s):
    r = s.post(f"{BASE_URL}/api/query", json={"metric": "profit"}, timeout=30)
    assert r.status_code == 422


def test_query_missing_n(s):
    r = s.post(
        f"{BASE_URL}/api/query",
        json={"metric": "order_count", "time_range": {"preset": "last_n_days"}},
        timeout=30,
    )
    assert r.status_code == 422


# Forecast tool
def test_forecast_paper(s):
    r = s.post(
        f"{BASE_URL}/api/forecast",
        json={"target_type": "category", "target": "PAPER", "horizon_months": 4},
        timeout=30,
    )
    assert r.status_code == 200
    d = r.json()
    assert len(d["forecast"]) == 4
    assert len(d["history"]) == 12
    rec = d["recommendation"]
    assert rec["recommended_stock"] >= rec["forecast_total"]
    assert d["method"] in ("linear_regression", "moving_average_3")


def test_forecast_sku_fallback(s):
    meta = s.get(f"{BASE_URL}/api/meta", timeout=30).json()
    sku = next(x for x in meta["skus"] if x.startswith("BOOK"))
    d = s.post(
        f"{BASE_URL}/api/forecast",
        json={"target_type": "sku", "target": sku, "horizon_months": 3},
        timeout=30,
    ).json()
    assert d["note"] is not None and "BOOK" in d["note"]
    assert d["level"] == "category"


def test_forecast_invalid(s):
    r = s.post(
        f"{BASE_URL}/api/forecast",
        json={"target_type": "category", "target": "FOOD"},
        timeout=30,
    )
    assert r.status_code == 422
    r = s.post(
        f"{BASE_URL}/api/forecast",
        json={"target_type": "all", "horizon_months": 20},
        timeout=30,
    )
    assert r.status_code == 422


# Ask SSE (1 real Gemini call)
def test_ask_sse(s):
    r = s.post(
        f"{BASE_URL}/api/ask",
        json={"question": "Which carrier has the highest delay rate?"},
        stream=True,
        timeout=90,
    )
    assert r.status_code == 200
    events = []
    for line in r.iter_lines(decode_unicode=True):
        if line and line.startswith("data: "):
            events.append(json.loads(line[6:]))
    types = [e["type"] for e in events]
    assert "result" in types, types
    res = next(e for e in events if e["type"] == "result")["result"]
    assert res["rows"][0]["carrier"] == "GLS"
    assert types[-1] == "done"


def test_ask_validation(s):
    r = s.post(f"{BASE_URL}/api/ask", json={"question": "a"}, timeout=30)
    assert r.status_code == 422
