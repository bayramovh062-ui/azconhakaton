import {
  Anchor,
  Bell,
  Building2,
  CalendarDays,
  ChevronLeft,
  Compass,
  Gauge,
  LayoutDashboard,
  LogOut,
  MapPin,
  Leaf,
  Ship,
} from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";
import { clearAuth, getStoredUser } from "../api";
import AlertBell from "./AlertBell";

const NAV_BASE = [
  { to: "/dashboard", label: "Dashboard", Icon: LayoutDashboard, roles: ["admin", "operator", "analyst", "viewer"] },
  { to: "/owner",     label: "Owner Panel", Icon: Building2,    roles: ["admin", "owner"] },
  { to: "/captain",   label: "Captain Cockpit", Icon: Compass,  roles: ["admin", "captain"] },
  { to: "/map",       label: "Live Map",  Icon: MapPin,         roles: ["admin", "operator", "analyst", "viewer", "owner", "captain"] },
  { to: "/fleet",     label: "Fleet",     Icon: Ship,           roles: ["admin", "operator", "analyst", "viewer", "owner"] },
  { to: "/bookings",  label: "Bookings",  Icon: CalendarDays,   roles: ["admin", "operator", "analyst", "viewer", "owner", "captain"] },
  { to: "/jit-tool",  label: "JIT Tool",  Icon: Gauge,          roles: ["admin", "operator", "analyst", "captain"] },
  { to: "/alerts",    label: "Alerts",    Icon: Bell, badge: true, roles: ["admin", "operator", "analyst", "owner", "captain"] },
  { to: "/esg",       label: "ESG Report", Icon: Leaf,          roles: ["admin", "operator", "analyst", "viewer", "owner"] },
  { to: "/compare",   label: "Compare",   Icon: Ship,           roles: ["admin", "operator", "analyst", "owner"] },
];

function navFor(role) {
  return NAV_BASE.filter((n) => n.roles.includes(role));
}

export default function Sidebar({ collapsed, onToggle }) {
  const nav = useNavigate();
  const user = getStoredUser();
  const NAV = navFor(user?.role || "viewer");

  function logout() {
    clearAuth();
    nav("/login", { replace: true });
  }

  return (
    <aside
      className={`hidden md:flex flex-col bg-bg-secondary border-r border-border transition-all duration-200 ${
        collapsed ? "w-16" : "w-60"
      }`}
    >
      <div className="h-16 flex items-center gap-2 px-4 border-b border-border">
        <Anchor className="text-accent-cyan shrink-0" size={22} />
        {!collapsed && (
          <span className="font-display font-bold tracking-wider text-text-primary">
            <span className="text-accent-cyan">AZ</span>MARINE
          </span>
        )}
        <button
          onClick={onToggle}
          className={`ml-auto text-text-muted hover:text-text-primary ${collapsed ? "rotate-180" : ""}`}
          title="Toggle sidebar"
        >
          <ChevronLeft size={18} />
        </button>
      </div>

      {!collapsed && user && (
        <div className="px-4 py-2 border-b border-border">
          <div className="text-[10px] uppercase text-text-muted tracking-wider">Signed in as</div>
          <div className="text-xs font-display truncate">{user.full_name || user.email}</div>
          <div className="text-[10px] font-mono uppercase mt-0.5">
            <span className="text-accent-cyan">{user.role}</span>
            {user.operator_company && <span className="text-text-muted"> • {user.operator_company}</span>}
            {user.vessel_name && <span className="text-text-muted"> • {user.vessel_name}</span>}
          </div>
        </div>
      )}

      <nav className="flex-1 py-4 px-2 space-y-1">
        {NAV.map(({ to, label, Icon, badge }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-md text-sm transition relative ${
                isActive
                  ? "bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/30"
                  : "text-text-muted hover:text-text-primary hover:bg-bg-card"
              }`
            }
          >
            <Icon size={18} className="shrink-0" />
            {!collapsed && <span className="flex-1">{label}</span>}
            {badge && !collapsed && <AlertBell />}
          </NavLink>
        ))}
      </nav>

      <button
        onClick={logout}
        className="m-2 flex items-center gap-3 px-3 py-2 rounded-md text-sm text-text-muted hover:text-accent-red hover:bg-bg-card"
      >
        <LogOut size={18} />
        {!collapsed && <span>Logout</span>}
      </button>
    </aside>
  );
}

export function MobileTabBar() {
  const user = getStoredUser();
  const NAV = navFor(user?.role || "viewer");
  return (
    <nav className={`md:hidden fixed bottom-0 inset-x-0 z-30 grid bg-bg-secondary/95 backdrop-blur border-t border-border`}
         style={{ gridTemplateColumns: `repeat(${NAV.length}, minmax(0, 1fr))` }}>
      {NAV.map(({ to, label, Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            `flex flex-col items-center justify-center py-2 text-[10px] ${
              isActive ? "text-accent-cyan" : "text-text-muted"
            }`
          }
        >
          <Icon size={18} />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
