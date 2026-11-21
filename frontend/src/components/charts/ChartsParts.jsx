export const ChartTooltip = ({ active, payload, label, formatter }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900/95 p-3 font-mono text-xs text-slate-100 shadow-xl">
      <div className="mb-1 text-slate-400">{label ?? payload[0]?.name}</div>
      {payload.map((p) => (
        <div key={p.dataKey ?? p.name} className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full" style={{ background: p.color || p.payload?.fill }} />
          <span className="text-slate-400">{p.name}:</span>
          <span>{formatter ? formatter(p.value, p) : p.value}</span>
        </div>
      ))}
    </div>
  );
};

export const ChartFrame = ({ title, subtitle, children, testId, right }) => (
  <section className="panel rise p-5" data-testid={testId}>
    <div className="mb-4 flex items-start justify-between gap-4">
      <div>
        <div className="eyebrow">{title}</div>
        {subtitle && <div className="mt-1 text-xs text-slate-500">{subtitle}</div>}
      </div>
      {right}
    </div>
    {children}
  </section>
);

export const axisProps = { stroke: "#475569", fontSize: 11, tickLine: false, axisLine: false, fontFamily: "JetBrains Mono" };
