import { Download } from "lucide-react";
import { downloadCsv, fmtMetric } from "@/lib/format";

export const DataTable = ({ result }) => {
  const { columns, rows } = result;
  const metric = result.plan.metric;
  return (
    <div data-testid="ask-data-table">
      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono text-xs text-slate-500">{rows.length} rows</span>
        <button data-testid="ask-csv-download-button" onClick={() => downloadCsv("query_result.csv", columns, rows)}
          className="flex items-center gap-2 rounded-full border border-slate-700 px-3 py-1.5 text-xs text-slate-300 transition-colors hover:border-sky-500 hover:text-sky-300">
          <Download className="h-3.5 w-3.5" /> Download CSV
        </button>
      </div>
      <div className="scroll-thin max-h-80 overflow-auto rounded-md border border-slate-800">
        <table className="w-full font-mono text-xs">
          <thead className="sticky top-0 bg-slate-900 text-slate-500">
            <tr>{columns.map((c) => <th key={c} className="px-3 py-2 text-left font-medium">{c}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-t border-slate-800/60 hover:bg-slate-800/30">
                {columns.map((c) => (
                  <td key={c} className={`px-3 py-1.5 ${c === "value" ? "text-sky-300" : "text-slate-200"}`}>
                    {c === "value" ? fmtMetric(r[c], metric) : String(r[c] ?? "—")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
