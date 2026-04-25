import { formatDistanceToNow } from "date-fns";
import {
  Anchor, AlertCircle, BookOpen, CheckCircle2, Compass, Gauge, MapPin,
  Plus, Send, Target, Wifi,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import apiFetch from "../api";
import FleetMap from "../components/FleetMap";
import PageHeader from "../components/PageHeader";
import Skeleton from "../components/Skeleton";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../components/Toast";

const KIND_LABEL = {
  entry: "Log entry", observation: "Observation", incident: "Incident",
  fuel: "Fuel", eta_update: "ETA update",
};

export default function CaptainPanel() {
  const toast = useToast();
  const [voyage, setVoyage] = useState(null);
  const [logs, setLogs] = useState(null);

  async function refresh() {
    try { setVoyage(await apiFetch("/captain/voyage")); }
    catch (e) { setVoyage(false); toast.error(e.message || "voyage load failed"); }
    apiFetch("/captain/log?limit=30").then(setLogs).catch(() => setLogs([]));
  }

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 30000);
    return () => clearInterval(t);
  }, []);

  if (voyage === false) {
    return <div className="p-8 text-text-muted">No vessel assigned to this account.</div>;
  }
  if (!voyage) return <div className="p-8"><Skeleton className="h-32" /></div>;

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      <PageHeader
        title={`Capt. cockpit — ${voyage.vessel_name}`}
        subtitle={
          <span className="font-mono text-xs">
            {voyage.imo || "—"} • {voyage.mmsi || "—"} • {voyage.flag || ""}
          </span>
        }
        actions={
          <button onClick={refresh}
            className="h-9 px-3 rounded-md border border-border text-text-muted hover:text-text-primary hover:border-accent-cyan/40 text-xs flex items-center gap-2">
            <Wifi size={14} /> Refresh
          </button>
        }
      />

      {/* Cockpit KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <Cell Icon={Compass} label="Heading"        value={voyage.last_cog != null ? `${voyage.last_cog.toFixed(0)}°` : "—"} />
        <Cell Icon={Gauge}   label="SOG (current)"  value={voyage.last_sog != null ? `${voyage.last_sog.toFixed(1)} kn` : "—"} />
        <Cell Icon={Target}  label="JIT recommended" value={voyage.recommended_speed != null ? `${voyage.recommended_speed.toFixed(1)} kn` : "—"} accent="cyan" />
        <Cell Icon={MapPin}  label="Distance to port" value={voyage.distance_to_port_nm != null ? `${voyage.distance_to_port_nm.toFixed(1)} nm` : "—"} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        {/* Map */}
        <div className="lg:col-span-2 h-[420px]">
          {voyage.last_lat != null ? (
            <FleetMap
              fullScreen
              center={[voyage.last_lat, voyage.last_lon]}
              zoom={9}
              vessels={[{
                vessel_id: voyage.vessel_id,
                vessel_name: voyage.vessel_name,
                lat: voyage.last_lat, lon: voyage.last_lon,
                current_speed: voyage.last_sog,
                recommended_speed: voyage.recommended_speed,
                distance_nm: voyage.distance_to_port_nm,
                status: voyage.jit_status || "OPTIMAL",
                course: voyage.last_cog || 0,
                scheduled_arrival: voyage.eta,
              }]}
            />
          ) : (
            <div className="h-full grid place-items-center bg-bg-card border border-border rounded-xl text-text-muted">No telemetry yet.</div>
          )}
        </div>

        {/* JIT advisory */}
        <JitAdvisory voyage={voyage} onAck={refresh} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Booking card */}
        <BookingCard voyage={voyage} />

        {/* Position submit */}
        <PositionForm onPosted={refresh} initial={voyage} />

        {/* Voyage log */}
        <VoyageLog logs={logs} onAdd={refresh} />
      </div>
    </div>
  );
}

function Cell({ Icon, label, value, accent }) {
  const color = accent === "cyan" ? "text-accent-cyan" : "text-text-primary";
  return (
    <div className="bg-bg-card border border-border rounded-xl p-3">
      <div className="flex items-center justify-between">
        <div className="text-[11px] uppercase text-text-muted tracking-wider">{label}</div>
        {Icon && <Icon size={14} className="text-text-muted" />}
      </div>
      <div className={`mt-1 font-mono text-xl ${color}`}>{value}</div>
    </div>
  );
}

function JitAdvisory({ voyage, onAck }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  if (!voyage.jit_status) {
    return (
      <div className="bg-bg-card border border-border rounded-xl p-5">
        <div className="text-text-muted text-sm">No JIT advisory — needs an active booking + recent position.</div>
      </div>
    );
  }
  const tone = {
    OPTIMAL:    "border-accent-green/40 text-accent-green",
    OVERSPEED:  "border-accent-red/40 text-accent-red",
    UNDERSPEED: "border-accent-yellow/40 text-accent-yellow",
    BERTH_READY:"border-accent-cyan/40 text-accent-cyan",
  }[voyage.jit_status] || "border-border text-text-muted";

  async function ack(decision) {
    if (!voyage.latest_recommendation_id) return;
    setBusy(true);
    try {
      await apiFetch(`/captain/jit/${voyage.latest_recommendation_id}/acknowledge`, {
        method: "POST",
        body: JSON.stringify({ decision }),
      });
      toast.success(`Recommendation ${decision}`);
      onAck();
    } catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  }

  return (
    <div className={`bg-bg-card border rounded-xl p-5 ${tone}`}>
      <div className="text-[11px] uppercase tracking-wider text-text-muted">JIT advisory</div>
      <div className="font-display font-bold text-2xl mt-1"><StatusBadge status={voyage.jit_status} /></div>

      <div className="mt-3 space-y-1 text-xs font-mono">
        <Row k="Recommended" v={`${voyage.recommended_speed?.toFixed(2) ?? "—"} kn`} />
        <Row k="Δ vs current" v={voyage.last_sog != null && voyage.recommended_speed != null
          ? `${(voyage.last_sog - voyage.recommended_speed).toFixed(2)} kn` : "—"} />
        <Row k="Time available" v={voyage.time_available_hours?.toFixed(2) ?? "—"} suffix="h" />
        <Row k="Distance" v={voyage.distance_to_port_nm?.toFixed(2) ?? "—"} suffix="nm" />
        <Row k="Fuel saved if applied" v={voyage.fuel_saved_liters?.toFixed(2) ?? "—"} suffix="L" />
        <Row k="CO₂ avoided" v={voyage.co2_saved_kg?.toFixed(2) ?? "—"} suffix="kg" />
      </div>

      {voyage.latest_recommendation_id && (
        <div className="grid grid-cols-3 gap-2 mt-4">
          <button disabled={busy} onClick={() => ack("accepted")}
            className="h-9 rounded-md bg-accent-green/15 border border-accent-green/40 text-accent-green text-xs flex items-center justify-center gap-1 disabled:opacity-50">
            <CheckCircle2 size={14} /> Accept
          </button>
          <button disabled={busy} onClick={() => ack("applied")}
            className="h-9 rounded-md bg-accent-cyan/15 border border-accent-cyan/40 text-accent-cyan text-xs flex items-center justify-center gap-1 disabled:opacity-50">
            <Target size={14} /> Apply
          </button>
          <button disabled={busy} onClick={() => ack("rejected")}
            className="h-9 rounded-md bg-accent-red/15 border border-accent-red/40 text-accent-red text-xs flex items-center justify-center gap-1 disabled:opacity-50">
            <AlertCircle size={14} /> Reject
          </button>
        </div>
      )}
    </div>
  );
}

function BookingCard({ voyage }) {
  return (
    <div className="bg-bg-card border border-border rounded-xl p-4">
      <h3 className="font-display font-semibold mb-2 flex items-center gap-2">
        <Anchor size={16} className="text-accent-cyan" /> Active booking
      </h3>
      {voyage.booking_id ? (
        <div className="text-sm space-y-1.5">
          <div className="font-mono text-xs text-text-muted">{voyage.booking_ref}</div>
          <div>Berth <strong className="font-mono">{voyage.berth_code}</strong> — {voyage.berth_name}</div>
          <div>ETA <span className="font-mono">{new Date(voyage.eta).toUTCString().slice(5, 22)}</span></div>
          <div className="text-text-muted text-xs">
            ({formatDistanceToNow(new Date(voyage.eta), { addSuffix: true })})
          </div>
        </div>
      ) : (
        <div className="text-text-muted text-sm">No active booking.</div>
      )}
    </div>
  );
}

function PositionForm({ onPosted, initial }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    lat: initial.last_lat ?? 40.30,
    lon: initial.last_lon ?? 49.85,
    sog: initial.last_sog ?? 11.0,
    cog: initial.last_cog ?? 30,
  });

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    try {
      await apiFetch("/captain/position", {
        method: "POST",
        body: JSON.stringify({
          lat: Number(form.lat), lon: Number(form.lon),
          speed_over_ground: Number(form.sog),
          course_over_ground: Number(form.cog),
          heading: Number(form.cog),
        }),
      });
      toast.success("Position logged");
      onPosted();
    } catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  }

  return (
    <form onSubmit={submit} className="bg-bg-card border border-border rounded-xl p-4 space-y-2">
      <h3 className="font-display font-semibold mb-1 flex items-center gap-2">
        <Send size={16} className="text-accent-cyan" /> Submit position
      </h3>
      <div className="grid grid-cols-2 gap-2">
        <Field label="Lat (°)" value={form.lat} onChange={(v) => setForm({ ...form, lat: v })} />
        <Field label="Lon (°)" value={form.lon} onChange={(v) => setForm({ ...form, lon: v })} />
        <Field label="SOG (kn)" value={form.sog} onChange={(v) => setForm({ ...form, sog: v })} />
        <Field label="COG (°)" value={form.cog} onChange={(v) => setForm({ ...form, cog: v })} />
      </div>
      <button type="submit" disabled={busy}
        className="w-full h-9 rounded-md bg-accent-cyan text-bg-primary font-semibold text-sm hover:shadow-glow disabled:opacity-50">
        {busy ? "Sending…" : "Push to AIS feed"}
      </button>
    </form>
  );
}

function VoyageLog({ logs, onAdd }) {
  const toast = useToast();
  const [note, setNote] = useState("");
  const [kind, setKind] = useState("entry");
  const [busy, setBusy] = useState(false);

  async function add(e) {
    e.preventDefault();
    if (!note.trim()) return;
    setBusy(true);
    try {
      await apiFetch("/captain/log", {
        method: "POST",
        body: JSON.stringify({ note: note.trim(), kind }),
      });
      setNote("");
      toast.success("Log added");
      onAdd();
    } catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  }

  return (
    <div className="bg-bg-card border border-border rounded-xl p-4 flex flex-col">
      <h3 className="font-display font-semibold mb-2 flex items-center gap-2">
        <BookOpen size={16} className="text-accent-cyan" /> Voyage log
      </h3>
      <form onSubmit={add} className="flex flex-col gap-2 mb-3">
        <select value={kind} onChange={(e) => setKind(e.target.value)}
          className="h-8 px-2 bg-bg-secondary border border-border rounded text-xs">
          {Object.entries(KIND_LABEL).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
        <textarea value={note} onChange={(e) => setNote(e.target.value)}
          placeholder="Note for the log…" rows={2}
          className="bg-bg-secondary border border-border rounded p-2 text-sm outline-none focus:border-accent-cyan/60" />
        <button disabled={busy || !note.trim()}
          className="self-end h-8 px-3 rounded bg-accent-cyan text-bg-primary text-xs font-semibold disabled:opacity-50 flex items-center gap-1">
          <Plus size={12} /> Add
        </button>
      </form>

      <div className="border-t border-border pt-2 max-h-[260px] overflow-auto divide-y divide-border/60 -mx-1">
        {logs === null && <div className="p-2"><Skeleton className="h-16" /></div>}
        {logs?.length === 0 && <div className="text-text-muted text-xs p-2">No log entries yet.</div>}
        {logs?.map((l) => (
          <div key={l.id} className="px-1 py-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono uppercase text-accent-cyan">{KIND_LABEL[l.kind] || l.kind}</span>
              <span className="text-[10px] text-text-muted">
                {formatDistanceToNow(new Date(l.created_at), { addSuffix: true })}
              </span>
            </div>
            <div className="text-sm mt-0.5">{l.note}</div>
            {l.author_name && <div className="text-[10px] text-text-muted">{l.author_name}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}

function Row({ k, v, suffix }) {
  return (
    <div className="flex justify-between border-b border-border/30 py-1">
      <span className="text-text-muted">{k}</span>
      <span>{v}{suffix && <span className="text-text-muted ml-1">{suffix}</span>}</span>
    </div>
  );
}

function Field({ label, value, onChange }) {
  return (
    <label className="block">
      <span className="text-[10px] uppercase tracking-wider text-text-muted">{label}</span>
      <input type="number" step="0.01" value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full h-8 px-2 rounded-md bg-bg-secondary border border-border outline-none focus:border-accent-cyan/60 text-sm" />
    </label>
  );
}
