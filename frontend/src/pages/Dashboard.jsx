import { CheckCircle2, Fuel, Leaf, Ship, Wifi, WifiOff } from "lucide-react";
import { useEffect, useState } from "react";
import apiFetch, { getStoredUser } from "../api";
import ActivityFeed from "../components/ActivityFeed";
import FleetMap from "../components/FleetMap";
import KpiCard from "../components/KpiCard";
import LiveClock from "../components/LiveClock";
import PageHeader from "../components/PageHeader";
import Skeleton from "../components/Skeleton";
import StatusBadge from "../components/StatusBadge";
import TopVessels from "../components/TopVessels";
import WeatherWidget from "../components/WeatherWidget";
import useFleetSocket from "../hooks/useFleetSocket";

export default function Dashboard() {
  const user = getStoredUser();
  const { vessels, connected } = useFleetSocket();
  const [summary, setSummary] = useState(null);
  const [berths, setBerths] = useState([]);

  useEffect(() => {
    apiFetch("/esg/summary").then(setSummary).catch(() => setSummary({}));
  }, []);

  useEffect(() => {
    apiFetch("/bookings")
      .then((rows) =>
        setBerths(
          rows.map((b) => ({
            id: b.berth_id,
            ...b.berth,
            location_lat: 40.35 + (b.berth?.code === "BAK-B2" ? -0.0008 : b.berth?.code === "BAK-B3" ? 0.0017 : 0.0005),
            location_lon: 49.87 + (b.berth?.code === "BAK-B2" ? 0.0015 : b.berth?.code === "BAK-B3" ? -0.0012 : 0.0002),
            vessel_name: b.vessel?.name,
          }))
        )
      )
      .catch(() => setBerths([]));
  }, []);

  const greeting = useGreeting();

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      {/* Top bar */}
      <div className="flex items-center justify-between flex-wrap gap-2 mb-6">
        <div>
          <h2 className="font-display text-xl">
            {greeting}, <span className="text-accent-cyan">{user?.email?.split("@")[0] || "operator"}</span>
          </h2>
          <p className="text-text-muted text-xs mt-1">
            <LiveClock />
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          {connected ? (
            <span className="flex items-center gap-1.5 text-accent-green">
              <Wifi size={14} /> Live
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-accent-red">
              <WifiOff size={14} /> Reconnecting…
            </span>
          )}
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {summary ? (
          <>
            <KpiCard Icon={Ship}        label="Vessels Tracked"  value={summary.vessels_tracked || 0} accent="cyan" />
            <KpiCard Icon={CheckCircle2} label="Optimal Arrivals" value={summary.total_optimal_arrivals || 0} accent="green" />
            <KpiCard Icon={Fuel}        label="Fuel Saved"        value={summary.total_fuel_saved_liters || 0} suffix="L" accent="yellow" />
            <KpiCard Icon={Leaf}        label="CO₂ Reduced"       value={summary.total_co2_saved_kg || 0} suffix="kg" accent="green" />
          </>
        ) : (
          [...Array(4)].map((_, i) => <Skeleton key={i} className="h-28" />)
        )}
      </div>

      {/* Map + Fleet list */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 mb-4">
        <div className="lg:col-span-3">
          <FleetMap vessels={vessels} berths={berths} height={460} zoom={9} />
        </div>
        <div className="lg:col-span-2 bg-bg-card border border-border rounded-xl">
          <div className="px-4 py-3 border-b border-border flex items-center justify-between">
            <h3 className="font-display font-semibold">Fleet Status</h3>
            <span className="text-xs text-text-muted font-mono">{vessels.length} vessels</span>
          </div>
          <div className="max-h-[400px] overflow-auto divide-y divide-border">
            {vessels.length === 0 && (
              <div className="p-6 text-center text-text-muted text-sm">
                Awaiting telemetry…
              </div>
            )}
            {vessels.map((v) => (
              <div key={v.vessel_id} className="px-4 py-3 hover:bg-bg-secondary transition">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-display text-sm">{v.vessel_name}</span>
                  <StatusBadge status={v.status} />
                </div>
                <div className="flex items-center justify-between text-xs font-mono text-text-muted">
                  <span>SOG {v.current_speed?.toFixed(1)} kn</span>
                  <span>→ Rec {v.recommended_speed?.toFixed(1)} kn</span>
                  <span>{v.distance_nm?.toFixed(1)} nm</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Weather + activity + top vessels */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <WeatherWidget />
        <ActivityFeed />
        <TopVessels limit={5} />
      </div>
    </div>
  );
}

function useGreeting() {
  const h = new Date().getUTCHours();
  if (h < 5) return "Good night";
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}
