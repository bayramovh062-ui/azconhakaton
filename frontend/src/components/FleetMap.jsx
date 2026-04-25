import { useEffect } from "react";
import { CircleMarker, MapContainer, Marker, Popup, TileLayer, Polyline, useMap } from "react-leaflet";
import { BAKU_PORT } from "../config";
import { berthIcon, vesselIcon } from "./VesselIcon";

const TILE_URL =
  "https://cartodb-basemaps-a.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png";
const ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>';

function FlyTo({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    if (center) map.flyTo(center, zoom ?? map.getZoom(), { duration: 0.6 });
  }, [center, zoom, map]);
  return null;
}

export default function FleetMap({
  vessels = [],
  berths = [],
  height = 400,
  zoom = 8,
  center,
  onVesselClick,
  vesselTrack = [],
  fullScreen = false,
}) {
  const c = center || [BAKU_PORT.lat, BAKU_PORT.lon];
  return (
    <div
      className="rounded-xl overflow-hidden border border-border"
      style={{ height: fullScreen ? "100%" : height, width: "100%" }}
    >
      <MapContainer
        center={c}
        zoom={zoom}
        style={{ height: "100%", width: "100%" }}
        scrollWheelZoom
      >
        <TileLayer url={TILE_URL} attribution={ATTRIBUTION} />
        <FlyTo center={center} zoom={zoom} />

        {/* Baku Port marker */}
        <CircleMarker
          center={[BAKU_PORT.lat, BAKU_PORT.lon]}
          radius={8}
          pathOptions={{ color: "#00d4ff", fillColor: "#00d4ff", fillOpacity: 0.4 }}
        >
          <Popup>
            <div className="font-display font-semibold text-accent-cyan">⚓ Baku Port</div>
            <div className="text-text-muted text-xs">Baku Int'l Sea Trade Port</div>
          </Popup>
        </CircleMarker>

        {/* Berths */}
        {berths.map((b) => (
          <Marker key={b.id} position={[b.location_lat, b.location_lon]} icon={berthIcon()}>
            <Popup>
              <div className="font-display text-sm">{b.code}</div>
              <div className="text-text-muted text-xs">{b.name}</div>
              <div className="text-xs mt-1">
                Status: <span className="font-mono uppercase">{b.status}</span>
              </div>
              {b.vessel_name && (
                <div className="text-xs">Vessel: <strong>{b.vessel_name}</strong></div>
              )}
            </Popup>
          </Marker>
        ))}

        {/* Vessel track (Polyline) */}
        {vesselTrack.length > 1 && (
          <Polyline
            positions={vesselTrack}
            pathOptions={{ color: "#00d4ff", weight: 2, opacity: 0.5, dashArray: "4 6" }}
          />
        )}

        {/* Vessels */}
        {vessels.map((v) => (
          <Marker
            key={v.vessel_id}
            position={[v.lat, v.lon]}
            icon={vesselIcon({
              status: v.status,
              course: v.course || 0,
              pulse: v.status === "OVERSPEED",
            })}
            eventHandlers={{
              click: () => onVesselClick && onVesselClick(v),
            }}
          >
            <Popup>
              <div className="space-y-1">
                <div className="font-display font-semibold text-text-primary">{v.vessel_name}</div>
                {v.mmsi && <div className="text-[11px] text-text-muted font-mono">MMSI {v.mmsi}</div>}
                <div className="text-xs"><span className="text-text-muted">Status:</span> <strong>{v.status}</strong></div>
                <div className="font-mono text-xs">
                  SOG: {v.current_speed?.toFixed(1)} kn ▸ Rec: {v.recommended_speed?.toFixed(1)} kn
                </div>
                <div className="font-mono text-xs">Distance: {v.distance_nm?.toFixed(1)} nm</div>
                {v.scheduled_arrival && (
                  <div className="font-mono text-xs">
                    ETA: {new Date(v.scheduled_arrival).toUTCString().slice(17, 22)}
                  </div>
                )}
                {v.fuel_saved_liters > 0 && (
                  <div className="text-xs text-accent-green">Fuel saved if corrected: {v.fuel_saved_liters.toFixed(1)} L</div>
                )}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
