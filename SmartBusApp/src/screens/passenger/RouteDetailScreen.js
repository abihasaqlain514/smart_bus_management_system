import { useState, useEffect, useCallback, useRef } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  Modal, Alert, ActivityIndicator, RefreshControl,
} from 'react-native';
import { passengerApi } from '../../api/index';
import { showError } from '../../components/UI';
import LeafletMap from '../../components/LeafletMap';
import { COLORS } from '../../config';

const today = () => new Date().toISOString().split('T')[0];

// ── Daewoo 2+2 Seat Layout ────────────────────────────────────────────────────
function SeatGrid({ capacity, bookedMap, selectedSeat, onSelect }) {
  const rows = Math.ceil(capacity / 4);

  const getColor = (n) => {
    if (n === selectedSeat) return COLORS.primary;
    const g = bookedMap.get(n);
    if (g === 'male')   return '#BBDEFB';
    if (g === 'female') return '#F8BBD9';
    if (g)              return '#E0E0E0';
    return '#E8F5E9';
  };

  const getTextColor = (n) => (n === selectedSeat ? '#fff' : bookedMap.has(n) ? '#757575' : COLORS.success);
  const isBooked = (n) => bookedMap.has(n);

  return (
    <ScrollView style={{ maxHeight: 320 }} showsVerticalScrollIndicator={false}>
      {/* Legend */}
      <View style={g.legend}>
        {[{ c: '#E8F5E9', l: 'Available' }, { c: '#BBDEFB', l: 'Male' }, { c: '#F8BBD9', l: 'Female' }, { c: COLORS.primary, l: 'Selected' }].map(x => (
          <View key={x.l} style={g.legendItem}>
            <View style={[g.legendDot, { backgroundColor: x.c, borderWidth: 1, borderColor: '#ddd' }]} />
            <Text style={g.legendTxt}>{x.l}</Text>
          </View>
        ))}
      </View>

      {/* Driver cabin */}
      <View style={g.cabin}>
        <View style={g.wheel}><Text>🚗</Text></View>
        <Text style={g.cabinTxt}>Driver</Text>
        <View style={g.door}><Text>🚪</Text></View>
      </View>

      {/* Seat rows */}
      {Array.from({ length: rows }, (_, row) => {
        const b = row * 4;
        return (
          <View key={row} style={g.row}>
            <View style={g.side}>
              {[b+1, b+2].map(n => n <= capacity ? (
                <TouchableOpacity key={n} style={[g.seat, { backgroundColor: getColor(n) }]}
                  onPress={() => !isBooked(n) && onSelect(n === selectedSeat ? null : n)}
                  disabled={isBooked(n)}>
                  <Text style={g.seatIcon}>💺</Text>
                  <Text style={[g.seatNum, { color: getTextColor(n) }]}>{n}</Text>
                </TouchableOpacity>
              ) : <View key={n} style={g.seatEmpty} />)}
            </View>
            <View style={g.aisle}><Text style={g.aisleNum}>{row+1}</Text></View>
            <View style={g.side}>
              {[b+3, b+4].map(n => n <= capacity ? (
                <TouchableOpacity key={n} style={[g.seat, { backgroundColor: getColor(n) }]}
                  onPress={() => !isBooked(n) && onSelect(n === selectedSeat ? null : n)}
                  disabled={isBooked(n)}>
                  <Text style={g.seatIcon}>💺</Text>
                  <Text style={[g.seatNum, { color: getTextColor(n) }]}>{n}</Text>
                </TouchableOpacity>
              ) : <View key={n} style={g.seatEmpty} />)}
            </View>
          </View>
        );
      })}
      <Text style={g.hint}>{selectedSeat ? `✅ Seat #${selectedSeat} selected` : 'Tap a green seat to select'}</Text>
    </ScrollView>
  );
}

// ── Main Screen ───────────────────────────────────────────────────────────────
export default function RouteDetailScreen({ route, navigation }) {
  const { routeId, routeData } = route.params;

  const mapRef   = useRef(null);
  const mapReady = useRef(false);
  const stopsRef = useRef([]);

  const [stops,      setStops]     = useState([]);
  const [buses,      setBuses]     = useState([]);
  const [loading,    setLoading]   = useState(true);
  const [refreshing, setRefresh]   = useState(false);

  const [modal,        setModal]   = useState(false);
  const [selBus,       setSelBus]  = useState(null);
  const [bookedMap,    setBooked]  = useState(new Map());
  const [selectedSeat, setSelSeat] = useState(null);
  const [loadSeats,    setLoadSts] = useState(false);
  const [booking,      setBooking] = useState(false);

  const load = useCallback(async () => {
    try {
      const [sRes, bRes] = await Promise.all([
        passengerApi.getRouteStops(routeId).catch(() => null),
        passengerApi.getRouteBuses(routeId).catch(() => null),
      ]);
      const stopsData = sRes?.data ?? [];
      setStops(stopsData);
      stopsRef.current = stopsData;
      if (bRes) setBuses(bRes.data ?? []);

      if (mapReady.current && stopsData.length) pushStopsToMap(stopsData);
    } catch (_) {}
    finally { setLoading(false); setRefresh(false); }
  }, [routeId]);

  useEffect(() => { load(); }, [load]);

  const pushStopsToMap = (data) => {
    const valid = data.filter(s => s.latitude && s.longitude &&
      Number(s.latitude) >= 23.5 && Number(s.longitude) >= 60.8);
    if (!valid.length) return;
    mapRef.current?.addStops(valid);
    if (valid.length > 1)
      mapRef.current?.setPolyline(valid.map(s => [Number(s.latitude), Number(s.longitude)]));
  };

  const onMapReady = () => {
    mapReady.current = true;
    if (stopsRef.current.length) pushStopsToMap(stopsRef.current);
  };

  const openBooking = async (bus) => {
    setSelBus(bus);
    setSelSeat(null);
    setBooked(new Map());
    setModal(true);
    setLoadSts(true);
    try {
      const res = await passengerApi.getBusBookingsByDate(bus.bus_id, today());
      setBooked(new Map((res.data || []).map(b => [b.seat_number, b.passenger_gender || 'other'])));
    } catch (_) {}
    finally { setLoadSts(false); }
  };

  const confirmBook = async () => {
    if (!selectedSeat) return Alert.alert('Choose a seat', 'Tap an available seat first.');
    setBooking(true);
    try {
      const res = await passengerApi.bookSeat({
        bus_id:       selBus.bus_id,
        route_id:     routeId,
        seat_number:  selectedSeat,
        booking_date: today(),
      });
      setModal(false);
      load();
      navigation.navigate('BookingQR', {
        booking: { ...res.data, bus_number: selBus.bus_number, route_name: routeData?.route_name ?? '' },
      });
    } catch (e) { showError(e); }
    finally { setBooking(false); }
  };

  const trackBus = (bus) => {
    if (!bus.active_trip_id) return Alert.alert('Bus Not Active', 'This bus has not started its trip yet. Please check back later.');
    navigation.navigate('LiveMap', {
      tripId:     bus.active_trip_id,
      busId:      bus.bus_id,
      routeId,
      busNumber:  bus.bus_number,
      driverName: bus.driver_name,
      routeName:  routeData?.route_name ?? '',
    });
  };

  return (
    <>
      <ScrollView
        style={{ flex: 1, backgroundColor: COLORS.bg }}
        contentContainerStyle={s.container}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefresh(true); load(); }} />}
      >
        {/* Route header */}
        <View style={s.header}>
          <Text style={s.routeName}>{routeData?.route_name}</Text>
          <View style={s.headerPath}>
            <View style={s.headerDot} />
            <Text style={s.headerTxt}>{routeData?.start_point}</Text>
          </View>
          <View style={[s.headerPath, { marginTop: 4 }]}>
            <View style={[s.headerDot, { backgroundColor: COLORS.danger }]} />
            <Text style={s.headerTxt}>{routeData?.end_point}</Text>
          </View>
          {routeData?.distance_km && (
            <Text style={s.dist}>📏 {Number(routeData.distance_km).toFixed(1)} km total route</Text>
          )}
        </View>

        {/* Map showing route stops */}
        <LeafletMap ref={mapRef} style={s.map} onReady={onMapReady} />

        {/* Stops timeline */}
        <Text style={s.sectionTitle}>🛑 All Stops & Timings</Text>
        {loading
          ? <ActivityIndicator color={COLORS.primary} style={{ marginVertical: 12 }} />
          : stops.map((st, idx) => {
            const isFirst = idx === 0;
            const isLast  = idx === stops.length - 1;
            return (
              <View key={st.id} style={s.stopRow}>
                {/* Timeline dot + connector */}
                <View style={s.stopLeft}>
                  <View style={[s.stopDot,
                    isFirst ? { backgroundColor: COLORS.success, width: 16, height: 16, borderRadius: 8 }
                    : isLast  ? { backgroundColor: COLORS.danger, width: 16, height: 16, borderRadius: 8 }
                    : { backgroundColor: COLORS.primary }
                  ]} />
                  {!isLast && <View style={s.stopConnector} />}
                </View>

                {/* Stop info */}
                <View style={s.stopInfo}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Text style={[s.stopName, (isFirst || isLast) && { fontWeight: '800', color: COLORS.text }]}>
                      {st.stop_name}
                    </Text>
                    {st.stop_time && (
                      <View style={[s.timeBadge, isLast && { backgroundColor: '#FFF3E0' }]}>
                        <Text style={[s.timeBadgeTxt, isLast && { color: '#E65100' }]}>
                          {st.stop_time}
                        </Text>
                      </View>
                    )}
                  </View>
                  {isFirst && <Text style={s.stopRole}>Departure</Text>}
                  {isLast  && <Text style={[s.stopRole, { color: COLORS.danger }]}>University Arrival</Text>}
                </View>
              </View>
            );
          })
        }

        {/* Available buses */}
        <Text style={s.sectionTitle}>🚌 Available Buses</Text>
        {loading
          ? <ActivityIndicator color={COLORS.primary} style={{ marginVertical: 12 }} />
          : buses.length === 0
            ? <View style={s.noBus}><Text style={s.noBusTxt}>No buses assigned to this route yet.</Text></View>
            : buses.map(b => (
              <View key={b.bus_id} style={s.busCard}>
                <View style={s.busHeader}>
                  <View style={s.busIconCircle}><Text style={{ fontSize: 20 }}>🚌</Text></View>
                  <View style={{ flex: 1 }}>
                    <Text style={s.busName}>{b.bus_number}</Text>
                    {b.driver_name && <Text style={s.driverName}>👤 Driver: {b.driver_name}</Text>}
                  </View>
                  {b.active_trip_id
                    ? <View style={s.livePill}><View style={s.liveDot} /><Text style={s.liveTxt}>LIVE</Text></View>
                    : <View style={s.waitPill}><Text style={s.waitTxt}>Not Started</Text></View>
                  }
                </View>

                {/* Seat availability bar */}
                <View style={s.seatRow}>
                  <Text style={s.seatTxt}>💺 Seats available</Text>
                  <Text style={s.seatCount}>{b.available_seats}/{b.capacity}</Text>
                </View>
                <View style={s.seatBar}>
                  <View style={[s.seatFill, {
                    width: `${Math.round((b.available_seats / b.capacity) * 100)}%`,
                    backgroundColor: b.available_seats > 10 ? COLORS.success : b.available_seats > 3 ? COLORS.warning : COLORS.danger,
                  }]} />
                </View>

                {b.started_at && (
                  <Text style={s.departure}>🕐 Departed at {new Date(b.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</Text>
                )}

                <View style={s.busActions}>
                  {b.active_trip_id && (
                    <TouchableOpacity style={s.trackBtn} onPress={() => trackBus(b)}>
                      <Text style={s.trackBtnTxt}>📍 Track Live</Text>
                    </TouchableOpacity>
                  )}
                  <TouchableOpacity
                    style={[s.bookBtn, b.available_seats === 0 && s.bookBtnDisabled]}
                    disabled={b.available_seats === 0}
                    onPress={() => openBooking(b)}
                  >
                    <Text style={s.bookBtnTxt}>
                      {b.available_seats > 0 ? '🎫 Book Seat' : '🚫 Full'}
                    </Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))
        }
      </ScrollView>

      {/* ── Seat Selection Modal ─────────────────────────────────────────── */}
      <Modal visible={modal} transparent animationType="slide" onRequestClose={() => setModal(false)}>
        <View style={s.overlay}>
          <View style={s.sheet}>
            <View style={s.sheetHandle} />
            <View style={s.sheetHeader}>
              <View>
                <Text style={s.sheetTitle}>Choose Your Seat</Text>
                {selBus && <Text style={s.sheetSub}>{selBus.bus_number} · {routeData?.route_name}</Text>}
              </View>
              <TouchableOpacity onPress={() => setModal(false)}>
                <Text style={{ fontSize: 24, color: COLORS.textLight }}>✕</Text>
              </TouchableOpacity>
            </View>

            {loadSeats
              ? <ActivityIndicator color={COLORS.primary} style={{ marginVertical: 24 }} />
              : selBus && (
                <SeatGrid
                  capacity={selBus.capacity ?? 40}
                  bookedMap={bookedMap}
                  selectedSeat={selectedSeat}
                  onSelect={setSelSeat}
                />
              )
            }

            <Text style={s.dateInfo}>📅 Travel date: {today()}</Text>

            <TouchableOpacity
              style={[s.confirmBtn, (!selectedSeat || booking) && s.confirmBtnOff]}
              onPress={confirmBook}
              disabled={!selectedSeat || booking}
            >
              <Text style={s.confirmBtnTxt}>
                {booking ? 'Booking…' : selectedSeat ? `Confirm Seat #${selectedSeat}` : 'Select a seat first'}
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </>
  );
}

const s = StyleSheet.create({
  container:   { paddingBottom: 50 },
  header:      { backgroundColor: COLORS.primary, padding: 20 },
  routeName:   { fontSize: 20, fontWeight: '800', color: '#fff', marginBottom: 10 },
  headerPath:  { flexDirection: 'row', alignItems: 'center', gap: 8 },
  headerDot:   { width: 10, height: 10, borderRadius: 5, backgroundColor: COLORS.success },
  headerTxt:   { fontSize: 14, color: 'rgba(255,255,255,0.85)' },
  dist:        { fontSize: 12, color: 'rgba(255,255,255,0.7)', marginTop: 8 },

  map:         { height: 220, marginHorizontal: 0 },

  sectionTitle:{ fontSize: 17, fontWeight: '700', color: COLORS.text, marginTop: 20, marginBottom: 12, paddingHorizontal: 16 },

  stopRow:     { flexDirection: 'row', paddingHorizontal: 16, marginBottom: 0 },
  stopLeft:    { alignItems: 'center', width: 20, marginRight: 14 },
  stopDot:     { width: 14, height: 14, borderRadius: 7, zIndex: 1 },
  stopConnector:{ width: 2, flex: 1, backgroundColor: COLORS.border, marginBottom: -2 },
  stopInfo:    { flex: 1, paddingBottom: 18 },
  stopName:    { fontSize: 14, fontWeight: '600', color: COLORS.text, flex: 1 },
  stopRole:    { fontSize: 11, color: COLORS.textLight, marginTop: 2 },
  timeBadge:   { backgroundColor: '#E8F5E9', borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3, marginLeft: 8 },
  timeBadgeTxt:{ fontSize: 12, fontWeight: '800', color: '#2E7D32' },

  noBus:       { alignItems: 'center', padding: 24, marginHorizontal: 16 },
  noBusTxt:    { color: COLORS.textLight, textAlign: 'center' },

  busCard:     { backgroundColor: '#fff', borderRadius: 18, padding: 16, marginHorizontal: 16, marginBottom: 12, elevation: 2, shadowColor: '#000', shadowOpacity: 0.07, shadowRadius: 6 },
  busHeader:   { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 12 },
  busIconCircle:{ width: 44, height: 44, borderRadius: 22, backgroundColor: '#E3F2FD', alignItems: 'center', justifyContent: 'center' },
  busName:     { fontSize: 16, fontWeight: '800', color: COLORS.text },
  driverName:  { fontSize: 13, color: COLORS.textLight, marginTop: 2 },
  livePill:    { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: '#E8F5E9', borderRadius: 10, paddingHorizontal: 8, paddingVertical: 4 },
  liveDot:     { width: 6, height: 6, borderRadius: 3, backgroundColor: COLORS.success },
  liveTxt:     { fontSize: 10, fontWeight: '800', color: COLORS.success },
  waitPill:    { backgroundColor: '#F5F5F5', borderRadius: 10, paddingHorizontal: 8, paddingVertical: 4 },
  waitTxt:     { fontSize: 10, fontWeight: '700', color: COLORS.textLight },

  seatRow:     { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  seatTxt:     { fontSize: 13, color: COLORS.textLight },
  seatCount:   { fontSize: 13, fontWeight: '700', color: COLORS.text },
  seatBar:     { height: 6, backgroundColor: '#EEE', borderRadius: 3, marginBottom: 10, overflow: 'hidden' },
  seatFill:    { height: '100%', borderRadius: 3 },

  departure:   { fontSize: 12, color: COLORS.textLight, marginBottom: 12 },

  busActions:  { flexDirection: 'row', gap: 8 },
  trackBtn:    { flex: 1, backgroundColor: '#E3F2FD', borderRadius: 12, paddingVertical: 12, alignItems: 'center' },
  trackBtnTxt: { color: COLORS.primary, fontWeight: '700', fontSize: 14 },
  bookBtn:     { flex: 2, backgroundColor: COLORS.primary, borderRadius: 12, paddingVertical: 12, alignItems: 'center' },
  bookBtnDisabled:{ backgroundColor: '#B0BEC5' },
  bookBtnTxt:  { color: '#fff', fontWeight: '700', fontSize: 14 },

  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  sheet:   { backgroundColor: '#fff', borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: 20, paddingBottom: 36, maxHeight: '90%' },
  sheetHandle: { width: 40, height: 4, borderRadius: 2, backgroundColor: '#E0E0E0', alignSelf: 'center', marginBottom: 16 },
  sheetHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 },
  sheetTitle:  { fontSize: 20, fontWeight: '800', color: COLORS.text },
  sheetSub:    { fontSize: 13, color: COLORS.textLight, marginTop: 3 },

  dateInfo:    { fontSize: 13, color: COLORS.textLight, textAlign: 'center', marginVertical: 12 },
  confirmBtn:  { backgroundColor: COLORS.primary, borderRadius: 16, paddingVertical: 16, alignItems: 'center' },
  confirmBtnOff:{ backgroundColor: '#B0BEC5' },
  confirmBtnTxt:{ color: '#fff', fontWeight: '800', fontSize: 16 },
});

const g = StyleSheet.create({
  legend:      { flexDirection: 'row', justifyContent: 'center', gap: 12, marginBottom: 10 },
  legendItem:  { flexDirection: 'row', alignItems: 'center', gap: 4 },
  legendDot:   { width: 12, height: 12, borderRadius: 3 },
  legendTxt:   { fontSize: 11, color: COLORS.textLight },

  cabin:    { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', backgroundColor: '#ECEFF1', borderRadius: 10, paddingHorizontal: 14, paddingVertical: 8, marginBottom: 10 },
  wheel:    { width: 32, height: 32, borderRadius: 16, backgroundColor: '#37474F', alignItems: 'center', justifyContent: 'center' },
  cabinTxt: { fontSize: 13, fontWeight: '700', color: '#37474F' },
  door:     { width: 32, height: 32, borderRadius: 8, backgroundColor: '#CFD8DC', alignItems: 'center', justifyContent: 'center' },

  row:       { flexDirection: 'row', alignItems: 'center', marginBottom: 6 },
  side:      { flexDirection: 'row', gap: 4 },
  aisle:     { width: 28, alignItems: 'center' },
  aisleNum:  { fontSize: 10, color: COLORS.textLight, fontWeight: '600' },
  seat:      { width: 50, height: 50, borderRadius: 10, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: '#E0E0E0' },
  seatEmpty: { width: 50, height: 50 },
  seatIcon:  { fontSize: 16, lineHeight: 20 },
  seatNum:   { fontSize: 11, fontWeight: '800', marginTop: -2 },
  hint:      { textAlign: 'center', fontSize: 12, color: COLORS.textLight, marginTop: 8, marginBottom: 4 },
});
