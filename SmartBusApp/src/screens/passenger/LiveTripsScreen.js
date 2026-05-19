import { useState, useEffect, useCallback } from 'react';
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  ActivityIndicator, RefreshControl,
} from 'react-native';
import { passengerApi } from '../../api/index';
import { Badge, statusColor } from '../../components/UI';
import { COLORS } from '../../config';

export default function LiveTripsScreen({ navigation }) {
  const [buses, setBuses]       = useState([]);
  const [loading, setLoading]   = useState(true);
  const [refreshing, setRefresh] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await passengerApi.getLiveBuses();
      // Show only buses that are currently on a trip
      setBuses((res.data ?? []).filter((b) => b.active_trip_id));
    } catch (e) {}
    finally { setLoading(false); setRefresh(false); }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 15000); // auto-refresh every 15 s
    return () => clearInterval(interval);
  }, [load]);

  if (loading) return (
    <View style={s.center}>
      <ActivityIndicator size="large" color={COLORS.primary} />
      <Text style={s.loadTxt}>Loading live buses…</Text>
    </View>
  );

  return (
    <FlatList
      data={buses}
      keyExtractor={(b) => b.bus_id}
      contentContainerStyle={s.list}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefresh(true); load(); }} />}
      ListEmptyComponent={
        <View style={s.emptyBox}>
          <Text style={s.emptyIcon}>🚏</Text>
          <Text style={s.emptyTxt}>No buses are currently on a trip.</Text>
          <Text style={s.emptyHint}>Pull down to refresh.</Text>
        </View>
      }
      renderItem={({ item: b }) => (
        <TouchableOpacity
          style={s.card}
          activeOpacity={0.82}
          onPress={() => navigation.navigate('LiveMap', {
            tripId:     b.active_trip_id,
            busId:      b.bus_id,
            routeId:    b.route_id,
            busNumber:  b.bus_number,
            driverName: b.driver_name,
            routeName:  b.route_name,
          })}
        >
          {/* Header row */}
          <View style={s.row}>
            <View style={s.busIcon}><Text style={{ fontSize: 22 }}>🚌</Text></View>
            <View style={{ flex: 1 }}>
              <Text style={s.busNum}>{b.bus_number}</Text>
              <Text style={s.routeName}>{b.route_name ?? '—'}  ({b.route_number ?? '—'})</Text>
            </View>
            <Badge label={b.status} color={statusColor(b.status)} />
          </View>

          {/* Details */}
          <View style={s.details}>
            {b.driver_name ? <Text style={s.detail}>👤 {b.driver_name}  ·  {b.driver_code}</Text> : null}
            <Text style={s.detail}>💺 {b.available_seats}/{b.capacity} seats free</Text>
            {b.latitude && b.longitude
              ? <Text style={s.detail}>📍 {Number(b.latitude).toFixed(4)}, {Number(b.longitude).toFixed(4)}</Text>
              : <Text style={s.detailGrey}>📍 Location not yet received</Text>}
          </View>

          {/* Track button */}
          <View style={s.trackBtn}>
            <Text style={s.trackTxt}>📡 Track on Map  →</Text>
          </View>
        </TouchableOpacity>
      )}
    />
  );
}

const s = StyleSheet.create({
  list:    { padding: 14, paddingBottom: 40 },
  center:  { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 10 },
  loadTxt: { color: COLORS.textLight },

  emptyBox: { flex: 1, alignItems: 'center', paddingTop: 80, gap: 10 },
  emptyIcon:{ fontSize: 56 },
  emptyTxt: { fontSize: 16, fontWeight: '600', color: COLORS.textLight },
  emptyHint:{ fontSize: 13, color: COLORS.border },

  card: {
    backgroundColor: '#fff', borderRadius: 16, padding: 16, marginBottom: 14,
    elevation: 3, shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 6, shadowOffset: { width: 0, height: 3 },
  },
  row:       { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 10 },
  busIcon:   { width: 46, height: 46, borderRadius: 23, backgroundColor: '#E3F2FD', alignItems: 'center', justifyContent: 'center' },
  busNum:    { fontSize: 18, fontWeight: '800', color: COLORS.text },
  routeName: { fontSize: 13, color: COLORS.textLight, marginTop: 2 },

  details:    { gap: 4, marginBottom: 12 },
  detail:     { fontSize: 13, color: COLORS.textLight },
  detailGrey: { fontSize: 13, color: '#BDBDBD', fontStyle: 'italic' },

  trackBtn: { backgroundColor: COLORS.primary, borderRadius: 10, padding: 11, alignItems: 'center' },
  trackTxt: { color: '#fff', fontWeight: '700', fontSize: 14 },
});