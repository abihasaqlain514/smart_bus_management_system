import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, Alert, SafeAreaView,
  RefreshControl, TouchableOpacity, Modal, FlatList,
} from 'react-native';
import LeafletMap from '../../components/LeafletMap';
import { useAuth } from '../../context/AuthContext';
import { adminApi } from '../../api/index';
import { Btn, Input, Card, SectionTitle, Badge, Row, showError, statusColor } from '../../components/UI';
import { COLORS } from '../../config';

const C = '#6A1B9A';

// ── Simple dropdown picker ────────────────────────────────────────────────────
function Picker({ label, value, placeholder, items, onSelect, renderItem }) {
  const [open, setOpen] = useState(false);
  return (
    <View style={pk.wrap}>
      <Text style={pk.label}>{label}</Text>
      <TouchableOpacity style={pk.trigger} onPress={() => setOpen(true)} activeOpacity={0.8}>
        <Text style={value ? pk.val : pk.placeholder} numberOfLines={1}>
          {value || placeholder}
        </Text>
        <Text style={pk.arrow}>▾</Text>
      </TouchableOpacity>
      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <TouchableOpacity style={pk.backdrop} activeOpacity={1} onPress={() => setOpen(false)}>
          <View style={pk.sheet}>
            <Text style={pk.sheetTitle}>{label}</Text>
            <FlatList
              data={items}
              keyExtractor={(_, i) => String(i)}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={pk.option}
                  onPress={() => { onSelect(item); setOpen(false); }}
                >
                  {renderItem ? renderItem(item) : (
                    <Text style={pk.optionTxt}>{item.label || item}</Text>
                  )}
                </TouchableOpacity>
              )}
              ListEmptyComponent={<Text style={pk.empty}>No items available</Text>}
            />
            <TouchableOpacity style={pk.cancelBtn} onPress={() => setOpen(false)}>
              <Text style={pk.cancelTxt}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </TouchableOpacity>
      </Modal>
    </View>
  );
}

// ── Status badge row selector ─────────────────────────────────────────────────
function StatusPicker({ value, onChange }) {
  const options = [
    { key: 'not_in_service', label: 'Not in Service', color: '#757575' },
    { key: 'on_route',       label: 'On Route',       color: COLORS.success },
    { key: 'delayed',        label: 'Delayed',        color: '#FB8C00' },
  ];
  return (
    <View style={{ marginBottom: 12 }}>
      <Text style={pk.label}>Bus Status</Text>
      <View style={{ flexDirection: 'row', gap: 8, marginTop: 6 }}>
        {options.map(o => (
          <TouchableOpacity
            key={o.key}
            onPress={() => onChange(o.key)}
            style={[st.statusChip, { borderColor: o.color, backgroundColor: value === o.key ? o.color : 'transparent' }]}
          >
            <Text style={[st.statusChipTxt, { color: value === o.key ? '#fff' : o.color }]}>
              {o.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

// ── Main dashboard ────────────────────────────────────────────────────────────
export default function AdminDashboard() {
  const { user, logout } = useAuth();
  const [analytics, setAnalytics] = useState(null);
  const [monitoring, setMonitor]  = useState([]);
  const [users,      setUsers]    = useState([]);
  const [selector,   setSelector] = useState({ buses: [], drivers: [], routes: [] });
  const fleetMapRef = useRef(null);
  const [refreshing, setRefresh]  = useState(false);
  const [busy,       setBusy]     = useState('');

  // Assign form — uses human-readable names, not UUIDs
  const [assign, setAssign] = useState({
    bus_number:   '',
    driver_code:  '',
    route_number: '',
    bus_status:   'on_route',
  });

  // Create bus form
  const [bus, setBus] = useState({ bus_number: '', capacity: '40', model: 'Toyota Coaster', plate_number: '' });

  // Create route form
  const [route, setRoute] = useState({ route_name: '', route_number: '', start_point: '', end_point: '', distance_km: '10' });

  // Add stop form — route selected by picker, not UUID
  const [stop, setStop] = useState({
    route_id: '', route_label: '',
    stop_name: '', stop_order: '1',
    latitude: '31.2681', longitude: '72.3178', estimated_minutes: '0',
  });

  // Broadcast form
  const [broad, setBroad] = useState({ title: '', message: '' });

  const load = useCallback(async () => {
    try {
      const [aRes, mRes, uRes, selRes] = await Promise.all([
        adminApi.getAnalytics().catch(() => null),
        adminApi.getMonitoring().catch(() => null),
        adminApi.getUsers().catch(() => null),
        adminApi.getSelectorData().catch(() => null),
      ]);
      if (aRes?.data) setAnalytics(aRes.data);
      if (mRes?.data) {
        setMonitor(mRes.data);
        mRes.data.forEach(b => {
          const lat = Number(b.latitude), lng = Number(b.longitude);
          if (lat >= 23.5 && lat <= 37.5 && lng >= 60.8 && lng <= 77.8) {
            fleetMapRef.current?.updateBus(b.bus_id, lat, lng);
          }
        });
      }
      if (uRes?.data)   setUsers(uRes.data);
      if (selRes?.data) setSelector(selRes.data);
    } catch (_) {}
  }, []);

  useEffect(() => { load(); }, [load]);
  const onRefresh = async () => { setRefresh(true); await load(); setRefresh(false); };

  // ── Assign bus (human-readable) ───────────────────────────────────────────
  const assignBus = async () => {
    if (!assign.bus_number) return Alert.alert('Select a Bus', 'Please select a bus first.');
    if (!assign.driver_code && !assign.route_number)
      return Alert.alert('Nothing to assign', 'Select a driver or route to assign.');
    setBusy('assign');
    try {
      await adminApi.assignBus({
        bus_number:   assign.bus_number,
        driver_code:  assign.driver_code  || undefined,
        route_number: assign.route_number || undefined,
        bus_status:   assign.bus_status   || undefined,
      });
      Alert.alert('Done!', `${assign.bus_number} updated successfully.`);
      setAssign({ bus_number: '', driver_code: '', route_number: '', bus_status: 'on_route' });
      load();
    } catch (e) { showError(e); }
    finally { setBusy(''); }
  };

  // ── Create bus ────────────────────────────────────────────────────────────
  const createBus = async () => {
    if (!bus.bus_number || !bus.plate_number)
      return Alert.alert('Missing', 'Bus number and plate are required.');
    setBusy('bus');
    try {
      await adminApi.createBus({ ...bus, capacity: Number(bus.capacity) });
      Alert.alert('Bus Created!', `${bus.bus_number} added to the fleet.`);
      setBus({ bus_number: '', capacity: '40', model: 'Toyota Coaster', plate_number: '' });
      load();
    } catch (e) { showError(e); }
    finally { setBusy(''); }
  };

  // ── Create route ──────────────────────────────────────────────────────────
  const createRoute = async () => {
    if (!route.route_name || !route.route_number)
      return Alert.alert('Missing', 'Route name and number are required.');
    setBusy('route');
    try {
      await adminApi.createRoute({ ...route, distance_km: Number(route.distance_km) });
      Alert.alert('Route Created!', `${route.route_name} added.`);
      setRoute({ route_name: '', route_number: '', start_point: '', end_point: '', distance_km: '10' });
      load();
    } catch (e) { showError(e); }
    finally { setBusy(''); }
  };

  // ── Add stop ──────────────────────────────────────────────────────────────
  const addStop = async () => {
    if (!stop.route_id) return Alert.alert('Select Route', 'Pick a route first.');
    if (!stop.stop_name) return Alert.alert('Missing', 'Enter a stop name.');
    setBusy('stop');
    try {
      await adminApi.addStop(stop.route_id, {
        stop_name: stop.stop_name, stop_order: Number(stop.stop_order),
        latitude: Number(stop.latitude), longitude: Number(stop.longitude),
        estimated_minutes: Number(stop.estimated_minutes),
      });
      Alert.alert('Stop Added!', `"${stop.stop_name}" added to route.`);
      setStop(s => ({ ...s, stop_name: '', stop_order: String(Number(s.stop_order) + 1) }));
    } catch (e) { showError(e); }
    finally { setBusy(''); }
  };

  // ── Broadcast ─────────────────────────────────────────────────────────────
  const broadcast = async () => {
    if (!broad.title || !broad.message) return Alert.alert('Missing', 'Fill title and message.');
    setBusy('broad');
    try {
      await adminApi.broadcast(broad);
      Alert.alert('Sent!', 'All users have been notified.');
      setBroad({ title: '', message: '' });
    } catch (e) { showError(e); }
    finally { setBusy(''); }
  };

  const Stat = ({ label, value }) => (
    <View style={st.stat}>
      <Text style={st.statNum}>{value ?? '—'}</Text>
      <Text style={st.statLabel}>{label}</Text>
    </View>
  );

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: COLORS.bg }}>
      <ScrollView
        contentContainerStyle={{ padding: 16, paddingBottom: 50 }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {/* ── Header ─────────────────────────────────────────────────────── */}
        <Card style={{ backgroundColor: C }}>
          <Text style={{ fontSize: 20, fontWeight: '800', color: '#fff' }}>
            {user?.full_name || 'Admin'}
          </Text>
          <Text style={{ color: 'rgba(255,255,255,0.8)', marginTop: 2 }}>{user?.email}</Text>
          <Btn title="Logout" color="rgba(255,255,255,0.25)" onPress={logout} style={{ marginTop: 10 }} />
        </Card>

        {/* ── Analytics ──────────────────────────────────────────────────── */}
        {analytics && (
          <>
            <SectionTitle>Analytics Overview</SectionTitle>
            <Card>
              <View style={st.statsRow}>
                <Stat label="Users"     value={analytics.total_users} />
                <Stat label="Passengers" value={analytics.total_passengers} />
                <Stat label="Drivers"   value={analytics.total_drivers} />
                <Stat label="Buses"     value={analytics.total_buses} />
              </View>
              <View style={st.statsRow}>
                <Stat label="Routes"    value={analytics.active_routes} />
                <Stat label="Bookings"  value={analytics.total_bookings} />
                <Stat label="Live Trips" value={analytics.active_trips} />
                <Stat label="Peak Hr"   value={analytics.peak_hour != null ? `${analytics.peak_hour}:00` : '—'} />
              </View>
            </Card>
          </>
        )}

        {/* ── Live Fleet Map ──────────────────────────────────────────────── */}
        <SectionTitle>Live Fleet Map — Jhang ({monitoring.length} buses)</SectionTitle>
        <LeafletMap
          ref={fleetMapRef}
          style={st.map}
          onReady={() => fleetMapRef.current?.zoomJhang()}
        />

        {/* Bus status cards */}
        {monitoring.map((b, i) => (
          <Card key={b.bus_id || i} style={{ borderLeftWidth: 4, borderLeftColor: b.status === 'on_route' ? COLORS.success : '#9E9E9E' }}>
            <Row style={{ justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <Text style={{ fontWeight: '800', fontSize: 16 }}>🚌 {b.bus_number}</Text>
              <Badge label={b.status} color={statusColor(b.status)} />
            </Row>
            <Text style={st.info}>Route: {b.route_name || '—'}</Text>
            <Text style={st.info}>Driver: {b.driver_name ? `${b.driver_name} (${b.driver_code})` : 'Not assigned'}</Text>
            <Text style={st.info}>{b.available_seats}/{b.capacity} seats available</Text>
            {b.latitude
              ? <Text style={st.info}>GPS: {Number(b.latitude).toFixed(4)}, {Number(b.longitude).toFixed(4)}</Text>
              : <Text style={[st.info, { color: '#FB8C00' }]}>No GPS data yet</Text>}
          </Card>
        ))}

        {/* ── Assign Driver / Route to Bus ────────────────────────────────── */}
        <SectionTitle>Assign Driver & Route to Bus</SectionTitle>
        <Card>
          <Text style={st.hint}>Select from your existing buses, drivers and routes below — no need to type any IDs.</Text>

          {/* Bus picker */}
          <Picker
            label="Select Bus *"
            value={assign.bus_number}
            placeholder="Tap to choose a bus…"
            items={selector.buses}
            onSelect={b => setAssign(a => ({ ...a, bus_number: b.bus_number }))}
            renderItem={b => (
              <View style={pk.itemRow}>
                <Text style={pk.itemMain}>🚌 {b.bus_number}</Text>
                <Text style={pk.itemSub}>{b.model}  ·  {b.capacity} seats  ·  {b.status}</Text>
              </View>
            )}
          />

          {/* Driver picker */}
          <Picker
            label="Select Driver (optional)"
            value={assign.driver_code ? `${assign.driver_code}` : ''}
            placeholder="Tap to assign a driver…"
            items={selector.drivers}
            onSelect={d => setAssign(a => ({ ...a, driver_code: d.driver_code }))}
            renderItem={d => (
              <View style={pk.itemRow}>
                <Text style={pk.itemMain}>👤 {d.full_name}</Text>
                <Text style={pk.itemSub}>{d.driver_code}  ·  {d.status}</Text>
              </View>
            )}
          />

          {/* Route picker */}
          <Picker
            label="Select Route (optional)"
            value={assign.route_number ? `${assign.route_number}` : ''}
            placeholder="Tap to assign a route…"
            items={selector.routes}
            onSelect={r => setAssign(a => ({ ...a, route_number: r.route_number }))}
            renderItem={r => (
              <View style={pk.itemRow}>
                <Text style={pk.itemMain}>🗺 {r.route_name}</Text>
                <Text style={pk.itemSub}>{r.start_point} → {r.end_point}</Text>
              </View>
            )}
          />

          {/* Status picker */}
          <StatusPicker value={assign.bus_status} onChange={v => setAssign(a => ({ ...a, bus_status: v }))} />

          <Btn title="Apply Assignment" color={C} onPress={assignBus} loading={busy === 'assign'} />

          {/* Clear selection */}
          {(assign.bus_number || assign.driver_code || assign.route_number) && (
            <TouchableOpacity
              onPress={() => setAssign({ bus_number: '', driver_code: '', route_number: '', bus_status: 'on_route' })}
              style={{ alignItems: 'center', marginTop: 8 }}
            >
              <Text style={{ color: COLORS.textLight, fontSize: 12 }}>✕ Clear selection</Text>
            </TouchableOpacity>
          )}
        </Card>

        {/* ── Add Bus to Fleet ────────────────────────────────────────────── */}
        <SectionTitle>Add New Bus to Fleet</SectionTitle>
        <Card>
          <Input label="Bus Number"   value={bus.bus_number}   onChangeText={v => setBus(b => ({ ...b, bus_number: v }))}   placeholder="e.g. JHG-004" />
          <Input label="Plate Number" value={bus.plate_number} onChangeText={v => setBus(b => ({ ...b, plate_number: v }))} placeholder="e.g. JHG-1004" />
          <Input label="Model"        value={bus.model}        onChangeText={v => setBus(b => ({ ...b, model: v }))}        placeholder="Toyota Coaster" />
          <Input label="Capacity (seats)" value={bus.capacity} onChangeText={v => setBus(b => ({ ...b, capacity: v }))}    keyboardType="numeric" />
          <Btn title="Add Bus" color={C} onPress={createBus} loading={busy === 'bus'} />
        </Card>

        {/* ── Create Route ────────────────────────────────────────────────── */}
        <SectionTitle>Create New Route</SectionTitle>
        <Card>
          <Input label="Route Name"    value={route.route_name}   onChangeText={v => setRoute(r => ({ ...r, route_name: v }))}   placeholder="University–City Center" />
          <Input label="Route Number"  value={route.route_number} onChangeText={v => setRoute(r => ({ ...r, route_number: v }))} placeholder="R-JHG-04" />
          <Input label="Start Point"   value={route.start_point}  onChangeText={v => setRoute(r => ({ ...r, start_point: v }))}  placeholder="University of Jhang" />
          <Input label="End Point"     value={route.end_point}    onChangeText={v => setRoute(r => ({ ...r, end_point: v }))}    placeholder="Clock Tower Chowk" />
          <Input label="Distance (km)" value={route.distance_km}  onChangeText={v => setRoute(r => ({ ...r, distance_km: v }))} keyboardType="numeric" />
          <Btn title="Create Route" color={C} onPress={createRoute} loading={busy === 'route'} />
        </Card>

        {/* ── Add Stop to Route ───────────────────────────────────────────── */}
        <SectionTitle>Add Stop to Route</SectionTitle>
        <Card>
          <Picker
            label="Select Route *"
            value={stop.route_label}
            placeholder="Tap to choose a route…"
            items={selector.routes}
            onSelect={r => setStop(s => ({ ...s, route_id: r.id, route_label: r.route_name }))}
            renderItem={r => (
              <View style={pk.itemRow}>
                <Text style={pk.itemMain}>🗺 {r.route_name}</Text>
                <Text style={pk.itemSub}>{r.start_point} → {r.end_point}</Text>
              </View>
            )}
          />
          <Input label="Stop Name"    value={stop.stop_name}  onChangeText={v => setStop(s => ({ ...s, stop_name: v }))}  placeholder="Civil Hospital Chowk" />
          <Input label="Stop Order"   value={stop.stop_order} onChangeText={v => setStop(s => ({ ...s, stop_order: v }))} keyboardType="numeric" />
          <Row>
            <View style={{ flex: 1, marginRight: 6 }}>
              <Input label="Latitude"  value={stop.latitude}  onChangeText={v => setStop(s => ({ ...s, latitude: v }))}  keyboardType="numeric" />
            </View>
            <View style={{ flex: 1 }}>
              <Input label="Longitude" value={stop.longitude} onChangeText={v => setStop(s => ({ ...s, longitude: v }))} keyboardType="numeric" />
            </View>
          </Row>
          <Input label="Minutes from Start" value={stop.estimated_minutes} onChangeText={v => setStop(s => ({ ...s, estimated_minutes: v }))} keyboardType="numeric" />
          <Btn title="Add Stop" color={C} onPress={addStop} loading={busy === 'stop'} />
        </Card>

        {/* ── Broadcast ───────────────────────────────────────────────────── */}
        <SectionTitle>Broadcast Announcement</SectionTitle>
        <Card>
          <Input label="Title"   value={broad.title}   onChangeText={v => setBroad(b => ({ ...b, title: v }))}   placeholder="System Announcement" />
          <Input label="Message" value={broad.message} onChangeText={v => setBroad(b => ({ ...b, message: v }))} multiline numberOfLines={3} />
          <Btn title="Send to All Users" color={C} onPress={broadcast} loading={busy === 'broad'} />
        </Card>

        {/* ── Users ───────────────────────────────────────────────────────── */}
        <SectionTitle>Users ({users.length})</SectionTitle>
        {users.slice(0, 15).map(u => (
          <Card key={u.id}>
            <Row style={{ justifyContent: 'space-between', alignItems: 'center' }}>
              <Text style={{ fontWeight: '700', flex: 1 }}>{u.full_name}</Text>
              <Badge label={u.role} color={statusColor(u.role)} />
            </Row>
            <Text style={st.info}>{u.email}</Text>
            <Btn
              title={u.is_active ? 'Block User' : 'Unblock User'}
              color={u.is_active ? COLORS.danger : COLORS.success}
              onPress={() => adminApi.blockUser(u.id).then(load).catch(showError)}
              style={{ marginTop: 8 }}
            />
          </Card>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────
const st = StyleSheet.create({
  info:       { fontSize: 13, color: COLORS.textLight, marginTop: 3 },
  hint:       { fontSize: 12, color: COLORS.textLight, marginBottom: 12, lineHeight: 18 },
  statsRow:   { flexDirection: 'row', justifyContent: 'space-around', marginBottom: 8 },
  stat:       { alignItems: 'center' },
  statNum:    { fontSize: 22, fontWeight: '800', color: C },
  statLabel:  { fontSize: 11, color: COLORS.textLight, marginTop: 2 },
  map:        { height: 220, borderRadius: 14, marginBottom: 12, overflow: 'hidden' },
  statusChip: { borderWidth: 1.5, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6 },
  statusChipTxt: { fontSize: 12, fontWeight: '700' },
});

const pk = StyleSheet.create({
  wrap:        { marginBottom: 14 },
  label:       { fontSize: 12, color: COLORS.textLight, fontWeight: '600', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.5 },
  trigger:     { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', borderWidth: 1, borderColor: '#E0E0E0', borderRadius: 12, paddingHorizontal: 14, paddingVertical: 13, backgroundColor: '#FAFAFA' },
  val:         { fontSize: 14, fontWeight: '600', color: COLORS.text, flex: 1 },
  placeholder: { fontSize: 14, color: COLORS.textLight, flex: 1 },
  arrow:       { fontSize: 16, color: COLORS.textLight, marginLeft: 8 },

  backdrop:    { flex: 1, backgroundColor: 'rgba(0,0,0,0.45)', justifyContent: 'flex-end' },
  sheet:       { backgroundColor: '#fff', borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 20, maxHeight: '70%' },
  sheetTitle:  { fontSize: 16, fontWeight: '800', color: COLORS.text, marginBottom: 14, textAlign: 'center' },
  option:      { paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#F5F5F5' },
  optionTxt:   { fontSize: 14, color: COLORS.text },
  itemRow:     { paddingVertical: 2 },
  itemMain:    { fontSize: 15, fontWeight: '700', color: COLORS.text },
  itemSub:     { fontSize: 12, color: COLORS.textLight, marginTop: 2 },
  empty:       { textAlign: 'center', color: COLORS.textLight, paddingVertical: 20 },
  cancelBtn:   { marginTop: 14, paddingVertical: 12, alignItems: 'center', backgroundColor: '#F5F5F5', borderRadius: 12 },
  cancelTxt:   { fontSize: 14, fontWeight: '700', color: COLORS.textLight },
});
