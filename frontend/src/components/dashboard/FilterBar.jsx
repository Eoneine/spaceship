import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RotateCcw } from "lucide-react";

const FilterSelect = ({ testId, value, onChange, options, allLabel }) => (
  <Select value={value} onValueChange={onChange}>
    <SelectTrigger data-testid={testId} className="h-9 w-full border-slate-700 bg-slate-900 font-mono text-xs sm:w-44">
      <SelectValue />
    </SelectTrigger>
    <SelectContent className="border-slate-700 bg-slate-900 text-slate-100">
      <SelectItem value="all">{allLabel}</SelectItem>
      {options.map((o) => (
        <SelectItem key={o} value={o} data-testid={`${testId}-option-${o}`}>{o}</SelectItem>
      ))}
    </SelectContent>
  </Select>
);

const Field = ({ label, children }) => (
  <label className="flex flex-col gap-1.5">
    <span className="eyebrow">{label}</span>
    {children}
  </label>
);

export const FilterBar = ({ meta, filters, setFilters, defaults }) => {
  const set = (k) => (v) => setFilters((f) => ({ ...f, [k]: v }));
  const dateCls = "h-9 w-full border-slate-700 bg-slate-900 font-mono text-xs [color-scheme:dark] sm:w-40";
  return (
    <div className="panel flex flex-col gap-4 p-4 sm:flex-row sm:flex-wrap sm:items-end" data-testid="filter-bar">
      <Field label="From">
        <Input type="date" data-testid="filter-date-start" className={dateCls} value={filters.start}
          min={meta?.date_min} max={filters.end} onChange={(e) => set("start")(e.target.value)} />
      </Field>
      <Field label="To">
        <Input type="date" data-testid="filter-date-end" className={dateCls} value={filters.end}
          min={filters.start} max={meta?.reference_date} onChange={(e) => set("end")(e.target.value)} />
      </Field>
      <Field label="Carrier">
        <FilterSelect testId="filter-carrier" value={filters.carrier} onChange={set("carrier")} options={meta?.carriers || []} allLabel="All carriers" />
      </Field>
      <Field label="Region">
        <FilterSelect testId="filter-region" value={filters.region} onChange={set("region")} options={meta?.regions || []} allLabel="All regions" />
      </Field>
      <button data-testid="filter-reset-button" onClick={() => setFilters(defaults)}
        className="flex h-9 items-center gap-2 rounded-full border border-slate-700 px-4 text-xs text-slate-300 transition-colors hover:border-sky-500 hover:text-sky-300">
        <RotateCcw className="h-3.5 w-3.5" /> Reset
      </button>
    </div>
  );
};
