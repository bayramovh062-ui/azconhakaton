import { Trophy } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import apiFetch from "../api";
import Skeleton from "./Skeleton";

const FLAG_EMOJI = {
  Azerbaijan: "🇦🇿", Russia: "🇷🇺", Turkey: "🇹🇷", Iran: "🇮🇷",
  Kazakhstan: "🇰🇿", Turkmenistan: "🇹🇲",
};

export default function TopVessels({ limit = 5 }) {
  const nav = useNavigate();
  const [rows, setRows] = useState(null);
  useEffect(() => {
    apiFetch(`/stats/top-vessels?limit=${limit}`).then(setRows).catch(() => setRows([]));
  }, [limit]);

  return (
    <div className="bg-bg-card border border-border rounded-xl">
      <div className="px-4 py-3 border-b border-border flex items-center gap-2">
        <Trophy className="text-accent-yellow" size={16} />
        <h3 className="font-display font-semibold">Top performing vessels</h3>
      </div>
      <div className="divide-y divide-border">
        {rows === null && <div className="p-4"><Skeleton className="h-32" /></div>}
        {rows?.map((r, i) => (
          <button
            key={r.vessel_id}
            onClick={() => nav(`/fleet/${r.vessel_id}`)}
            className="w-full text-left px-4 py-2 hover:bg-bg-secondary flex items-center gap-3"
          >
            <span className="font-display text-accent-cyan w-5 text-right">{i + 1}</span>
            <span>{FLAG_EMOJI[r.flag] || "🏳️"}</span>
            <div className="flex-1 min-w-0">
              <div className="text-sm truncate">{r.vessel_name}</div>
              <div className="text-[11px] text-text-muted truncate">{r.operator}</div>
            </div>
            <div className="text-right text-xs font-mono">
              <div className="text-accent-green">{r.co2_saved_kg.toLocaleString(undefined, { maximumFractionDigits: 0 })} kg</div>
              <div className="text-text-muted">{r.optimal_count}/{r.total_recs} optimal</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
