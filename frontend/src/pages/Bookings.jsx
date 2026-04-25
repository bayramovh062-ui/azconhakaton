import { Plus } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import apiFetch from "../api";
import BerthGantt from "../components/BerthGantt";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";
import Skeleton from "../components/Skeleton";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../components/Toast";

const TABS = [
  { key: "ALL",         match: () => true },
  { key: "SCHEDULED",   match: (s) => s === "scheduled" || s === "confirmed" },
  { key: "IN_PORT",     match: (s) => s === "in_progress" },
  { key: "DEPARTED",    match: (s) => s === "completed" },
  { key: "CANCELLED",   match: (s) => s === "cancelled" },
];

export default function Bookings() {
  const toast = useToast();
  const [rows, setRows] = useState(null);
  const [tab, setTab] = useState("ALL");
  const [openCreate, setOpenCreate] = useState(false);
  const [editing, setEditing] = useState(null);

  async function load() {
    setRows(null);
    try { setRows(await apiFetch("/bookings")); }
    catch (e) { toast.error(e.message); setRows([]); }
  }
  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    if (!rows) return null;
    const t = TABS.find((x) => x.key === tab);
    return rows.filter((r) => t.match(r.status));
  }, [rows, tab]);

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      <PageHeader
        title="Port Bookings"
        subtitle="Vessel arrivals scheduled at Baku Int'l Sea Trade Port"
        actions={
          <button onClick={() => setOpenCreate(true)}
            className="h-10 px-4 rounded-md bg-accent-cyan text-bg-primary font-semibold hover:shadow-glow flex items-center gap-2">
            <Plus size={16} /> New Booking
          </button>
        }
      />

      <div className="flex gap-2 mb-4 flex-wrap">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-3 h-8 rounded-md text-xs font-mono uppercase tracking-wider border transition ${
              tab === t.key
                ? "bg-accent-cyan/15 text-accent-cyan border-accent-cyan/40"
                : "bg-bg-card text-text-muted border-border hover:text-text-primary"
            }`}>
            {t.key}
          </button>
        ))}
      </div>

      <div className="mb-4">
        <BerthGantt bookings={rows || []} days={14} />
      </div>

      <div className="bg-bg-card border border-border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-bg-secondary text-text-muted text-[11px] uppercase tracking-wider">
            <tr>
              {["Vessel","Berth","Cargo","Scheduled","Actual","Status",""].map((h) => (
                <th key={h} className="text-left px-4 py-3 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered === null && [...Array(4)].map((_, i) => (
              <tr key={i}><td colSpan={7} className="px-4 py-2"><Skeleton className="h-8" /></td></tr>
            ))}
            {filtered?.map((b) => (
              <tr key={b.id} className="border-t border-border hover:bg-bg-secondary/40">
                <td className="px-4 py-3 font-display">{b.vessel?.name || "—"}</td>
                <td className="px-4 py-3 font-mono text-xs">{b.berth?.code} <span className="text-text-muted">{b.berth?.name}</span></td>
                <td className="px-4 py-3 text-xs text-text-muted truncate max-w-[220px]">{b.cargo_type || "—"}</td>
                <td className="px-4 py-3 font-mono text-xs">{fmt(b.scheduled_arrival)}</td>
                <td className="px-4 py-3 font-mono text-xs">{fmt(b.actual_arrival) || <span className="text-text-muted/60">pending</span>}</td>
                <td className="px-4 py-3"><StatusBadge status={b.status} /></td>
                <td className="px-4 py-3">
                  <button onClick={() => setEditing(b)} className="text-accent-cyan hover:underline text-xs">
                    Update
                  </button>
                </td>
              </tr>
            ))}
            {filtered?.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-text-muted">No bookings in this filter.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <CreateBookingModal open={openCreate}
        onClose={() => setOpenCreate(false)}
        onCreated={() => { setOpenCreate(false); load(); toast.success("Booking created"); }} />

      <UpdateBookingModal booking={editing}
        onClose={() => setEditing(null)}
        onSaved={() => { setEditing(null); load(); toast.success("Booking updated"); }} />
    </div>
  );
}

function fmt(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  return d.toUTCString().slice(5, 22);
}

function CreateBookingModal({ open, onClose, onCreated }) {
  const toast = useToast();
  const [vessels, setVessels] = useState([]);
  const [berths, setBerths] = useState([]);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    vessel_id: "", berth_id: "",
    scheduled_arrival: "", scheduled_departure: "",
    cargo_type: "",
  });

  useEffect(() => {
    if (!open) return;
    apiFetch("/vessels").then(setVessels);
    // berths come from existing bookings (read-only convenience)
    apiFetch("/bookings").then((rows) => {
      const seen = new Map();
      rows.forEach((r) => r.berth && seen.set(r.berth.id, r.berth));
      setBerths([...seen.values()]);
    });
  }, [open]);

  function set(k, v) { setForm((f) => ({ ...f, [k]: v })); }

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    try {
      await apiFetch("/bookings", {
        method: "POST",
        body: JSON.stringify({
          vessel_id: form.vessel_id,
          berth_id: form.berth_id,
          scheduled_arrival: new Date(form.scheduled_arrival).toISOString(),
          scheduled_departure: form.scheduled_departure ? new Date(form.scheduled_departure).toISOString() : null,
          cargo_type: form.cargo_type || null,
        }),
      });
      onCreated();
    } catch (err) { toast.error(err.message); }
    finally { setBusy(false); }
  }

  return (
    <Modal open={open} onClose={onClose} title="New Booking">
      <form onSubmit={submit} className="space-y-3">
        <Select label="Vessel" value={form.vessel_id} onChange={(v) => set("vessel_id", v)}
          options={[{ value: "", label: "— Select —" }, ...vessels.map((v) => ({ value: v.id, label: v.name }))]} required />
        <Select label="Berth" value={form.berth_id} onChange={(v) => set("berth_id", v)}
          options={[{ value: "", label: "— Select —" }, ...berths.map((b) => ({ value: b.id, label: `${b.code} — ${b.name}` }))]} required />
        <div className="grid grid-cols-2 gap-3">
          <Input label="Scheduled arrival" type="datetime-local" value={form.scheduled_arrival} onChange={(v) => set("scheduled_arrival", v)} required />
          <Input label="Scheduled departure" type="datetime-local" value={form.scheduled_departure} onChange={(v) => set("scheduled_departure", v)} />
        </div>
        <Input label="Cargo description" value={form.cargo_type} onChange={(v) => set("cargo_type", v)} />
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="px-4 h-9 rounded-md border border-border text-text-muted">Cancel</button>
          <button type="submit" disabled={busy} className="px-4 h-9 rounded-md bg-accent-cyan text-bg-primary font-semibold disabled:opacity-50">
            {busy ? "Saving…" : "Create"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function UpdateBookingModal({ booking, onClose, onSaved }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ status: "", actual_arrival: "", actual_departure: "" });

  useEffect(() => {
    if (!booking) return;
    setForm({
      status: booking.status,
      actual_arrival: booking.actual_arrival ? toLocal(booking.actual_arrival) : "",
      actual_departure: booking.actual_departure ? toLocal(booking.actual_departure) : "",
    });
  }, [booking?.id]);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    try {
      await apiFetch(`/bookings/${booking.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          status: form.status,
          actual_arrival: form.actual_arrival ? new Date(form.actual_arrival).toISOString() : null,
          actual_departure: form.actual_departure ? new Date(form.actual_departure).toISOString() : null,
        }),
      });
      onSaved();
    } catch (err) { toast.error(err.message); }
    finally { setBusy(false); }
  }

  return (
    <Modal open={!!booking} onClose={onClose} title="Update Booking">
      {booking && (
        <form onSubmit={submit} className="space-y-3">
          <Select label="Status" value={form.status} onChange={(v) => setForm((f) => ({ ...f, status: v }))}
            options={["scheduled","confirmed","in_progress","completed","cancelled","delayed"].map((o) => ({ value: o, label: o }))} />
          <div className="grid grid-cols-2 gap-3">
            <Input label="Actual arrival" type="datetime-local" value={form.actual_arrival} onChange={(v) => setForm((f) => ({ ...f, actual_arrival: v }))} />
            <Input label="Actual departure" type="datetime-local" value={form.actual_departure} onChange={(v) => setForm((f) => ({ ...f, actual_departure: v }))} />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="px-4 h-9 rounded-md border border-border text-text-muted">Cancel</button>
            <button type="submit" disabled={busy} className="px-4 h-9 rounded-md bg-accent-cyan text-bg-primary font-semibold disabled:opacity-50">
              {busy ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}

function toLocal(iso) {
  // Convert ISO → datetime-local string
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function Input({ label, type = "text", value, onChange, required }) {
  return (
    <label className="block">
      <span className="text-[11px] uppercase tracking-wider text-text-muted">{label}</span>
      <input type={type} value={value} required={required}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full h-9 px-3 rounded-md bg-bg-secondary border border-border outline-none focus:border-accent-cyan/60" />
    </label>
  );
}

function Select({ label, value, onChange, options, required }) {
  return (
    <label className="block">
      <span className="text-[11px] uppercase tracking-wider text-text-muted">{label}</span>
      <select value={value} required={required}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full h-9 px-2 rounded-md bg-bg-secondary border border-border outline-none focus:border-accent-cyan/60">
        {options.map((o) => (
          typeof o === "string"
            ? <option key={o} value={o}>{o}</option>
            : <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </label>
  );
}
