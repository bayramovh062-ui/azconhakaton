import { Plus, Ship, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import apiFetch from "../api";
import PageHeader from "../components/PageHeader";
import Skeleton from "../components/Skeleton";
import StatusBadge from "../components/StatusBadge";

const FLAG = {
  Azerbaijan: "🇦🇿", Russia: "🇷🇺", Turkey: "🇹🇷", Iran: "🇮🇷",
  Kazakhstan: "🇰🇿", Turkmenistan: "🇹🇲",
};

export default function Compare() {
  const [vessels, setVessels] = useState([]);
  const [picked, setPicked] = useState([]);   // array of vessel ids
  const [details, setDetails] = useState({}); // id -> { vessel, positions, recs }

  useEffect(() => { apiFetch("/vessels").then(setVessels).catch(() => {}); }, []);

  async function add(id) {
    if (!id || picked.includes(id) || picked.length >= 3) return;
    setPicked([...picked, id]);
    if (!details[id]) {
      const [vessel, positions, recs] = await Promise.all([
        apiFetch(`/vessels/${id}`),
        apiFetch(`/vessels/${id}/positions?limit=20`).catch(() => []),
        apiFetch(`/jit/recommendations/${id}`).catch(() => []),
      ]);
      setDetails((d) => ({ ...d, [id]: { vessel, positions, recs } }));
    }
  }

  function remove(id) {
    setPicked(picked.filter((x) => x !== id));
  }

  const cards = picked.map((id) => details[id]);

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      <PageHeader
        title="Compare vessels"
        subtitle="Select up to three vessels to compare side-by-side"
      />

      <div className="bg-bg-card border border-border rounded-xl p-3 flex items-center gap-2 mb-4">
        <Ship size={16} className="text-accent-cyan ml-1" />
        <select
          onChange={(e) => { add(e.target.value); e.target.value = ""; }}
          disabled={picked.length >= 3}
          className="flex-1 h-9 px-2 bg-bg-secondary border border-border rounded text-sm disabled:opacity-50">
          <option value="">{picked.length >= 3 ? "Maximum 3 selected — remove one to add another" : "+ Add a vessel…"}</option>
          {vessels.filter((v) => !picked.includes(v.id)).map((v) => (
            <option key={v.id} value={v.id}>{v.name} • {v.flag} • {v.imo}</option>
          ))}
        </select>
        <span className="text-xs text-text-muted font-mono">{picked.length}/3</span>
      </div>

      {cards.length === 0 && (
        <div className="text-center text-text-muted py-16">
          <Plus className="mx-auto mb-2" />
          Pick vessels from the dropdown to begin comparing.
        </div>
      )}

      {cards.length > 0 && (
        <div className={`grid gap-4 ${cards.length === 1 ? "grid-cols-1" : cards.length === 2 ? "grid-cols-1 md:grid-cols-2" : "grid-cols-1 md:grid-cols-3"}`}>
          {cards.map((c, i) =>
            c ? <Card key={c.vessel.id} card={c} onRemove={() => remove(c.vessel.id)} />
              : <Skeleton key={i} className="h-[400px]" />
          )}
        </div>
      )}
    </div>
  );
}

function Card({ card, onRemove }) {
  const v = card.vessel;
  const lastPos = card.positions?.[0];
  const lastRec = card.recs?.[0];
  const totalCo2 = (card.recs || []).reduce((s, r) => s + (r.co2_saved_kg || 0), 0);
  const optimal = (card.recs || []).filter((r) => r.status === "OPTIMAL").length;
  const overspeed = (card.recs || []).filter((r) => r.status === "OVERSPEED").length;
  const avgSog = useMemo(() => {
    const ps = (card.positions || []).map((p) => p.speed_over_ground).filter(Boolean);
    if (!ps.length) return null;
    return ps.reduce((a, b) => a + b, 0) / ps.length;
  }, [card.positions]);

  return (
    <div className="bg-bg-card border border-border rounded-xl p-4 relative">
      <button onClick={onRemove} title="Remove"
        className="absolute top-2 right-2 text-text-muted hover:text-accent-red">
        <X size={14} />
      </button>
      <div className="flex items-start gap-3 mb-3">
        <div className="text-3xl">{FLAG[v.flag] || "🏳️"}</div>
        <div>
          <div className="font-display font-semibold">{v.name}</div>
          <div className="font-mono text-[11px] text-text-muted">{v.imo} · {v.mmsi}</div>
        </div>
      </div>

      <Row k="Status" v={<StatusBadge status={v.status} />} />
      <Row k="Type"   v={<span className="capitalize">{v.vessel_type}</span>} />
      <Row k="Length" v={`${v.length_meters?.toFixed(1) ?? "—"} m`} />
      <Row k="Operator" v={v.operator || "—"} />
      <Row k="Last SOG" v={lastPos ? `${lastPos.speed_over_ground?.toFixed(1) ?? "—"} kn` : "—"} />
      <Row k="Avg SOG (last 20)" v={avgSog ? `${avgSog.toFixed(2)} kn` : "—"} />
      <Row k="Last seen" v={lastPos ? new Date(lastPos.recorded_at).toUTCString().slice(5, 22) : "—"} />

      <div className="mt-4 pt-3 border-t border-border">
        <div className="text-[11px] uppercase text-text-muted mb-2">JIT performance</div>
        <Row k="Total recommendations" v={(card.recs || []).length} />
        <Row k="Optimal arrivals" v={<span className="text-accent-green">{optimal}</span>} />
        <Row k="Overspeed events"  v={<span className="text-accent-red">{overspeed}</span>} />
        <Row k="Total CO₂ saved"   v={<span className="text-accent-green">{totalCo2.toFixed(1)} kg</span>} />
        <Row k="Latest status" v={lastRec ? <StatusBadge status={lastRec.status} /> : "—"} />
      </div>
    </div>
  );
}

function Row({ k, v }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-border/40 text-sm">
      <span className="text-text-muted">{k}</span>
      <span className="font-mono text-xs">{v}</span>
    </div>
  );
}
