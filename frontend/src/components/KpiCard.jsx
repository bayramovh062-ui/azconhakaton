import { useEffect, useState } from "react";

/**
 * Animated KPI tile. `value` is animated from 0 → final on mount/update.
 */
export default function KpiCard({ Icon, label, value, suffix = "", accent = "cyan", trend = null }) {
  const display = useCountUp(value, 1000);
  const accentClass = {
    cyan:   "text-accent-cyan border-accent-cyan/30 shadow-glow",
    green:  "text-accent-green border-accent-green/30 shadow-glow-green",
    red:    "text-accent-red border-accent-red/30 shadow-glow-red",
    yellow: "text-accent-yellow border-accent-yellow/30",
  }[accent];

  return (
    <div className={`bg-bg-card border ${accentClass} rounded-xl p-5 relative overflow-hidden`}>
      <div className="flex items-start justify-between">
        <div>
          <div className="text-text-muted text-xs uppercase tracking-wider">{label}</div>
          <div className={`mt-2 font-display font-bold text-3xl ${accentClass.split(" ")[0]}`}>
            {Number.isFinite(value) ? display.toLocaleString(undefined, { maximumFractionDigits: 1 }) : "—"}
            {suffix && <span className="text-text-muted text-base ml-1">{suffix}</span>}
          </div>
          {trend != null && (
            <div className={`mt-1 text-xs ${trend >= 0 ? "text-accent-green" : "text-accent-red"}`}>
              {trend >= 0 ? "▲" : "▼"} {Math.abs(trend).toFixed(1)}% vs last week
            </div>
          )}
        </div>
        {Icon && <Icon className={accentClass.split(" ")[0]} size={28} />}
      </div>
      <div className="absolute -right-8 -bottom-8 w-24 h-24 rounded-full bg-current opacity-5 pointer-events-none" />
    </div>
  );
}

function useCountUp(target, duration = 800) {
  const [v, setV] = useState(0);
  useEffect(() => {
    if (!Number.isFinite(target)) return;
    let raf;
    const start = performance.now();
    const from = 0;
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setV(from + (target - from) * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);
  return v;
}
