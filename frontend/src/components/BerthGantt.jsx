/**
 * Compact 14-day Gantt-style chart of berth bookings.
 * Each row = berth; bars span (eta..etd or actual times) with color by status.
 */
import { useMemo } from "react";

const STATUS_COLOR = {
  scheduled:   "#00d4ff",
  confirmed:   "#00d4ff",
  in_progress: "#00ff88",
  completed:   "#6b7fa3",
  cancelled:   "#ff3d3d",
  delayed:     "#ffd700",
};

export default function BerthGantt({ bookings = [], days = 14 }) {
  const now = Date.now();
  const start = now - 24 * 3600 * 1000;          // 1d in past
  const end = start + days * 24 * 3600 * 1000;
  const total = end - start;

  // group by berth
  const byBerth = useMemo(() => {
    const m = new Map();
    bookings.forEach((b) => {
      if (!b.berth) return;
      const key = b.berth.id;
      if (!m.has(key)) m.set(key, { berth: b.berth, items: [] });
      m.get(key).items.push(b);
    });
    return [...m.values()].sort((a, b) => a.berth.code.localeCompare(b.berth.code));
  }, [bookings]);

  if (byBerth.length === 0) {
    return <div className="text-text-muted text-sm py-6 text-center">No bookings to chart.</div>;
  }

  const dayTicks = [];
  for (let d = 0; d < days; d++) {
    const t = start + d * 24 * 3600 * 1000;
    dayTicks.push({ pct: ((t - start) / total) * 100, label: new Date(t).toUTCString().slice(5, 11) });
  }
  const nowPct = ((now - start) / total) * 100;

  return (
    <div className="bg-bg-card border border-border rounded-xl p-4">
      <h3 className="font-display font-semibold mb-3 text-sm">Berth occupancy — next {days} days</h3>

      {/* axis */}
      <div className="relative h-6 ml-32 border-b border-border text-[10px] font-mono text-text-muted">
        {dayTicks.map((t, i) => (
          <div key={i} style={{ left: `${t.pct}%` }}
            className="absolute -top-0.5 -translate-x-1/2 whitespace-nowrap">
            {t.label}
          </div>
        ))}
        <div style={{ left: `${nowPct}%` }}
          className="absolute -top-1 bottom-0 w-px bg-accent-cyan/60" />
      </div>

      <div className="space-y-1 mt-1">
        {byBerth.map(({ berth, items }) => (
          <div key={berth.id} className="flex items-center">
            <div className="w-32 shrink-0 pr-3">
              <div className="font-mono text-xs">{berth.code}</div>
              <div className="text-[10px] text-text-muted truncate">{berth.name}</div>
            </div>
            <div className="relative flex-1 h-7 bg-bg-secondary border border-border/50 rounded">
              {/* now line */}
              <div style={{ left: `${nowPct}%` }} className="absolute top-0 bottom-0 w-px bg-accent-cyan/60" />
              {items.map((b) => {
                const a = new Date(b.actual_arrival || b.scheduled_arrival).getTime();
                const e = new Date(b.actual_departure || b.scheduled_departure || (a + 12 * 3600 * 1000)).getTime();
                const x = Math.max(0, ((a - start) / total) * 100);
                const w = Math.min(100 - x, ((e - a) / total) * 100);
                if (w <= 0 || x >= 100) return null;
                const color = STATUS_COLOR[b.status] || "#6b7fa3";
                return (
                  <div
                    key={b.id}
                    title={`${b.vessel?.name || ""} • ${b.status}`}
                    style={{ left: `${x}%`, width: `${w}%`, background: color, borderColor: color }}
                    className="absolute top-1 bottom-1 rounded text-[10px] font-mono px-1 text-bg-primary truncate"
                  >
                    {b.vessel?.name}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-3 mt-3 text-[10px] font-mono text-text-muted">
        {Object.entries(STATUS_COLOR).map(([k, c]) => (
          <span key={k} className="flex items-center gap-1">
            <span className="w-3 h-3 rounded" style={{ background: c }} />{k}
          </span>
        ))}
      </div>
    </div>
  );
}
