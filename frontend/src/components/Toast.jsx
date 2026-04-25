import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { CheckCircle2, XCircle, Info, X } from "lucide-react";

const ToastCtx = createContext(null);

export function useToast() {
  const ctx = useContext(ToastCtx);
  if (!ctx) throw new Error("useToast must be used within <ToastProvider>");
  return ctx;
}

let _id = 0;
const nextId = () => ++_id;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts((t) => t.filter((x) => x.id !== id));
  }, []);

  const push = useCallback(
    (message, type = "info", ttl = 4000) => {
      const id = nextId();
      setToasts((t) => [...t, { id, message, type }]);
      if (ttl > 0) setTimeout(() => dismiss(id), ttl);
    },
    [dismiss]
  );

  const api = {
    success: (m) => push(m, "success"),
    error: (m) => push(m, "error"),
    info: (m) => push(m, "info"),
  };

  return (
    <ToastCtx.Provider value={api}>
      {children}
      <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 w-80 max-w-[90vw]">
        {toasts.map((t) => (
          <Toast key={t.id} toast={t} onClose={() => dismiss(t.id)} />
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

function Toast({ toast, onClose }) {
  const styles = {
    success: { Icon: CheckCircle2, color: "text-accent-green border-accent-green/40" },
    error:   { Icon: XCircle,      color: "text-accent-red border-accent-red/40" },
    info:    { Icon: Info,         color: "text-accent-cyan border-accent-cyan/40" },
  }[toast.type] || { Icon: Info, color: "text-text-primary border-border" };
  const { Icon, color } = styles;
  return (
    <div
      className={`glass rounded-lg p-3 pr-8 flex items-start gap-3 shadow-lg border ${color} animate-countUp`}
    >
      <Icon size={18} className="mt-0.5 shrink-0" />
      <div className="text-sm text-text-primary flex-1">{toast.message}</div>
      <button
        onClick={onClose}
        className="absolute top-2 right-2 text-text-muted hover:text-text-primary"
        style={{ position: "absolute" }}
      >
        <X size={14} />
      </button>
    </div>
  );
}
