import { useState, useEffect } from 'react';
import {
  View, Text, ScrollView, StyleSheet, RefreshControl,
  SafeAreaView, Alert, TouchableOpacity,
} from 'react-native';
import { useAuth } from '../../context/AuthContext';
import { passengerApi } from '../../api/index';
import { Card, SectionTitle, Badge, Row, showError, statusColor } from '../../components/UI';
import { COLORS } from '../../config';

export default function PassengerDashboard({ navigation }) {
  const { user, logout } = useAuth();
  const [bookings,  setBookings]  = useState([]);
  const [notifs,    setNotifs]    = useState([]);
  const [profile,   setProfile]   = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    try {
      const [pRes, bRes, nRes] = await Promise.all([
        passengerApi.getProfile().catch(() => null),
        passengerApi.myBookings().catch(() => null),
        passengerApi.myNotifications().catch(() => null),
      ]);
      if (pRes) setProfile(pRes.data);
      if (bRes) setBookings(bRes.data);
      if (nRes) setNotifs(nRes.data);
    } catch (e) { showError(e); }
  };

  useEffect(() => { load(); }, []);
  const onRefresh = async () => { setRefreshing(true); await load(); setRefreshing(false); };

  const doCancel = (id) => Alert.alert('Cancel Booking?', '', [
    { text: 'No' },
    { text: 'Yes, Cancel', style: 'destructive', onPress: async () => {
      try { await passengerApi.cancelBooking(id, {}); load(); } catch (e) { showError(e); }
    }},
  ]);

  const markRead = async (id) => {
    try { await passengerApi.markRead(id); load(); } catch {}
  };

  const unread = notifs.filter((n) => !n.is_read).length;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: COLORS.bg }}>
      <ScrollView
        contentContainerStyle={s.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {/* ── Welcome card ─────────────────────────────────────────────────── */}
        <Card style={s.heroCard}>
          <Text style={s.hi}>👋 Hello, {user?.full_name?.split(' ')[0] ?? 'Passenger'}</Text>
          <Text style={s.email}>{user?.email}</Text>
          {profile && (
            <Text style={s.profileLine}>
              🎓 {profile.university_id ?? '—'}  ·  {profile.student_type ?? '—'}
            </Text>
          )}

          {/* Quick-action row */}
          <Row style={s.quickRow}>
            <TouchableOpacity style={s.quickBtn} onPress={() => navigation.navigate('RoutesTab')}>
              <Text style={s.quickEmoji}>🗺</Text>
              <Text style={s.quickLbl}>Browse{'\n'}Routes</Text>
            </TouchableOpacity>
            <TouchableOpacity style={s.quickBtn} onPress={() => navigation.navigate('LiveTab')}>
              <Text style={s.quickEmoji}>📡</Text>
              <Text style={s.quickLbl}>Live{'\n'}Tracking</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[s.quickBtn, { backgroundColor: 'rgba(229,57,53,0.15)' }]} onPress={logout}>
              <Text style={s.quickEmoji}>🚪</Text>
              <Text style={[s.quickLbl, { color: COLORS.danger }]}>Log{'\n'}Out</Text>
            </TouchableOpacity>
          </Row>
        </Card>

        {/* ── My Bookings ──────────────────────────────────────────────────── */}
        <SectionTitle>🎫 My Bookings</SectionTitle>
        {bookings.length === 0
          ? (
            <Card>
              <Text style={s.empty}>No bookings yet.</Text>
              <TouchableOpacity onPress={() => navigation.navigate('RoutesTab')}>
                <Text style={{ color: COLORS.primary, fontWeight: '600', marginTop: 6 }}>Browse routes →</Text>
              </TouchableOpacity>
            </Card>
          )
          : bookings.map((b) => (
            <Card key={b.id}>
              <Row style={{ justifyContent: 'space-between' }}>
                <Text style={s.seatNum}>Seat #{b.seat_number}</Text>
                <Badge label={b.status} color={statusColor(b.status)} />
              </Row>
              <Text style={s.info}>📅 {b.booking_date}</Text>
              {b.status !== 'cancelled' && b.status !== 'completed' && (
                <TouchableOpacity style={s.cancelBtn} onPress={() => doCancel(b.id)}>
                  <Text style={s.cancelTxt}>Cancel Booking</Text>
                </TouchableOpacity>
              )}
            </Card>
          ))
        }

        {/* ── Notifications ────────────────────────────────────────────────── */}
        <SectionTitle>🔔 Notifications  {unread > 0 ? `(${unread} new)` : ''}</SectionTitle>
        {notifs.length === 0
          ? <Card><Text style={s.empty}>No notifications.</Text></Card>
          : notifs.slice(0, 6).map((n) => (
            <Card key={n.id} style={!n.is_read ? s.unread : undefined}>
              <Row style={{ justifyContent: 'space-between' }}>
                <Text style={s.notifTitle} numberOfLines={1}>{n.title}</Text>
                <Badge label={n.type} color={statusColor(n.type)} />
              </Row>
              <Text style={s.info}>{n.message}</Text>
              {!n.is_read && (
                <TouchableOpacity onPress={() => markRead(n.id)}>
                  <Text style={{ color: COLORS.primary, fontSize: 12, marginTop: 6 }}>Mark as read</Text>
                </TouchableOpacity>
              )}
            </Card>
          ))
        }
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  content:   { padding: 16, paddingBottom: 40 },
  heroCard:  { backgroundColor: COLORS.primary, marginBottom: 4 },
  hi:        { fontSize: 22, fontWeight: '800', color: '#fff' },
  email:     { fontSize: 13, color: 'rgba(255,255,255,0.75)', marginTop: 2 },
  profileLine: { fontSize: 13, color: 'rgba(255,255,255,0.70)', marginTop: 4 },

  quickRow:  { marginTop: 16, gap: 10 },
  quickBtn:  { flex: 1, backgroundColor: 'rgba(255,255,255,0.18)', borderRadius: 12, padding: 12, alignItems: 'center', gap: 6 },
  quickEmoji:{ fontSize: 26 },
  quickLbl:  { color: '#fff', fontSize: 12, fontWeight: '700', textAlign: 'center', lineHeight: 16 },

  seatNum:   { fontSize: 15, fontWeight: '700', color: COLORS.text },
  info:      { fontSize: 13, color: COLORS.textLight, marginTop: 4 },
  cancelBtn: { marginTop: 8, backgroundColor: '#FFEBEE', borderRadius: 8, padding: 8, alignItems: 'center' },
  cancelTxt: { color: COLORS.danger, fontWeight: '600', fontSize: 13 },
  empty:     { color: COLORS.textLight, textAlign: 'center' },
  unread:    { borderLeftWidth: 3, borderLeftColor: COLORS.primary },
  notifTitle:{ fontSize: 14, fontWeight: '700', color: COLORS.text, flex: 1 },
});