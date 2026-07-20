import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, Alert,
  SafeAreaView, RefreshControl, TouchableOpacity, ActivityIndicator,
} from 'react-native';
import { useAuth }   from '../../context/AuthContext';
import { parentApi } from '../../api/index';
import { Btn, Input, Card, showError } from '../../components/UI';
import LeafletMap    from '../../components/LeafletMap';
import { COLORS }   from '../../config';

const C = '#E65100';   // parent brand colour

// ─── tiny helpers ────────────────────────────────────────────────────────────
const Badge = ({ label, color }) => (
  <View style={[bs.badge, { backgroundColor: color || COLORS.textLight }]}>
    <Text style={bs.badgeText}>{label}</Text>
  </View>
);

const SectionTitle = ({ children }) => (
  <Text style={bs.sectionTitle}>{children}</Text>
);

// ─── component ───────────────────────────────────────────────────────────────
export default function ParentDashboard() {
  const { user, logout } = useAuth();

  const [children,  setChildren]  = useState([]);
  const [notifs,    setNotifs]    = useState([]);
  const [refreshing,setRefreshing]= useState(false);
  const [linkBusy,  setLinkBusy]  = useState(false);
  const [link, setLink]           = useState({ university_id: '', relationship_type: 'father' });

  // One tracking snapshot per child  { [childId]: data }
  const [tracking,  setTracking]  = useState({});
  const [trackBusy, setTrackBusy] = useState({});
  // Which child's map is expanded
  const [mapOpen, setMapOpen]     = useState(null);

  // Map refs keyed by childId
  const mapRefs = useRef({});

  // ── data load ──────────────────────────────────────────────────────────────
  const load = useCallback(async () => {
    try {
      const [cRes, nRes] = await Promise.all([
        parentApi.getChildren().catch(() => null),
        parentApi.myNotifications().catch(() => null),
      ]);
      if (cRes) {
        setChildren(cRes.data);
        // Automatically fetch tracking data for all children
        const trackingPromises = cRes.data.map(child =>
          parentApi.trackChild(child.child_id)
            .then(res => ({ childId: child.child_id, data: res.data }))
            .catch(() => ({ childId: child.child_id, data: null }))
        );
        const trackingResults = await Promise.all(trackingPromises);
        const trackingMap = {};
        trackingResults.forEach(({ childId, data }) => {
          if (data) trackingMap[childId] = data;
        });
        setTracking(trackingMap);
      }
      if (nRes) setNotifs(nRes.data);
    } catch (_) {}
  }, []);

  useEffect(() => { load(); }, [load]);

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  // ── link child ────────────────────────────────────────────────────────────
  const linkChild = async () => {
    if (!link.university_id.trim())
      return Alert.alert('Missing', 'Enter the child\'s University ID.');
    setLinkBusy(true);
    try {
      const res = await parentApi.linkChild(link);
      const newChild = res.data;
      Alert.alert('✅ Child linked!', 'Fetching their bus location...');
      setLink({ university_id: '', relationship_type: 'father' });
      
      // Fetch tracking data immediately for the new child
      try {
        const trackRes = await parentApi.trackChild(newChild.child_id);
        if (trackRes.data) {
          setTracking(t => ({ ...t, [newChild.child_id]: trackRes.data }));
          // Auto-open map if GPS data is available
          if (trackRes.data.latitude && trackRes.data.longitude) {
            setMapOpen(newChild.child_id);
          }
        }
      } catch (e) {
        console.log('Could not fetch tracking data immediately', e);
      }
      
      // Reload all children and tracking
      load();
    } catch (e) { showError(e); }
    finally { setLinkBusy(false); }
  };

  // ── unlink child ──────────────────────────────────────────────────────────
  const unlinkChild = (linkId, name) => {
    Alert.alert(`Remove ${name}?`, 'They will no longer be tracked.', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Remove', style: 'destructive', onPress: async () => {
        try {
          await parentApi.unlinkChild(linkId);
          setTracking(t => { const n = { ...t }; delete n[linkId]; return n; });
          if (mapOpen === linkId) setMapOpen(null);
          load();
        } catch (e) { showError(e); }
      }},
    ]);
  };

  // ── track child — fetch + update map ─────────────────────────────────────
  const trackChild = async (childId) => {
    setTrackBusy(b => ({ ...b, [childId]: true }));
    try {
      const res = await parentApi.trackChild(childId);
      const data = res.data;
      setTracking(t => ({ ...t, [childId]: data }));

      // Update map if it's open
      if (mapOpen === childId && mapRefs.current[childId]) {
        pushToMap(mapRefs.current[childId], data);
      }
      // Auto-open map when we get GPS
      if (data.latitude && data.longitude) {
        setMapOpen(childId);
      }
    } catch (e) { showError(e); }
    finally { setTrackBusy(b => ({ ...b, [childId]: false })); }
  };

  // ── push tracking data onto a LeafletMap ref ──────────────────────────────
  const pushToMap = (ref, data) => {
    if (!ref || !data) return;
    if (data.latitude && data.longitude) {
      const lat = parseFloat(data.latitude);
      const lng = parseFloat(data.longitude);
      const label = data.bus_number || 'Bus';
      ref.addBus('child_bus', lat, lng, label);
      ref.zoomTo(lat, lng, 16);
    }
  };

  // When a map mounts, push any existing tracking data into it
  const onMapReady = (childId, ref) => {
    mapRefs.current[childId] = ref;
    const data = tracking[childId];
    if (data) pushToMap(ref, data);
  };

  // When map opens or tracking data updates, refresh the map
  useEffect(() => {
    if (mapOpen && mapRefs.current[mapOpen]) {
      const data = tracking[mapOpen];
      if (data) pushToMap(mapRefs.current[mapOpen], data);
    }
  }, [mapOpen, tracking]);

  // ── mark notification read ────────────────────────────────────────────────
  const markRead = async (id) => {
    try { await parentApi.markRead(id); load(); } catch (_) {}
  };

  // ─── render ────────────────────────────────────────────────────────────────
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: COLORS.bg }}>
      <ScrollView
        contentContainerStyle={{ padding: 16, paddingBottom: 48 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {/* ── Header ── */}
        <Card style={bs.header}>
          <Text style={bs.headerName}>👨‍👧 {user?.full_name || 'Parent'}</Text>
          <Text style={bs.headerEmail}>{user?.email}</Text>
          <Btn title="Logout" color="rgba(255,255,255,0.25)" onPress={logout} style={{ marginTop: 10 }} />
        </Card>

        {/* ── Link a child ── */}
        <SectionTitle>➕ Link a Child</SectionTitle>
        <Card>
          <Input
            label="University ID *"
            value={link.university_id}
            onChangeText={(v) => setLink({ ...link, university_id: v })}
            placeholder="e.g. 2021-CS-001"
            autoCapitalize="none"
          />
          <Text style={bs.label}>Relationship *</Text>
          <View style={bs.relRow}>
            {['father', 'mother', 'guardian'].map((r) => (
              <TouchableOpacity
                key={r}
                style={[bs.relBtn, link.relationship_type === r && { backgroundColor: C }]}
                onPress={() => setLink({ ...link, relationship_type: r })}
              >
                <Text style={[bs.relText, link.relationship_type === r && { color: '#fff' }]}>
                  {r.charAt(0).toUpperCase() + r.slice(1)}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
          <Btn title="Link Child" color={C} onPress={linkChild} loading={linkBusy} />
        </Card>

        {/* ── Children list ── */}
        <SectionTitle>👨‍👧 My Children ({children.length})</SectionTitle>

        {children.length === 0 && (
          <Card>
            <Text style={{ color: COLORS.textLight, textAlign: 'center', paddingVertical: 8 }}>
              No children linked yet.{'\n'}Enter your child's University ID above to start tracking.
            </Text>
          </Card>
        )}

        {children.map((child) => {
          const td = tracking[child.child_id];
          const busy = trackBusy[child.child_id];
          const isMapOpen = mapOpen === child.child_id;

          return (
            <Card key={child.link_id} style={{ marginBottom: 12 }}>
              {/* ── Child info row ── */}
              <View style={bs.childRow}>
                <View style={{ flex: 1 }}>
                  <Text style={bs.childName}>{child.full_name}</Text>
                  <Text style={bs.childInfo}>
                    {child.university_id}  ·  {child.student_type || 'Student'}
                  </Text>
                  <Text style={bs.childInfo}>
                    {child.department || '—'}  ·  {child.relationship_type}
                  </Text>
                  <Badge
                    label={child.is_verified ? '✓ Verified' : '⏳ Pending'}
                    color={child.is_verified ? COLORS.success : COLORS.warning}
                  />
                </View>
                <TouchableOpacity style={bs.removeBtn} onPress={() => unlinkChild(child.link_id, child.full_name)}>
                  <Text style={bs.removeText}>✕</Text>
                </TouchableOpacity>
              </View>

              {/* ── Tracking summary ── */}
              {td && (
                <View style={bs.trackSummary}>
                  <Badge
                    label={td.has_active_booking ? '🚌 ON BUS TODAY' : '📅 NO BOOKING TODAY'}
                    color={td.has_active_booking ? COLORS.success : COLORS.textLight}
                  />
                  {td.has_active_booking && (
                    <View style={{ marginTop: 6 }}>
                      <Text style={bs.trackInfo}>🚌 Bus: <Text style={bs.trackVal}>{td.bus_number || '—'}</Text></Text>
                      <Text style={bs.trackInfo}>🛣 Route: <Text style={bs.trackVal}>{td.route_name || '—'}</Text></Text>
                      <Text style={bs.trackInfo}>💺 Seat: <Text style={bs.trackVal}>#{td.seat_number || '—'}</Text></Text>
                      {td.speed_kmh != null && (
                        <Text style={bs.trackInfo}>⚡ Speed: <Text style={bs.trackVal}>{Number(td.speed_kmh).toFixed(1)} km/h</Text></Text>
                      )}
                      {td.next_stop_name && (
                        <Text style={bs.trackInfo}>⏭ Next stop: <Text style={bs.trackVal}>{td.next_stop_name} (~{td.estimated_minutes_to_stop} min)</Text></Text>
                      )}
                      {td.last_seen_at && (
                        <Text style={bs.trackInfo}>🕐 Updated: <Text style={bs.trackVal}>{new Date(td.last_seen_at).toLocaleTimeString()}</Text></Text>
                      )}
                      {!td.latitude && (
                        <Text style={{ fontSize: 12, color: COLORS.warning, marginTop: 4 }}>
                          📍 GPS not available yet — driver hasn't started sharing location
                        </Text>
                      )}
                    </View>
                  )}
                </View>
              )}

              {/* ── LIVE MAP ── */}
              {isMapOpen && td?.latitude && (
                <View style={bs.mapWrap}>
                  <Text style={bs.mapTitle}>📍 Live Bus Location</Text>
                  <LeafletMap
                    ref={(ref) => { if (ref) onMapReady(child.child_id, ref); }}
                    style={bs.map}
                  />
                </View>
              )}

              {/* ── Action buttons ── */}
              <View style={bs.btnRow}>
                <TouchableOpacity
                  style={[bs.trackBtn, busy && { opacity: 0.6 }]}
                  onPress={() => trackChild(child.child_id)}
                  disabled={busy}
                >
                  {busy
                    ? <ActivityIndicator size="small" color="#fff" />
                    : <Text style={bs.trackBtnText}>🔴 Track Bus</Text>
                  }
                </TouchableOpacity>

                {td?.latitude && (
                  <TouchableOpacity
                    style={[bs.mapBtn, isMapOpen && { backgroundColor: '#BF360C' }]}
                    onPress={() => setMapOpen(isMapOpen ? null : child.child_id)}
                  >
                    <Text style={bs.trackBtnText}>{isMapOpen ? 'Hide Map' : '🗺 Show Map'}</Text>
                  </TouchableOpacity>
                )}
              </View>
            </Card>
          );
        })}

        {/* ── Notifications ── */}
        <SectionTitle>
          🔔 Notifications
          {notifs.filter(n => !n.is_read).length > 0 &&
            ` (${notifs.filter(n => !n.is_read).length} unread)`}
        </SectionTitle>

        {notifs.length === 0 && (
          <Card>
            <Text style={{ color: COLORS.textLight, textAlign: 'center' }}>No notifications</Text>
          </Card>
        )}

        {notifs.slice(0, 10).map((n) => (
          <Card
            key={n.id}
            style={!n.is_read ? { borderLeftWidth: 3, borderLeftColor: C } : {}}
          >
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <Text style={[bs.notifTitle, !n.is_read && { color: C }]}>{n.title}</Text>
              <Badge label={n.type} color={C} />
            </View>
            <Text style={bs.notifMsg}>{n.message}</Text>
            {!n.is_read && (
              <TouchableOpacity onPress={() => markRead(n.id)}>
                <Text style={[bs.markRead, { color: C }]}>Mark as read</Text>
              </TouchableOpacity>
            )}
          </Card>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

// ─── styles ───────────────────────────────────────────────────────────────────
const bs = StyleSheet.create({
  // header
  header:       { backgroundColor: C, marginBottom: 16 },
  headerName:   { fontSize: 20, fontWeight: '800', color: '#fff' },
  headerEmail:  { color: 'rgba(255,255,255,0.8)', fontSize: 13, marginTop: 2 },

  // section title
  sectionTitle: { fontSize: 14, fontWeight: '700', color: COLORS.text, marginTop: 16, marginBottom: 6 },

  // relationship selector
  label:   { fontSize: 13, fontWeight: '600', color: COLORS.text, marginBottom: 6, marginTop: 4 },
  relRow:  { flexDirection: 'row', gap: 8, marginBottom: 12 },
  relBtn:  { flex: 1, paddingVertical: 10, borderRadius: 8, borderWidth: 1.5, borderColor: C, alignItems: 'center' },
  relText: { fontSize: 13, fontWeight: '600', color: C },

  // badge
  badge:     { alignSelf: 'flex-start', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 10, marginTop: 4 },
  badgeText: { color: '#fff', fontSize: 11, fontWeight: '700' },

  // child card
  childRow:  { flexDirection: 'row', marginBottom: 8 },
  childName: { fontSize: 16, fontWeight: '700', color: COLORS.text },
  childInfo: { fontSize: 12, color: COLORS.textLight, marginTop: 2 },
  removeBtn: { padding: 6, alignSelf: 'flex-start' },
  removeText:{ fontSize: 18, color: COLORS.danger },

  // tracking summary
  trackSummary: { backgroundColor: '#FFF8E1', borderRadius: 8, padding: 10, marginBottom: 10 },
  trackInfo:    { fontSize: 13, color: COLORS.textLight, marginTop: 3 },
  trackVal:     { color: COLORS.text, fontWeight: '600' },

  // map
  mapWrap:  { borderRadius: 10, overflow: 'hidden', marginBottom: 10, height: 260 },
  mapTitle: { fontSize: 12, fontWeight: '700', color: COLORS.text, marginBottom: 6 },
  map:      { flex: 1, borderRadius: 10 },

  // buttons
  btnRow:      { flexDirection: 'row', gap: 8, marginTop: 4 },
  trackBtn:    { flex: 1, backgroundColor: C, borderRadius: 8, paddingVertical: 10, alignItems: 'center' },
  mapBtn:      { flex: 1, backgroundColor: '#FF6D00', borderRadius: 8, paddingVertical: 10, alignItems: 'center' },
  trackBtnText:{ color: '#fff', fontWeight: '700', fontSize: 13 },

  // notifications
  notifTitle: { fontSize: 14, fontWeight: '700', color: COLORS.text, flex: 1 },
  notifMsg:   { fontSize: 13, color: COLORS.textLight, marginTop: 4, lineHeight: 19 },
  markRead:   { fontSize: 12, fontWeight: '600', marginTop: 6 },
});
