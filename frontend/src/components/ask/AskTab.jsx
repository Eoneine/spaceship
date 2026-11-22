import { useEffect, useRef, useState } from "react";
import { ArrowUp, History, Trash2 } from "lucide-react";
import { askStream } from "@/lib/api";
import { AnswerCard } from "./AnswerCards";

const STORE = "lac_history_v1";

const reduceEvent = (item, ev) => {
  const next = { ...item, cached: item.cached || ev.cached };
  switch (ev.type) {
    case "status": return { ...next, step: ev.step };
    case "tool": return { ...next, tool: ev.name };
    case "result": return { ...next, result: ev.result };
    case "delta": return { ...next, answer: (next.answer || "") + ev.text };
    case "done": return { ...next, status: "done", answer: ev.answer, step: "done" };
    case "unsupported": return { ...next, status: "unsupported", kind: ev.kind, reason: ev.reason, suggestions: ev.suggestions };
    case "error": return { ...next, status: "error", error: ev.message };
    default: return next;
  }
};

const HistoryList = ({ history, activeId, onSelect, onClear }) => (
  <aside className="panel p-4 lg:sticky lg:top-24" data-testid="ask-history">
    <div className="mb-3 flex items-center justify-between">
      <span className="eyebrow flex items-center gap-2"><History className="h-3.5 w-3.5" /> Session history</span>
      {history.length > 0 && (
        <button data-testid="ask-history-clear" onClick={onClear} className="text-slate-600 transition-colors hover:text-rose-400">
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
    {history.length === 0 && <p className="text-xs text-slate-500">Questions you ask appear here.</p>}
    <div className="scroll-thin max-h-[60vh] space-y-1 overflow-y-auto">
      {history.map((h, i) => (
        <button key={h.id} data-testid={`ask-history-item-${i}`} onClick={() => onSelect(h.id)}
          className={`w-full rounded-md px-3 py-2 text-left text-xs transition-colors ${h.id === activeId ? "bg-sky-500/10 text-sky-200" : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"}`}>
          <span className={`mr-2 inline-block h-1.5 w-1.5 rounded-full ${h.status === "done" ? "bg-emerald-400" : h.status === "running" ? "pulse-dot bg-sky-400" : "bg-amber-400"}`} />
          {h.question}
        </button>
      ))}
    </div>
  </aside>
);

export const AskTab = ({ meta }) => {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState(() => JSON.parse(localStorage.getItem(STORE) || "[]"));
  const [activeId, setActiveId] = useState(history[0]?.id || null);
  const running = history.some((h) => h.status === "running");
  const inputRef = useRef(null);

  useEffect(() => {
    localStorage.setItem(STORE, JSON.stringify(history.filter((h) => h.status !== "running").slice(0, 30)));
  }, [history]);

  const ask = async (q) => {
    const text = (q ?? question).trim();
    if (!text || running) return;
    const id = `${Date.now()}`;
    setHistory((h) => [{ id, question: text, status: "running", step: "interpreting" }, ...h]);
    setActiveId(id);
    setQuestion("");
    const update = (fn) => setHistory((h) => h.map((x) => (x.id === id ? fn(x) : x)));
    try {
      await askStream(text, (ev) => update((x) => reduceEvent(x, ev)));
      update((x) => (x.status === "running" ? { ...x, status: x.result ? "done" : "error", error: x.error || "No answer received." } : x));
    } catch (e) {
      update((x) => ({ ...x, status: "error", error: `Request failed: ${e.message}` }));
    }
  };

  const active = history.find((h) => h.id === activeId);

  return (
    <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-12" data-testid="ask-tab">
      <div className="space-y-6 lg:col-span-9">
        <div>
          <div className="eyebrow">Diagnostic · Ask in plain English</div>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Ask the data</h1>
          <p className="mt-1 text-sm text-slate-400">
            AI only picks a tool and fills a structured plan. Every number is computed by code. Relative dates resolve against {meta?.reference_date || "2025-12-31"}.
          </p>
        </div>
        {meta && !meta.ai_available && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-sm text-amber-200" data-testid="ask-ai-unavailable">
            AI unavailable: no Gemini key configured. Dashboard and Forecast still work.
          </div>
        )}
        <form onSubmit={(e) => { e.preventDefault(); ask(); }}
          className="panel flex items-center gap-2 p-2 focus-within:border-sky-500/60">
          <input ref={inputRef} data-testid="ask-input-field" value={question} onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. Which carrier has the highest delay rate?"
            className="h-11 flex-1 bg-transparent px-3 text-sm text-slate-100 outline-none placeholder:text-slate-600" />
          <button type="submit" data-testid="ask-submit-button" disabled={running || !question.trim()}
            className="flex h-10 w-10 items-center justify-center rounded-full bg-sky-500 text-slate-950 transition-colors hover:bg-sky-400 disabled:bg-slate-800 disabled:text-slate-600">
            <ArrowUp className="h-4 w-4" />
          </button>
        </form>
        <div className="flex flex-wrap gap-2" data-testid="ask-examples">
          {(meta?.examples || []).map((ex, i) => (
            <button key={ex} data-testid={`ask-example-chip-${i}`} onClick={() => ask(ex)} disabled={running}
              className="rounded-full border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-xs text-slate-400 transition-colors hover:border-sky-500/60 hover:text-sky-200 disabled:opacity-40">
              {ex}
            </button>
          ))}
        </div>
        {active ? <AnswerCard key={active.id} item={active} onAsk={ask} /> : (
          <div className="panel p-10 text-sm text-slate-500" data-testid="ask-empty-state">
            Pick an example above or type a question about orders, delays, carriers, regions, categories or demand.
          </div>
        )}
      </div>
      <div className="lg:col-span-3">
        <HistoryList history={history} activeId={activeId} onSelect={setActiveId}
          onClear={() => { setHistory((h) => h.filter((x) => x.status === "running")); setActiveId(null); }} />
      </div>
    </div>
  );
};
