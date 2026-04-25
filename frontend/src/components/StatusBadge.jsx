const MAP = {
  OPTIMAL:    { color: "bg-accent-green/15 text-accent-green border-accent-green/40" },
  OVERSPEED:  { color: "bg-accent-red/15 text-accent-red border-accent-red/40" },
  UNDERSPEED: { color: "bg-accent-yellow/15 text-accent-yellow border-accent-yellow/40" },
  BERTH_READY:{ color: "bg-accent-cyan/15 text-accent-cyan border-accent-cyan/40" },
  scheduled:  { color: "bg-blue-400/15 text-blue-400 border-blue-400/40" },
  confirmed:  { color: "bg-accent-cyan/15 text-accent-cyan border-accent-cyan/40" },
  in_progress:{ color: "bg-accent-green/15 text-accent-green border-accent-green/40 animate-pulse" },
  completed:  { color: "bg-text-muted/15 text-text-muted border-text-muted/40" },
  cancelled:  { color: "bg-accent-red/15 text-accent-red border-accent-red/40 line-through" },
  delayed:    { color: "bg-accent-yellow/15 text-accent-yellow border-accent-yellow/40" },
  active:     { color: "bg-accent-green/15 text-accent-green border-accent-green/40" },
  inactive:   { color: "bg-text-muted/15 text-text-muted border-text-muted/40" },
};

export default function StatusBadge({ status }) {
  const cfg = MAP[status] || { color: "bg-text-muted/15 text-text-muted border-text-muted/40" };
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md border text-[11px] font-mono uppercase tracking-wide ${cfg.color}`}
    >
      <span className="status-dot bg-current" />
      {status}
    </span>
  );
}
