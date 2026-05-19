import { useState, useEffect, useRef, useCallback } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity, Platform } from 'react-native';
import * as Location from 'expo-location';
import LeafletMap from '../../components/LeafletMap';
import { passengerApi } from '../../api/index';
import { COLORS, WS_URL } from '../../config';

function haversine(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat/2)**2 +
    Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)**2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

// Pakistan bounding box — rejects emulator's default Mountain View, CA coords
function validCoord(lat, lng) {
  const a = Number(lat), b = Number(lng);
  return isFinite(a) && isFinite(b) &&
         a >= 23.5 && a <= 37.5 &&    // Pakistan latitude range
         b >= 60.8 && b <= 77.8;      // Pakistan longitude range
}

export default function LiveMapScreen({ route }) {
  const { tripId, busId, routeId, busNumber, driverName, routeName } = route.params;

  const mapRef    = useRef(null);
  const wsRef     = useRef(null);
  const etaTimer  = useRef(null);
  const locSub    = useRef(null);
  const mapReady  = useRef(false);
  const stopsRef  = useRef([]);   // mirror of stops state for onMapReady race fix

  // pending updates to apply once map is ready
  const pendingBus = useRef(null);
  const pendingPas = useRef(null);

  const [busCoord,  setBusCoord]  = useState(null);
  // keep stopsRef in sync
  const setStopsSync = (s) => { stopsRef.current = s; setStops(s); };
  const [pasCoord,  setPasCoord]  = useState(null);
  const [speed,     setSpeed]     = useState(null);
  const [stops,     setStops]     = useState([]);
  const [eta,       setEta]       = useState(null);
  const [pasEta,    setPasEta]    = useState(null);
  const [wsStatus,  setWsStatus]  = useState('connecting');
  const [showMap,   setShowMap]   = useState(true);

  // Track whether the bus has been placed on the map yet (first appearance)
  const busPlaced = useRef(false);

  // ── Helpers ───────────────────────────────────────────────────────────────
  const pushBus = useCallback((lat, lng) => {
    const id = busId || 'bus';
    if (!mapReady.current) { pendingBus.current = { lat, lng }; return; }
    if (!busPlaced.current) {
      // First GPS fix received — add bus marker and fly to it
      busPlaced.current = true;
      mapRef.current?.addBus(id, lat, lng, busNumber ?? 'Bus');
    } else {
      mapRef.current?.updateBus(id, lat, lng);
    }
  }, [busId, busNumber]);

  const pushPas = useCallback((lat, lng) => {
    if (!mapReady.current) { pendingPas.current = { lat, lng }; return; }
    mapRef.current?.setPassenger(lat, lng);
  }, []);

  const onMapReady = useCallback(() => {
    mapReady.current = true;
    // flush pending bus
    if (pendingBus.current) {
      const { lat, lng } = pendingBus.current;
      mapRef.current?.addBus(busId || 'bus', lat, lng, `${busNumber ?? 'Bus'}`);
      pendingBus.current = null;
    }
    // flush pending passenger
    if (pendingPas.current) {
      const { lat, lng } = pendingPas.current;
      mapRef.current?.setPassenger(lat, lng);
      pendingPas.current = null;
    }
    // push stops immediately if already loaded (race condition fix)
    if (stopsRef.current?.length) {
      const valid = stopsRef.current.filter(s => validCoord(s.latitude, s.longitude));
      if (valid.length) {
        mapRef.current?.addStops(valid);
        if (valid.length > 1)
          mapRef.current?.setPolyline(valid.map(s => [Number(s.latitude), Number(s.longitude)]));
      }
    }
  }, [busId, busNumber]);

  // ── Passenger → bus ETA ───────────────────────────────────────────────────
  useEffect(() => {
    if (!pasCoord || !busCoord) return;
    const d = haversine(pasCoord.latitude, pasCoord.longitude, busCoord.latitude, busCoord.longitude);
    if (d < 200) setPasEta({ dist_km: d.toFixed(2), walk_mins: Math.round((d/5)*60) });
  }, [pasCoord?.latitude, pasCoord?.longitude, busCoord?.latitude, busCoord?.longitude]);

  // ── Passenger GPS — get first fix immediately ─────────────────────────────
  useEffect(() => {
    (async () => {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') return;

      // Immediate first fix (fast)
      try {
        const first = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
        const { latitude, longitude } = first.coords;
        if (validCoord(latitude, longitude)) {
          setPasCoord({ latitude, longitude });
          pushPas(latitude, longitude);
        }
      } catch (_) {}

      // Continuous updates
      locSub.current = await Location.watchPositionAsync(
        { accuracy: Location.Accuracy.High, timeInterval: 3000, distanceInterval: 10 },
        (pos) => {
          const { latitude, longitude } = pos.coords;
          if (validCoord(latitude, longitude)) {
            setPasCoord({ latitude, longitude });
            pushPas(latitude, longitude);
          }
        }
      );
    })();
    return () => locSub.current?.remove();
  }, []);

  // ── Push bus coord changes to map ─────────────────────────────────────────
  useEffect(() => {
    if (!busCoord) return;
    pushBus(busCoord.latitude, busCoord.longitude);
  }, [busCoord?.latitude, busCoord?.longitude]);

  // ── Push stops to map after load — fitBounds auto-zooms to show full route ─
  useEffect(() => {
    if (!stops.length || !mapReady.current) return;
    const valid = stops.filter(s => validCoord(s.latitude, s.longitude));
    if (!valid.length) return;
    mapRef.current?.addStops(valid);
    if (valid.length > 1) {
      mapRef.current?.setPolyline(valid.map(s => [Number(s.latitude), Number(s.longitude)]));
    }
    // fitBounds is called inside addStops automatically on first load
  }, [stops, mapReady.current]);

  // ── Data fetchers ─────────────────────────────────────────────────────────
  const loadStops = useCallback(async () => {
    if (!routeId) return;
    try {
      const r = await passengerApi.getRouteStops(routeId);
      setStopsSync(r.data ?? []);
    } catch {}
  }, [routeId]);

  const fetchBusLocation = useCallback(async () => {
    if (!busId) return;
    try {
      const r = await passengerApi.getBusLocation(busId);
      const lat = Number(r.data?.latitude), lng = Number(r.data?.longitude);
      if (validCoord(lat, lng)) setBusCoord({ latitude: lat, longitude: lng });
    } catch {}
  }, [busId]);

  const fetchETA = useCallback(async () => {
    if (!tripId) return;
    try {
      const r = await passengerApi.getETA(tripId);
      const d = r.data;
      if (d && Number(d.estimated_minutes) < 300 && Number(d.distance_to_stop_km) < 200) {
        setEta(d);
      }
    } catch {}
  }, [tripId]);

  // ── WebSocket ─────────────────────────────────────────────────────────────
  const connectWS = useCallback(() => {
    if (!busId) return;
    const ws = new WebSocket(`${WS_URL}/api/locations/ws/live-tracking?bus_id=${busId}`);
    wsRef.current = ws;
    ws.onopen    = () => setWsStatus('waiting');
    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        const lat = Number(d.latitude), lng = Number(d.longitude);
        if (!validCoord(lat, lng)) return;
        setBusCoord({ latitude: lat, longitude: lng });
        if (d.speed_kmh != null) setSpeed(d.speed_kmh);
        setWsStatus('live');
      } catch {}
    };
    ws.onerror = () => setWsStatus('offline');
    ws.onclose = () => setWsStatus(s => s !== 'offline' ? 'waiting' : s);
  }, [busId]);

  useEffect(() => {
    loadStops();
    fetchBusLocation();
    fetchETA();
    connectWS();
    etaTimer.current = setInterval(fetchETA, 30000);
    return () => {
      clearInterval(etaTimer.current);
      wsRef.current?.close();
    };
  }, []);

  const wsLabel  = { live: '● Live', waiting: '◌ Waiting for driver', connecting: '◌ Connecting', offline: '✕ Offline' }[wsStatus];
  const wsColour = { live: '#43A047', waiting: '#FB8C00', connecting: '#FB8C00', offline: '#E53935' }[wsStatus];
  const showNextStop = eta?.next_stop_name && Number(eta?.estimated_minutes) < 300;
  const showDist     = eta?.distance_to_stop_km != null && Number(eta.distance_to_stop_km) < 200;

  return (
    <View style={st.root}>

      {/* ── Stable map (never remounts) ──────────────────────────────────── */}
      <LeafletMap
        ref={mapRef}
        style={st.map}
        onReady={onMapReady}
      />

      {/* Waiting for bus GPS banner */}
      {!busCoord && (
        <View style={st.gpsBanner}>
          <ActivityIndicator size="small" color="#fff" style={{ marginRight: 8 }} />
          <View>
            <Text style={st.gpsBannerTxt}>Waiting for bus GPS signal</Text>
            <Text style={st.gpsBannerSub}>Driver must start trip and enable GPS</Text>
          </View>
        </View>
      )}

      {/* Center-on-bus FAB — only visible when bus is active */}
      {busCoord && (
        <TouchableOpacity
          style={st.busFab}
          onPress={() => mapRef.current?.zoomTo(busCoord.latitude, busCoord.longitude, 16)}
          activeOpacity={0.85}
        >
          <Text style={st.busFabTxt}>🚌</Text>
        </TouchableOpacity>
      )}

      {/* Center-on-me FAB */}
      {pasCoord && (
        <TouchableOpacity
          style={[st.busFab, { bottom: 240 }]}
          onPress={() => mapRef.current?.zoomTo(pasCoord.latitude, pasCoord.longitude, 16)}
          activeOpacity={0.85}
        >
          <Text style={st.busFabTxt}>🎯</Text>
        </TouchableOpacity>
      )}

      {/* ── Top bar ──────────────────────────────────────────────────────── */}
      <View style={st.topBar}>
        <View style={{ flex: 1 }}>
          <Text style={st.busNum}>{busNumber ?? '—'}</Text>
          <Text style={st.routeTxt} numberOfLines={1}>{routeName ?? '—'}</Text>
        </View>
        <View style={[st.wsPill, { backgroundColor: wsColour }]}>
            <Text style={st.wsTxt}>{wsLabel}</Text>
        </View>
      </View>

      {/* ── Bottom ETA sheet ─────────────────────────────────────────────── */}
      <View style={st.sheet}>
        <View style={st.handle} />

        {driverName && (
          <View style={st.driverRow}>
            <Text style={{ fontSize: 22 }}>👤</Text>
            <Text style={st.driverName}>{driverName}</Text>
            {speed != null && <Text style={st.speedBadge}>{Math.round(speed)} km/h</Text>}
          </View>
        )}

        {pasEta && (
          <View style={st.pasRow}>
            <Text style={{ fontSize: 20 }}>📍</Text>
            <View style={{ flex: 1 }}>
              <Text style={st.pasLabel}>Your distance to bus</Text>
              <Text style={st.pasVal}>{pasEta.dist_km} km · ~{pasEta.walk_mins} min walk</Text>
            </View>
          </View>
        )}

        {showNextStop && (
          <View style={st.etaRow}>
            <View style={st.etaIconBox}><Text style={{ fontSize: 20 }}>🛑</Text></View>
            <View style={{ flex: 1 }}>
              <Text style={st.etaLabel}>Next Stop</Text>
              <Text style={st.etaValue}>{eta.next_stop_name}</Text>
            </View>
            <View style={st.etaBox}>
              <Text style={st.etaMin}>{eta.estimated_minutes}</Text>
              <Text style={st.etaMinLbl}>min</Text>
            </View>
          </View>
        )}

        {showDist && (
          <Text style={st.distTxt}>📏 {Number(eta.distance_to_stop_km).toFixed(2)} km to next stop</Text>
        )}

        {stops.filter(s => validCoord(s.latitude, s.longitude)).length > 0 && (
          <View style={st.stopsBar}>
            {stops.filter(s => validCoord(s.latitude, s.longitude)).map((s, i, arr) => (
              <View key={s.id} style={st.chip}>
                <View style={[st.chipDot,
                  i === 0       ? { backgroundColor: COLORS.success }
                  : i === arr.length-1 ? { backgroundColor: COLORS.danger }
                  : { backgroundColor: COLORS.border }
                ]} />
                <Text style={st.chipTxt} numberOfLines={1}>{s.stop_name}</Text>
              </View>
            ))}
          </View>
        )}

        <TouchableOpacity style={st.refreshBtn} onPress={() => { fetchBusLocation(); fetchETA(); }}>
          <Text style={st.refreshTxt}>↺  Refresh</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const st = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#e8dfc8' },
  map:  { flex: 1 },

  gpsBanner:    { position: 'absolute', top: 44, left: 12, right: 12, flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.65)', borderRadius: 12, paddingHorizontal: 14, paddingVertical: 10 },
  gpsBannerTxt: { color: '#fff', fontSize: 13, fontWeight: '700' },
  gpsBannerSub: { color: 'rgba(255,255,255,0.75)', fontSize: 11, marginTop: 1 },

  topBar:   { position: 'absolute', top: 0, left: 0, right: 0, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', backgroundColor: 'rgba(26,35,126,0.92)', paddingHorizontal: 16, paddingVertical: 10 },
  busNum:   { color: '#fff', fontSize: 16, fontWeight: '800' },
  routeTxt: { color: 'rgba(255,255,255,0.75)', fontSize: 12, marginTop: 1 },
  wsPill:   { borderRadius: 12, paddingHorizontal: 10, paddingVertical: 4 },
  wsTxt:    { color: '#fff', fontSize: 11, fontWeight: '700' },

  sheet:     { backgroundColor: '#fff', borderTopLeftRadius: 24, borderTopRightRadius: 24, paddingHorizontal: 20, paddingTop: 10, paddingBottom: 24, elevation: 16, shadowColor: '#000', shadowOpacity: 0.25, shadowRadius: 14, shadowOffset: { width: 0, height: -4 } },
  handle:    { width: 40, height: 4, borderRadius: 2, backgroundColor: COLORS.border, alignSelf: 'center', marginBottom: 12 },

  driverRow:  { flexDirection: 'row', alignItems: 'center', marginBottom: 10, gap: 8 },
  driverName: { flex: 1, fontSize: 15, fontWeight: '600', color: COLORS.text },
  speedBadge: { backgroundColor: '#E3F2FD', borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3, fontSize: 12, fontWeight: '700', color: COLORS.primary },

  pasRow:   { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#E8F5E9', borderRadius: 10, padding: 10, marginBottom: 10 },
  pasLabel: { fontSize: 11, color: COLORS.textLight, textTransform: 'uppercase' },
  pasVal:   { fontSize: 14, fontWeight: '700', color: COLORS.success },

  etaRow:    { flexDirection: 'row', alignItems: 'center', marginBottom: 6, gap: 10 },
  etaIconBox:{ width: 40, height: 40, borderRadius: 20, backgroundColor: '#FFF3E0', alignItems: 'center', justifyContent: 'center' },
  etaLabel:  { fontSize: 11, color: COLORS.textLight, textTransform: 'uppercase', letterSpacing: 0.5 },
  etaValue:  { fontSize: 16, fontWeight: '700', color: COLORS.text },
  etaBox:    { backgroundColor: COLORS.primary, borderRadius: 10, paddingHorizontal: 10, paddingVertical: 6, alignItems: 'center' },
  etaMin:    { color: '#fff', fontSize: 20, fontWeight: '800', lineHeight: 24 },
  etaMinLbl: { color: 'rgba(255,255,255,0.8)', fontSize: 10 },
  distTxt:   { fontSize: 13, color: COLORS.textLight, marginBottom: 10 },

  stopsBar: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginVertical: 10 },
  chip:     { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: COLORS.bg, borderRadius: 8, paddingHorizontal: 8, paddingVertical: 4 },
  chipDot:  { width: 8, height: 8, borderRadius: 4 },
  chipTxt:  { fontSize: 11, color: COLORS.text, maxWidth: 80 },

  refreshBtn: { backgroundColor: COLORS.bg, borderRadius: 10, paddingVertical: 10, alignItems: 'center', marginTop: 4 },
  refreshTxt: { color: COLORS.primary, fontWeight: '700', fontSize: 14 },

  busFab:    { position: 'absolute', right: 14, bottom: 290, width: 48, height: 48, borderRadius: 24, backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center', elevation: 6, shadowColor: '#000', shadowOpacity: 0.2, shadowRadius: 6, shadowOffset: { width: 0, height: 2 } },
  busFabTxt: { fontSize: 22 },
});
