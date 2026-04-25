import {
  Anchor, Bell, BookOpen, Building2, CalendarDays, Compass, Gauge, LayoutDashboard,
  Leaf, MapPin, Search, Settings, Ship,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import apiFetch, { getStoredUser } from "../api";

const STATIC_ITEMS = [
  { id: "nav-dashboard", title: "Go to Dashboard",    Icon: LayoutDashboard, kind: "nav", to: "/dashboard" },
  { id: "nav-owner",     title: "Go to Owner Panel",  Icon: Building2,       kind: "nav", to: "/owner",   roles: ["admin", "owner"] },
  { id: "nav-captain",   title: "Go to Captain Cockpit", Icon: Compass,      kind: "nav", to: "/captain", roles: ["admin", "captain"] },
  { id: "nav-map",       title: "Go to Live Map",     Icon: MapPin,          kind: "nav", to: "/map" },
  { id: "nav-fleet",     title: "Go to Fleet",        Icon: Ship,            kind: "nav", to: "/fleet" },
  { id: "nav-bookings",  title: "Go to Bookings",     Icon: CalendarDays,    kind: "nav", to: "/bookings" },
  { id: "nav-alerts",    title: "Go to Alerts",       Icon: Bell,            kind: "nav", to: "/alerts" },
  { id: "nav-jit",       title: "Go to JIT Tool",     Icon: Gauge,           kind: "nav", to: "/jit-tool" },
  { id: "nav-esg",       title: "Go to ESG Report",   Icon: Leaf,            kind: "nav", to: "/esg" },
  { id: "nav-compare",   title: "Compare vessels",    Icon: Ship,            kind: "nav", to: "/compare" },
  { id: "nav-settings",  title: "Settings",           Icon: Settings,        kind: "nav", to: "/settings" },
];

export default function CommandPalette({ open, onClose }) {
  const nav = useNavigate();
  const me = getStoredUser();
  const [q, setQ] = useState("");
  const [vessels, setVessels] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [activeIdx, setActiveIdx] = useState(0);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    setQ(""); setActiveIdx(0);
    setTimeout(() => inputRef.current?.focus(), 50);
    apiFetch("/vessels").then(setVessels).catch(() => {});
    apiFetch("/bookings").then(setBookings).catch(() => {});
  }, [open]);

  const role = me?.role || "viewer";

  const items = useMemo(() => {
    const navItems = STATIC_ITEMS.filter((it) => !it.roles || it.roles.includes(role));
    const vItems = vessels.map((v) => ({
      id: `v-${v.id}`,
      title: `Vessel · ${v.name}`,
      subtitle: `${v.imo || "—"} · ${v.flag || ""}`,
      Icon: Ship,
      kind: "vessel",
      to: `/fleet/${v.id}`,
    }));
    const bItems = bookings.map((b) => ({
      id: `b-${b.id}`,
      title: `Booking · ${b.booking_reference}`,
      subtitle: `${b.vessel?.name} → ${b.berth?.code} · ${b.status}`,
      Icon: CalendarDays,
      kind: "booking",
      to: "/bookings",
    }));
    const all = [...navItems, ...vItems, ...bItems];
    if (!q.trim()) return all.slice(0, 12);
    const needle = q.toLowerCase();
    return all
      .filter((it) =>
        it.title.toLowerCase().includes(needle) ||
        it.subtitle?.toLowerCase().includes(needle)
      )
      .slice(0, 30);
  }, [q, vessels, bookings, role]);

  function run(idx) {
    const it = items[idx];
    if (!it) return;
    onClose?.();
    nav(it.to);
  }

  function onKey(e) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((i) => Math.min(items.length - 1, i + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => Math.max(0, i - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      run(activeIdx);
    } else if (e.key === "Escape") {
      onClose?.();
    }
  }

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-24 px-4 bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-xl bg-bg-card border border-border rounded-xl shadow-2xl overflow-hidden animate-countUp" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2 px-4 h-12 border-b border-border">
          <Search size={16} className="text-text-muted" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => { setQ(e.target.value); setActiveIdx(0); }}
            onKeyDown={onKey}
            placeholder="Type to search vessels, bookings, pages…"
            className="flex-1 bg-transparent outline-none text-sm text-text-primary placeholder:text-text-muted/60"
          />
          <span className="text-[10px] text-text-muted font-mono">ESC</span>
        </div>
        <ul className="max-h-[55vh] overflow-auto">
          {items.length === 0 && (
            <li className="px-4 py-6 text-center text-text-muted text-sm">No matches.</li>
          )}
          {items.map((it, i) => {
            const Icon = it.Icon;
            const isActive = i === activeIdx;
            return (
              <li key={it.id}
                  onMouseEnter={() => setActiveIdx(i)}
                  onClick={() => run(i)}
                  className={`px-4 py-2 flex items-center gap-3 cursor-pointer ${
                    isActive ? "bg-accent-cyan/10 border-l-2 border-accent-cyan" : "border-l-2 border-transparent"
                  }`}>
                <Icon size={16} className={isActive ? "text-accent-cyan" : "text-text-muted"} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm truncate">{it.title}</div>
                  {it.subtitle && <div className="text-[11px] text-text-muted truncate">{it.subtitle}</div>}
                </div>
                <span className="text-[10px] font-mono text-text-muted uppercase">{it.kind}</span>
              </li>
            );
          })}
        </ul>
        <div className="px-4 py-2 border-t border-border text-[10px] font-mono text-text-muted flex justify-between">
          <span>↑↓ navigate · ↵ open</span>
          <span><Anchor className="inline" size={10} /> AZMarine</span>
        </div>
      </div>
    </div>
  );
}
