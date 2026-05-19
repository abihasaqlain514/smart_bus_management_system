import { useState, useEffect, useRef, useCallback } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, ScrollView,
  SafeAreaView, StatusBar, Dimensions,
} from 'react-native';
import * as Location from 'expo-location';
import LeafletMap from '../../components/LeafletMap';
import { useAuth } from '../../context/AuthContext';
import { passengerApi } from '../../api/index';
import { COLORS } from '../../config';

const SCREEN_H   = Dimensions.get('window').height;
const SHEET_H    = Math.min(300, SCREEN_H * 0.42); // max 42% of screen for sheet
const FAB_BOTTOM = SHEET_H + 16;

// University of Jhang — fallback when device GPS is unavailable / emulator
const JHANG_UNI = { latitude: 31.2693, longitude: 72.3210 };

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good Morning';
  if (h < 17) return 'Good Afternoon';
  return 'Good Evening';
}

function inPakistan(lat, lng) {
  return lat >= 23.5 && lat <= 37.5 && lng >= 60.8 && lng <= 77.8;
}

export default function HomeScreen({ navigation }) {
  const { user, logout } = useAuth();
  const mapRef        = useRef(null);
  const locSub        = useRef(null);
  const mapReady      = useRef(false);
  // Store the first real GPS fix so onMapReady can use it even if state hasn't propagated yet
  const firstFixRef   = useRef(null);

  const [pasCoord,     setPasCoord]     = useState(null);
  const [usingDefault, setUsingDefault] = useState(false);
  const [liveBuses,    setLiveBuses]    = useState([]);
  const [nearRoutes,   setNearRoutes]   = useState([]);
  const [booking,      setBooking]      = useState(null);
  const [locReady,     setLocReady]     = useState(false); // GPS fix obtained

  // ── Data load ─────────────────────────────────────────────────────────────
  const load = useCallback(async () => {
    try {
      const [busRes, bkRes, routeRes] = await Promise.all([
        passengerApi.getLiveBuses().catch(() => null),
        passengerApi.myBookings().catch(() => null),
        passengerApi.getRoutes().catch(() => null),
      ]);
      if (busRes?.data) setLiveBuses((busRes.data ?? []).filter(b => b.active_trip_id));
      if (bkRes?.data?.length) {
        setBooking(bkRes.data.find(b => b.status === 'confirmed' || b.status === 'pending') || null);
      }
      if (routeRes?.data) setNearRoutes(routeRes.data.slice(0, 5));
    } catch (_) {}
  }, []);

  useEffect(() => {
    load();
    // Auto-refresh live buses every 5 seconds so bus appears without manual refresh
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  // ── Push buses onto map ───────────────────────────────────────────────────
  const pushBusesToMap = useCallback((buses) => {
    buses.forEach(b => {
      const lat = Number(b.latitude), lng = Number(b.longitude);
      if (inPakistan(lat, lng)) mapRef.current?.updateBus(b.bus_id, lat, lng);
    });
  }, []);

  useEffect(() => {
    if (mapReady.current && liveBuses.length) pushBusesToMap(liveBuses);
  }, [liveBuses]);

  // ── Apply location to map immediately ─────────────────────────────────────
  const applyLocationToMap = useCallback((latitude, longitude, centerMap = false) => {
    mapRef.current?.setPassenger(latitude, longitude);
    if (centerMap) {
      mapRef.current?.zoomTo(latitude, longitude, 16);
    }
  }, []);

  // ── Passenger GPS — InDrive style: get first fix immediately ─────────────
  useEffect(() => {
    (async () => {
      try {
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status !== 'granted') {
          _useDefault();
          return;
        }
        const enabled = await Location.hasServicesEnabledAsync();
        if (!enabled) {
          _useDefault();
          return;
        }

        // Step 1: Get first fix immediately (fast, like InDrive opening animation)
        try {
          const firstFix = await Location.getCurrentPositionAsync({
            accuracy: Location.Accuracy.Balanced,
          });
          const { latitude, longitude } = firstFix.coords;
          if (inPakistan(latitude, longitude)) {
            firstFixRef.current = { latitude, longitude };
            setPasCoord({ latitude, longitude });
            setUsingDefault(false);
            setLocReady(true);
            // If map is already ready, center on user right now
            if (mapReady.current) {
              applyLocationToMap(latitude, longitude, true);
            }
          } else {
            _useDefault();
          }
        } catch (_) {
          _useDefault();
        }

        // Step 2: Keep watching for real-time movement updates
        locSub.current = await Location.watchPositionAsync(
          {
            accuracy: Location.Accuracy.High,
            timeInterval: 3000,      // update every 3 seconds
            distanceInterval: 10,    // or every 10 meters moved
          },
          (pos) => {
            const { latitude, longitude } = pos.coords;
            if (inPakistan(latitude, longitude)) {
              firstFixRef.current = { latitude, longitude };
              setPasCoord({ latitude, longitude });
              setUsingDefault(false);
              setLocReady(true);
              if (mapReady.current) {
                // Smoothly move "You" pin — don't re-center after first use
                mapRef.current?.setPassenger(latitude, longitude);
              }
            }
          }
        );
      } catch (_) {
        _useDefault();
      }
    })();
    return () => locSub.current?.remove();
  }, []);

  const _useDefault = () => {
    setUsingDefault(true);
    setPasCoord(JHANG_UNI);
    firstFixRef.current = JHANG_UNI;
    if (mapReady.current) applyLocationToMap(JHANG_UNI.latitude, JHANG_UNI.longitude, true);
  };

  // ── Map ready — center on real GPS location, just like InDrive ────────────
  const onMapReady = useCallback(() => {
    mapReady.current = true;

    // Use the most recent GPS fix (or Jhang University fallback)
    const loc = firstFixRef.current || pasCoord || JHANG_UNI;

    // Center map on user's actual location at street level
    mapRef.current?.zoomTo(loc.latitude, loc.longitude, 16);
    mapRef.current?.setPassenger(loc.latitude, loc.longitude);

    // Show any live buses already loaded
    pushBusesToMap(liveBuses);
  }, [pasCoord, liveBuses]);

  const centerOnMe = () => {
    const loc = firstFixRef.current || pasCoord || JHANG_UNI;
    mapRef.current?.zoomTo(loc.latitude, loc.longitude, 16);
  };

  const firstName = user?.full_name?.split(' ')[0] ?? 'there';

  return (
    <View style={s.root}>
      <StatusBar barStyle="dark-content" backgroundColor="transparent" translucent />

      {/* ── Full-screen map — fills the entire screen ──────────────────────── */}
      <LeafletMap ref={mapRef} style={s.map} onReady={onMapReady} />

      {/* ── Top greeting bar — floats over map ────────────────────────────── */}
      <SafeAreaView pointerEvents="box-none" style={s.topOverlay}>
        <View style={s.topBar}>
          <View style={{ flex: 1 }}>
            <Text style={s.greet}>{greeting()}, {firstName} 👋</Text>
            <Text style={s.sub}>SmartBus Jhang</Text>
          </View>
          <TouchableOpacity style={s.avatarBtn} onPress={logout}>
            <Text style={s.avatarTxt}>{(firstName[0] ?? 'U').toUpperCase()}</Text>
          </TouchableOpacity>
        </View>

        {usingDefault && (
          <View style={s.locNote}>
            <Text style={s.locNoteIco}>📍</Text>
            <Text style={s.locNoteTxt}>
              Showing Jhang University as your location. Enable GPS for exact location.
            </Text>
          </View>
        )}
      </SafeAreaView>

      {/* ── Centre-on-me FAB — floats above the sheet ─────────────────────── */}
      <TouchableOpacity style={[s.locFab, { bottom: FAB_BOTTOM }]} onPress={centerOnMe}>
        <Text style={s.locFabIcon}>🎯</Text>
      </TouchableOpacity>

      {/* ── Bottom sheet — absolutely pinned to bottom, fixed height ──────── */}
      <View style={[s.sheet, { height: SHEET_H }]}>
        <View style={s.handle} />

        <ScrollView showsVerticalScrollIndicator={false} bounces={false}>
          {/* Live status row */}
          <View style={s.liveRow}>
            <View style={[s.livePill, { backgroundColor: liveBuses.length ? '#E8F5E9' : '#FFF8E1' }]}>
              <View style={[s.liveDot, { backgroundColor: liveBuses.length ? COLORS.success : '#FFA000' }]} />
              <Text style={[s.liveTxt, { color: liveBuses.length ? COLORS.success : '#F57C00' }]}>
                {liveBuses.length > 0
                  ? `${liveBuses.length} bus${liveBuses.length > 1 ? 'es' : ''} running now`
                  : 'No buses running currently'}
              </Text>
            </View>
            <TouchableOpacity onPress={load} style={s.refreshBtn}>
              <Text style={s.refreshIco}>↺</Text>
            </TouchableOpacity>
          </View>

          {/* Active booking banner */}
          {booking && (
            <TouchableOpacity style={s.bookingCard} onPress={() => navigation.navigate('MyTripsTab')}>
              <Text style={s.bookingIco}>🎫</Text>
              <View style={{ flex: 1 }}>
                <Text style={s.bookingTitle}>Active Booking — Seat #{booking.seat_number}</Text>
                <Text style={s.bookingDate}>Travel date: {booking.booking_date}</Text>
              </View>
              <Text style={s.bookingArrow}>›</Text>
            </TouchableOpacity>
          )}

          {/* Find a bus CTA */}
          <TouchableOpacity style={s.findBtn} onPress={() => navigation.navigate('RoutesTab')}>
            <Text style={s.findIco}>🔍</Text>
            <Text style={s.findTxt}>Find a Bus</Text>
          </TouchableOpacity>

          {/* Route chips */}
          {nearRoutes.length > 0 && (
            <>
              <Text style={s.sectionHd}>Available Routes in Jhang</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                {nearRoutes.map(r => (
                  <TouchableOpacity
                    key={r.id}
                    style={s.routeChip}
                    onPress={() => navigation.navigate('RouteDetail', { routeId: r.id, routeData: r })}
                  >
                    <Text style={s.routeChipIco}>🗺</Text>
                    <Text style={s.routeChipName} numberOfLines={2}>{r.route_name}</Text>
                    <Text style={s.routeChipPath} numberOfLines={1}>{r.start_point}</Text>
                    <Text style={s.routeChipArrow}>→</Text>
                    <Text style={s.routeChipPath} numberOfLines={1}>{r.end_point}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            </>
          )}

          {/* Live buses strip */}
          {liveBuses.length > 0 && (
            <>
              <Text style={[s.sectionHd, { marginTop: 10 }]}>Live Buses Now</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                {liveBuses.map(b => (
                  <TouchableOpacity
                    key={b.bus_id}
                    style={s.busChip}
                    onPress={() => navigation.navigate('LiveMap', {
                      tripId: b.active_trip_id, busId: b.bus_id, routeId: b.route_id,
                      busNumber: b.bus_number, driverName: b.driver_name, routeName: b.route_name,
                    })}
                  >
                    <Text style={s.busChipIco}>🚌</Text>
                    <Text style={s.busChipNum}>{b.bus_number}</Text>
                    <Text style={s.busChipRoute} numberOfLines={1}>{b.route_name}</Text>
                    <Text style={s.busChipSeats}>{b.available_seats} seats free</Text>
                    <View style={s.trackPill}><Text style={s.trackPillTxt}>Track →</Text></View>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            </>
          )}

          {/* Bottom spacer so last item isn't clipped */}
          <View style={{ height: 12 }} />
        </ScrollView>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#f0ede8' },
  // Map fills the ENTIRE screen (sheet floats on top via absolute positioning)
  map: { flex: 1 },

  // ── Top overlay ──────────────────────────────────────────────────────────
  topOverlay: {
    position: 'absolute', top: 0, left: 0, right: 0,
    zIndex: 10,
  },
  topBar: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    marginHorizontal: 14, marginTop: 50,
    backgroundColor: '#fff', borderRadius: 18,
    paddingHorizontal: 16, paddingVertical: 12,
    elevation: 6, shadowColor: '#000', shadowOpacity: 0.12,
    shadowRadius: 10, shadowOffset: { width: 0, height: 3 },
  },
  greet:     { fontSize: 16, fontWeight: '800', color: COLORS.text },
  sub:       { fontSize: 12, color: COLORS.textLight, marginTop: 1 },
  avatarBtn: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: COLORS.primary, alignItems: 'center', justifyContent: 'center',
    marginLeft: 10,
  },
  avatarTxt: { color: '#fff', fontSize: 17, fontWeight: '800' },

  locNote: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    backgroundColor: 'rgba(255,248,225,0.97)',
    marginHorizontal: 14, marginTop: 8,
    borderRadius: 12, paddingHorizontal: 12, paddingVertical: 8,
    elevation: 4,
  },
  locNoteIco: { fontSize: 16 },
  locNoteTxt: { flex: 1, fontSize: 11, color: '#E65100', lineHeight: 16 },

  // ── FAB ──────────────────────────────────────────────────────────────────
  locFab: {
    position: 'absolute', right: 14,
    backgroundColor: '#fff', width: 48, height: 48, borderRadius: 24,
    alignItems: 'center', justifyContent: 'center',
    elevation: 6, shadowColor: '#000', shadowOpacity: 0.15,
    shadowRadius: 8, shadowOffset: { width: 0, height: 3 },
    zIndex: 10,
  },
  locFabIcon: { fontSize: 22 },

  // ── Bottom sheet — ABSOLUTE so map is always full screen ─────────────────
  sheet: {
    position: 'absolute', bottom: 0, left: 0, right: 0,
    backgroundColor: '#fff',
    borderTopLeftRadius: 28, borderTopRightRadius: 28,
    paddingHorizontal: 18, paddingTop: 10,
    elevation: 20, shadowColor: '#000', shadowOpacity: 0.18,
    shadowRadius: 18, shadowOffset: { width: 0, height: -6 },
    zIndex: 9,
  },
  handle: {
    width: 42, height: 4, borderRadius: 2,
    backgroundColor: '#E0E0E0', alignSelf: 'center', marginBottom: 12,
  },

  // ── Sheet content ─────────────────────────────────────────────────────────
  liveRow:    { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 },
  livePill:   { flexDirection: 'row', alignItems: 'center', gap: 6, borderRadius: 20, paddingHorizontal: 12, paddingVertical: 6 },
  liveDot:    { width: 8, height: 8, borderRadius: 4 },
  liveTxt:    { fontSize: 13, fontWeight: '700' },
  refreshBtn: { padding: 6 },
  refreshIco: { fontSize: 20, color: COLORS.textLight },

  bookingCard:  { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: '#EEF2FF', borderRadius: 14, padding: 12, marginBottom: 10 },
  bookingIco:   { fontSize: 22 },
  bookingTitle: { fontSize: 13, fontWeight: '700', color: '#3949AB' },
  bookingDate:  { fontSize: 11, color: COLORS.textLight, marginTop: 2 },
  bookingArrow: { fontSize: 22, color: '#3949AB', fontWeight: '700' },

  findBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 8, backgroundColor: COLORS.primary, borderRadius: 16,
    paddingVertical: 14, marginBottom: 12,
  },
  findIco: { fontSize: 18 },
  findTxt: { color: '#fff', fontSize: 16, fontWeight: '800' },

  sectionHd: { fontSize: 13, fontWeight: '700', color: COLORS.text, marginBottom: 8 },

  routeChip:      { backgroundColor: '#F8F9FA', borderRadius: 14, padding: 10, marginRight: 10, width: 140, borderWidth: 1, borderColor: '#EEEEEE' },
  routeChipIco:   { fontSize: 20, marginBottom: 4 },
  routeChipName:  { fontSize: 12, fontWeight: '800', color: COLORS.text, marginBottom: 3 },
  routeChipPath:  { fontSize: 10, color: COLORS.textLight },
  routeChipArrow: { fontSize: 10, color: COLORS.textLight, marginVertical: 1 },

  busChip:      { backgroundColor: '#F8F9FA', borderRadius: 14, padding: 10, marginRight: 10, minWidth: 130, borderWidth: 1, borderColor: '#EEEEEE' },
  busChipIco:   { fontSize: 24, marginBottom: 3 },
  busChipNum:   { fontSize: 14, fontWeight: '800', color: COLORS.text },
  busChipRoute: { fontSize: 10, color: COLORS.textLight, marginTop: 2, maxWidth: 120 },
  busChipSeats: { fontSize: 11, fontWeight: '600', color: COLORS.success, marginTop: 3 },
  trackPill:    { backgroundColor: COLORS.primary, borderRadius: 7, paddingHorizontal: 7, paddingVertical: 3, alignSelf: 'flex-start', marginTop: 5 },
  trackPillTxt: { fontSize: 10, fontWeight: '700', color: '#fff' },
});
