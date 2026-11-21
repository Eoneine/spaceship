"""Forecast Tool: monthly demand (units) -> linear trend vs 3-month moving average."""

import math
from typing import Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, model_validator

from .data import DF, DIMENSION_VALUES

Z_95 = 1.65
MIN_SKU_MONTHS = 6
CATEGORIES = DIMENSION_VALUES["product_category"]


class ForecastRequest(BaseModel):
    target_type: Literal["category", "sku", "all"] = "category"
    target: str = ""
    horizon_months: int = Field(3, ge=1, le=12)

    @model_validator(mode="after")
    def _normalize(self):
        t = self.target.strip().upper()
        if self.target_type == "all":
            self.target = "ALL"
        elif self.target_type == "category":
            if t not in CATEGORIES:
                raise ValueError(
                    f"Unknown category '{self.target}'. Allowed: {', '.join(CATEGORIES)}"
                )
            self.target = t
        else:
            if t not in set(DF["sku"]):
                raise ValueError(
                    f"Unknown SKU '{self.target}'. SKUs look like 'PAPER-0197'."
                )
            self.target = t
        return self


def _monthly(df: pd.DataFrame) -> pd.Series:
    months = pd.period_range("2025-01", "2025-12", freq="M")
    s = df.groupby(df["order_date"].dt.to_period("M"))["quantity"].sum()
    return s.reindex(months, fill_value=0).astype(float)


def _linear(y: np.ndarray, steps: int) -> np.ndarray:
    t = np.arange(len(y))
    slope, intercept = np.polyfit(t, y, 1)
    return intercept + slope * np.arange(len(y), len(y) + steps)


def _ma3(y: np.ndarray, steps: int) -> np.ndarray:
    return np.repeat(y[-3:].mean(), steps)


def _backtest(y: np.ndarray, fn) -> np.ndarray:
    """One-step-ahead rolling errors from month 4 onwards (fit only on the past)."""
    return np.array([y[i] - fn(y[:i], 1)[0] for i in range(3, len(y))])


def run_forecast(req: ForecastRequest) -> dict:
    base = DF[DF["status"] != "canceled"]
    level, note = req.target_type, None
    if req.target_type == "sku":
        sku_series = _monthly(base[base["sku"] == req.target])
        active = int((sku_series > 0).sum())
        if active >= MIN_SKU_MONTHS:
            series = sku_series
        else:
            cat = req.target.split("-")[0]
            note = (
                f"SKU {req.target} has demand in only {active} of 12 months (need >= {MIN_SKU_MONTHS}), "
                f"so the forecast uses its category trend ({cat})."
            )
            level, series = "category", _monthly(base[base["product_category"] == cat])
            req = ForecastRequest(
                target_type="category", target=cat, horizon_months=req.horizon_months
            )
    elif req.target_type == "category":
        series = _monthly(base[base["product_category"] == req.target])
    else:
        series = _monthly(base)

    y = series.values
    h = req.horizon_months
    errs = {
        "linear_regression": _backtest(y, _linear),
        "moving_average_3": _backtest(y, _ma3),
    }
    mae = {k: round(float(np.abs(v).mean()), 2) for k, v in errs.items()}
    method = min(mae, key=mae.get)
    preds = np.clip((_linear if method == "linear_regression" else _ma3)(y, h), 0, None)
    sigma = float(errs[method].std(ddof=1))
    band = Z_95 * sigma

    future = pd.period_range("2026-01", periods=h, freq="M")
    forecast = [
        {
            "month": str(m),
            "forecast": round(float(p), 1),
            "lower": round(max(0.0, p - band), 1),
            "upper": round(float(p + band), 1),
        }
        for m, p in zip(future, preds)
    ]
    total = float(preds.sum())
    safety = Z_95 * sigma * math.sqrt(h)
    slope = float(np.polyfit(np.arange(len(y)), y, 1)[0])
    method_name = (
        "Linear regression trend"
        if method == "linear_regression"
        else "3-month moving average"
    )

    return {
        "tool": "forecast_tool",
        "request": req.model_dump(),
        "level": level,
        "target": req.target,
        "note": note,
        "demand_definition": "Monthly demand = sum of quantity per order month, canceled orders excluded.",
        "history": [
            {"month": str(m), "actual": float(v)} for m, v in zip(series.index, y)
        ],
        "forecast": forecast,
        "method": method,
        "method_label": method_name,
        "backtest_mae": mae,
        "trend_slope_per_month": round(slope, 2),
        "residual_std": round(sigma, 2),
        "recommendation": {
            "forecast_total": int(math.ceil(total)),
            "safety_stock": int(math.ceil(safety)),
            "recommended_stock": int(math.ceil(total + safety)),
            "service_level": "~95%",
        },
        "explanation": (
            f"Both methods were back-tested month by month on 2025 (each month predicted only from earlier months). "
            f"{method_name} had the lower mean absolute error ({mae[method]} units vs "
            f"{mae['moving_average_3' if method == 'linear_regression' else 'linear_regression']}), so it is used. "
            f"Safety stock = 1.65 x error std ({sigma:.1f}) x sqrt({h} months) to cover ~95% of demand swings. "
            f"Recommended stock = forecast total + safety stock."
        ),
        "rows_scanned": int(
            len(base)
            if req.target_type == "all"
            else (base["product_category"] == req.target).sum()
            if level == "category"
            else (base["sku"] == req.target).sum()
        ),
        "headline": (
            f"Forecast {req.target} demand for the next {h} months (Jan-{future[-1].strftime('%b %Y')}): "
            f"~{int(math.ceil(total))} units; plan {int(math.ceil(total + safety))} units incl. safety stock."
        ),
    }
