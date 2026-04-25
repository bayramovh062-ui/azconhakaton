import { Building2, Copy, KeyRound, LogOut, Mail, Ship, User } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { clearAuth, getStoredUser, getToken } from "../api";
import PageHeader from "../components/PageHeader";
import { useToast } from "../components/Toast";

export default function Settings() {
  const me = getStoredUser();
  const nav = useNavigate();
  const toast = useToast();
  const [showToken, setShowToken] = useState(false);

  function copyToken() {
    const t = getToken();
    if (!t) return;
    navigator.clipboard.writeText(t);
    toast.success("Token copied");
  }

  function logout() {
    clearAuth();
    nav("/login", { replace: true });
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <PageHeader
        title="Settings"
        subtitle="Profile, session and preferences"
      />

      {/* Profile */}
      <div className="bg-bg-card border border-border rounded-xl p-5 mb-4">
        <h3 className="font-display font-semibold text-sm mb-3 flex items-center gap-2">
          <User size={16} className="text-accent-cyan" /> Profile
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
          <Field Icon={User}      label="Full name"        value={me?.full_name || "—"} />
          <Field Icon={Mail}      label="Email"            value={me?.email || "—"} mono />
          <Field                  label="Role"             value={(me?.role || "viewer").toUpperCase()} accent />
          <Field Icon={Building2} label="Operator"         value={me?.operator_company || "—"} />
          <Field Icon={Ship}      label="Assigned vessel"  value={me?.vessel_name || "—"} />
          <Field                  label="User ID"          value={me?.id || "—"} mono />
        </div>
      </div>

      {/* Session / Token */}
      <div className="bg-bg-card border border-border rounded-xl p-5 mb-4">
        <h3 className="font-display font-semibold text-sm mb-3 flex items-center gap-2">
          <KeyRound size={16} className="text-accent-cyan" /> Session
        </h3>
        <div className="text-text-muted text-xs mb-2">JWT bearer token (kept in localStorage):</div>
        <div className="bg-bg-secondary border border-border rounded p-2 font-mono text-[11px] break-all">
          {showToken ? (getToken() || "—") : "•".repeat(40)}
        </div>
        <div className="flex gap-2 mt-3">
          <button onClick={() => setShowToken((v) => !v)}
            className="h-9 px-3 rounded-md border border-border text-text-muted hover:text-text-primary text-xs">
            {showToken ? "Hide" : "Reveal"}
          </button>
          <button onClick={copyToken}
            className="h-9 px-3 rounded-md border border-border text-text-muted hover:text-text-primary text-xs flex items-center gap-1">
            <Copy size={12} /> Copy
          </button>
          <button onClick={logout}
            className="h-9 px-3 rounded-md border border-accent-red/40 text-accent-red text-xs flex items-center gap-1 ml-auto">
            <LogOut size={12} /> Sign out
          </button>
        </div>
      </div>

      {/* Preferences */}
      <div className="bg-bg-card border border-border rounded-xl p-5">
        <h3 className="font-display font-semibold text-sm mb-3">Preferences</h3>
        <ul className="text-sm text-text-muted space-y-2">
          <li>Theme — <span className="text-text-primary">Dark (locked for v2)</span></li>
          <li>Time zone — <span className="text-text-primary">UTC (vessel ops)</span></li>
          <li>Notification polling — <span className="text-text-primary">30s</span></li>
          <li>Keyboard — <span className="text-text-primary font-mono">⌘/Ctrl + K</span> to open command palette</li>
        </ul>
      </div>
    </div>
  );
}

function Field({ Icon, label, value, mono, accent }) {
  return (
    <div className="bg-bg-secondary border border-border rounded p-3">
      <div className="flex items-center gap-2 text-[11px] uppercase text-text-muted">
        {Icon && <Icon size={12} />} {label}
      </div>
      <div className={`mt-1 ${mono ? "font-mono text-xs break-all" : ""} ${accent ? "text-accent-cyan font-display" : "text-text-primary"}`}>
        {value}
      </div>
    </div>
  );
}
