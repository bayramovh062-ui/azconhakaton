import { formatDistanceToNow } from "date-fns";
import { AlertTriangle, Bell, CheckCircle2, Info, Wifi } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import apiFetch from "../api";
import PageHeader from "../components/PageHeader";
import Skeleton from "../components/Skeleton";

const SEV_ICON = {
  critical: { Icon: AlertTriangle, color: "text-accent-red"   },
  warning:  { Icon: AlertTriangle, color: "text-accent-yellow"},
  info:     { Icon: Info,          color: "text-accent-cyan"  },
};

const CAT_LABEL = {
  jit: "JIT", sla: "Booking", infra: "Infrastructure", telemetry: "Telemetry",
};

export default function Alerts() {
  const nav = useNavigate();
  const [rows, setRows] = useState(null);
  const [sev, setSev] = useState("ALL");
  const [cat, setCat] = useState("ALL");
  const [acked, setAcked] = useState(() => new Set());

  async function load() {
    setRows(null);
    try { setRows(await apiFetch("/alerts?limit=100")); }
    catch { setRows([]); }
  }
  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    if (!rows) return null;
    return rows.filter((a) =>
      (sev === "ALL" || a.severity === sev) &&
      (cat === "ALL" || a.category === cat)
    );
  }, [rows, sev, cat]);

  function ack(id) {
    setAcked((s) => new Set(s).add(id));
  }

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      <PageHeader
        title="Alerts"
        subtitle="Live feed derived from JIT, telemetry, bookings and infrastructure"
        actions={
          <button onClick={load}
            className="h-9 px-3 rounded-md border border-border text-text-muted hover:text-text-primary hover:border-accent-cyan/40 text-xs flex items-center gap-2">
            <Wifi size={14} /> Refresh
          </button>
        }
      />

      <div className="flex flex-wrap gap-2 mb-4">
        {["ALL", "critical", "warning", "info"].map((s) => (
          <button key={s} onClick={() => setSev(s)}
            className={`h-8 px-3 rounded-md text-[11px] uppercase font-mono tracking-wider border ${
              sev === s
                ? "bg-accent-cyan/15 text-accent-cyan border-accent-cyan/40"
                : "bg-bg-card text-text-muted border-border"
            }`}>{s}</button>
        ))}
        <span className="w-px self-stretch bg-border mx-2" />
        {["ALL", "jit", "sla", "infra", "telemetry"].map((c) => (
          <button key={c} onClick={() => setCat(c)}
            className={`h-8 px-3 rounded-md text-[11px] uppercase font-mono tracking-wider border ${
              cat === c
                ? "bg-accent-cyan/15 text-accent-cyan border-accent-cyan/40"
                : "bg-bg-card text-text-muted border-border"
            }`}>{c}</button>
        ))}
      </div>

      <div className="space-y-2">
        {filtered === null && [...Array(5)].map((_, i) => <Skeleton key={i} className="h-16" />)}
        {filtered?.length === 0 && (
          <div className="text-center text-text-muted py-12">
            <CheckCircle2 className="mx-auto mb-2 text-accent-green" />
            All clear — no alerts match the current filter.
          </div>
        )}
        {filtered?.map((a) => {
          const cfg = SEV_ICON[a.severity] || SEV_ICON.info;
          const Icon = cfg.Icon;
          const isAcked = acked.has(a.id);
          return (
            <div
              key={a.id}
              className={`bg-bg-card border border-border rounded-lg p-4 flex gap-3 ${isAcked ? "opacity-50" : ""}`}
            >
              <Icon className={`${cfg.color} mt-0.5 shrink-0`} size={20} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-display font-semibold text-text-primary">{a.title}</span>
                  <span className="text-[10px] font-mono uppercase text-text-muted border border-border px-1.5 rounded">
                    {CAT_LABEL[a.category] || a.category}
                  </span>
                  <span className={`text-[10px] font-mono uppercase ${cfg.color}`}>{a.severity}</span>
                </div>
                <div className="text-sm text-text-muted mt-0.5">{a.message}</div>
                <div className="text-[11px] text-text-muted/80 font-mono mt-1">
                  {formatDistanceToNow(new Date(a.occurred_at), { addSuffix: true })}
                </div>
              </div>
              <div className="flex flex-col gap-1 items-end shrink-0">
                {a.vessel_id && (
                  <button onClick={() => nav(`/fleet/${a.vessel_id}`)}
                    className="text-xs text-accent-cyan hover:underline">View vessel</button>
                )}
                {!isAcked && (
                  <button onClick={() => ack(a.id)}
                    className="text-xs text-text-muted hover:text-text-primary">Acknowledge</button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
