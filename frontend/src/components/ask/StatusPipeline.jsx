import { Check, Loader2, X } from "lucide-react";

const STEPS = [
  { id: "interpreting", label: "Interpreting question" },
  { id: "computing", label: "Running tool" },
  { id: "summarizing", label: "Writing answer" },
  { id: "done", label: "Done" },
];

export const StatusPipeline = ({ step, tool, finished, failed, skipped }) => {
  const idx = finished ? STEPS.length : STEPS.findIndex((s) => s.id === step);
  const failIdx = failed ? Math.max(0, STEPS.findIndex((s) => s.id === step)) : -1;
  return (
    <div className="flex flex-wrap items-center gap-2 font-mono text-[11px]" data-testid="ask-status-pipeline">
      {STEPS.map((s, i) => {
        const isFail = i === failIdx;
        const isSkipped = skipped && (s.id === "computing" || s.id === "summarizing");
        const done = !isFail && !isSkipped && (failed ? i < failIdx : i < idx || (finished && i <= idx));
        const active = i === idx && !finished;
        const label = isSkipped ? `${s.label} · skipped` : s.id === "computing" && tool ? `Running ${tool}` : s.label;
        return (
          <div key={s.id} className="flex items-center gap-2">
            <span
              data-testid={`ask-status-step-${s.id}`}
              className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 transition-colors duration-200 ${
                isFail ? "border-rose-500/50 bg-rose-500/10 text-rose-300"
                  : done ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                  : active ? "border-sky-500/50 bg-sky-500/10 text-sky-300"
                  : "border-slate-800 text-slate-600"
              }`}
            >
              {isFail ? <X className="h-3 w-3" /> : done ? <Check className="h-3 w-3" /> : active ? <Loader2 className="h-3 w-3 animate-spin" /> : <span className="h-1.5 w-1.5 rounded-full bg-slate-700" />}
              {label}
            </span>
            {i < STEPS.length - 1 && <span className="text-slate-700">→</span>}
          </div>
        );
      })}
    </div>
  );
};
