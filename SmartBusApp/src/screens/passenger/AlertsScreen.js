import { useState, useEffect, useCallback } from 'react';
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  ActivityIndicator, RefreshControl, SafeAreaView,
} from 'react-native';
import { passengerApi } from '../../api/index';
import { COLORS } from '../../config';

const TYPE_CONFIG = {
  arriving:  { icon: '🚌', color: COLORS.success,  label: 'Bus Arriving' },
  delay:     { icon: '⏰', color: COLORS.warning,  label: 'Delay'        },
  emergency: { icon: '🚨', color: COLORS.danger,   label: 'Emergency'    },
  cancelled: { icon: '❌', color: COLORS.danger,   label: 'Cancelled'    },
  broadcast: { icon: '📢', color: COLORS.primary,  label: 'Announcement' },
};

export default function AlertsScreen() {
  const [notifs,    setNotifs]   = useState([]);
  const [loading,   setLoading]  = useState(true);
  const [refreshing,setRefresh]  = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await passengerApi.myNotifications();
      setNotifs(res.data ?? []);
    } catch (_) {}
    finally { setLoading(false); setRefresh(false); }
  }, []);

  useEffect(() => { load(); }, []);

  const markRead = async (id) => {
    try { await passengerApi.markRead(id); load(); } catch (_) {}
  };

  const unread = notifs.filter(n => !n.is_read).length;

  if (loading) return (
    <SafeAreaView style={s.root}>
      <View style={s.center}>
        <ActivityIndicator size="large" color={COLORS.primary} />
      </View>
    </SafeAreaView>
  );

  return (
    <SafeAreaView style={s.root}>
      <View style={s.header}>
        <Text style={s.headerTitle}>Alerts</Text>
        {unread > 0 && (
          <View style={s.badge}><Text style={s.badgeTxt}>{unread} new</Text></View>
        )}
      </View>

      <FlatList
        data={notifs}
        keyExtractor={n => n.id}
        contentContainerStyle={s.list}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefresh(true); load(); }} />}
        ListEmptyComponent={
          <View style={s.empty}>
            <Text style={s.emptyIcon}>🔔</Text>
            <Text style={s.emptyTitle}>No alerts yet</Text>
            <Text style={s.emptySub}>You'll see bus alerts and announcements here</Text>
          </View>
        }
        renderItem={({ item: n }) => {
          const cfg = TYPE_CONFIG[n.type] ?? TYPE_CONFIG.broadcast;
          return (
            <TouchableOpacity
              style={[s.card, !n.is_read && s.cardUnread]}
              onPress={() => !n.is_read && markRead(n.id)}
              activeOpacity={0.8}
            >
              <View style={[s.iconBox, { backgroundColor: cfg.color + '20' }]}>
                <Text style={s.icon}>{cfg.icon}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <View style={s.topRow}>
                  <Text style={s.typeLbl}>{cfg.label}</Text>
                  <Text style={s.time}>{new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</Text>
                </View>
                <Text style={s.title}>{n.title}</Text>
                <Text style={s.msg}>{n.message}</Text>
                {!n.is_read && <Text style={s.tapHint}>Tap to mark as read</Text>}
              </View>
            </TouchableOpacity>
          );
        }}
      />
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  root:   { flex: 1, backgroundColor: COLORS.bg },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },

  header:      { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: '#fff', paddingHorizontal: 20, paddingTop: 54, paddingBottom: 16, borderBottomWidth: 1, borderBottomColor: '#F0F0F0' },
  headerTitle: { fontSize: 22, fontWeight: '800', color: COLORS.text, flex: 1 },
  badge:       { backgroundColor: COLORS.danger, borderRadius: 12, paddingHorizontal: 10, paddingVertical: 4 },
  badgeTxt:    { color: '#fff', fontSize: 12, fontWeight: '700' },

  list: { padding: 16, paddingBottom: 40 },

  empty:      { alignItems: 'center', paddingTop: 80, gap: 10 },
  emptyIcon:  { fontSize: 56 },
  emptyTitle: { fontSize: 18, fontWeight: '700', color: COLORS.textLight },
  emptySub:   { fontSize: 14, color: COLORS.border, textAlign: 'center' },

  card:       { flexDirection: 'row', gap: 12, backgroundColor: '#fff', borderRadius: 16, padding: 14, marginBottom: 10, elevation: 1, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 4 },
  cardUnread: { borderLeftWidth: 4, borderLeftColor: COLORS.primary },
  iconBox:    { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center' },
  icon:       { fontSize: 20 },
  topRow:     { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  typeLbl:    { fontSize: 11, fontWeight: '700', color: COLORS.textLight, textTransform: 'uppercase', letterSpacing: 0.5 },
  time:       { fontSize: 11, color: COLORS.textLight },
  title:      { fontSize: 14, fontWeight: '700', color: COLORS.text, marginBottom: 3 },
  msg:        { fontSize: 13, color: COLORS.textLight, lineHeight: 18 },
  tapHint:    { fontSize: 11, color: COLORS.primary, marginTop: 6, fontWeight: '600' },
});
