import { useEffect, useState } from "react";
import "@/App.css";
import { Toaster } from "@/components/ui/sonner";
import { Header } from "@/components/Header";
import { DashboardTab } from "@/components/dashboard/DashboardTab";
import { AskTab } from "@/components/ask/AskTab";
import { ForecastTab } from "@/components/forecast/ForecastTab";
import { getMeta } from "@/lib/api";

function App() {
  const [tab, setTab] = useState("dashboard");
  const [meta, setMeta] = useState(null);

  useEffect(() => {
    getMeta().then(setMeta).catch(() => setMeta(null));
  }, []);

  return (
    <div className="App noise grid-bg min-h-screen bg-[#070b14] text-slate-100">
      <Header tab={tab} onTab={setTab} meta={meta} />
      <main className="relative z-10 mx-auto max-w-[1600px] px-4 py-8 sm:px-6 lg:px-10">
        <div className={tab === "dashboard" ? "" : "hidden"}>
          <DashboardTab meta={meta} />
        </div>
        <div className={tab === "ask" ? "" : "hidden"}>
          <AskTab meta={meta} />
        </div>
        <div className={tab === "forecast" ? "" : "hidden"}>
          <ForecastTab meta={meta} />
        </div>
      </main>
      <Toaster theme="dark" />
    </div>
  );
}

export default App;
