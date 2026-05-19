import { useState, useEffect, useCallback } from 'react';
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  Alert, ActivityIndicator, RefreshControl, SafeAreaView,
} from 'react-native';
import { passengerApi } from '../../api/index';
import { COLORS } from '../../config';

const STATUS_CONFIG = {
  confirmed:  { color: COLORS.success,  bg: '#E8F5E9', label: 'Confirmed' },
  pending:    { color: '#F57C00',        bg: '#FFF3E0', label: 'Pending'   },
  cancelled:  { color: COLORS.danger,   bg: '#FFEBEE', label: 'Cancelled' },
  completed:  { color: COLORS.textLight,bg: '#F5F5F5', label: 'Completed' },
};

export default function MyTripsScreen({ navigation }) {
  const [bookings,   setBookings]  = useState([]);
  const [loading,    setLoading]   = useState(true);
  const [refreshing, setRefresh]   = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await passengerApi.myBookings();
      setBookings(res.data ?? []);
    } catch (_) {}
    finally { setLoading(false); setRefresh(false); }
  }, []);

  useEffect(() => { load(); }, []);

  const cancelBooking = (id, seat, date) => {
    Alert.alert(
      'Cancel Booking?',
      `Seat #${seat} on ${date}`,
      [
        { text: 'Keep It' },
        { text: 'Cancel Booking', style: 'destructive', onPress: async () => {
          try { await passengerApi.cancelBooking(id, {}); load(); }
          catch (e) { Alert.alert('Error', 'Could not cancel booking.'); }
        }},
      ]
    );
  };

  if (loading) return (
    <SafeAreaView style={s.root}>
      <View style={s.center}>
        <ActivityIndicator size="large" color={COLORS.primary} />
        <Text style={s.loadTxt}>Loading your trips…</Text>
      </View>
    </SafeAreaView>
  );

  return (
    <SafeAreaView style={s.root}>
      {/* Header */}
      <View style={s.header}>
        <Text style={s.headerTitle}>My Trips</Text>
        <Text style={s.headerSub}>{bookings.length} booking{bookings.length !== 1 ? 's' : ''}</Text>
      </View>

      <FlatList
        data={bookings}
        keyExtractor={b => b.id}
        contentContainerStyle={s.list}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefresh(true); load(); }} />}
        ListEmptyComponent={
          <View style={s.empty}>
            <Text style={s.emptyIcon}>🎫</Text>
            <Text style={s.emptyTitle}>No bookings yet</Text>
            <Text style={s.emptySub}>Browse routes and book your first seat</Text>
          </View>
        }
        renderItem={({ item: b }) => {
          const cfg = STATUS_CONFIG[b.status] ?? STATUS_CONFIG.pending;
          return (
            <View style={s.card}>
              {/* Status pill */}
              <View style={[s.statusPill, { backgroundColor: cfg.bg }]}>
                <Text style={[s.statusTxt, { color: cfg.color }]}>{cfg.label}</Text>
              </View>

              {/* Main info */}
              <View style={s.cardRow}>
                <View style={s.seatCircle}>
                  <Text style={s.seatNum}>{b.seat_number}</Text>
                  <Text style={s.seatLbl}>Seat</Text>
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={s.cardDate}>📅 {b.booking_date}</Text>
                  <Text style={s.cardTime}>⏰ Booked {new Date(b.booked_at).toLocaleDateString()}</Text>
                  {b.cancellation_reason && (
                    <Text style={s.cancelReason}>Reason: {b.cancellation_reason}</Text>
                  )}
                </View>
              </View>

              {/* Actions */}
              <View style={s.actions}>
                {(b.status === 'confirmed' || b.status === 'pending') && (
                  <>
                    <TouchableOpacity
                      style={s.qrBtn}
                      onPress={() => navigation.navigate('BookingQR', { booking: b })}
                    >
                      <Text style={s.qrBtnTxt}>📲 Show Ticket</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={s.cancelBtn}
                      onPress={() => cancelBooking(b.id, b.seat_number, b.booking_date)}
                    >
                      <Text style={s.cancelBtnTxt}>Cancel</Text>
                    </TouchableOpacity>
                  </>
                )}
                {b.status === 'completed' && (
                  <TouchableOpacity
                    style={s.qrBtn}
                    onPress={() => navigation.navigate('BookingQR', { booking: b })}
                  >
                    <Text style={s.qrBtnTxt}>📋 View Ticket</Text>
                  </TouchableOpacity>
                )}
              </View>
            </View>
          );
        }}
      />
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  root:   { flex: 1, backgroundColor: COLORS.bg },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 10 },
  loadTxt:{ color: COLORS.textLight },

  header:      { backgroundColor: '#fff', paddingHorizontal: 20, paddingTop: 54, paddingBottom: 16, borderBottomWidth: 1, borderBottomColor: '#F0F0F0' },
  headerTitle: { fontSize: 22, fontWeight: '800', color: COLORS.text },
  headerSub:   { fontSize: 13, color: COLORS.textLight, marginTop: 2 },

  list: { padding: 16, paddingBottom: 40 },

  empty:      { alignItems: 'center', paddingTop: 80, gap: 10 },
  emptyIcon:  { fontSize: 56 },
  emptyTitle: { fontSize: 18, fontWeight: '700', color: COLORS.textLight },
  emptySub:   { fontSize: 14, color: COLORS.border, textAlign: 'center' },

  card: { backgroundColor: '#fff', borderRadius: 18, padding: 16, marginBottom: 14, elevation: 2, shadowColor: '#000', shadowOpacity: 0.07, shadowRadius: 6, shadowOffset: { width: 0, height: 2 } },

  statusPill: { borderRadius: 20, paddingHorizontal: 12, paddingVertical: 4, alignSelf: 'flex-start', marginBottom: 12 },
  statusTxt:  { fontSize: 12, fontWeight: '700' },

  cardRow:    { flexDirection: 'row', alignItems: 'center', gap: 14, marginBottom: 14 },
  seatCircle: { width: 60, height: 60, borderRadius: 30, backgroundColor: COLORS.primary, alignItems: 'center', justifyContent: 'center' },
  seatNum:    { color: '#fff', fontSize: 22, fontWeight: '800', lineHeight: 26 },
  seatLbl:    { color: 'rgba(255,255,255,0.8)', fontSize: 10, fontWeight: '600' },

  cardDate:   { fontSize: 15, fontWeight: '700', color: COLORS.text, marginBottom: 4 },
  cardTime:   { fontSize: 13, color: COLORS.textLight },
  cancelReason:{ fontSize: 12, color: COLORS.danger, marginTop: 4 },

  actions:    { flexDirection: 'row', gap: 8 },
  qrBtn:      { flex: 2, backgroundColor: COLORS.primary, borderRadius: 12, paddingVertical: 11, alignItems: 'center' },
  qrBtnTxt:   { color: '#fff', fontWeight: '700', fontSize: 14 },
  cancelBtn:  { flex: 1, backgroundColor: '#FFF0F0', borderRadius: 12, paddingVertical: 11, alignItems: 'center' },
  cancelBtnTxt:{ color: COLORS.danger, fontWeight: '700', fontSize: 14 },
});
