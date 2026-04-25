import { Cloud, CloudRain, Eye, Sun, Wind } from "lucide-react";
import { useEffect, useState } from "react";
import apiFetch from "../api";
import Skeleton from "./Skeleton";

const ICON = {
  clear:           Sun,
  "partly cloudy": Cloud,
  cloudy:          Cloud,
  "light rain":    CloudRain,
  haze:            Cloud,
  windy:           Wind,
};

export default function WeatherWidget() {
  const [w, setW] = useState(null);
  useEffect(() => {
    apiFetch("/stats/weather").then(setW).catch(() => setW({}));
    const t = setInterval(() => apiFetch("/stats/weather").then(setW), 60000);
    return () => clearInterval(t);
  }, []);

  if (!w) return <Skeleton className="h-28" />;

  const Icon = ICON[w.condition] || Cloud;
  return (
    <div className="bg-bg-card border border-border rounded-xl p-5">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-text-muted text-xs uppercase tracking-wider">Baku Port — weather</div>
          <div className="font-display text-3xl mt-1">{w.temp_c?.toFixed(1)}°<span className="text-text-muted text-base ml-1">C</span></div>
          <div className="text-text-muted text-xs capitalize mt-0.5">{w.condition}</div>
        </div>
        <Icon className="text-accent-cyan" size={32} />
      </div>
      <div className="grid grid-cols-3 gap-2 mt-4 text-xs font-mono">
        <Cell label="Wind"   value={`${w.wind_speed_knots?.toFixed(1)} kn`} />
        <Cell label="Wave"   value={`${w.wave_height_m?.toFixed(2)} m`} />
        <Cell label="Vis"    value={`${w.visibility_nm?.toFixed(1)} nm`} />
      </div>
      {w.advisory && (
        <div className="mt-3 text-[11px] text-accent-yellow border border-accent-yellow/30 bg-accent-yellow/5 rounded p-2">
          ⚠ {w.advisory}
        </div>
      )}
    </div>
  );
}

function Cell({ label, value }) {
  return (
    <div className="bg-bg-secondary rounded p-2 border border-border">
      <div className="text-text-muted text-[10px] uppercase">{label}</div>
      <div className="text-text-primary">{value}</div>
    </div>
  );
}
