import { useEffect, useRef, useState } from "react";
import { WS_URL } from "../config";

/**
 * Subscribes to /ws/fleet. Auto-reconnects with 3s back-off.
 * Returns { vessels, connected }.
 */
export default function useFleetSocket() {
  const [vessels, setVessels] = useState([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);
  const closedByCleanup = useRef(false);

  useEffect(() => {
    closedByCleanup.current = false;

    function connect() {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        if (closedByCleanup.current) return;
        reconnectTimer.current = setTimeout(connect, 3000);
      };
      ws.onerror = () => ws.close();
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === "fleet_status" && Array.isArray(msg.vessels)) {
            setVessels(msg.vessels);
          }
        } catch {
          /* ignore */
        }
      };
    }
    connect();

    return () => {
      closedByCleanup.current = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, []);

  return { vessels, connected };
}
