import { useEffect, useState } from "react";
import { toast } from "sonner";
import { getDashboard } from "@/lib/api";
import { FilterBar } from "./FilterBar";
import { KpiGrid } from "./KpiGrid";
import { CarrierChart, PerformanceChart, RegionChart, VolumeChart } from "./DashboardCharts";

const DEFAULTS = { start: "2025-01-01", end: "2025-12-31", carrier: "all", region: "all" };

export const DashboardTab = ({ meta }) => {
  const [filters, setFilters] = useState(DEFAULTS);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getDashboard(filters)
      .then(setData)
      .catch(() => toast.error("Could not load dashboard data"))
      .finally(() => setLoading(false));
  }, [filters]);

  return (
    <div className="space-y-6" data-testid="dashboard-tab">
      <div className="flex flex-col gap-1">
        <div className="eyebrow">Descriptive · Control room</div>
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Delivery performance</h1>
        <p className="text-sm text-slate-400" data-testid="dashboard-rows-matched">
          {data ? `${data.rows_matched} orders match the current filters.` : "Loading…"}
        </p>
      </div>
      <FilterBar meta={meta} filters={filters} setFilters={setFilters} defaults={DEFAULTS} />
      <KpiGrid kpis={data?.kpis} loading={loading} />
      {data && (
        <>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <VolumeChart data={data.monthly} />
            <PerformanceChart data={data.monthly} />
          </div>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <CarrierChart data={data.by_carrier} />
            <RegionChart data={data.by_region} />
          </div>
        </>
      )}
    </div>
  );
};
