import { useState, useEffect, useRef, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, Alert, SafeAreaView,
  RefreshControl, Switch, TouchableOpacity, Platform,
} from 'react-native';
import * as Location from 'expo-location';
import { useAuth } from '../../context/AuthContext';
import { driverApi } from '../../api/index';
import { Btn, Input, Card, SectionTitle, Badge, Row, showError, statusColor } from '../../components/UI';
import { COLORS } from '../../config';

const C = COLORS.secondary;

// Jhang University — used as demo GPS for emulator testing
const JHANG_DEMO_COORDS = [
  { latitude: 31.2693, longitude: 72.3210, label: 'University of Jhang' },
  { latitude: 31.2741, longitude: 72.3265, label: 'Clock Tower Chowk' },
  { latitude: 31.2653, longitude: 72.3101, label: 'Gol Bagh' },
  { latitude: 31.2599, longitude: 72.3181, label: 'Civil Hospital' },
  { latitude: 31.2812, longitude: 72.3356, label: 'Jhang Sadar' },
];

function inPakistan(lat, lng) {
  return lat >= 23.5 && lat <= 37.5 && lng >= 60.8 && lng <= 77.8;
}

function fmtDuration(sec) {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  return h > 0 ? `${h}h ${m}m ${s}s` : `${m}m ${s}s`;
}

export default function DriverDashboard() {
  const { user, logout } = useAuth();
  const [profile,    setProfile]  = useState(null);
  const [activeTrip, setTrip]     = useState(null);
  const [refreshing, setRefresh]  = useState(false);
  const [busy,       setBusy]     = useState('');

  // GPS
  const [gpsEnabled,  setGpsEnabled]  = useState(false);
  const [demoMode,    setDemoMode]    = useState(false);
  const [demoIndex,   setDemoIndex]   = useState(0);
  const [currentPos,  setCurrentPos]  = useState(null);
  const [gpsError,    setGpsError]    = useState('');
  const [postCount,   setPostCount]   = useState(0);
  const gpsInterval  = useRef(null);
  const demoInterval = useRef(null);

  // Trip timer
  const [tripSeconds, setTripSec] = useState(0);
  const timerRef = useRef(null);

  // Forms (store IDs internally, show names to user)
  const [tripForm, setTripForm] = useState({ bus_id: '', route_id: '' });
  const [seats,    setSeats]    = useState('');
  const [issue,    setIssue]    = useState({ trip_id: '', issue_type: 'breakdown', description: '', severity: 'high' });
  const [notif,    setNotif]    = useState({ type: 'delay', title: '', message: '', trip_id: '' });

  // Single source of truth for GPS — updated immediately, no React timing issues
  const gpsParamsRef = useRef({ tripId: null, busId: null });

  // Keep these in sync too for UI display only
  const activeTripRef = useRef(null);
  useEffect(() => { activeTripRef.current = activeTrip; }, [activeTrip]);

  const load = useCallback(async () => {
    try {
      const [pRes, tripRes] = await Promise.all([
        driverApi.getProfile().catch(() => null),
        driverApi.getActiveTrip().catch(() => null),
      ]);

      let busId = '';
      if (pRes?.data) {
        const p = pRes.data;
        setProfile(p);
        busId = p.assigned_bus_id || '';
        setTripForm(f => ({
          bus_id:   f.bus_id   || busId,
          route_id: f.route_id || p.bus_route_id || '',
        }));
      }

      const trip = tripRes?.data ?? null;
      if (trip && trip.id) {
        setTrip(trip);
        const started = new Date(trip.started_at).getTime();
        setTripSec(Math.max(0, Math.floor((Date.now() - started) / 1000)));
        setIssue(i => ({ ...i, trip_id: trip.id }));
        setNotif(n => ({ ...n, trip_id: trip.id }));

        // Immediately wire GPS params — no React state delay
        const effectiveBusId = trip.bus_id || busId;
        if (effectiveBusId) {
          gpsParamsRef.current = { tripId: trip.id, busId: effectiveBusId };
          // Auto-start GPS for existing active trip (app reloaded or resumed)
          setTimeout(autoStartGPS, 1000);
        }
      } else {
        setTrip(null);
        gpsParamsRef.current = { tripId: null, busId: null };
      }
    } catch (_) {}
  }, []);

  useEffect(() => { load(); }, [load]);

  // Trip duration counter
  useEffect(() => {
    if (activeTrip) {
      timerRef.current = setInterval(() => setTripSec(s => s + 1), 1000);
    } else {
      clearInterval(timerRef.current);
      setTripSec(0);
    }
    return () => clearInterval(timerRef.current);
  }, [activeTrip?.id]);

  // GPS on/off
  useEffect(() => {
    if (gpsEnabled) startGPS();
    else            stopGPS();
    return () => stopGPS();
  }, [gpsEnabled]);

  // Demo mode on/off
  useEffect(() => {
    if (demoMode) startDemo();
    else          stopDemo();
    return () => stopDemo();
  }, [demoMode]);

  // Direct GPS posting — reads from gpsParamsRef, no React closure issues
  const postGPS = useCallback(async (coords) => {
    const { tripId, busId } = gpsParamsRef.current;
    if (!tripId || !busId) return;
    try {
      await driverApi.postLocation({
        bus_id:      busId,
        trip_id:     tripId,
        latitude:    coords.latitude,
        longitude:   coords.longitude,
        speed_kmh:   coords.speed != null ? Math.max(0, coords.speed * 3.6) : 0,
        heading_deg: coords.heading ?? 0,
      });
    } catch (_) {}
  }, []);

  const startGPS = async () => {
    setGpsError('');
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') {
      setGpsError('Location permission denied. Enable in Settings > Apps > SmartBus > Permissions.');
      setGpsEnabled(false);
      return;
    }
    const enabled = await Location.hasServicesEnabledAsync();
    if (!enabled) {
      setGpsError('GPS is OFF. Enable Location Services in Settings.');
      setGpsEnabled(false);
      return;
    }
    try {
      const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      const { latitude, longitude } = pos.coords;
      if (!inPakistan(latitude, longitude)) {
        setGpsError('Real GPS not in Pakistan (emulator detected). Use "Demo Mode" button below to simulate Jhang location.');
        setGpsEnabled(false);
        return;
      }
      setCurrentPos(pos.coords);
      postGPS(pos.coords);
    } catch (_) {
      setGpsError('GPS signal unavailable. Use "Demo Mode" button below for emulator testing.');
      setGpsEnabled(false);
      return;
    }
    gpsInterval.current = setInterval(async () => {
      try {
        const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
        const { latitude, longitude } = pos.coords;
        if (!inPakistan(latitude, longitude)) return;
        setCurrentPos(pos.coords);
        await postGPS(pos.coords);
        setPostCount(c => c + 1);
      } catch (_) {}
    }, 4000);
  };

  const stopGPS = () => {
    clearInterval(gpsInterval.current);
    gpsInterval.current = null;
  };

  // Demo mode: cycles through Jhang waypoints every 3 seconds
  // Does NOT check activeTripRef — uses gpsParamsRef directly (no timing issues)
  const startDemo = () => {
    let idx = 0;
    const tick = async () => {
      const { tripId, busId } = gpsParamsRef.current;
      // Safety check inline — no stale ref issues
      if (!tripId || !busId) return;
      const coord = JHANG_DEMO_COORDS[idx % JHANG_DEMO_COORDS.length];
      setDemoIndex(idx % JHANG_DEMO_COORDS.length);
      setCurrentPos({ latitude: coord.latitude, longitude: coord.longitude, speed: 25 / 3.6, heading: 45 });
      try {
        await driverApi.postLocation({
          bus_id:      busId,
          trip_id:     tripId,
          latitude:    coord.latitude,
          longitude:   coord.longitude,
          speed_kmh:   25,
          heading_deg: 45,
        });
        setPostCount(c => c + 1);
      } catch (_) {}
      idx++;
    };
    tick();  // immediate first post
    demoInterval.current = setInterval(tick, 3000);
  };

  const stopDemo = () => {
    clearInterval(demoInterval.current);
    demoInterval.current = null;
  };

  const toggleDemo = () => {
    if (!activeTrip) { Alert.alert('Start a trip first', 'You need an active trip before enabling GPS.'); return; }
    if (!demoMode) {
      setGpsEnabled(false);
      setGpsError('');
    }
    setDemoMode(v => !v);
  };

  const onRefresh = async () => { setRefresh(true); await load(); setRefresh(false); };

  // Auto-start GPS: tries real GPS → falls back to demo (emulator-safe)
  // Not wrapped in useCallback — always reads fresh state
  async function autoStartGPS() {
    setGpsError('');
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status === 'granted') {
        const enabled = await Location.hasServicesEnabledAsync();
        if (enabled) {
          const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
          const { latitude, longitude } = pos.coords;
          if (inPakistan(latitude, longitude)) {
            setGpsEnabled(true);   // real device in Pakistan
            return;
          }
        }
      }
    } catch (_) {}
    // Emulator or no real GPS — use demo Jhang waypoints
    setDemoMode(true);
  }

  const startTrip = async () => {
    const busId   = tripForm.bus_id;
    const routeId = tripForm.route_id;
    if (!busId || !routeId) {
      return Alert.alert('No Bus Assigned', 'You have no active bus or route assigned.\n\nContact your admin to assign a bus and route to your account.');
    }
    setBusy('start');
    try {
      const res = await driverApi.startTrip({ bus_id: busId, route_id: routeId });
      // Set GPS params IMMEDIATELY — before any async delay
      gpsParamsRef.current = { tripId: res.data.id, busId: res.data.bus_id || busId };
      setTrip(res.data);
      setTripSec(0);
      setIssue(i => ({ ...i, trip_id: res.data.id }));
      setNotif(n => ({ ...n, trip_id: res.data.id }));
      // Short delay so React re-renders first, then start GPS
      setTimeout(autoStartGPS, 400);
      Alert.alert('Trip Started!', 'GPS tracking is now active.\nPassengers can see your bus on the live map.');
    } catch (e) { showError(e); }
    finally { setBusy(''); }
  };

  const updateTripStatus = async (status) => {
    if (!activeTrip) return;
    setBusy('status');
    try {
      await driverApi.updateStatus(activeTrip.id, { status });
      Alert.alert('Status Updated', `Trip marked as: ${status}`);
    } catch (e) { showError(e); }
    finally { setBusy(''); }
  };

  const endTrip = () => {
    Alert.alert('End Trip?', 'GPS will stop and trip will be closed.', [
      { text: 'Cancel' },
      { text: 'End Trip', style: 'destructive', onPress: async () => {
        setGpsEnabled(false);
        setDemoMode(false);
        setBusy('end');
        try {
          await driverApi.endTrip(activeTrip.id);
          gpsParamsRef.current = { tripId: null, busId: null };
          setTrip(null);
          setCurrentPos(null);
          setPostCount(0);
          Alert.alert('Trip Ended', `Duration: ${fmtDuration(tripSeconds)}`);
        } catch (e) { showError(e); }
        finally { setBusy(''); }
      }},
    ]);
  };

  const updateSeats = async () => {
    if (!activeTrip || !seats) return;
    setBusy('seats');
    try {
      await driverApi.updateSeats(activeTrip.id, { available_seats: Number(seats) });
      Alert.alert('Updated', 'Seat count updated.');
      setSeats('');
    } catch (e) { showError(e); }
    finally { setBusy(''); }
  };

  const reportIssue = async () => {
    if (!issue.description) return Alert.alert('Missing', 'Describe the issue first.');
    setBusy('issue');
    try {
      await driverApi.reportIssue(issue);
      Alert.alert('Reported', 'Issue reported to admin.');
      setIssue(i => ({ ...i, description: '' }));
    } catch (e) { showError(e); }
    finally { setBusy(''); }
  };

  const sendNotif = async () => {
    if (!notif.title || !notif.message) return Alert.alert('Missing', 'Fill title and message.');
    setBusy('notif');
    try {
      await driverApi.sendNotif(notif);
      Alert.alert('Sent', 'Passengers have been notified.');
      setNotif(n => ({ ...n, title: '', message: '' }));
    } catch (e) { showError(e); }
    finally { setBusy(''); }
  };

  const isGpsActive   = gpsEnabled || demoMode;
  const busAssigned   = !!(profile?.bus_number || tripForm.bus_id);
  const routeAssigned = !!(profile?.route_name || tripForm.route_id);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: COLORS.bg }}>
      <ScrollView
        contentContainerStyle={{ padding: 16, paddingBottom: 50 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {/* Header */}
        <Card style={{ backgroundColor: C }}>
          <Text style={st.hName}>🚌 {user?.full_name || 'Driver'}</Text>
          <Text style={st.hSub}>{profile?.driver_code || user?.email}</Text>
          {busAssigned && (
            <Text style={st.hSub}>
              Bus: {profile?.bus_number ?? '—'}  ·  Route: {profile?.route_name ?? '—'}
            </Text>
          )}
          {profile?.avg_rating != null && (
            <Text style={st.hSub}>
              {Number(profile.avg_rating).toFixed(1)} ⭐  ·  {profile.total_trips} trips completed
            </Text>
          )}
          <Badge label={profile?.status || 'offline'} color={statusColor(profile?.status)} style={{ marginTop: 8, alignSelf: 'flex-start' }} />
          <Btn title="Logout" color="rgba(255,255,255,0.25)" onPress={logout} style={{ marginTop: 10 }} />
        </Card>

        {/* Active / Start Trip */}
        {activeTrip ? (
          <>
            <SectionTitle>Active Trip</SectionTitle>
            <Card style={{ borderLeftWidth: 4, borderLeftColor: COLORS.success }}>
              <Row style={{ justifyContent: 'space-between', alignItems: 'center' }}>
                <Badge label="LIVE" color={COLORS.success} />
                <Text style={st.timer}>{fmtDuration(tripSeconds)}</Text>
              </Row>
              <Text style={st.info}>Bus: {profile?.bus_number ?? '—'}</Text>
              <Text style={st.info}>Route: {profile?.route_name ?? '—'}</Text>
              {activeTrip.total_passengers != null &&
                <Text style={st.info}>{activeTrip.total_passengers} passengers on board</Text>}

              {/* Trip status update */}
              <Text style={{ fontSize: 12, color: COLORS.textLight, marginTop: 12, marginBottom: 6 }}>Update Trip Status</Text>
              <Row style={{ gap: 6 }}>
                {[
                  { label: '✅ On Time', val: 'active',    color: COLORS.success },
                  { label: '⏰ Delayed', val: 'delayed',   color: '#FB8C00' },
                ].map(opt => (
                  <TouchableOpacity
                    key={opt.val}
                    onPress={() => updateTripStatus(opt.val)}
                    style={{ flex: 1, borderWidth: 1.5, borderColor: opt.color, borderRadius: 10, paddingVertical: 8, alignItems: 'center' }}
                  >
                    <Text style={{ fontSize: 12, fontWeight: '700', color: opt.color }}>{opt.label}</Text>
                  </TouchableOpacity>
                ))}
              </Row>

              <Btn title="End Trip" color={COLORS.danger} onPress={endTrip} loading={busy === 'end'} style={{ marginTop: 10 }} />
            </Card>
          </>
        ) : (
          <>
            <SectionTitle>Start Trip</SectionTitle>
            {busAssigned && routeAssigned ? (
              <Card>
                <View style={st.assignRow}>
                  <Text style={st.assignIcon}>🚌</Text>
                  <View style={{ flex: 1 }}>
                    <Text style={st.assignLabel}>Bus</Text>
                    <Text style={st.assignVal}>{profile?.bus_number ?? 'Assigned'}</Text>
                  </View>
                </View>
                <View style={[st.assignRow, { marginTop: 10 }]}>
                  <Text style={st.assignIcon}>🗺</Text>
                  <View style={{ flex: 1 }}>
                    <Text style={st.assignLabel}>Route</Text>
                    <Text style={st.assignVal}>{profile?.route_name ?? 'Assigned'}</Text>
                  </View>
                </View>
                <Btn title="Start Trip" color={C} onPress={startTrip} loading={busy === 'start'} style={{ marginTop: 14 }} />
              </Card>
            ) : (
              <Card>
                <Text style={{ color: COLORS.warning, fontSize: 13, textAlign: 'center', paddingVertical: 8 }}>
                  No bus or route assigned yet. Please contact the admin.
                </Text>
              </Card>
            )}
          </>
        )}

        {/* GPS Tracking */}
        <SectionTitle>GPS Tracking</SectionTitle>
        <Card>
          {/* Status banner */}
          {!activeTrip ? (
            <View style={st.gpsWaiting}>
              <Text style={{ fontSize: 22 }}>📡</Text>
              <View style={{ flex: 1, marginLeft: 10 }}>
                <Text style={{ fontSize: 14, fontWeight: '700', color: COLORS.textLight }}>GPS inactive</Text>
                <Text style={{ fontSize: 12, color: COLORS.textLight, marginTop: 2 }}>Start a trip to broadcast your location</Text>
              </View>
            </View>
          ) : isGpsActive ? (
            <View style={[st.gpsLive, demoMode && { backgroundColor: '#FFF3E0', borderColor: '#FF9800' }]}>
              <View style={[st.gpsPulse, demoMode && { backgroundColor: '#FF9800' }]} />
              <View style={{ flex: 1, marginLeft: 10 }}>
                <Text style={{ fontSize: 14, fontWeight: '800', color: demoMode ? '#E65100' : COLORS.success }}>
                  {demoMode ? 'Demo GPS Active' : 'Live GPS Active'}
                </Text>
                {currentPos && (
                  <Text style={{ fontSize: 12, color: COLORS.textLight, marginTop: 2 }}>
                    {demoMode ? JHANG_DEMO_COORDS[demoIndex]?.label : `${currentPos.latitude.toFixed(5)}, ${currentPos.longitude.toFixed(5)}`}
                  </Text>
                )}
                <Text style={{ fontSize: 11, color: COLORS.textLight, marginTop: 2 }}>
                  {postCount} updates sent · Passengers see your bus live
                </Text>
              </View>
              <TouchableOpacity
                onPress={() => { setGpsEnabled(false); setDemoMode(false); }}
                style={{ padding: 6 }}
              >
                <Text style={{ fontSize: 11, color: COLORS.danger, fontWeight: '700' }}>Stop</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <View style={st.gpsOff}>
              <Text style={{ fontSize: 14, fontWeight: '700', color: COLORS.warning }}>GPS Stopped</Text>
              <Text style={{ fontSize: 12, color: COLORS.textLight, marginTop: 2 }}>Passengers cannot see your location</Text>
            </View>
          )}

          {gpsError ? <Text style={st.gpsErr}>{gpsError}</Text> : null}

          {/* Manual controls — only visible during active trip */}
          {activeTrip && (
            <Row style={{ gap: 8, marginTop: 12 }}>
              <TouchableOpacity
                onPress={() => { setDemoMode(false); setGpsEnabled(v => !v); }}
                style={[st.gpsBtn, gpsEnabled && { backgroundColor: COLORS.success }]}
                activeOpacity={0.8}
              >
                <Text style={[st.gpsBtnTxt, gpsEnabled && { color: '#fff' }]}>
                  {gpsEnabled ? '📡 Real GPS On' : '📡 Real GPS'}
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                onPress={toggleDemo}
                style={[st.gpsBtn, demoMode && { backgroundColor: '#FF9800' }]}
                activeOpacity={0.8}
              >
                <Text style={[st.gpsBtnTxt, demoMode && { color: '#fff' }]}>
                  {demoMode ? '📍 Demo On' : '📍 Demo GPS'}
                </Text>
              </TouchableOpacity>
            </Row>
          )}
        </Card>

        {/* Update Seats */}
        {activeTrip && (
          <>
            <SectionTitle>Update Available Seats</SectionTitle>
            <Card>
              <Row style={{ gap: 8 }}>
                <View style={{ flex: 1 }}>
                  <Input label="Available Seats" value={seats} onChangeText={setSeats} keyboardType="numeric" placeholder="e.g. 18" />
                </View>
                <Btn title="Update" color={C} onPress={updateSeats} loading={busy === 'seats'} style={{ marginTop: 22, minWidth: 90 }} />
              </Row>
            </Card>
          </>
        )}

        {/* Report Issue */}
        <SectionTitle>Report Issue</SectionTitle>
        <Card>
          <Input label="Issue Type" value={issue.issue_type} onChangeText={v => setIssue(i => ({ ...i, issue_type: v }))} placeholder="breakdown / delay / accident / emergency" autoCapitalize="none" />
          <Input label="Severity"   value={issue.severity}   onChangeText={v => setIssue(i => ({ ...i, severity: v }))}   placeholder="low / medium / high / critical" autoCapitalize="none" />
          <Input label="Description" value={issue.description} onChangeText={v => setIssue(i => ({ ...i, description: v }))} placeholder="Describe the problem…" multiline />
          <Btn title="Report Issue" color={COLORS.warning} onPress={reportIssue} loading={busy === 'issue'} />
        </Card>

        {/* Send Notification */}
        <SectionTitle>Notify Passengers</SectionTitle>
        <Card>
          <Input label="Type"    value={notif.type}    onChangeText={v => setNotif(n => ({ ...n, type: v }))}    placeholder="delay / arriving / emergency" autoCapitalize="none" />
          <Input label="Title"   value={notif.title}   onChangeText={v => setNotif(n => ({ ...n, title: v }))}   placeholder="e.g. Bus Delayed 10 min" />
          <Input label="Message" value={notif.message} onChangeText={v => setNotif(n => ({ ...n, message: v }))} placeholder="Details for passengers…" multiline />
          <Btn title="Send to All Passengers" color={C} onPress={sendNotif} loading={busy === 'notif'} />
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  hName:    { fontSize: 20, fontWeight: '800', color: '#fff' },
  hSub:     { color: 'rgba(255,255,255,0.8)', marginTop: 3, fontSize: 13 },
  timer:    { fontSize: 18, fontWeight: '800', color: COLORS.success },
  info:     { fontSize: 13, color: COLORS.textLight, marginTop: 4 },

  assignRow:  { flexDirection: 'row', alignItems: 'center', gap: 10 },
  assignIcon: { fontSize: 26 },
  assignLabel:{ fontSize: 11, color: COLORS.textLight, textTransform: 'uppercase', letterSpacing: 0.5 },
  assignVal:  { fontSize: 15, fontWeight: '700', color: COLORS.text, marginTop: 1 },

  gpsErr:    { color: COLORS.danger, fontSize: 12, marginTop: 8, lineHeight: 18 },

  gpsWaiting: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#F5F5F5', borderRadius: 12, padding: 12 },
  gpsLive:    { flexDirection: 'row', alignItems: 'center', backgroundColor: '#E8F5E9', borderRadius: 12, padding: 12, borderWidth: 1, borderColor: COLORS.success },
  gpsOff:     { backgroundColor: '#FFF8E1', borderRadius: 12, padding: 12 },
  gpsPulse:   { width: 12, height: 12, borderRadius: 6, backgroundColor: COLORS.success },

  gpsBtn:    { flex: 1, borderWidth: 1.5, borderColor: COLORS.primary, borderRadius: 10, paddingVertical: 9, alignItems: 'center' },
  gpsBtnTxt: { fontSize: 12, fontWeight: '700', color: COLORS.primary },
});
