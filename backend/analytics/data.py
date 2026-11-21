"""Loads the logistics CSV once (read-only) and exposes shared helpers."""

from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "mock_logistics_data.csv"

# Relative phrases ("last month") resolve against the end of the dataset, not the calendar.
REFERENCE_DATE = date(2025, 12, 31)

METRIC_DEFINITIONS = {
    "order_count": "Number of orders (rows) matching the filters, all statuses.",
    "delivered_count": "Orders with status = 'delivered'.",
    "delayed_count": "Orders with status = 'delayed' (the dataset has no promised date, so 'late' = status 'delayed').",
    "on_time_rate": "delivered / (delivered + delayed) x 100. exception, in_transit and canceled are excluded.",
    "delay_rate": "delayed / (delivered + delayed) x 100. exception, in_transit and canceled are excluded.",
    "avg_delivery_days": "Mean of (delivery_date - order_date) in days, only for orders that have a delivery_date.",
    "total_order_value": "Sum of order_value_usd.",
    "avg_order_value": "Mean of order_value_usd per order.",
    "total_quantity": "Sum of quantity (units).",
}


def _load() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, parse_dates=["order_date", "delivery_date"])
    df["delivery_days"] = (df["delivery_date"] - df["order_date"]).dt.days
    df["is_delivered"] = df["status"].eq("delivered")
    df["is_delayed"] = df["status"].eq("delayed")
    df["is_promo"] = df["is_promo"].astype(bool)
    return df


DF = _load()

DIMENSION_VALUES = {
    col: sorted(DF[col].dropna().unique().tolist())
    for col in [
        "carrier",
        "region",
        "status",
        "product_category",
        "warehouse",
        "destination_city",
        "origin_city",
        "client_id",
    ]
}


def apply_filters(
    df: pd.DataFrame,
    start: Optional[date] = None,
    end: Optional[date] = None,
    **eq_filters,
) -> pd.DataFrame:
    """eq_filters: column -> list of allowed values (empty/None = no filter)."""
    mask = pd.Series(True, index=df.index)
    if start:
        mask &= df["order_date"] >= pd.Timestamp(start)
    if end:
        mask &= df["order_date"] <= pd.Timestamp(end)
    for col, values in eq_filters.items():
        if values is None or (isinstance(values, list) and not values):
            continue
        if isinstance(values, list):
            mask &= df[col].isin(values)
        else:
            mask &= df[col].eq(values)
    return df[mask]


def kpis(df: pd.DataFrame) -> dict:
    delivered = int(df["is_delivered"].sum())
    delayed = int(df["is_delayed"].sum())
    resolved = delivered + delayed
    avg_days = df["delivery_days"].mean()
    return {
        "total_orders": int(len(df)),
        "delivered": delivered,
        "delayed": delayed,
        "on_time_rate": round(delivered / resolved * 100, 1) if resolved else None,
        "avg_delivery_days": round(float(avg_days), 2) if pd.notna(avg_days) else None,
    }
