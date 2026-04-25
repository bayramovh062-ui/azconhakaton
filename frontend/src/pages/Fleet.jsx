import { formatDistanceToNow } from "date-fns";
import { ArrowDown, ArrowUp, Download, Eye, Plus, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import apiFetch from "../api";
import Drawer from "../components/Drawer";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import Skeleton from "../components/Skeleton";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../components/Toast";

const FLAG_EMOJI = {
  Azerbaijan: "🇦🇿",
  Russia: "🇷🇺",
  Turkey: "🇹🇷",
  Iran: "🇮🇷",
  Kazakhstan: "🇰🇿",
  Turkmenistan: "🇹🇲",
  Simulated: "🛰️",
};

export default function Fleet() {
  const toast = useToast();
  const nav = useNavigate();
  const [vessels, setVessels] = useState(null);
  const [openCreate, setOpenCreate] = useState(false);
  const [drawerVessel, setDrawerVessel] = useState(null);
  const [query, setQuery] = useState("");
  const [filterType, setFilterType] = useState("ALL");
  const [filterFlag, setFilterFlag] = useState("ALL");
  const [sort, setSort] = useState({ key: "name", dir: "asc" });

  async function load() {
    setVessels(null);
    try {
      setVessels(await apiFetch("/vessels"));
    } catch (e) {
      toast.error(e.message);
      setVessels([]);
    }
  }

  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    if (!vessels) return null;
    const q = query.trim().toLowerCase();
    let rows = vessels.filter((v) => {
      if (filterType !== "ALL" && v.vessel_type !== filterType) return false;
      if (filterFlag !== "ALL" && v.flag !== filterFlag) return false;
      if (!q) return true;
      return (
        v.name?.toLowerCase().includes(q) ||
        v.imo?.toLowerCase().includes(q) ||
        v.mmsi?.toLowerCase().includes(q) ||
        v.operator?.toLowerCase().includes(q)
      );
    });
    rows = [...rows].sort((a, b) => {
      const av = a[sort.key] ?? "";
      const bv = b[sort.key] ?? "";
      const cmp = (typeof av === "number" ? av - bv : String(av).localeCompare(String(bv)));
      return sort.dir === "asc" ? cmp : -cmp;
    });
    return rows;
  }, [vessels, query, filterType, filterFlag, sort]);

  const types = useMemo(() => [...new Set((vessels || []).map((v) => v.vessel_type))].sort(), [vessels]);
  const flags = useMemo(() => [...new Set((vessels || []).map((v) => v.flag).filter(Boolean))].sort(), [vessels]);

  function toggleSort(key) {
    setSort((s) => s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: "asc" });
  }

  function exportCsv() {
    if (!filtered?.length) return;
    const headers = ["id","imo","mmsi","name","flag","vessel_type","length_meters","operator","status","updated_at"];
    const lines = [headers.join(",")];
    filtered.forEach((v) => {
      lines.push(headers.map((h) => csv(v[h])).join(","));
    });
    const blob = new Blob([lines.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `nexusaz-fleet-${Date.now()}.csv`; a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      <PageHeader
        title="Fleet Management"
        subtitle="All vessels visible to NexusAZ telemetry layer"
        actions={
          <>
            <button onClick={exportCsv} disabled={!filtered?.length}
              className="h-10 px-4 rounded-md border border-border text-text-muted hover:text-text-primary hover:border-accent-cyan/40 flex items-center gap-2 disabled:opacity-40">
              <Download size={16} /> CSV
            </button>
            <button
              onClick={() => setOpenCreate(true)}
              className="h-10 px-4 rounded-md bg-accent-cyan text-bg-primary font-semibold hover:shadow-glow flex items-center gap-2"
            >
              <Plus size={16} /> Add Vessel
            </button>
          </>
        }
      />

      <div className="flex flex-wrap gap-2 mb-3">
        <div className="flex items-center gap-2 bg-bg-card border border-border rounded-md px-3 h-9 flex-1 min-w-[220px] focus-within:border-accent-cyan/60">
          <Search size={14} className="text-text-muted" />
          <input value={query} onChange={(e) => setQuery(e.target.value)}
            placeholder="Search name, IMO, MMSI, operator…"
            className="flex-1 bg-transparent outline-none text-sm placeholder:text-text-muted/60" />
          <span className="text-[11px] text-text-muted font-mono">{filtered?.length ?? 0}</span>
        </div>
        <select value={filterType} onChange={(e) => setFilterType(e.target.value)}
          className="h-9 px-2 bg-bg-card border border-border rounded-md text-sm">
          <option value="ALL">All types</option>
          {types.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <select value={filterFlag} onChange={(e) => setFilterFlag(e.target.value)}
          className="h-9 px-2 bg-bg-card border border-border rounded-md text-sm">
          <option value="ALL">All flags</option>
          {flags.map((f) => <option key={f} value={f}>{f}</option>)}
        </select>
      </div>

      <div className="bg-bg-card border border-border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-bg-secondary text-text-muted text-[11px] uppercase tracking-wider">
            <tr>
              <SortableTh label="MMSI" k="mmsi" sort={sort} onClick={toggleSort} />
              <SortableTh label="Name" k="name" sort={sort} onClick={toggleSort} />
              <SortableTh label="Flag" k="flag" sort={sort} onClick={toggleSort} />
              <SortableTh label="Type" k="vessel_type" sort={sort} onClick={toggleSort} />
              <SortableTh label="Length" k="length_meters" sort={sort} onClick={toggleSort} />
              <SortableTh label="Status" k="status" sort={sort} onClick={toggleSort} />
              <SortableTh label="Updated" k="updated_at" sort={sort} onClick={toggleSort} />
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filtered === null && [...Array(5)].map((_, i) => (
              <tr key={i}><td colSpan={8} className="px-4 py-2"><Skeleton className="h-8" /></td></tr>
            ))}
            {filtered?.map((v) => (
              <tr key={v.id} onClick={() => nav(`/fleet/${v.id}`)}
                  className="border-t border-border hover:bg-bg-secondary/40 cursor-pointer">
                <td className="px-4 py-3 font-mono text-xs">{v.mmsi || "—"}</td>
                <td className="px-4 py-3 font-display">{v.name}</td>
                <td className="px-4 py-3">{FLAG_EMOJI[v.flag] || "🏳️"} <span className="text-text-muted text-xs ml-1">{v.flag}</span></td>
                <td className="px-4 py-3 capitalize">{v.vessel_type}</td>
                <td className="px-4 py-3 font-mono text-xs">{v.length_meters ? `${v.length_meters.toFixed(1)} m` : "—"}</td>
                <td className="px-4 py-3"><StatusBadge status={v.status} /></td>
                <td className="px-4 py-3 text-xs text-text-muted">
                  {v.updated_at ? formatDistanceToNow(new Date(v.updated_at), { addSuffix: true }) : "—"}
                </td>
                <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                  <button
                    onClick={() => setDrawerVessel(v)}
                    className="text-accent-cyan hover:underline flex items-center gap-1 text-xs"
                  >
                    <Eye size={14} /> Quick view
                  </button>
                </td>
              </tr>
            ))}
            {filtered?.length === 0 && (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-text-muted">No vessels match this filter.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <CreateVesselModal
        open={openCreate}
        onClose={() => setOpenCreate(false)}
        onCreated={() => { setOpenCreate(false); load(); toast.success("Vessel created"); }}
      />

      <VesselDrawer
        vessel={drawerVessel}
        onClose={() => setDrawerVessel(null)}
        onViewMap={() => nav("/map")}
      />
    </div>
  );
}

function CreateVesselModal({ open, onClose, onCreated }) {
  const toast = useToast();
  const [form, setForm] = useState({
    name: "", mmsi: "", imo: "", flag: "Azerbaijan",
    vessel_type: "cargo", length_meters: 150,
  });
  const [busy, setBusy] = useState(false);

  function set(k, v) { setForm((f) => ({ ...f, [k]: v })); }

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    try {
      await apiFetch("/vessels", {
        method: "POST",
        body: JSON.stringify({
          name: form.name,
          mmsi: form.mmsi || null,
          imo: form.imo || null,
          flag: form.flag,
          vessel_type: form.vessel_type,
          length_meters: Number(form.length_meters) || null,
          max_speed_knots: 14.0,
        }),
      });
      onCreated();
    } catch (err) {
      toast.error(err.message);
    } finally { setBusy(false); }
  }

  return (
    <Modal open={open} onClose={onClose} title="Add Vessel">
      <form onSubmit={submit} className="space-y-3">
        <Input label="Name" value={form.name} onChange={(v) => set("name", v)} required />
        <div className="grid grid-cols-2 gap-3">
          <Input label="IMO" value={form.imo} onChange={(v) => set("imo", v)} />
          <Input label="MMSI" value={form.mmsi} onChange={(v) => set("mmsi", v)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Select label="Flag" value={form.flag} onChange={(v) => set("flag", v)}
            options={["Azerbaijan", "Russia", "Turkey", "Iran", "Kazakhstan", "Turkmenistan"]} />
          <Select label="Type" value={form.vessel_type} onChange={(v) => set("vessel_type", v)}
            options={["cargo","tanker","container","bulk","ro-ro","passenger","tug","fishing","other"]} />
        </div>
        <Input label="Length (m)" type="number" value={form.length_meters} onChange={(v) => set("length_meters", v)} />
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="px-4 h-9 rounded-md border border-border text-text-muted">Cancel</button>
          <button type="submit" disabled={busy}
            className="px-4 h-9 rounded-md bg-accent-cyan text-bg-primary font-semibold disabled:opacity-50">
            {busy ? "Saving…" : "Create"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function VesselDrawer({ vessel, onClose, onViewMap }) {
  const [positions, setPositions] = useState([]);
  const [recs, setRecs] = useState([]);

  useEffect(() => {
    if (!vessel) return;
    apiFetch(`/vessels/${vessel.id}/positions?limit=10`).then(setPositions).catch(() => setPositions([]));
    apiFetch(`/jit/recommendations/${vessel.id}`).then(setRecs).catch(() => setRecs([]));
  }, [vessel?.id]);

  return (
    <Drawer open={!!vessel} title={vessel?.name || ""} onClose={onClose}>
      {vessel && (
        <div className="space-y-5">
          <DetailGrid v={vessel} />

          <Section title="Latest JIT recommendation">
            {recs.length === 0 ? (
              <div className="text-text-muted text-sm">No recommendations yet.</div>
            ) : (
              <div className="bg-bg-secondary border border-border rounded-md p-3 text-sm space-y-1">
                <div className="flex items-center justify-between"><span>Status</span><StatusBadge status={recs[0].status} /></div>
                <div className="flex items-center justify-between font-mono text-xs"><span>Recommended</span><span>{recs[0].recommended_speed?.toFixed(1)} kn</span></div>
                <div className="flex items-center justify-between font-mono text-xs"><span>Distance</span><span>{recs[0].distance_nm?.toFixed(1)} nm</span></div>
                <div className="flex items-center justify-between font-mono text-xs"><span>Fuel saved</span><span>{(recs[0].fuel_saved_liters ?? 0).toFixed(2)} L</span></div>
              </div>
            )}
          </Section>

          <Section title="Recent positions (last 10)">
            <div className="text-xs font-mono">
              {positions.length === 0 ? <div className="text-text-muted">No positions logged.</div> :
                <table className="w-full">
                  <thead className="text-text-muted">
                    <tr><th className="text-left py-1">Time</th><th className="text-left">Lat</th><th className="text-left">Lon</th><th className="text-right">SOG</th></tr>
                  </thead>
                  <tbody>
                    {positions.map((p) => (
                      <tr key={p.id} className="border-t border-border/50">
                        <td className="py-1">{new Date(p.recorded_at).toUTCString().slice(17, 22)}</td>
                        <td>{p.lat.toFixed(3)}</td>
                        <td>{p.lon.toFixed(3)}</td>
                        <td className="text-right">{p.speed_over_ground?.toFixed(1) ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              }
            </div>
          </Section>

          <button onClick={onViewMap}
            className="w-full h-10 rounded-md bg-accent-cyan text-bg-primary font-semibold hover:shadow-glow">
            View on Map
          </button>
        </div>
      )}
    </Drawer>
  );
}

function DetailGrid({ v }) {
  const Row = ({ k, val }) => (
    <div className="flex justify-between py-1.5 border-b border-border/50 text-sm">
      <span className="text-text-muted">{k}</span><span className="font-mono">{val ?? "—"}</span>
    </div>
  );
  return (
    <Section title="Details">
      <Row k="IMO" val={v.imo} />
      <Row k="MMSI" val={v.mmsi} />
      <Row k="Flag" val={v.flag} />
      <Row k="Type" val={v.vessel_type} />
      <Row k="Length" val={v.length_meters ? `${v.length_meters.toFixed(1)} m` : null} />
      <Row k="Operator" val={v.operator} />
      <Row k="Status" val={v.status} />
    </Section>
  );
}

function Section({ title, children }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wider text-text-muted mb-2">{title}</div>
      {children}
    </div>
  );
}

function Input({ label, value, onChange, type = "text", required }) {
  return (
    <label className="block">
      <span className="text-[11px] uppercase tracking-wider text-text-muted">{label}</span>
      <input
        type={type} value={value} required={required}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full h-9 px-3 rounded-md bg-bg-secondary border border-border outline-none focus:border-accent-cyan/60"
      />
    </label>
  );
}

function SortableTh({ label, k, sort, onClick }) {
  const active = sort.key === k;
  return (
    <th onClick={() => onClick(k)} className="text-left px-4 py-3 font-medium cursor-pointer select-none">
      <span className={`inline-flex items-center gap-1 ${active ? "text-accent-cyan" : ""}`}>
        {label}
        {active && (sort.dir === "asc" ? <ArrowUp size={11} /> : <ArrowDown size={11} />)}
      </span>
    </th>
  );
}

function csv(v) {
  if (v == null) return "";
  const s = String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function Select({ label, value, onChange, options }) {
  return (
    <label className="block">
      <span className="text-[11px] uppercase tracking-wider text-text-muted">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full h-9 px-2 rounded-md bg-bg-secondary border border-border outline-none focus:border-accent-cyan/60">
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </label>
  );
}
