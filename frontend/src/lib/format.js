export const COLORS = {
  sky: "#38bdf8",
  ontime: "#10b981",
  delayed: "#f43f5e",
  indigo: "#818cf8",
  amber: "#fbbf24",
  violet: "#c084fc",
  grid: "#1e293b",
  axis: "#64748b",
};
export const PALETTE = ["#38bdf8", "#10b981", "#f43f5e", "#818cf8", "#fbbf24", "#c084fc", "#2dd4bf", "#fb923c", "#a3e635"];

export const metricColor = (metric) => {
  if (!metric) return COLORS.sky;
  if (metric.includes("delay")) return COLORS.delayed;
  if (metric.includes("on_time") || metric.includes("delivered")) return COLORS.ontime;
  return COLORS.sky;
};

export const fmtNum = (v, digits = 0) =>
  v === null || v === undefined ? "—" : Number(v).toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits });

export const fmtMetric = (v, metric) => {
  if (v === null || v === undefined) return "—";
  if (metric === "on_time_rate" || metric === "delay_rate") return `${fmtNum(v, 1)}%`;
  if (metric === "total_order_value" || metric === "avg_order_value") return `$${fmtNum(v, 2)}`;
  if (metric === "avg_delivery_days") return `${fmtNum(v, 2)} d`;
  return fmtNum(v, Number.isInteger(v) ? 0 : 2);
};

export const monthLabel = (m) => {
  if (!m || m.length !== 7) return m;
  const [y, mo] = m.split("-");
  return new Date(Number(y), Number(mo) - 1, 1).toLocaleString("en-US", { month: "short" }) + " " + y.slice(2);
};

export function downloadCsv(filename, columns, rows) {
  const esc = (v) => {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const csv = [columns.join(","), ...rows.map((r) => columns.map((c) => esc(r[c])).join(","))].join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
