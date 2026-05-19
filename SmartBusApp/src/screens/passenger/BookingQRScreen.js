import { View, Text, StyleSheet, TouchableOpacity, Share, ScrollView } from 'react-native';
import QRCode from 'react-native-qrcode-svg';
import { COLORS } from '../../config';

export default function BookingQRScreen({ route, navigation }) {
  const { booking } = route.params;
  // booking = { id, seat_number, bus_number, route_name, booking_date, status }

  // QR payload — compact JSON that driver/admin scans to verify
  const qrPayload = JSON.stringify({
    bid:  booking.id,
    seat: booking.seat_number,
    bus:  booking.bus_number  || '—',
    rt:   booking.route_name  || '—',
    date: booking.booking_date,
    st:   booking.status,
  });

  const shareTicket = async () => {
    await Share.share({
      message:
        `SmartBus Ticket\n` +
        `Booking ID: ${booking.id}\n` +
        `Seat: #${booking.seat_number}\n` +
        `Bus: ${booking.bus_number || '—'}\n` +
        `Route: ${booking.route_name || '—'}\n` +
        `Date: ${booking.booking_date}\n` +
        `Status: ${booking.status}`,
    });
  };

  return (
    <ScrollView style={s.root} contentContainerStyle={s.content}>

      {/* Header */}
      <View style={s.header}>
        <Text style={s.headerEmoji}>🎫</Text>
        <Text style={s.headerTitle}>Booking Confirmed!</Text>
        <Text style={s.headerSub}>Show this QR to the driver when boarding</Text>
      </View>

      {/* QR Code */}
      <View style={s.qrCard}>
        <QRCode
          value={qrPayload}
          size={200}
          color="#1A237E"
          backgroundColor="#ffffff"
          ecl="M"
        />
        <Text style={s.qrHint}>Scan to verify boarding</Text>
      </View>

      {/* Ticket details */}
      <View style={s.ticketCard}>
        <View style={s.ticketTop}>
          <Text style={s.ticketBus}>{booking.bus_number || 'Bus'}</Text>
          <View style={[s.statusPill, { backgroundColor: booking.status === 'confirmed' ? COLORS.success : COLORS.warning }]}>
            <Text style={s.statusTxt}>{(booking.status || 'pending').toUpperCase()}</Text>
          </View>
        </View>

        <View style={s.divider} />

        <View style={s.detailRow}>
          <Text style={s.detailLabel}>Seat</Text>
          <Text style={s.detailValue}>#{booking.seat_number}</Text>
        </View>
        <View style={s.detailRow}>
          <Text style={s.detailLabel}>Route</Text>
          <Text style={s.detailValue} numberOfLines={1}>{booking.route_name || '—'}</Text>
        </View>
        <View style={s.detailRow}>
          <Text style={s.detailLabel}>Date</Text>
          <Text style={s.detailValue}>{booking.booking_date}</Text>
        </View>
        <View style={s.detailRow}>
          <Text style={s.detailLabel}>Booking ID</Text>
          <Text style={[s.detailValue, { fontSize: 11, color: COLORS.textLight }]} numberOfLines={1}>
            {booking.id}
          </Text>
        </View>

        <View style={s.divider} />

        {/* Payment notice */}
        <View style={s.paymentBox}>
          <Text style={s.paymentIcon}>💳</Text>
          <View style={{ flex: 1 }}>
            <Text style={s.paymentTitle}>Payment</Text>
            <Text style={s.paymentDesc}>Pay fare to the driver on boarding. Show this QR code as your seat reservation.</Text>
          </View>
        </View>
      </View>

      {/* Actions */}
      <TouchableOpacity style={s.shareBtn} onPress={shareTicket}>
        <Text style={s.shareTxt}>📤  Share Ticket</Text>
      </TouchableOpacity>

      <TouchableOpacity style={s.doneBtn} onPress={() => navigation.popToTop()}>
        <Text style={s.doneTxt}>✓  Back to Dashboard</Text>
      </TouchableOpacity>

    </ScrollView>
  );
}

const s = StyleSheet.create({
  root:    { flex: 1, backgroundColor: COLORS.bg },
  content: { padding: 20, paddingBottom: 50, alignItems: 'center' },

  header:      { alignItems: 'center', marginBottom: 24 },
  headerEmoji: { fontSize: 48, marginBottom: 8 },
  headerTitle: { fontSize: 24, fontWeight: '800', color: COLORS.text },
  headerSub:   { fontSize: 14, color: COLORS.textLight, marginTop: 4, textAlign: 'center' },

  qrCard:  { backgroundColor: '#fff', borderRadius: 20, padding: 24, alignItems: 'center', elevation: 4, shadowColor: '#000', shadowOpacity: 0.12, shadowRadius: 8, shadowOffset: { width: 0, height: 4 }, marginBottom: 20 },
  qrHint:  { marginTop: 12, fontSize: 12, color: COLORS.textLight, fontWeight: '600' },

  ticketCard: { backgroundColor: '#fff', borderRadius: 20, padding: 20, width: '100%', elevation: 3, shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 6, shadowOffset: { width: 0, height: 3 }, marginBottom: 20 },
  ticketTop:  { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  ticketBus:  { fontSize: 22, fontWeight: '800', color: COLORS.text },
  statusPill: { borderRadius: 10, paddingHorizontal: 12, paddingVertical: 4 },
  statusTxt:  { color: '#fff', fontSize: 11, fontWeight: '800' },

  divider:     { height: 1, backgroundColor: COLORS.border, marginVertical: 12 },

  detailRow:   { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginVertical: 5 },
  detailLabel: { fontSize: 13, color: COLORS.textLight, fontWeight: '600' },
  detailValue: { fontSize: 14, fontWeight: '700', color: COLORS.text, flex: 1, textAlign: 'right' },

  paymentBox:  { flexDirection: 'row', alignItems: 'flex-start', gap: 10, backgroundColor: '#E3F2FD', borderRadius: 12, padding: 12, marginTop: 4 },
  paymentIcon: { fontSize: 22 },
  paymentTitle:{ fontSize: 13, fontWeight: '700', color: COLORS.primary, marginBottom: 2 },
  paymentDesc: { fontSize: 12, color: COLORS.textLight, lineHeight: 18 },

  shareBtn: { backgroundColor: COLORS.primary, borderRadius: 14, paddingVertical: 14, paddingHorizontal: 32, width: '100%', alignItems: 'center', marginBottom: 12 },
  shareTxt: { color: '#fff', fontSize: 16, fontWeight: '700' },
  doneBtn:  { backgroundColor: '#fff', borderRadius: 14, paddingVertical: 14, paddingHorizontal: 32, width: '100%', alignItems: 'center', borderWidth: 2, borderColor: COLORS.border },
  doneTxt:  { color: COLORS.text, fontSize: 16, fontWeight: '700' },
});
