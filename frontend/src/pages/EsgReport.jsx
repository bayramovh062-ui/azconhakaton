import { CheckCircle2, Fuel, Leaf, AlertTriangle } from "lucide-react";
import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import apiFetch from "../api";
import KpiCard from "../components/KpiCard";
import PageHeader from "../components/PageHeader";
import Skeleton from "../components/Skeleton";

const AXIS = { stroke: "#6b7fa3", fontSize: 11, fontFamily: "JetBrains Mono" };

export default function EsgReport() {
  const [summary, setSummary] = useState(null);
  const [daily, setDaily] = useState(null);

  useEffect(() => {
    apiFetch("/esg/summary").then(setSummary).catch(() => setSummary({}));
    apiFetch("/esg/daily?days=30").then(setDaily).catch(() => setDaily([]));
  }, []);

  const last7 = (daily || []).slice(-7).map((d) => ({
    day: d.day?.slice(5),
    optimal: d.optimal_arrivals,
    overspeed: d.overspeed_events,
  }));

  const trees = summary ? Math.max(0, Math.round((summary.total_co2_saved_kg || 0) / 21.7)) : 0;
  const overAlert = (summary?.total_overspeed_events || 0) > 10;

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      <PageHeader
        title="ESG Analytics"
        subtitle="Environmental impact report — Just-in-Time arrival optimization"
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {summary ? (
          <>
            <KpiCard Icon={Fuel}        label="Total Fuel Saved" value={summary.total_fuel_saved_liters || 0} suffix="L" accent="yellow" trend={4.8} />
            <KpiCard Icon={Leaf}        label="Total CO₂ Reduced" value={summary.total_co2_saved_kg || 0} suffix="kg" accent="green" trend={5.6} />
            <KpiCard Icon={CheckCircle2} label="Optimal Arrival Rate" value={optimalRate(summary)} suffix="%" accent="cyan" />
            <KpiCard Icon={AlertTriangle} label="Overspeed Events" value={summary.total_overspeed_events || 0} accent={overAlert ? "red" : "yellow"} />
          </>
        ) : (
          [...Array(4)].map((_, i) => <Skeleton key={i} className="h-28" />)
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <Panel title="Fuel & CO₂ saved (last 30 days)">
          {daily ? (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={daily} margin={{ top: 10, right: 12, bottom: 0, left: -10 }}>
                <CartesianGrid stroke="#1e2d4a" strokeDasharray="3 3" />
                <XAxis dataKey="day" {...AXIS} tickFormatter={(d) => d?.slice(5)} />
                <YAxis {...AXIS} />
                <Tooltip contentStyle={{ background: "#141d35", border: "1px solid #1e2d4a", color: "#e8f0fe" }} />
                <Legend />
                <Line type="monotone" dataKey="fuel_saved_liters" name="Fuel saved (L)" stroke="#00d4ff" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="co2_saved_kg"      name="CO₂ saved (kg)" stroke="#00ff88" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : <Skeleton className="h-[280px]" />}
        </Panel>

        <Panel title="Optimal vs Overspeed (last 7 days)">
          {daily ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={last7} margin={{ top: 10, right: 12, bottom: 0, left: -10 }}>
                <CartesianGrid stroke="#1e2d4a" strokeDasharray="3 3" />
                <XAxis dataKey="day" {...AXIS} />
                <YAxis {...AXIS} />
                <Tooltip contentStyle={{ background: "#141d35", border: "1px solid #1e2d4a", color: "#e8f0fe" }} />
                <Legend />
                <Bar dataKey="optimal"   name="Optimal"   stackId="a" fill="#00ff88" />
                <Bar dataKey="overspeed" name="Overspeed" stackId="a" fill="#ff3d3d" />
              </BarChart>
            </ResponsiveContainer>
          ) : <Skeleton className="h-[280px]" />}
        </Panel>
      </div>

      <div className="bg-bg-card border border-border rounded-xl p-6">
        <h3 className="font-display font-semibold mb-3 text-accent-cyan">Impact Summary</h3>
        <p className="text-text-primary text-base leading-relaxed">
          NexusAZ has prevented{" "}
          <span className="font-mono text-accent-green">
            {(summary?.total_co2_saved_kg || 0).toLocaleString(undefined, { maximumFractionDigits: 1 })} kg
          </span>{" "}
          of CO₂ emissions, equivalent to planting{" "}
          <span className="font-mono text-accent-green">{trees.toLocaleString()}</span> trees.
        </p>
        <p className="text-text-muted text-sm mt-2">
          Fleet average CII improvement:{" "}
          <span className="font-mono text-accent-cyan">
            {(summary?.co2_reduction_percent ?? 0).toFixed(2)}%
          </span>
        </p>
      </div>
    </div>
  );
}

function optimalRate(s) {
  const total = (s.total_optimal_arrivals || 0) + (s.total_overspeed_events || 0) + (s.total_underspeed_events || 0);
  if (!total) return 0;
  return ((s.total_optimal_arrivals || 0) / total) * 100;
}

function Panel({ title, children }) {
  return (
    <div className="bg-bg-card border border-border rounded-xl p-4">
      <h3 className="font-display font-semibold mb-2 text-text-primary text-sm">{title}</h3>
      {children}
    </div>
  );
}
