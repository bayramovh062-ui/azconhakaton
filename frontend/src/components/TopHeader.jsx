import { Bell, Command, LogOut, Search, Settings, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import apiFetch, { clearAuth, getStoredUser } from "../api";
import LiveClock from "./LiveClock";

/**
 * Persistent top header with:
 *  - global search shortcut button (Cmd-K)
 *  - notification bell + popover
 *  - user menu (settings, logout)
 *  - live UTC clock
 */
export default function TopHeader({ onOpenPalette }) {
  const nav = useNavigate();
  const me = getStoredUser();
  const [notif, setNotif] = useState({ open: false, items: null, counts: null });
  const [menu, setMenu] = useState(false);
  const popRef = useRef(null);
  const menuRef = useRef(null);

  // Poll counts every 30s, items only when popover opens
  useEffect(() => {
    let mounted = true;
    async function loadCounts() {
      try {
        const c = await apiFetch("/alerts/counts");
        if (mounted) setNotif((s) => ({ ...s, counts: c }));
      } catch {/*silent*/}
    }
    loadCounts();
    const t = setInterval(loadCounts, 30000);
    return () => { mounted = false; clearInterval(t); };
  }, []);

  useEffect(() => {
    function close(e) {
      if (popRef.current && !popRef.current.contains(e.target)) {
        setNotif((s) => ({ ...s, open: false }));
      }
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenu(false);
      }
    }
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  async function openNotif() {
    setNotif((s) => ({ ...s, open: !s.open }));
    if (!notif.items) {
      try {
        const data = await apiFetch("/alerts?limit=10");
        setNotif((s) => ({ ...s, items: data }));
      } catch {
        setNotif((s) => ({ ...s, items: [] }));
      }
    }
  }

  function logout() {
    clearAuth();
    nav("/login", { replace: true });
  }

  const total = notif.counts?.total || 0;
  const tone = (notif.counts?.critical || 0) > 0 ? "bg-accent-red text-white" : "bg-accent-cyan text-bg-primary";

  return (
    <header className="h-14 border-b border-border bg-bg-secondary/80 backdrop-blur flex items-center gap-3 px-4 sticky top-0 z-30">
      <button
        onClick={onOpenPalette}
        className="hidden md:flex items-center gap-2 h-9 px-3 rounded-md bg-bg-card border border-border text-text-muted hover:text-text-primary hover:border-accent-cyan/40 text-xs flex-1 max-w-md"
      >
        <Search size={14} />
        <span>Search vessels, bookings, pages…</span>
        <span className="ml-auto flex items-center gap-1 text-[10px] font-mono text-text-muted/70">
          <Command size={10} /> K
        </span>
      </button>

      <span className="hidden lg:flex ml-auto text-xs"><LiveClock /></span>

      {/* Notification bell */}
      <div className="relative ml-auto md:ml-0" ref={popRef}>
        <button
          onClick={openNotif}
          className="relative h-9 w-9 rounded-md hover:bg-bg-card border border-transparent hover:border-border flex items-center justify-center text-text-muted hover:text-text-primary"
        >
          <Bell size={18} />
          {total > 0 && (
            <span className={`absolute -top-1 -right-1 text-[9px] min-w-[16px] h-4 px-1 rounded-full font-mono leading-4 text-center ${tone}`}>
              {total}
            </span>
          )}
        </button>

        {notif.open && (
          <div className="absolute right-0 top-11 w-96 max-h-[70vh] overflow-auto bg-bg-card border border-border rounded-lg shadow-2xl z-40">
            <div className="px-4 py-2.5 border-b border-border flex items-center justify-between">
              <span className="font-display font-semibold text-sm">Notifications</span>
              {notif.counts && (
                <span className="text-[10px] font-mono text-text-muted">
                  {notif.counts.critical}c • {notif.counts.warning}w • {notif.counts.info}i
                </span>
              )}
            </div>
            {notif.items === null && <div className="p-4 text-text-muted text-sm">Loading…</div>}
            {notif.items?.length === 0 && (
              <div className="p-4 text-text-muted text-sm">No notifications.</div>
            )}
            <ul className="divide-y divide-border/60">
              {notif.items?.map((a) => {
                const tone =
                  a.severity === "critical" ? "text-accent-red" :
                  a.severity === "warning"  ? "text-accent-yellow" : "text-accent-cyan";
                return (
                  <li key={a.id} className="px-4 py-2.5 hover:bg-bg-secondary/60">
                    <div className="flex items-center gap-2">
                      <span className={`status-dot bg-current ${tone}`} />
                      <span className="text-sm font-display truncate">{a.title}</span>
                    </div>
                    <div className="text-[11px] text-text-muted mt-0.5">{a.message}</div>
                  </li>
                );
              })}
            </ul>
            <div className="border-t border-border p-2">
              <Link to="/alerts" onClick={() => setNotif((s) => ({ ...s, open: false }))}
                className="block text-center text-xs text-accent-cyan hover:underline py-1">
                View all alerts →
              </Link>
            </div>
          </div>
        )}
      </div>

      {/* User menu */}
      <div className="relative" ref={menuRef}>
        <button onClick={() => setMenu(!menu)}
          className="h-9 px-2 rounded-md hover:bg-bg-card border border-transparent hover:border-border flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-accent-cyan/15 border border-accent-cyan/40 grid place-items-center text-accent-cyan text-xs font-mono uppercase">
            {(me?.full_name || me?.email || "?").slice(0, 1)}
          </div>
          <div className="hidden md:flex flex-col items-start leading-tight">
            <span className="text-xs">{me?.full_name?.split(" ")[0] || me?.email}</span>
            <span className="text-[10px] text-text-muted font-mono uppercase">{me?.role}</span>
          </div>
        </button>
        {menu && (
          <div className="absolute right-0 top-11 w-52 bg-bg-card border border-border rounded-lg shadow-2xl z-40 py-1">
            <Link to="/settings" onClick={() => setMenu(false)}
              className="px-3 py-2 flex items-center gap-2 text-sm hover:bg-bg-secondary">
              <Settings size={14} /> Settings
            </Link>
            <Link to="/" onClick={() => setMenu(false)}
              className="px-3 py-2 flex items-center gap-2 text-sm hover:bg-bg-secondary">
              <User size={14} /> My home
            </Link>
            <button onClick={logout}
              className="w-full text-left px-3 py-2 flex items-center gap-2 text-sm text-accent-red hover:bg-bg-secondary">
              <LogOut size={14} /> Logout
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
