import { Anchor, Loader2, Lock, Mail } from "lucide-react";
import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import apiFetch, { getToken, TOKEN_KEY, USER_KEY } from "../api";
import { useToast } from "../components/Toast";

export default function Login() {
  const nav = useNavigate();
  const toast = useToast();
  const [email, setEmail] = useState("admin@nexusaz.io");
  const [password, setPassword] = useState("Admin@123");
  const [loading, setLoading] = useState(false);

  if (getToken()) return <Navigate to="/dashboard" replace />;

  async function onSubmit(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await apiFetch("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem(TOKEN_KEY, res.access_token);
      const me = await apiFetch("/auth/me");
      localStorage.setItem(USER_KEY, JSON.stringify(me));
      toast.success(`Welcome back, ${me.full_name || me.email}`);
      nav("/", { replace: true });
    } catch (err) {
      toast.error(err.message || "Invalid credentials");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative min-h-screen w-full bg-bg-primary text-text-primary overflow-hidden flex items-center justify-center p-4">
      {/* animated grid */}
      <div className="absolute inset-0 bg-grid animate-gridShift opacity-70" />
      {/* radial glow */}
      <div className="absolute inset-0 pointer-events-none"
           style={{ background: "radial-gradient(ellipse at 50% 35%, rgba(0,212,255,0.18), transparent 60%)" }} />

      <div className="relative z-10 w-full max-w-md">
        <div className="text-center mb-6">
          <div className="inline-flex items-center gap-2 mb-2">
            <Anchor className="text-accent-cyan" size={28} />
            <span className="font-display font-bold text-3xl tracking-wider">
              <span className="text-accent-cyan">AZ</span>MARINE
            </span>
          </div>
          <p className="text-text-muted text-sm">
            Just-in-Time arrivals • Caspian fleet intelligence
          </p>
        </div>

        <form
          onSubmit={onSubmit}
          className="glass rounded-xl p-6 space-y-4 shadow-2xl"
        >
          <Field
            Icon={Mail}
            label="Email"
            type="email"
            value={email}
            onChange={setEmail}
            placeholder="admin@nexusaz.io"
          />
          <Field
            Icon={Lock}
            label="Password"
            type="password"
            value={password}
            onChange={setPassword}
            placeholder="••••••••"
          />

          <button
            type="submit"
            disabled={loading}
            className="w-full h-11 rounded-md bg-accent-cyan text-bg-primary font-semibold tracking-wide hover:shadow-glow transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading && <Loader2 size={16} className="animate-spin" />}
            Sign In
          </button>

          <p className="text-center text-[11px] text-text-muted/80 font-mono pt-1">
            Demo creds: admin@nexusaz.io / Admin@123
          </p>
        </form>
      </div>
    </div>
  );
}

function Field({ Icon, label, type, value, onChange, placeholder }) {
  return (
    <label className="block">
      <span className="text-xs uppercase tracking-wider text-text-muted">{label}</span>
      <div className="mt-1 flex items-center gap-2 rounded-md border border-border bg-bg-secondary/60 px-3 h-10 focus-within:border-accent-cyan/60 focus-within:shadow-glow">
        <Icon size={16} className="text-text-muted" />
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          required
          className="flex-1 bg-transparent outline-none text-text-primary placeholder:text-text-muted/60"
        />
      </div>
    </label>
  );
}
