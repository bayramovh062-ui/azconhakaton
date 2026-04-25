import { formatDistanceToNow } from "date-fns";
import { CalendarDays, Gauge, Radio } from "lucide-react";
import { useEffect, useState } from "react";
import apiFetch from "../api";
import Skeleton from "./Skeleton";

const ICON = {
  booking:   { Icon: CalendarDays, color: "text-accent-cyan" },
  jit:       { Icon: Gauge,        color: "text-accent-green" },
  telemetry: { Icon: Radio,        color: "text-accent-yellow" },
};

export default function ActivityFeed() {
  const [items, setItems] = useState(null);
  useEffect(() => {
    apiFetch("/stats/activity?limit=12").then(setItems).catch(() => setItems([]));
  }, []);
  return (
    <div className="bg-bg-card border border-border rounded-xl">
      <div className="px-4 py-3 border-b border-border">
        <h3 className="font-display font-semibold">Recent activity</h3>
      </div>
      <div className="max-h-[360px] overflow-auto divide-y divide-border">
        {items === null && <div className="p-4"><Skeleton className="h-32" /></div>}
        {items?.length === 0 && (
          <div className="p-4 text-text-muted text-sm">No activity yet.</div>
        )}
        {items?.map((it, idx) => {
          const cfg = ICON[it.kind] || ICON.booking;
          const Icon = cfg.Icon;
          return (
            <div key={idx} className="px-4 py-2 flex items-start gap-2 text-sm">
              <Icon className={`${cfg.color} mt-0.5`} size={16} />
              <div className="flex-1">
                <div className="text-text-primary">{it.text}</div>
                <div className="text-[11px] text-text-muted font-mono">
                  {formatDistanceToNow(new Date(it.timestamp), { addSuffix: true })}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
