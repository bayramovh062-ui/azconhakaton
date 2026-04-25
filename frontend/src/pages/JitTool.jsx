import { Calculator, Loader2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import apiFetch from "../api";
import PageHeader from "../components/PageHeader";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../components/Toast";

const PORT = { lat: 40.35, lon: 49.87 };
const FUEL_RATE = 0.12;
const CO2_PER_L = 2.68;

function haversineNm(la1, lo1, la2, lo2) {
  const R = 3440.065;
  const toRad = (x) => (x * Math.PI) / 180;
  const dLa = toRad(la2 - la1), dLo = toRad(lo2 - lo1);
  const a = Math.sin(dLa / 2) ** 2 +
    Math.cos(toRad(la1)) * Math.cos(toRad(la2)) * Math.sin(dLo / 2) ** 2;
  return R * 2 * Math.asin(Math.min(1, Math.sqrt(a)));
}

export default function JitTool() {
  const toast = useToast();
  const [vessels, setVessels] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [vesselId, setVesselId] = useState("");
  const [bookingId, setBookingId] = useState("");
  const [lat, setLat] = useState(40.10);
  const [lon, setLon] = useState(49.40);
  const [speed, setSpeed] = useState(11.5);
  const [maxSpeed, setMaxSpeed] = useState(14.0);
  const [eta, setEta] = useState(() => {
    const d = new Date(Date.now() + 8 * 3600 * 1000);
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  });
  const [busy, setBusy] = useState(false);
  const [persisted, setPersisted] = useState(null);

  useEffect(() => {
    apiFetch("/vessels").then(setVessels).catch(() => {});
    apiFetch("/bookings").then(setBookings).catch(() => {});
  }, []);

  // Local mirror of the backend engine — instant feedback while you type.
  const local = useMemo(() => {
    const distance = haversineNm(lat, lon, PORT.lat, PORT.lon);
    const etaDate = new Date(eta);
    const tHours = (etaDate.getTime() - Date.now()) / 3600000;
    if (tHours <= 0) {
      return { distance, tHours, recommended: speed, status: "BERTH_READY", fuel: 0, co2: 0 };
    }
    let rec = distance / tHours;
    rec = Math.max(4, Math.min(maxSpeed, rec));
    const delta = speed - rec;
    let status = "OPTIMAL";
    if (delta > 1) status = "OVERSPEED";
    else if (delta < -1) status = "UNDERSPEED";
    const excess = Math.max(0, speed - rec);
    const fuel = excess * distance * FUEL_RATE;
    return { distance, tHours, recommended: rec, status, fuel, co2: fuel * CO2_PER_L };
  }, [lat, lon, speed, eta, maxSpeed]);

  async function persist() {
    if (!vesselId) return toast.error("Pick a vessel from the list (the engine reads its latest AIS position)");
    setBusy(true); setPersisted(null);
    try {
      const res = await apiFetch("/jit/calculate", {
        method: "POST",
        body: JSON.stringify({
          vessel_id: vesselId,
          booking_id: bookingId || null,
        }),
      });
      setPersisted(res);
      toast.success("Recommendation saved to history");
    } catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  }

  return (
    <div className="p-6 max-w-[1400px] mx-auto">
      <PageHeader
        title="JIT Calculator"
        subtitle="Manually evaluate optimal speed for any inbound vessel — preview locally or persist via the engine"
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-bg-card border border-border rounded-xl p-5 space-y-4">
          <h3 className="font-display font-semibold text-accent-cyan flex items-center gap-2">
            <Calculator size={18} /> Inputs
          </h3>

          <div className="grid grid-cols-2 gap-3">
            <Input label="Vessel lat (°)" type="number" step="0.0001" value={lat} onChange={setLat} />
            <Input label="Vessel lon (°)" type="number" step="0.0001" value={lon} onChange={setLon} />
            <Input label="Current SOG (kn)" type="number" step="0.1" value={speed} onChange={setSpeed} />
            <Input label="Max speed (kn)" type="number" step="0.1" value={maxSpeed} onChange={setMaxSpeed} />
          </div>
          <Input label="Scheduled arrival (UTC)" type="datetime-local" value={eta} onChange={setEta} />

          <div className="border-t border-border pt-4 space-y-3">
            <div className="text-[11px] uppercase tracking-wider text-text-muted">Persist via backend engine</div>
            <Select label="Vessel" value={vesselId} onChange={setVesselId}
              options={[{ value: "", label: "— pick to enable persist —" },
                ...vessels.map((v) => ({ value: v.id, label: `${v.name} • ${v.flag}` }))]} />
            <Select label="Booking (optional)" value={bookingId} onChange={setBookingId}
              options={[{ value: "", label: "(no booking — uses +6h default)" },
                ...bookings.map((b) => ({ value: b.id, label: `${b.booking_reference} • ${b.vessel?.name}` }))]} />
            <button onClick={persist} disabled={busy}
              className="w-full h-10 rounded-md bg-accent-cyan text-bg-primary font-semibold hover:shadow-glow flex items-center justify-center gap-2 disabled:opacity-50">
              {busy && <Loader2 size={14} className="animate-spin" />} Persist recommendation
            </button>
          </div>
        </div>

        <div className="bg-bg-card border border-border rounded-xl p-5 space-y-4">
          <h3 className="font-display font-semibold text-accent-cyan">Live preview</h3>
          <div className="grid grid-cols-2 gap-3">
            <Stat label="Distance" value={`${local.distance.toFixed(2)} nm`} />
            <Stat label="Time available" value={`${local.tHours.toFixed(2)} h`} />
            <Stat label="Recommended SOG" value={`${local.recommended.toFixed(2)} kn`} accent="cyan" />
            <Stat label="Current SOG" value={`${Number(speed).toFixed(2)} kn`} />
            <Stat label="Δ Speed" value={`${(speed - local.recommended).toFixed(2)} kn`} />
            <div className="bg-bg-secondary border border-border rounded p-3">
              <div className="text-[11px] uppercase text-text-muted">Status</div>
              <div className="mt-1"><StatusBadge status={local.status} /></div>
            </div>
            <Stat label="Fuel saved" value={`${local.fuel.toFixed(2)} L`} accent="green" />
            <Stat label="CO₂ avoided" value={`${local.co2.toFixed(2)} kg`} accent="green" />
          </div>

          {persisted && (
            <div className="border-t border-border pt-3 text-xs space-y-1">
              <div className="text-text-muted uppercase">Persisted record</div>
              <div className="font-mono">id {persisted.id}</div>
              <div className="font-mono">status {persisted.status} • rec {persisted.recommended_speed?.toFixed(2)} kn</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, accent = "" }) {
  const color = accent === "cyan" ? "text-accent-cyan" :
                accent === "green" ? "text-accent-green" : "text-text-primary";
  return (
    <div className="bg-bg-secondary border border-border rounded p-3">
      <div className="text-[11px] uppercase text-text-muted">{label}</div>
      <div className={`mt-1 font-mono text-lg ${color}`}>{value}</div>
    </div>
  );
}

function Input({ label, value, onChange, type = "text", step }) {
  return (
    <label className="block">
      <span className="text-[11px] uppercase tracking-wider text-text-muted">{label}</span>
      <input type={type} value={value} step={step}
        onChange={(e) => onChange(type === "number" ? Number(e.target.value) : e.target.value)}
        className="mt-1 w-full h-9 px-3 rounded-md bg-bg-secondary border border-border outline-none focus:border-accent-cyan/60" />
    </label>
  );
}

function Select({ label, value, onChange, options }) {
  return (
    <label className="block">
      <span className="text-[11px] uppercase tracking-wider text-text-muted">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full h-9 px-2 rounded-md bg-bg-secondary border border-border outline-none focus:border-accent-cyan/60">
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  );
}
