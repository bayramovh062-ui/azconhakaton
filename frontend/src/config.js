// Central API configuration. Override via Vite env vars in `.env.local`.
//   VITE_API_BASE  e.g.  http://localhost:8765
//   VITE_WS_URL    e.g.  ws://localhost:8765/ws/fleet
export const API_BASE =
  import.meta.env.VITE_API_BASE || "http://127.0.0.1:8765";
export const WS_URL =
  import.meta.env.VITE_WS_URL || "ws://127.0.0.1:8765/ws/fleet";

export const BAKU_PORT = { lat: 40.35, lon: 49.87 };
