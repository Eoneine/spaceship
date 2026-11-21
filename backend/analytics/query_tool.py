"""Query Tool: validates a structured QueryPlan and computes it with pandas.

The AI never writes SQL or code. It only fills a QueryPlan; every value is
validated against the dataset before anything is computed."""

import calendar
from datetime import date, timedelta
from typing import List, Literal, Optional

import pandas as pd
from pydantic import BaseModel, Field, field_validator, model_validator

from .data import (
    DF,
    DIMENSION_VALUES,
    METRIC_DEFINITIONS,
    REFERENCE_DATE,
    apply_filters,
)

Metric = Literal[
    "order_count",
    "delivered_count",
    "delayed_count",
    "on_time_rate",
    "delay_rate",
    "avg_delivery_days",
    "total_order_value",
    "avg_order_value",
    "total_quantity",
]
Dimension = Literal[
    "carrier",
    "region",
    "status",
    "product_category",
    "warehouse",
    "destination_city",
    "origin_city",
    "client_id",
    "is_promo",
]
Grain = Literal["day", "week", "month", "quarter"]
Preset = Literal[
    "all",
    "last_n_days",
    "last_n_weeks",
    "last_n_months",
    "last_month",
    "this_month",
    "quarter",
    "month",
    "custom",
]

METRIC_LABELS = {
    "order_count": "Orders",
    "delivered_count": "Delivered orders",
    "delayed_count": "Delayed orders",
    "on_time_rate": "On-time rate (%)",
    "delay_rate": "Delay rate (%)",
    "avg_delivery_days": "Avg delivery days",
    "total_order_value": "Order value (USD)",
    "avg_order_value": "Avg order value (USD)",
    "total_quantity": "Units",
}
ADDITIVE = {
    "order_count",
    "delivered_count",
    "delayed_count",
    "total_order_value",
    "total_quantity",
}
FILTER_COLUMNS = {
    "carriers": "carrier",
    "regions": "region",
    "statuses": "status",
    "categories": "product_category",
    "warehouses": "warehouse",
    "destination_cities": "destination_city",
    "origin_cities": "origin_city",
    "client_ids": "client_id",
}


class TimeRange(BaseModel):
    preset: Preset = "all"
    n: Optional[int] = Field(None, ge=1, le=365)
    quarter: Optional[int] = Field(None, ge=1, le=4)
    month: Optional[int] = Field(None, ge=1, le=12)
    start: Optional[date] = None
    end: Optional[date] = None

    @model_validator(mode="after")
    def _check(self):
        if self.preset.startswith("last_n_") and not self.n:
            raise ValueError(f"time_range.n is required for preset '{self.preset}'")
        if self.preset == "quarter" and not self.quarter:
            raise ValueError(
                "time_range.quarter (1-4) is required for preset 'quarter'"
            )
        if self.preset == "month" and not self.month:
            raise ValueError("time_range.month (1-12) is required for preset 'month'")
        if self.preset == "custom" and not (self.start or self.end):
            raise ValueError(
                "time_range.start and/or end are required for preset 'custom'"
            )
        return self

    def resolve(self) -> tuple:
        ref, y = REFERENCE_DATE, REFERENCE_DATE.year
        p = self.preset
        if p == "all":
            return None, None, "all data (2025-01-01 to 2025-12-31)"
        if p == "last_n_days":
            s = ref - timedelta(days=self.n - 1)
            return s, ref, f"last {self.n} days"
        if p == "last_n_weeks":
            s = ref - timedelta(days=7 * self.n - 1)
            return s, ref, f"last {self.n} weeks"
        if p == "last_n_months":
            m0 = (ref.year * 12 + ref.month - 1) - (self.n - 1)
            s = date(m0 // 12, m0 % 12 + 1, 1)
            return s, ref, f"last {self.n} months"
        if p in ("this_month", "last_month"):
            m0 = ref.year * 12 + ref.month - 1 - (1 if p == "last_month" else 0)
            yy, mm = m0 // 12, m0 % 12 + 1
            return (
                date(yy, mm, 1),
                date(yy, mm, calendar.monthrange(yy, mm)[1]),
                p.replace("_", " "),
            )
        if p == "quarter":
            m1 = (self.quarter - 1) * 3 + 1
            return (
                date(y, m1, 1),
                date(y, m1 + 2, calendar.monthrange(y, m1 + 2)[1]),
                f"Q{self.quarter} {y}",
            )
        if p == "month":
            return (
                date(y, self.month, 1),
                date(y, self.month, calendar.monthrange(y, self.month)[1]),
                f"{calendar.month_name[self.month]} {y}",
            )
        return self.start, self.end, "custom range"


class Filters(BaseModel):
    carriers: List[str] = []
    regions: List[str] = []
    statuses: List[str] = []
    categories: List[str] = []
    warehouses: List[str] = []
    destination_cities: List[str] = []
    origin_cities: List[str] = []
    client_ids: List[str] = []
    is_promo: Optional[bool] = None

    @model_validator(mode="after")
    def _normalize(self):
        """Map values case-insensitively onto real dataset values; reject unknown ones."""
        for field, col in FILTER_COLUMNS.items():
            allowed = DIMENSION_VALUES[col]
            fixed = []
            for v in getattr(self, field):
                vl = str(v).strip().lower()
                exact = [a for a in allowed if a.lower() == vl]
                partial = (
                    [a for a in allowed if a.lower().startswith(vl)]
                    if col.endswith("_city")
                    else []
                )
                match = exact or partial
                if not match:
                    raise ValueError(
                        f"Unknown {col} '{v}'. Allowed: {', '.join(allowed[:50])}"
                    )
                fixed.extend(match)
            setattr(self, field, sorted(set(fixed)))
        return self


class QueryPlan(BaseModel):
    metric: Metric
    group_by: Optional[Dimension] = None
    time_grain: Optional[Grain] = None
    time_range: TimeRange = TimeRange()
    filters: Filters = Filters()
    sort: Literal["desc", "asc"] = "desc"
    limit: Optional[int] = Field(None, ge=1, le=50)

    @field_validator("group_by", "time_grain", mode="before")
    @classmethod
    def _empty_to_none(cls, v):
        return None if v in ("", "none", "null") else v


def _aggregate(g, metric: str):
    """g is a DataFrame or GroupBy; returns scalar or Series."""
    if metric == "order_count":
        return g["order_id"].count()
    if metric == "delivered_count":
        return g["is_delivered"].sum()
    if metric == "delayed_count":
        return g["is_delayed"].sum()
    if metric in ("on_time_rate", "delay_rate"):
        num = g["is_delivered" if metric == "on_time_rate" else "is_delayed"].sum()
        den = g["is_delivered"].sum() + g["is_delayed"].sum()
        if isinstance(den, pd.Series):
            return (num / den.replace(0, pd.NA) * 100).astype("Float64")
        return num / den * 100 if den else None
    if metric == "avg_delivery_days":
        return g["delivery_days"].mean()
    if metric == "total_order_value":
        return g["order_value_usd"].sum()
    if metric == "avg_order_value":
        return g["order_value_usd"].mean()
    return g["quantity"].sum()


def _clean(v, metric):
    if v is None or pd.isna(v):
        return None
    if metric in ADDITIVE and metric not in ("total_order_value",):
        return int(v)
    return round(float(v), 2)


def _period_key(s: pd.Series, grain: str) -> pd.Series:
    if grain == "day":
        return s.dt.strftime("%Y-%m-%d")
    if grain == "week":
        return s.dt.to_period("W-SUN").dt.start_time.dt.strftime("%Y-%m-%d")
    if grain == "month":
        return s.dt.strftime("%Y-%m")
    return s.dt.to_period("Q").astype(str)


def _all_periods(start, end, grain):
    start = pd.Timestamp(start or "2025-01-01")
    end = pd.Timestamp(end or REFERENCE_DATE)
    if grain == "day":
        return [d.strftime("%Y-%m-%d") for d in pd.date_range(start, end, freq="D")]
    if grain == "week":
        return [
            p.start_time.strftime("%Y-%m-%d")
            for p in pd.period_range(start, end, freq="W-SUN")
        ]
    if grain == "month":
        return [str(p) for p in pd.period_range(start, end, freq="M")]
    return [str(p) for p in pd.period_range(start, end, freq="Q")]


def _support(g) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "orders": g["order_id"].count(),
            "delivered": g["is_delivered"].sum(),
            "delayed": g["is_delayed"].sum(),
        }
    )


def run_query(plan: QueryPlan) -> dict:
    start, end, period_label = plan.time_range.resolve()
    f = plan.filters
    eq = {col: getattr(f, field) for field, col in FILTER_COLUMNS.items()}
    if f.is_promo is not None:
        eq["is_promo"] = f.is_promo
    df = apply_filters(DF, start, end, **eq)
    metric, dim, grain = plan.metric, plan.group_by, plan.time_grain
    label = METRIC_LABELS[metric]
    rate_metric = metric in ("on_time_rate", "delay_rate")

    work = df.copy()
    keys = []
    if grain:
        work["period"] = _period_key(work["order_date"], grain)
        keys.append("period")
    if dim:
        work[dim] = (
            work[dim].astype(str)
            if dim != "is_promo"
            else work[dim].map({True: "promo", False: "no promo"})
        )
        keys.append(dim)

    if not keys:
        value = _clean(_aggregate(work, metric), metric)
        rows = [
            {
                "metric": label,
                "value": value,
                "orders": int(len(work)),
                "delivered": int(work["is_delivered"].sum()),
                "delayed": int(work["is_delayed"].sum()),
            }
        ]
        columns = ["metric", "value", "orders", "delivered", "delayed"]
        chart = {"type": "kpi", "value_key": "value", "label": label}
    else:
        grouped = work.groupby(keys)
        agg = (
            _aggregate(grouped, metric)
            .rename("value")
            .to_frame()
            .join(_support(grouped))
            .reset_index()
        )
        if grain:
            periods = _all_periods(start, end, grain)
            if dim:
                groups = sorted(work[dim].unique().tolist())
                full = pd.MultiIndex.from_product(
                    [periods, groups], names=keys
                ).to_frame(index=False)
            else:
                full = pd.DataFrame({"period": periods})
            agg = full.merge(agg, on=keys, how="left")
            for c in ["orders", "delivered", "delayed"]:
                agg[c] = agg[c].fillna(0).astype(int)
            if metric in ADDITIVE:
                agg["value"] = agg["value"].fillna(0)
            agg = agg.sort_values(keys)
        else:
            agg = agg.sort_values(
                "value", ascending=plan.sort == "asc", na_position="last"
            )
            if plan.limit:
                agg = agg.head(plan.limit)
        rows = []
        for r in agg.to_dict("records"):
            r["value"] = _clean(r["value"], metric)
            for c in ["orders", "delivered", "delayed"]:
                r[c] = int(r[c])
            rows.append(r)
        columns = keys + ["value", "orders", "delivered", "delayed"]
        if grain and dim:
            chart = {
                "type": "multi_line",
                "x": "period",
                "series_key": dim,
                "value_key": "value",
                "label": label,
            }
        elif grain:
            chart = {
                "type": "line" if len(rows) > 2 else "bar",
                "x": "period",
                "value_key": "value",
                "label": label,
            }
        elif metric in ADDITIVE and len(rows) <= 6 and not plan.limit:
            chart = {"type": "donut", "x": dim, "value_key": "value", "label": label}
        else:
            chart = {"type": "bar", "x": dim, "value_key": "value", "label": label}
    if not rate_metric:
        columns = [c for c in columns if c not in ("delivered", "delayed")]
        rows = [{k: v for k, v in r.items() if k in columns} for r in rows]

    return {
        "tool": "query_tool",
        "plan": plan.model_dump(mode="json"),
        "resolved": {
            "start": str(start) if start else "2025-01-01",
            "end": str(end) if end else "2025-12-31",
            "period_label": period_label,
            "reference_date": str(REFERENCE_DATE),
        },
        "metric_label": label,
        "definition": METRIC_DEFINITIONS[metric],
        "rows_scanned": int(len(df)),
        "columns": columns,
        "rows": rows,
        "chart": chart,
        "headline": _headline(rows, metric, label, dim, grain, period_label, plan.sort),
    }


def _fmt(v, metric):
    if v is None:
        return "n/a"
    if metric in ("on_time_rate", "delay_rate"):
        return f"{v:.1f}%"
    if metric in ("total_order_value", "avg_order_value"):
        return f"${v:,.2f}"
    if metric == "avg_delivery_days":
        return f"{v:.2f} days"
    return f"{v:,}"


def _headline(rows, metric, label, dim, grain, period_label, sort="desc") -> str:
    if not rows:
        return f"No orders match these filters for {period_label}."
    if not dim and not grain:
        return f"{label}: {_fmt(rows[0]['value'], metric)} ({period_label}, {rows[0]['orders']} orders matched)."
    vals = [r for r in rows if r["value"] is not None]
    if not vals:
        return f"No computable values for {label} in {period_label}."
    if grain and not dim:
        peak = max(vals, key=lambda r: r["value"])
        extra = (
            f" Total {_fmt(round(sum(r['value'] for r in vals), 2), metric)}."
            if metric in ADDITIVE
            else ""
        )
        return f"{label} by {grain} for {period_label}: peak {_fmt(peak['value'], metric)} in {peak['period']}.{extra}"
    key = dim
    top, bottom = vals[0], vals[-1]
    if not grain and len(vals) == 1:
        return f"{label} by {key} for {period_label}: {'lowest' if sort == 'asc' else 'highest'} is {top[key]} ({_fmt(top['value'], metric)})."
    if grain:
        tot = {}
        for r in vals:
            tot[r[key]] = tot.get(r[key], 0) + (r["value"] or 0)
        best = max(tot, key=tot.get)
        return (
            f"{label} by {grain} and {key} for {period_label}; highest overall: {best}."
        )
    return (
        f"{label} by {key} for {period_label}: highest {top[key]} ({_fmt(top['value'], metric)}), "
        f"lowest {bottom[key]} ({_fmt(bottom['value'], metric)})."
    )
