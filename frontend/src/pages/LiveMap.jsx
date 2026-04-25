import { Wifi, WifiOff } from "lucide-react";
import { useEffect, useState } from "react";
import apiFetch from "../api";
import FleetMap from "../components/FleetMap";
import StatusBadge from "../components/StatusBadge";
import useFleetSocket from "../hooks/useFleetSocket";

export default function LiveMap() {
  const { vessels, connected } = useFleetSocket();
  const [berths, setBerths] = useState([]);
  const [trackVessel, setTrackVessel] = useState(null);
  const [track, setTrack] = useState([]);
  const [center, setCenter] = useState(null);

  useEffect(() => {
    apiFetch("/bookings")
      .then((rows) =>
        setBerths(
          rows.map((b) => ({
            id: b.berth_id,
            ...b.berth,
            location_lat: 40.35 + (b.berth?.code === "BAK-B2" ? -0.0008 : b.berth?.code === "BAK-B3" ? 0.0017 : 0.0005),
            location_lon: 49.87 + (b.berth?.code === "BAK-B2" ? 0.0015 : b.berth?.code === "BAK-B3" ? -0.0012 : 0.0002),
            vessel_name: b.vessel?.name,
          }))
        )
      )
      .catch(() => setBerths([]));
  }, []);

  async function onVesselClick(v) {
    setTrackVessel(v);
    setCenter([v.lat, v.lon]);
    try {
      const positions = await apiFetch(`/vessels/${v.vessel_id}/positions?limit=20`);
      setTrack(positions.map((p) => [p.lat, p.lon]).reverse());
    } catch {
      setTrack([]);
    }
  }

  return (
    <div className="relative h-[calc(100vh-0px)] w-full">
      <div className="absolute inset-0">
        <FleetMap
          fullScreen
          vessels={vessels}
          berths={berths}
          zoom={9}
          center={center}
          onVesselClick={onVesselClick}
          vesselTrack={track}
        />
      </div>

      {/* floating panel */}
      <div className="absolute top-4 right-4 z-[400] glass rounded-xl w-72 max-h-[80vh] overflow-hidden flex flex-col">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <span className="font-display font-semibold">Fleet Status</span>
          {connected ? (
            <span className="flex items-center gap-1 text-accent-green text-[11px]">
              <Wifi size={12} /> Live
            </span>
          ) : (
            <span className="flex items-center gap-1 text-accent-red text-[11px]">
              <WifiOff size={12} /> Disconnected
            </span>
          )}
        </div>
        <div className="overflow-auto divide-y divide-border">
          {vessels.length === 0 && <div className="p-4 text-text-muted text-xs">No vessels tracked.</div>}
          {vessels.map((v) => (
            <button
              key={v.vessel_id}
              onClick={() => onVesselClick(v)}
              className="w-full text-left px-4 py-2 hover:bg-bg-secondary"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-display text-xs truncate">{v.vessel_name}</span>
                <StatusBadge status={v.status} />
              </div>
              <div className="font-mono text-[10px] text-text-muted">
                SOG {v.current_speed?.toFixed(1)} ▸ Rec {v.recommended_speed?.toFixed(1)} kn
              </div>
            </button>
          ))}
        </div>
        {trackVessel && (
          <div className="px-4 py-2 border-t border-border bg-bg-secondary/40">
            <div className="text-[11px] text-text-muted">Track</div>
            <div className="text-xs font-display">{trackVessel.vessel_name}</div>
            <button
              onClick={() => { setTrack([]); setTrackVessel(null); }}
              className="text-[10px] text-accent-cyan hover:underline mt-1"
            >
              Clear track
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
