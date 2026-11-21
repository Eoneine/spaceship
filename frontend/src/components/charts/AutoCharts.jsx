import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { ChartTooltip, axisProps } from "./ChartParts";
import { COLORS, PALETTE, fmtMetric, metricColor } from "@/lib/format";

const pivot = (rows, x, seriesKey) => {
  const map = new Map();
  const series = new Set();
  rows.forEach((r) => {
    const k = r[x];
    if (!map.has(k)) map.set(k, { [x]: k });
    map.get(k)[r[seriesKey]] = r.value;
    series.add(r[seriesKey]);
  });
  return { data: [...map.values()], series: [...series].slice(0, 9) };
};

const KpiValue = ({ result, metric }) => (
  <div className="flex h-[260px] flex-col justify-center" data-testid="auto-chart-kpi">
    <div className="eyebrow">{result.metric_label}</div>
    <div className="mt-2 font-mono text-6xl font-extrabold tracking-tight" style={{ color: metricColor(metric) }} data-testid="auto-chart-kpi-value">
      {fmtMetric(result.rows[0]?.value, metric)}
    </div>
    <div className="mt-3 text-sm text-slate-400">
      {result.resolved.period_label} · {result.rows[0]?.orders} orders matched
    </div>
  </div>
);

export const AutoChart = ({ result }) => {
  const { chart, rows } = result;
  const metric = result.plan.metric;
  const color = metricColor(metric);
  const fmt = (v) => fmtMetric(v, metric);
  if (chart.type === "kpi") return <KpiValue result={result} metric={metric} />;
  if (!rows.length) return <div className="py-16 text-center text-sm text-slate-500">No rows match.</div>;

  if (chart.type === "multi_line") {
    const { data, series } = pivot(rows, chart.x, chart.series_key);
    return (
      <ResponsiveContainer width="100%" height={300} data-testid="auto-chart-multi-line">
        <LineChart data={data} margin={{ left: -10, right: 10 }}>
          <CartesianGrid stroke={COLORS.grid} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey={chart.x} {...axisProps} />
          <YAxis {...axisProps} />
          <Tooltip content={<ChartTooltip formatter={fmt} />} />
          <Legend wrapperStyle={{ fontSize: 11, fontFamily: "JetBrains Mono" }} />
          {series.map((s, i) => (
            <Line key={s} dataKey={s} name={s} stroke={PALETTE[i % PALETTE.length]} strokeWidth={2} dot={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    );
  }
  if (chart.type === "line") {
    return (
      <ResponsiveContainer width="100%" height={300} data-testid="auto-chart-line">
        <LineChart data={rows} margin={{ left: -10, right: 10 }}>
          <CartesianGrid stroke={COLORS.grid} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey={chart.x} {...axisProps} />
          <YAxis {...axisProps} />
          <Tooltip content={<ChartTooltip formatter={fmt} />} />
          <Line dataKey="value" name={chart.label} stroke={color} strokeWidth={2.5} dot={{ r: 3, fill: color }} />
        </LineChart>
      </ResponsiveContainer>
    );
  }
  if (chart.type === "donut") {
    return (
      <ResponsiveContainer width="100%" height={300} data-testid="auto-chart-donut">
        <PieChart>
          <Pie data={rows} dataKey="value" nameKey={chart.x} innerRadius={70} outerRadius={110} paddingAngle={2} stroke="none">
            {rows.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
          </Pie>
          <Tooltip content={<ChartTooltip formatter={fmt} />} />
          <Legend wrapperStyle={{ fontSize: 11, fontFamily: "JetBrains Mono" }} />
        </PieChart>
      </ResponsiveContainer>
    );
  }
  const height = Math.max(220, rows.length * 34);
  return (
    <ResponsiveContainer width="100%" height={height} data-testid="auto-chart-bar">
      <BarChart data={rows} layout="vertical" margin={{ left: 10, right: 30 }}>
        <CartesianGrid stroke={COLORS.grid} strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" {...axisProps} />
        <YAxis type="category" dataKey={chart.x} width={120} {...axisProps} />
        <Tooltip cursor={{ fill: "rgba(148,163,184,0.06)" }} content={<ChartTooltip formatter={fmt} />} />
        <Bar dataKey="value" name={chart.label} fill={color} radius={[0, 4, 4, 0]} barSize={18} />
      </BarChart>
    </ResponsiveContainer>
  );
};
