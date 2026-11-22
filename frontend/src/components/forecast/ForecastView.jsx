import {
  Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { ChartTooltip, axisProps } from "@/components/charts/ChartsParts";
import { COLORS, fmtNum, monthLabel } from "@/lib/format";

const buildData = (r) => {
  const hist = r.history.map((h) => ({ month: h.month, actual: h.actual }));
  const last = hist[hist.length - 1];
  last.forecast = last.actual;
  last.band = [last.actual, last.actual];
  return [...hist, ...r.forecast.map((f) => ({ month: f.month, forecast: f.forecast, band: [f.lower, f.upper] }))];
};

const ForecastChart = ({ result }) => (
  <ResponsiveContainer width="100%" height={300} data-testid="forecast-chart">
    <ComposedChart data={buildData(result)} margin={{ left: -15, right: 28 }}>
      <CartesianGrid stroke={COLORS.grid} strokeDasharray="3 3" vertical={false} />
      <XAxis dataKey="month" tickFormatter={monthLabel} {...axisProps} />
      <YAxis {...axisProps} />
      <Tooltip content={<ChartTooltip formatter={(v) => (Array.isArray(v) ? `${v[0]} – ${v[1]}` : v)} />} />
      <Legend wrapperStyle={{ fontSize: 11, fontFamily: "JetBrains Mono" }} />
      <Area dataKey="band" name="95% range" fill={COLORS.sky} fillOpacity={0.12} stroke="none" />
      <Line dataKey="actual" name="Actual units" stroke={COLORS.indigo} strokeWidth={2.5} dot={{ r: 3, fill: COLORS.indigo }} />
      <Line dataKey="forecast" name="Forecast" stroke={COLORS.sky} strokeWidth={2.5} strokeDasharray="6 4" dot={{ r: 3, fill: COLORS.sky }} />
    </ComposedChart>
  </ResponsiveContainer>
);

const Stat = ({ label, value, testId, accent }) => (
  <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
    <div className="eyebrow">{label}</div>
    <div className={`mt-2 font-mono text-2xl font-extrabold ${accent || "text-slate-100"}`} data-testid={testId}>{value}</div>
  </div>
);

export const ForecastView = ({ result }) => {
  const rec = result.recommendation;
  return (
    <div className="space-y-5" data-testid="forecast-view">
      {result.note && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200" data-testid="forecast-fallback-note">
          {result.note}
        </div>
      )}
      <ForecastChart result={result} />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Stat label="Forecast demand" value={`${fmtNum(rec.forecast_total)} u`} testId="forecast-total-value" />
        <Stat label="Safety stock" value={`+${fmtNum(rec.safety_stock)} u`} testId="forecast-safety-stock-value" accent="text-amber-300" />
        <Stat label="Recommended stock" value={`${fmtNum(rec.recommended_stock)} u`} testId="forecast-recommended-stock-value" accent="text-sky-300" />
      </div>
      <div className="overflow-x-auto scroll-thin">
        <table className="w-full font-mono text-xs" data-testid="forecast-table">
          <thead className="text-slate-500">
            <tr className="border-b border-slate-800">
              <th className="py-2 text-left font-medium">Month</th>
              <th className="py-2 text-right font-medium">Forecast</th>
              <th className="py-2 text-right font-medium">Low</th>
              <th className="py-2 text-right font-medium">High</th>
            </tr>
          </thead>
          <tbody>
            {result.forecast.map((f) => (
              <tr key={f.month} className="border-b border-slate-800/60">
                <td className="py-2">{f.month}</td>
                <td className="py-2 text-right text-sky-300">{f.forecast}</td>
                <td className="py-2 text-right text-slate-400">{f.lower}</td>
                <td className="py-2 text-right text-slate-400">{f.upper}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 text-sm leading-relaxed text-slate-300" data-testid="forecast-method-explanation">
        <div className="eyebrow mb-2">Method · {result.method_label}</div>
        <p>{result.explanation}</p>
        <p className="mt-2 font-mono text-xs text-slate-500">
          Back-test MAE — linear: {result.backtest_mae.linear_regression} · moving avg (3m): {result.backtest_mae.moving_average_3} · trend slope: {result.trend_slope_per_month} u/month · {result.demand_definition}
        </p>
      </div>
    </div>
  );
};
