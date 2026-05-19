/**
 * useLiveTracking
 * ===============
 * WebSocket hook that subscribes to a single bus's live GPS stream.
 *
 * Usage:
 *   const { location, connected, error } = useLiveTracking(busId);
 *
 * Returns:
 *   location  — { latitude, longitude, speed_kmh, heading_deg, recorded_at }
 *   connected — boolean
 *   error     — string | null
 *
 * The hook automatically reconnects with exponential back-off when the
 * connection drops (network flap, server restart, etc.).
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { WS_URL } from '../config';

const BASE_RETRY_MS  = 2_000;   // first retry after 2 s
const MAX_RETRY_MS   = 30_000;  // cap at 30 s
const PING_INTERVAL  = 25_000;  // keep-alive ping every 25 s

export function useLiveTracking(busId) {
  const [location,  setLocation]  = useState(null);
  const [connected, setConnected] = useState(false);
  const [error,     setError]     = useState(null);

  const ws        = useRef(null);
  const retryMs   = useRef(BASE_RETRY_MS);
  const retryTimer= useRef(null);
  const pingTimer = useRef(null);
  const active    = useRef(true);       // false after unmount

  const clearTimers = () => {
    clearTimeout(retryTimer.current);
    clearInterval(pingTimer.current);
  };

  const connect = useCallback(() => {
    if (!active.current || !busId) return;

    const url = `${WS_URL}/api/locations/ws/live-tracking?bus_id=${busId}`;
    const socket = new WebSocket(url);
    ws.current = socket;

    socket.onopen = () => {
      if (!active.current) { socket.close(); return; }
      setConnected(true);
      setError(null);
      retryMs.current = BASE_RETRY_MS;   // reset back-off on successful connect

      // Keep-alive pings (server drops idle WS after ~60 s on most hosts)
      pingTimer.current = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) socket.send('ping');
      }, PING_INTERVAL);
    };

    socket.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        if (data.latitude && data.longitude) {
          setLocation({
            latitude:   parseFloat(data.latitude),
            longitude:  parseFloat(data.longitude),
            speed_kmh:  data.speed_kmh  != null ? parseFloat(data.speed_kmh)  : null,
            heading_deg:data.heading_deg != null ? parseFloat(data.heading_deg): null,
            recorded_at:data.recorded_at || new Date().toISOString(),
            simulated:  data.simulated  ?? false,
          });
        }
      } catch (_) {}
    };

    socket.onerror = () => setError('WebSocket error');

    socket.onclose = () => {
      clearTimers();
      setConnected(false);
      if (!active.current) return;

      // Exponential back-off reconnect
      retryTimer.current = setTimeout(() => {
        retryMs.current = Math.min(retryMs.current * 2, MAX_RETRY_MS);
        connect();
      }, retryMs.current);
    };
  }, [busId]);

  useEffect(() => {
    active.current = true;
    connect();

    return () => {
      active.current = false;
      clearTimers();
      ws.current?.close();
    };
  }, [connect]);

  return { location, connected, error };
}
