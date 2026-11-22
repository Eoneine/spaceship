import { useState } from "react";
import { AlertCircle, Ban, Sparkles } from "lucide-react";
import { AutoChart } from "@/components/charts/AutoCharts";
import { ForecastView } from "@/components/forecast/ForecastView";
import { StatusPipeline } from "./StatusPipeline";
import { ExplainPanel } from "./ExplainPanel";
import { DataTable } from "./DataTable";

const ViewToggle = ({ view, setView }) => (
  <div className="flex gap-1 rounded-full border border-slate-800 p-0.5 text-xs">
    {["chart", "data"].map((v) => (
      <button key={v} data-testid={`ask-view-${v}`} onClick={() => setView(v)}
        className={`rounded-full px-3 py-1 capitalize transition-colors ${view === v ? "bg-slate-700 text-slate-100" : "text-slate-500 hover:text-slate-200"}`}>
        {v}
      </button>
    ))}
  </div>
);

const Declined = ({ item, onAsk }) => (
  <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4" data-testid="ask-unsupported">
    <div className="flex items-center gap-2 text-sm font-semibold text-amber-300">
      <Ban className="h-4 w-4" /> {item.kind === "ambiguous" ? "Needs a clearer question" : "Not supported by this dataset"}
    </div>
    <p className="mt-2 text-sm text-slate-300" data-testid="ask-unsupported-reason">{item.reason}</p>
    <div className="mt-3 flex flex-wrap gap-2">
      {(item.suggestions || []).map((s, i) => (
        <button key={s} data-testid={`ask-suggestion-${i}`} onClick={() => onAsk(s)}
          className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 transition-colors hover:border-sky-500 hover:text-sky-300">
          {s}
        </button>
      ))}
    </div>
  </div>
);

export const AnswerCard = ({ item, onAsk }) => {
  const [view, setView] = useState("chart");
  const r = item.result;
  const finished = ["done", "unsupported", "error"].includes(item.status);
  return (
    <section className="panel rise space-y-5 p-5 sm:p-6" data-testid="ask-answer-card">
      <div className="space-y-3">
        <div className="text-lg font-semibold tracking-tight" data-testid="ask-question-text">{item.question}</div>
        <StatusPipeline step={item.step} tool={item.tool} finished={finished && item.status !== "error"} failed={item.status === "error"} skipped={item.status === "unsupported"} />
      </div>
      {item.status === "error" && (
        <div className="flex items-start gap-2 rounded-lg border border-rose-500/30 bg-rose-500/5 p-4 text-sm text-rose-200" data-testid="ask-error">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> {item.error}
        </div>
      )}
      {item.status === "unsupported" && <Declined item={item} onAsk={onAsk} />}
      {(item.answer || (r && item.status === "done")) && (
        <div className="flex gap-3 rounded-lg border border-sky-500/20 bg-sky-500/5 p-4">
          <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-sky-400" />
          <div className="space-y-1">
            <p className="text-sm leading-relaxed text-slate-100" data-testid="ask-answer-text">{item.answer || r.headline}</p>
            {r && item.answer && item.answer !== r.headline && <p className="font-mono text-[11px] text-slate-500" data-testid="ask-computed-headline">Computed: {r.headline}</p>}
          </div>
        </div>
      )}
      {r && r.tool === "forecast_tool" && <ForecastView result={r} />}
      {r && r.tool === "query_tool" && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="eyebrow">{r.metric_label} · {r.chart.type}</span>
            <ViewToggle view={view} setView={setView} />
          </div>
          {view === "chart" ? <AutoChart result={r} /> : <DataTable result={r} />}
        </div>
      )}
      {r && <ExplainPanel result={r} />}
      {item.cached && <div className="font-mono text-[11px] text-slate-600" data-testid="ask-cached-flag">served from cache</div>}
    </section>
  );
};
