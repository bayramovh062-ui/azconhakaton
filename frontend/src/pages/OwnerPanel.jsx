import { formatDistanceToNow } from "date-fns";
import {
  Activity, Anchor, Building2, CheckCircle2, DollarSign, Fuel, Leaf, Ship, TrendingUp,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import apiFetch, { getStoredUser } from "../api";
import KpiCard from "../components/KpiCard";
import PageHeader from "../components/PageHeader";
import Skeleton from "../components/Skeleton";
import StatusBadge from "../components/StatusBadge";

const FLAG_EMOJI = {
  Azerbaijan: "🇦🇿", Russia: "🇷🇺", Turkey: "🇹🇷", Iran: "🇮🇷",
  Kazakhstan: "🇰🇿", Turkmenistan: "🇹🇲",
};

export default function OwnerPanel() {
  const me = getStoredUser();
  const nav = useNavigate();
  const [summary, setSummary] = useState(null);
  const [vessels, setVessels] = useState(null);
  const [trend, setTrend] = useState(null);

  useEffect(() => {
    apiFetch("/owner/summary").then(setSummary).catch(() => setSummary({}));
    apiFetch("/owner/vessels").then(setVessels).catch(() => setVessels([]));
    apiFetch("/owner/trend?days=30").then(setTrend).catch(() => setTrend([]));
  }, []);

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      <PageHeader
        title="Ship Owner Panel"
        subtitle={
          <span className="flex items-center gap-2">
            <Building2 size={14} className="text-accent-cyan" />
            <span className="font-mono">{summary?.company || me?.operator_company || "—"}</span>
          </span>
        }
      />

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        {summary ? (
          <>
            <KpiCard Icon={Ship}        label="Fleet vessels"     value={summary.vessel_count || 0} accent="cyan" />
            <KpiCard Icon={Activity}    label="Active right now"  value={summary.active_vessels || 0} accent="green" />
            <KpiCard Icon={Anchor}      label="Upcoming bookings" value={summary.upcoming_bookings || 0} accent="cyan" />
            <KpiCard Icon={DollarSign}  label="Cost savings (USD)" value={summary.cost_savings_usd || 0} accent="green" />
          </>
        ) : [...Array(4)].map((_, i) => <Skeleton key={i} className="h-28" />)}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {summary ? (
          <>
            <KpiCard Icon={Fuel}         label="Fuel saved"        value={summary.total_fuel_saved_liters || 0} suffix="L"  accent="yellow" />
            <KpiCard Icon={Leaf}         label="CO₂ avoided"       value={summary.total_co2_saved_kg || 0}      suffix="kg" accent="green" />
            <KpiCard Icon={CheckCircle2} label="Optimal arrivals"  value={summary.optimal_arrivals || 0}        accent="green" />
            <KpiCard Icon={TrendingUp}   label="Overspeed alerts"  value={summary.overspeed_alerts || 0}        accent={summary.overspeed_alerts > 5 ? "red" : "yellow"} />
          </>
        ) : [...Array(4)].map((_, i) => <Skeleton key={i + 4} className="h-28" />)}
      </div>

      {/* Trend chart */}
      <div className="bg-bg-card border border-border rounded-xl p-4 mb-4">
        <h3 className="font-display font-semibold text-sm mb-2">Fleet savings trend (last 30 days)</h3>
        {trend === null ? <Skeleton className="h-[260px]" /> :
          trend.length === 0
            ? <div className="text-text-muted text-sm py-12 text-center">No JIT activity for this fleet yet.</div>
            : (
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={trend} margin={{ top: 5, right: 16, bottom: 0, left: -10 }}>
                  <CartesianGrid stroke="#1e2d4a" strokeDasharray="3 3" />
                  <XAxis dataKey="day" stroke="#6b7fa3" fontSize={11} fontFamily="JetBrains Mono" />
                  <YAxis stroke="#6b7fa3" fontSize={11} fontFamily="JetBrains Mono" />
                  <Tooltip contentStyle={{ background: "#141d35", border: "1px solid #1e2d4a", color: "#e8f0fe" }} />
                  <Legend />
                  <Line type="monotone" dataKey="fuel_saved_liters" name="Fuel saved (L)" stroke="#00d4ff" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="co2_saved_kg"      name="CO₂ saved (kg)" stroke="#00ff88" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )
        }
      </div>

      {/* Vessel table */}
      <div className="bg-bg-card border border-border rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <h3 className="font-display font-semibold">Your fleet</h3>
          <span className="text-xs text-text-muted font-mono">{vessels?.length ?? 0} vessels</span>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-bg-secondary text-text-muted text-[11px] uppercase tracking-wider">
            <tr>
              {["Vessel", "Type", "Status", "Last position", "SOG", "Next ETA", "Berth", "CO₂ saved"].map((h) => (
                <th key={h} className="text-left px-4 py-3 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {vessels === null && [...Array(3)].map((_, i) => (
              <tr key={i}><td colSpan={8} className="px-4 py-2"><Skeleton className="h-8" /></td></tr>
            ))}
            {vessels?.length === 0 && (
              <tr><td colSpan={8} className="px-6 py-8 text-center text-text-muted">No vessels assigned to this operator.</td></tr>
            )}
            {vessels?.map((v) => (
              <tr key={v.id} onClick={() => nav(`/fleet/${v.id}`)}
                  className="border-t border-border hover:bg-bg-secondary/40 cursor-pointer">
                <td className="px-4 py-3">
                  <div className="font-display">{v.name} {FLAG_EMOJI[v.flag] || ""}</div>
                  <div className="font-mono text-[11px] text-text-muted">{v.imo} • {v.mmsi}</div>
                </td>
                <td className="px-4 py-3 capitalize">{v.vessel_type}</td>
                <td className="px-4 py-3"><StatusBadge status={v.status} /></td>
                <td className="px-4 py-3 font-mono text-[11px] text-text-muted">
                  {v.last_lat != null ? `${v.last_lat.toFixed(3)}°, ${v.last_lon.toFixed(3)}°` : "—"}
                  <div className="text-[10px]">
                    {v.last_seen ? formatDistanceToNow(new Date(v.last_seen), { addSuffix: true }) : "no telemetry"}
                  </div>
                </td>
                <td className="px-4 py-3 font-mono">{v.last_sog?.toFixed(1) ?? "—"} kn</td>
                <td className="px-4 py-3 font-mono text-xs">
                  {v.next_eta ? new Date(v.next_eta).toUTCString().slice(5, 22) : <span className="text-text-muted/60">no booking</span>}
                </td>
                <td className="px-4 py-3 font-mono">{v.next_berth || "—"}</td>
                <td className="px-4 py-3 font-mono text-accent-green">{v.co2_saved_kg?.toFixed(1) ?? "0"} kg</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
