import { ArrowLeft, MapPin } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import apiFetch from "../api";
import FleetMap from "../components/FleetMap";
import PageHeader from "../components/PageHeader";
import Skeleton from "../components/Skeleton";
import StatusBadge from "../components/StatusBadge";

export default function VesselDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [vessel, setVessel] = useState(null);
  const [positions, setPositions] = useState([]);
  const [recs, setRecs] = useState([]);
  const [crew, setCrew] = useState([]);
  const [maint, setMaint] = useState([]);

  useEffect(() => {
    apiFetch(`/vessels/${id}`).then(setVessel).catch(() => setVessel(false));
    apiFetch(`/vessels/${id}/positions?limit=100`).then(setPositions).catch(() => {});
    apiFetch(`/jit/recommendations/${id}`).then(setRecs).catch(() => {});
    apiFetch(`/vessels/${id}/crew`).then(setCrew).catch(() => {});
    apiFetch(`/vessels/${id}/maintenance`).then(setMaint).catch(() => {});
  }, [id]);

  const speedSeries = useMemo(() =>
    [...positions].reverse().map((p) => ({
      t: new Date(p.recorded_at).toISOString().slice(11, 16),
      sog: p.speed_over_ground,
      cog: p.course_over_ground,
    })), [positions]);

  const trackPoints = useMemo(() =>
    [...positions].reverse().map((p) => [p.lat, p.lon]), [positions]);

  const lastPos = positions[0];

  if (vessel === false) {
    return <div className="p-8 text-text-muted">Vessel not found.</div>;
  }
  if (!vessel) return <div className="p-8"><Skeleton className="h-32" /></div>;

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      <button onClick={() => nav(-1)} className="text-text-muted hover:text-text-primary text-xs flex items-center gap-1 mb-3">
        <ArrowLeft size={14} /> Back
      </button>

      <PageHeader
        title={vessel.name}
        subtitle={`${vessel.imo || "—"} • ${vessel.mmsi || "—"} • ${vessel.flag || ""} • ${vessel.vessel_type}`}
        actions={
          <button onClick={() => nav("/map")}
            className="h-9 px-4 rounded-md border border-border text-text-muted hover:text-text-primary hover:border-accent-cyan/40 text-xs flex items-center gap-2">
            <MapPin size={14} /> View on Live Map
          </button>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <Stat label="Status" value={<StatusBadge status={vessel.status} />} />
        <Stat label="Operator" value={vessel.operator || "—"} />
        <Stat label="Length" value={vessel.length_meters ? `${vessel.length_meters.toFixed(1)} m` : "—"} />
        {lastPos && (
          <>
            <Stat label="Last position" value={`${lastPos.lat.toFixed(3)}°, ${lastPos.lon.toFixed(3)}°`} mono />
            <Stat label="Last SOG" value={`${(lastPos.speed_over_ground ?? 0).toFixed(1)} kn`} mono accent />
            <Stat label="Last seen" value={new Date(lastPos.recorded_at).toUTCString().slice(5, 22)} mono />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <Panel title={`Speed history (last ${positions.length} positions)`}>
          {speedSeries.length === 0
            ? <div className="text-text-muted text-sm">No positions logged.</div>
            : (
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={speedSeries} margin={{ top: 5, right: 12, bottom: 0, left: -10 }}>
                  <CartesianGrid stroke="#1e2d4a" strokeDasharray="3 3" />
                  <XAxis dataKey="t" stroke="#6b7fa3" fontSize={11} fontFamily="JetBrains Mono" />
                  <YAxis stroke="#6b7fa3" fontSize={11} fontFamily="JetBrains Mono" />
                  <Tooltip contentStyle={{ background: "#141d35", border: "1px solid #1e2d4a", color: "#e8f0fe" }} />
                  <Line type="monotone" dataKey="sog" name="SOG (kn)" stroke="#00d4ff" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="cog" name="COG (°)" stroke="#ffd700" strokeWidth={1.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )
          }
        </Panel>

        <Panel title="Track">
          {lastPos ? (
            <div className="h-[250px]">
              <FleetMap
                fullScreen
                vessels={[{
                  vessel_id: vessel.id, vessel_name: vessel.name, lat: lastPos.lat, lon: lastPos.lon,
                  current_speed: lastPos.speed_over_ground, recommended_speed: lastPos.speed_over_ground,
                  distance_nm: 0, status: "OPTIMAL", course: lastPos.course_over_ground,
                }]}
                vesselTrack={trackPoints}
                center={[lastPos.lat, lastPos.lon]}
                zoom={9}
              />
            </div>
          ) : (
            <div className="text-text-muted text-sm">No track yet.</div>
          )}
        </Panel>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <CrewPanel crew={crew} />
        <MaintenancePanel items={maint} />
      </div>

      <Panel title={`JIT recommendations (${recs.length})`}>
        {recs.length === 0
          ? <div className="text-text-muted text-sm">No JIT recommendations yet.</div>
          : (
            <div className="overflow-auto max-h-[320px]">
              <table className="w-full text-sm">
                <thead className="text-text-muted text-[11px] uppercase">
                  <tr>
                    {["Issued","Status","Rec speed","Distance","Fuel saved","CO₂ saved"].map((h) =>
                      <th key={h} className="text-left py-2 font-medium">{h}</th>)}
                  </tr>
                </thead>
                <tbody className="font-mono text-xs">
                  {recs.map((r) => (
                    <tr key={r.id} className="border-t border-border/60">
                      <td className="py-1.5">{new Date(r.issued_at).toUTCString().slice(5, 22)}</td>
                      <td><StatusBadge status={r.status} /></td>
                      <td>{r.recommended_speed?.toFixed(1)} kn</td>
                      <td>{r.distance_nm?.toFixed(1) ?? "—"} nm</td>
                      <td>{(r.fuel_saved_liters ?? 0).toFixed(2)} L</td>
                      <td>{(r.co2_saved_kg ?? 0).toFixed(1)} kg</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        }
      </Panel>
    </div>
  );
}

function CrewPanel({ crew }) {
  return (
    <Panel title={`Crew (${crew.length})`}>
      {crew.length === 0 ? <div className="text-text-muted text-sm">No crew data.</div> : (
        <div className="max-h-[280px] overflow-auto">
          <table className="w-full text-sm">
            <thead className="text-text-muted text-[11px] uppercase">
              <tr>
                {["Name", "Rank", "Nationality", "Years", "Duty"].map((h) =>
                  <th key={h} className="text-left py-2 font-medium">{h}</th>)}
              </tr>
            </thead>
            <tbody className="text-xs">
              {crew.map((c) => (
                <tr key={c.id} className="border-t border-border/50">
                  <td className="py-1.5">{c.name}</td>
                  <td className="font-mono">{c.rank}</td>
                  <td>{c.nationality}</td>
                  <td className="font-mono">{c.years_experience}y</td>
                  <td>
                    <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded ${
                      c.on_duty ? "bg-accent-green/15 text-accent-green" : "bg-text-muted/15 text-text-muted"
                    }`}>{c.on_duty ? "on" : "off"}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}

function MaintenancePanel({ items }) {
  const colorFor = (s) => ({
    overdue:    "text-accent-red border-accent-red/40 bg-accent-red/10",
    in_progress:"text-accent-cyan border-accent-cyan/40 bg-accent-cyan/10",
    scheduled:  "text-accent-yellow border-accent-yellow/40 bg-accent-yellow/10",
    completed:  "text-text-muted border-border bg-bg-secondary",
  })[s] || "text-text-muted border-border";
  return (
    <Panel title={`Maintenance (${items.length})`}>
      {items.length === 0 ? <div className="text-text-muted text-sm">No maintenance items.</div> : (
        <div className="max-h-[280px] overflow-auto space-y-2">
          {items.map((m) => (
            <div key={m.id} className="bg-bg-secondary border border-border rounded p-2.5 flex items-start gap-3">
              <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded border ${colorFor(m.status)}`}>{m.status}</span>
              <div className="flex-1 min-w-0">
                <div className="text-sm">{m.title}</div>
                <div className="text-[11px] text-text-muted font-mono">
                  {m.category} • due {new Date(m.due_date).toUTCString().slice(5, 16)} • ~${m.cost_estimate_usd.toLocaleString()}
                </div>
                {m.notes && <div className="text-[11px] text-text-muted mt-1">{m.notes}</div>}
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function Panel({ title, children }) {
  return (
    <div className="bg-bg-card border border-border rounded-xl p-4">
      <h3 className="font-display font-semibold mb-2 text-text-primary text-sm">{title}</h3>
      {children}
    </div>
  );
}

function Stat({ label, value, mono, accent }) {
  return (
    <div className="bg-bg-card border border-border rounded-lg p-3">
      <div className="text-[11px] uppercase text-text-muted">{label}</div>
      <div className={`mt-1 ${mono ? "font-mono" : "font-display"} ${accent ? "text-accent-cyan" : "text-text-primary"}`}>
        {value}
      </div>
    </div>
  );
}
