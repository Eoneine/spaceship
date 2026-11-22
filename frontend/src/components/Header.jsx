import { BarChart3, Package, Sparkles, TrendingUp } from "lucide-react";

const TABS = [
  { id: "dashboard", label: "Dashboard", icon: BarChart3 },
  { id: "ask", label: "Ask the Data", icon: Sparkles },
  { id: "forecast", label: "Forecast", icon: TrendingUp },
];

export const Header = ({ tab, onTab, meta }) => (
  <header className="sticky top-0 z-30 border-b border-slate-800/80 bg-[#070b14]/90 backdrop-blur-md">
    <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-4 px-4 py-3.5 sm:px-6 lg:px-10">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-500/10 text-cyan-400">
          <Package className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-base font-semibold tracking-tight text-slate-100">
            Logistics Analytics Copilot
          </h1>
          <p className="text-xs text-slate-400">
            {meta
              ? `${meta.rows} orders · ${meta.date_min} to ${meta.date_max}`
              : "Loading dataset metadata..."}
          </p>
        </div>
      </div>

      <nav className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-900/70 p-1">
        {TABS.map(({ id, label, icon: Icon }) => {
          const active = tab === id;
          return (
            <button
              key={id}
              type="button"
              data-testid={`nav-tab-${id}`}
              onClick={() => onTab(id)}
              className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-sm font-medium transition-colors ${
                active
                  ? "bg-cyan-500/15 text-cyan-300 shadow-sm ring-1 ring-cyan-500/30"
                  : "text-slate-400 hover:bg-slate-800/70 hover:text-slate-200"
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  </header>
);
