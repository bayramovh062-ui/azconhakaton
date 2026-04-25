import { useEffect, useState } from "react";
import apiFetch from "../api";

/**
 * Tiny inline badge for the sidebar — polls /alerts/counts every 30s.
 */
export default function AlertBell() {
  const [counts, setCounts] = useState(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const c = await apiFetch("/alerts/counts");
        if (mounted) setCounts(c);
      } catch {/* silent */}
    }
    load();
    const t = setInterval(load, 30000);
    return () => { mounted = false; clearInterval(t); };
  }, []);

  if (!counts || counts.total === 0) return null;
  const tone = counts.critical > 0 ? "bg-accent-red text-white" : "bg-accent-yellow text-bg-primary";
  return (
    <span className={`text-[10px] font-mono px-1.5 rounded ${tone}`}>
      {counts.total}
    </span>
  );
}
