import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { getForecast } from "@/lib/api";
import { ForecastView } from "./ForecastView";

const HORIZONS = [1, 2, 3, 4, 6, 9, 12];
const trigger = "h-10 border-slate-700 bg-slate-900 font-mono text-xs";
const content = "max-h-72 border-slate-700 bg-slate-900 text-slate-100";

export const ForecastTab = ({ meta }) => {
  const [target, setTarget] = useState("category:PAPER");
  const [horizon, setHorizon] = useState("3");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const [target_type, value] = target.split(":");
    setLoading(true);
    getForecast({ target_type, target: value || "", horizon_months: Number(horizon) })
      .then(setResult)
      .catch(() => toast.error("Forecast failed"))
      .finally(() => setLoading(false));
  }, [target, horizon]);

  return (
    <div className="space-y-6" data-testid="forecast-tab">
      <div>
        <div className="eyebrow">Predictive · Prescriptive</div>
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Demand forecast & stock plan</h1>
        <p className="mt-1 text-sm text-slate-400">History = 2025 monthly units. Forecast starts January 2026.</p>
      </div>
      <div className="panel flex flex-col gap-4 p-4 sm:flex-row sm:items-end">
        <label className="flex flex-col gap-1.5 sm:w-72">
          <span className="eyebrow">Category / SKU</span>
          <Select value={target} onValueChange={setTarget}>
            <SelectTrigger data-testid="forecast-sku-select" className={trigger}><SelectValue /></SelectTrigger>
            <SelectContent className={content}>
              <SelectItem value="all:">All products (total)</SelectItem>
              {(meta?.categories || []).map((c) => (
                <SelectItem key={c} value={`category:${c}`} data-testid={`forecast-option-${c}`}>Category · {c}</SelectItem>
              ))}
              {(meta?.skus || []).map((s) => (
                <SelectItem key={s} value={`sku:${s}`}>SKU · {s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </label>
        <label className="flex flex-col gap-1.5 sm:w-44">
          <span className="eyebrow">Horizon</span>
          <Select value={horizon} onValueChange={setHorizon}>
            <SelectTrigger data-testid="forecast-horizon-select" className={trigger}><SelectValue /></SelectTrigger>
            <SelectContent className={content}>
              {HORIZONS.map((h) => (
                <SelectItem key={h} value={String(h)} data-testid={`forecast-horizon-option-${h}`}>{h} month{h > 1 ? "s" : ""}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </label>
        {loading && <Loader2 className="mb-2 h-5 w-5 animate-spin text-sky-400" />}
      </div>
      {result && (
        <section className="panel rise p-5" data-testid="forecast-result">
          <div className="mb-4 text-sm text-slate-300" data-testid="forecast-headline">{result.headline}</div>
          <ForecastView result={result} />
        </section>
      )}
    </div>
  );
};
