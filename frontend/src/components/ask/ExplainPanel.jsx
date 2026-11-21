import { useState } from "react";
import { ChevronDown, Code2 } from "lucide-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";

const Row = ({ k, v, testId }) => (
  <div className="grid grid-cols-[140px_1fr] gap-3 border-b border-slate-800/60 py-2 text-xs" data-testid={testId}>
    <span className="font-mono text-slate-500">{k}</span>
    <span className="break-words text-slate-200">{v}</span>
  </div>
);

const activeFilters = (filters = {}) => {
  const parts = Object.entries(filters)
    .filter(([, v]) => (Array.isArray(v) ? v.length : v !== null && v !== undefined))
    .map(([k, v]) => `${k} = ${Array.isArray(v) ? v.join(", ") : String(v)}`);
  return parts.length ? parts.join(" · ") : "none";
};

const QueryRows = ({ r }) => (
  <>
    <Row k="tool" v="query_tool (pandas aggregation)" testId="explain-tool" />
    <Row k="time range" v={`${r.resolved.period_label} → ${r.resolved.start} to ${r.resolved.end} (reference date ${r.resolved.reference_date})`} testId="explain-time-range" />
    <Row k="filters" v={activeFilters(r.plan.filters)} testId="explain-filters" />
    <Row k="metric" v={`${r.plan.metric} — ${r.definition}`} testId="explain-metric" />
    <Row k="dimensions" v={[r.plan.time_grain && `time: ${r.plan.time_grain}`, r.plan.group_by && `group: ${r.plan.group_by}`].filter(Boolean).join(" · ") || "none (single value)"} testId="explain-dimensions" />
    <Row k="sort / limit" v={`${r.plan.sort}${r.plan.limit ? ` · top ${r.plan.limit}` : ""}`} />
    <Row k="rows computed" v={`${r.rows_scanned} orders matched → ${r.rows.length} result rows`} testId="explain-rows" />
    <Row k="chart choice" v={`${r.chart.type} (picked from result shape)`} />
  </>
);

const ForecastRows = ({ r }) => (
  <>
    <Row k="tool" v="forecast_tool (numpy)" testId="explain-tool" />
    <Row k="target" v={`${r.level} · ${r.target}${r.note ? " (SKU fallback)" : ""}`} />
    <Row k="history" v="2025-01 to 2025-12, monthly" testId="explain-time-range" />
    <Row k="metric" v={r.demand_definition} testId="explain-metric" />
    <Row k="method" v={`${r.method_label} (back-test MAE ${r.backtest_mae[r.method]})`} />
    <Row k="rows computed" v={`${r.rows_scanned} orders`} testId="explain-rows" />
  </>
);

export const ExplainPanel = ({ result }) => {
  const [open, setOpen] = useState(false);
  const plan = result.tool === "query_tool" ? result.plan : result.request;
  return (
    <Collapsible open={open} onOpenChange={setOpen} className="rounded-lg border border-slate-800 bg-slate-950/60">
      <CollapsibleTrigger data-testid="ask-computed-toggle-button"
        className="flex w-full items-center justify-between px-4 py-3 text-sm text-slate-300 transition-colors hover:text-sky-300">
        <span className="flex items-center gap-2"><Code2 className="h-4 w-4 text-sky-400" /> How this was computed</span>
        <ChevronDown className={`h-4 w-4 transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
      </CollapsibleTrigger>
      <CollapsibleContent className="px-4 pb-4" data-testid="ask-explain-panel">
        {result.tool === "query_tool" ? <QueryRows r={result} /> : <ForecastRows r={result} />}
        <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
          <div>
            <div className="eyebrow mb-1.5">AI output (raw tool arguments)</div>
            <pre className="scroll-thin max-h-64 overflow-auto rounded-md bg-black/40 p-3 font-mono text-[11px] text-amber-200" data-testid="explain-ai-args">
              {JSON.stringify(result.ai_tool_args ?? {}, null, 2)}
            </pre>
          </div>
          <div>
            <div className="eyebrow mb-1.5">Validated query plan (executed)</div>
            <pre className="scroll-thin max-h-64 overflow-auto rounded-md bg-black/40 p-3 font-mono text-[11px] text-emerald-200" data-testid="explain-query-plan">
              {JSON.stringify(plan, null, 2)}
            </pre>
          </div>
        </div>
        {result.validation_attempts?.length > 0 && (
          <div className="mt-3 text-xs text-amber-300" data-testid="explain-validation-attempts">
            {result.validation_attempts.length} invalid plan(s) were rejected and corrected: {result.validation_attempts.map((a) => a.error).join(" | ")}
          </div>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
};
