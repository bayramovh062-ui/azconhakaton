import L from "leaflet";

const COLOR = {
  OPTIMAL:    "#00ff88",
  OVERSPEED:  "#ff3d3d",
  UNDERSPEED: "#ffd700",
  BERTH_READY:"#00d4ff",
};

/**
 * Builds a Leaflet DivIcon shaped like a triangular ship pointing along
 * `course` degrees, colored by JIT `status`. OVERSPEED vessels get an
 * extra animated pulse ring.
 */
export function vesselIcon({ status, course = 0, size = 26, pulse = false }) {
  const color = COLOR[status] || "#00d4ff";
  const html = `
    <div style="position:relative;width:${size}px;height:${size}px;display:flex;align-items:center;justify-content:center;">
      ${pulse ? '<div class="vessel-pulse"></div>' : ""}
      <svg viewBox="0 0 24 24" width="${size}" height="${size}"
           style="transform: rotate(${course}deg); filter: drop-shadow(0 0 6px ${color}aa);">
        <path d="M12 2 L19 22 L12 18 L5 22 Z"
              fill="${color}" stroke="#0a0e1a" stroke-width="1.2" stroke-linejoin="round"/>
      </svg>
    </div>`;
  return L.divIcon({
    className: "nexusaz-vessel-icon",
    html,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

export function berthIcon() {
  const html = `
    <svg viewBox="0 0 24 24" width="22" height="22"
         style="filter: drop-shadow(0 0 4px #00d4ff);">
      <path d="M12 2 a3 3 0 1 1 0 6 a3 3 0 1 1 0 -6 z M11 9 h2 v9 h4 v2 H7 v-2 h4 z"
            fill="#00d4ff" stroke="#0a0e1a" stroke-width="0.8"/>
    </svg>`;
  return L.divIcon({
    className: "nexusaz-berth-icon",
    html,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });
}
