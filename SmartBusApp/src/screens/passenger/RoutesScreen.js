import { useState, useCallback, useMemo } from 'react';
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  ActivityIndicator, RefreshControl, TextInput, SafeAreaView,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { passengerApi } from '../../api/index';
import { COLORS } from '../../config';

export default function RoutesScreen({ navigation }) {
  const [routes,     setRoutes]  = useState([]);
  const [loading,    setLoading] = useState(true);
  const [refreshing, setRefresh] = useState(false);
  const [error,      setError]   = useState(null);
  const [query,      setQuery]   = useState('');

  // ── Load routes — runs every time this tab gains focus ───────────────────
  const load = useCallback(async (showSpinner = false) => {
    if (showSpinner) setLoading(true);
    setError(null);
    try {
      const res = await passengerApi.getRoutes();
      const data = Array.isArray(res.data) ? res.data : [];
      setRoutes(data);
    } catch (e) {
      setError(e?.message || 'Could not load routes. Check your connection.');
    } finally {
      setLoading(false);
      setRefresh(false);
    }
  }, []);

  // Reload every time the user navigates to this tab
  useFocusEffect(
    useCallback(() => {
      load(routes.length === 0);   // show spinner only on first load
    }, [load])
  );

  // ── Search filter ─────────────────────────────────────────────────────────
  const filtered = useMemo(() => {
    if (!query.trim()) return routes;
    const q = query.trim().toLowerCase();
    return routes.filter(r =>
      r.route_name?.toLowerCase().includes(q) ||
      r.route_number?.toLowerCase().includes(q) ||
      r.start_point?.toLowerCase().includes(q) ||
      r.end_point?.toLowerCase().includes(q) ||
      r.stops?.some(s => s.stop_name?.toLowerCase().includes(q))
    );
  }, [routes, query]);

  const matchedStop = (r) => {
    if (!query.trim()) return null;
    const q = query.trim().toLowerCase();
    return r.stops?.find(s => s.stop_name?.toLowerCase().includes(q));
  };

  // ── Loading state ─────────────────────────────────────────────────────────
  if (loading) return (
    <SafeAreaView style={s.root}>
      <View style={s.center}>
        <ActivityIndicator size="large" color={COLORS.primary} />
        <Text style={s.loadTxt}>Loading routes…</Text>
      </View>
    </SafeAreaView>
  );

  // ── Error state ───────────────────────────────────────────────────────────
  if (error) return (
    <SafeAreaView style={s.root}>
      <View style={s.header}>
        <Text style={s.headerTitle}>University Bus Routes</Text>
      </View>
      <View style={s.center}>
        <Text style={{ fontSize: 48, marginBottom: 12 }}>📡</Text>
        <Text style={s.errTitle}>Connection Error</Text>
        <Text style={s.errMsg}>{error}</Text>
        <TouchableOpacity style={s.retryBtn} onPress={() => load(true)}>
          <Text style={s.retryTxt}>Try Again</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );

  // ── Main UI ───────────────────────────────────────────────────────────────
  return (
    <SafeAreaView style={s.root}>

      {/* ── Header ── */}
      <View style={s.header}>
        <Text style={s.headerTitle}>University Bus Routes</Text>
        <Text style={s.headerSub}>
          {query
            ? `${filtered.length} of ${routes.length} routes matched`
            : `${routes.length} routes · All arrive University of Jhang 8:00 AM`}
        </Text>
      </View>

      {/* ── Search ── */}
      <View style={s.searchWrap}>
        <Text style={s.searchIcon}>🔍</Text>
        <TextInput
          style={s.searchInput}
          placeholder="Route number, stop name or area…"
          placeholderTextColor={COLORS.textLight}
          value={query}
          onChangeText={setQuery}
          returnKeyType="search"
        />
        {query.length > 0 && (
          <TouchableOpacity onPress={() => setQuery('')}>
            <Text style={s.clearTxt}>✕</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* ── Route cards ── */}
      <FlatList
        data={filtered}
        keyExtractor={r => r.id}
        contentContainerStyle={s.list}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => { setRefresh(true); load(); }}
            colors={[COLORS.primary]}
          />
        }
        ListEmptyComponent={
          <View style={s.empty}>
            <Text style={s.emptyIcon}>{query ? '🔍' : '🚌'}</Text>
            <Text style={s.emptyTitle}>
              {query ? `No routes match "${query}"` : 'No routes available'}
            </Text>
            <Text style={s.emptySub}>
              {query
                ? 'Try a stop name like "Chiniot Mor" or a route number like "1-M"'
                : 'Pull down to refresh'}
            </Text>
          </View>
        }
        renderItem={({ item: r }) => {
          const hit       = matchedStop(r);
          const stopCount = r.stops?.length ?? 0;
          const firstStop = r.stops?.[0]?.stop_name ?? r.start_point ?? '—';
          const lastStop  = r.stops?.[stopCount - 1]?.stop_name ?? r.end_point ?? 'University of Jhang';

          return (
            <TouchableOpacity
              style={s.card}
              activeOpacity={0.82}
              onPress={() => navigation.navigate('RouteDetail', { routeId: r.id, routeData: r })}
            >
              {/* Left: route badge + connector + UJ badge */}
              <View style={s.badgeCol}>
                <View style={s.routeBadge}>
                  <Text style={s.routeBadgeTxt}>{r.route_number}</Text>
                </View>
                <View style={s.connLine} />
                <View style={[s.routeBadge, { backgroundColor: '#E53935' }]}>
                  <Text style={s.routeBadgeTxt}>UJ</Text>
                </View>
              </View>

              {/* Right: route info */}
              <View style={s.infoBlock}>
                <Text style={s.routeName} numberOfLines={2}>{r.route_name}</Text>

                {/* Origin → Destination */}
                <View style={s.routePath}>
                  <View style={s.dotGreen} />
                  <Text style={s.pathTxt} numberOfLines={1}>{firstStop}</Text>
                </View>
                <View style={s.vLine} />
                <View style={[s.routePath, { marginBottom: 6 }]}>
                  <View style={s.dotRed} />
                  <Text style={s.pathTxt} numberOfLines={1}>{lastStop}</Text>
                </View>

                {/* Chips */}
                <View style={s.metaRow}>
                  <View style={[s.chip, { backgroundColor: '#E8F5E9' }]}>
                    <Text style={[s.chipTxt, { color: '#2E7D32' }]}>⏰ 7:00 AM</Text>
                  </View>
                  <View style={[s.chip, { backgroundColor: '#FFF3E0' }]}>
                    <Text style={[s.chipTxt, { color: '#E65100' }]}>🏫 8:00 AM</Text>
                  </View>
                  <View style={[s.chip, { backgroundColor: '#F3E5F5' }]}>
                    <Text style={[s.chipTxt, { color: '#6A1B9A' }]}>🛑 {stopCount} stops</Text>
                  </View>
                  {r.distance_km && (
                    <View style={[s.chip, { backgroundColor: '#E3F2FD' }]}>
                      <Text style={[s.chipTxt, { color: '#1565C0' }]}>📏 {Number(r.distance_km).toFixed(1)} km</Text>
                    </View>
                  )}
                </View>

                {/* Matched stop highlight */}
                {hit && (
                  <View style={s.hitStop}>
                    <Text style={s.hitIco}>📍</Text>
                    <Text style={s.hitTxt}>
                      Stops at <Text style={{ fontWeight: '800' }}>{hit.stop_name}</Text>
                    </Text>
                  </View>
                )}
              </View>

              <Text style={s.chevron}>›</Text>
            </TouchableOpacity>
          );
        }}
      />
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  root:    { flex: 1, backgroundColor: COLORS.bg },
  center:  { flex: 1, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 30 },
  loadTxt: { color: COLORS.textLight, marginTop: 10 },

  header:      { backgroundColor: '#fff', paddingHorizontal: 20, paddingTop: 14, paddingBottom: 14, borderBottomWidth: 1, borderBottomColor: '#F0F0F0' },
  headerTitle: { fontSize: 22, fontWeight: '800', color: COLORS.text },
  headerSub:   { fontSize: 12, color: COLORS.textLight, marginTop: 3 },

  errTitle: { fontSize: 18, fontWeight: '700', color: COLORS.text, marginBottom: 8, textAlign: 'center' },
  errMsg:   { fontSize: 13, color: COLORS.textLight, textAlign: 'center', lineHeight: 20, marginBottom: 20 },
  retryBtn: { backgroundColor: COLORS.primary, borderRadius: 14, paddingHorizontal: 28, paddingVertical: 12 },
  retryTxt: { color: '#fff', fontWeight: '700', fontSize: 15 },

  searchWrap:  { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', margin: 12, borderRadius: 14, paddingHorizontal: 14, paddingVertical: 10, elevation: 2, shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 4 },
  searchIcon:  { fontSize: 16, marginRight: 8 },
  searchInput: { flex: 1, fontSize: 15, color: COLORS.text, paddingVertical: 2 },
  clearTxt:    { color: COLORS.textLight, fontSize: 16, fontWeight: '700', paddingLeft: 8 },

  list:      { paddingHorizontal: 12, paddingBottom: 40 },
  empty:     { alignItems: 'center', paddingTop: 60, paddingHorizontal: 30 },
  emptyIcon: { fontSize: 52, marginBottom: 12 },
  emptyTitle:{ fontSize: 16, color: COLORS.textLight, textAlign: 'center', fontWeight: '700', marginBottom: 6 },
  emptySub:  { fontSize: 13, color: COLORS.textLight, textAlign: 'center', lineHeight: 20 },

  card: {
    flexDirection: 'row', alignItems: 'flex-start',
    backgroundColor: '#fff', borderRadius: 18, padding: 14, marginBottom: 10,
    elevation: 2, shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 6, shadowOffset: { width: 0, height: 2 },
  },

  badgeCol:      { alignItems: 'center', marginRight: 12, paddingTop: 4 },
  routeBadge:    { backgroundColor: COLORS.primary, borderRadius: 10, paddingHorizontal: 8, paddingVertical: 5, minWidth: 48, alignItems: 'center' },
  routeBadgeTxt: { color: '#fff', fontSize: 13, fontWeight: '800' },
  connLine:      { width: 2, height: 32, backgroundColor: COLORS.border, marginVertical: 4 },

  infoBlock:  { flex: 1 },
  routeName:  { fontSize: 14, fontWeight: '800', color: COLORS.text, marginBottom: 8 },
  routePath:  { flexDirection: 'row', alignItems: 'center', gap: 6 },
  vLine:      { width: 1.5, height: 10, backgroundColor: COLORS.border, marginLeft: 3, marginVertical: 2 },
  dotGreen:   { width: 8, height: 8, borderRadius: 4, backgroundColor: COLORS.success },
  dotRed:     { width: 8, height: 8, borderRadius: 4, backgroundColor: '#E53935' },
  pathTxt:    { fontSize: 12, color: COLORS.textLight, flex: 1 },

  metaRow: { flexDirection: 'row', gap: 5, flexWrap: 'wrap' },
  chip:    { borderRadius: 8, paddingHorizontal: 7, paddingVertical: 3 },
  chipTxt: { fontSize: 11, fontWeight: '600' },

  hitStop: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 8, backgroundColor: '#FFF8E1', borderRadius: 8, paddingHorizontal: 8, paddingVertical: 4 },
  hitIco:  { fontSize: 13 },
  hitTxt:  { fontSize: 12, color: '#E65100' },

  chevron: { fontSize: 26, color: COLORS.textLight, marginLeft: 6, marginTop: 2 },
});
