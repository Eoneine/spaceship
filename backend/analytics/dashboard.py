from datetime import date
from typing import Optional

import pandas as pd

from .data import DF, apply_filters, kpis


def _rate(delayed: int, delivered: int) -> Optional[float]:
    total = delayed + delivered
    return round(delayed / total * 100, 1) if total else None


def _breakdown(df: pd.DataFrame, col: str) -> list:
    g = df.groupby(col).agg(
        orders=("order_id", "count"),
        delivered=("is_delivered", "sum"),
        delayed=("is_delayed", "sum"),
        avg_delivery_days=("delivery_days", "mean"),
    )
    out = []
    for key, r in g.iterrows():
        out.append(
            {
                col: key,
                "orders": int(r.orders),
                "delivered": int(r.delivered),
                "delayed": int(r.delayed),
                "delay_rate": _rate(int(r.delayed), int(r.delivered)),
                "avg_delivery_days": round(float(r.avg_delivery_days), 2)
                if pd.notna(r.avg_delivery_days)
                else None,
            }
        )
    return sorted(out, key=lambda x: x["orders"], reverse=True)


def build_dashboard(
    start: Optional[date], end: Optional[date], carriers: list, regions: list
) -> dict:
    df = apply_filters(DF, start, end, carrier=carriers, region=regions)
    months = pd.period_range("2025-01", "2025-12", freq="M")
    if start:
        months = [m for m in months if m.end_time.date() >= start]
    if end:
        months = [m for m in months if m.start_time.date() <= end]
    per = df.groupby(df["order_date"].dt.to_period("M")).agg(
        orders=("order_id", "count"),
        delivered=("is_delivered", "sum"),
        delayed=("is_delayed", "sum"),
    )
    monthly = []
    for m in months:
        r = per.loc[m] if m in per.index else None
        monthly.append(
            {
                "month": str(m),
                "orders": int(r.orders) if r is not None else 0,
                "delivered": int(r.delivered) if r is not None else 0,
                "delayed": int(r.delayed) if r is not None else 0,
            }
        )
    return {
        "kpis": kpis(df),
        "monthly": monthly,
        "by_carrier": sorted(
            _breakdown(df, "carrier"), key=lambda x: x["delay_rate"] or 0, reverse=True
        ),
        "by_region": _breakdown(df, "region"),
        "rows_matched": int(len(df)),
        "filters": {
            "start": str(start) if start else None,
            "end": str(end) if end else None,
            "carriers": carriers,
            "regions": regions,
        },
    }
