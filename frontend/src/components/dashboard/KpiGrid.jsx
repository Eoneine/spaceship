import { AlertTriangle, CheckCircle2, Clock, Package, TrendingUp } from "lucide-react";
import { fmtNum } from "@/lib/format";

const CARDS = [
  { key: "total_orders", id: "kpi-total-orders", title: "Total orders", icon: Package, color: "#38bdf8", fmt: (v) => fmtNum(v) },
  { key: "delivered", id: "kpi-delivered", title: "Delivered", icon: CheckCircle2, color: "#10b981", fmt: (v) => fmtNum(v) },
  { key: "delayed", id: "kpi-delayed", title: "Delayed", icon: AlertTriangle, color: "#f43f5e", fmt: (v) => fmtNum(v) },
  { key: "on_time_rate", id: "kpi-ontime-rate", title: "On-time rate", icon: TrendingUp, color: "#10b981", fmt: (v) => (v == null ? "—" : `${fmtNum(v, 1)}%`) },
  { key: "avg_delivery_days", id: "kpi-avg-delivery-days", title: "Avg delivery time", icon: Clock, color: "#fbbf24", fmt: (v) => (v == null ? "—" : `${fmtNum(v, 2)}d`) },
];

const NOTES = {
  on_time_rate: "delivered ÷ (delivered + delayed)",
  avg_delivery_days: "delivery − order date",
  delayed: "status = delayed",
  delivered: "status = delivered",
  total_orders: "all statuses",
};

export const KpiGrid = ({ kpis, loading }) => (
  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5" data-testid="kpi-grid">
    {CARDS.map(({ key, id, title, icon: Icon, color, fmt }, i) => (
      <div key={key} className="panel rise relative overflow-hidden p-5" style={{ animationDelay: `${i * 60}ms` }} data-testid={id}>
        <div className="absolute inset-x-0 top-0 h-[2px]" style={{ background: color, opacity: 0.7 }} />
        <div className="flex items-center justify-between">
          <span className="eyebrow">{title}</span>
          <Icon className="h-4 w-4" style={{ color }} />
        </div>
        <div className={`mt-3 font-mono text-3xl font-extrabold tracking-tight ${loading ? "opacity-40" : ""}`} data-testid={`${id}-value`}>
          {kpis ? fmt(kpis[key]) : "—"}
        </div>
        <div className="mt-1 font-mono text-[11px] text-slate-500">{NOTES[key]}</div>
      </div>
    ))}
  </div>
);
