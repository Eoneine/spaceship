import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { ChartFrame, ChartTooltip, axisProps } from "@/components/charts/ChartsParts";
import { COLORS, monthLabel } from "@/lib/format";

const grid = <CartesianGrid stroke={COLORS.grid} strokeDasharray="3 3" vertical={false} />;
const legend = <Legend wrapperStyle={{ fontSize: 11, fontFamily: "JetBrains Mono", color: "#94a3b8" }} />;

export const VolumeChart = ({ data }) => (
  <ChartFrame title="Order volume per month" subtitle="All statuses" testId="chart-monthly-volume">
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ left: -20, right: 24 }}>
        {grid}
        <XAxis dataKey="month" tickFormatter={monthLabel} {...axisProps} />
        <YAxis {...axisProps} allowDecimals={false} />
        <Tooltip content={<ChartTooltip />} labelFormatter={monthLabel} />
        <Line dataKey="orders" name="Orders" stroke={COLORS.sky} strokeWidth={2.5} dot={{ r: 3, fill: COLORS.sky }} />
      </LineChart>
    </ResponsiveContainer>
  </ChartFrame>
);

export const PerformanceChart = ({ data }) => (
  <ChartFrame title="Delivered on-time vs delayed" subtitle="Per month, resolved orders only" testId="chart-ontime-vs-delayed">
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ left: -20, right: 24 }}>
        {grid}
        <XAxis dataKey="month" tickFormatter={monthLabel} {...axisProps} />
        <YAxis {...axisProps} allowDecimals={false} />
        <Tooltip cursor={{ fill: "rgba(148,163,184,0.06)" }} content={<ChartTooltip />} />
        {legend}
        <Bar dataKey="delivered" name="Delivered" stackId="a" fill={COLORS.ontime} />
        <Bar dataKey="delayed" name="Delayed" stackId="a" fill={COLORS.delayed} radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  </ChartFrame>
);

export const CarrierChart = ({ data }) => (
  <ChartFrame title="Delay rate by carrier" subtitle="delayed ÷ (delivered + delayed)" testId="chart-carrier-delay-rate">
    <ResponsiveContainer width="100%" height={Math.max(240, data.length * 30)}>
      <BarChart data={data} layout="vertical" margin={{ left: 0, right: 30 }}>
        <CartesianGrid stroke={COLORS.grid} strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" unit="%" {...axisProps} />
        <YAxis type="category" dataKey="carrier" width={84} {...axisProps} />
        <Tooltip cursor={{ fill: "rgba(148,163,184,0.06)" }}
          content={<ChartTooltip formatter={(v, p) => `${v}% (${p.payload.delayed}/${p.payload.delayed + p.payload.delivered})`} />} />
        <Bar dataKey="delay_rate" name="Delay rate" fill={COLORS.delayed} radius={[0, 4, 4, 0]} barSize={14} />
      </BarChart>
    </ResponsiveContainer>
  </ChartFrame>
);

export const RegionChart = ({ data }) => (
  <ChartFrame title="Orders & delays by region" subtitle="Order count with delayed share" testId="chart-region-breakdown">
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ left: -20, right: 24 }}>
        {grid}
        <XAxis dataKey="region" {...axisProps} />
        <YAxis {...axisProps} allowDecimals={false} />
        <Tooltip cursor={{ fill: "rgba(148,163,184,0.06)" }} content={<ChartTooltip />} />
        {legend}
        <Bar dataKey="orders" name="Orders" fill={COLORS.indigo} radius={[3, 3, 0, 0]} />
        <Bar dataKey="delayed" name="Delayed" fill={COLORS.delayed} radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  </ChartFrame>
);
