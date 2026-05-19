import { useState, useEffect } from 'react';
import { View, Text, StyleSheet, SafeAreaView, ActivityIndicator } from 'react-native';
import { COLORS, API_URL } from '../config';
import { Btn } from '../components/UI';
import client from '../api/client';

const ROLES = [
  { label: '🎓  Passenger',  screen: 'PassengerAuth', color: COLORS.primary },
  { label: '🚌  Driver',     screen: 'DriverAuth',    color: COLORS.secondary },
  { label: '🛠   Admin',      screen: 'AdminAuth',     color: '#6A1B9A' },
  { label: '👨‍👧  Parent',     screen: 'ParentAuth',    color: '#E65100' },
];

export default function WelcomeScreen({ navigation }) {
  const [status, setStatus] = useState('checking'); // 'checking' | 'ok' | 'error'

  // Ping backend when screen loads
  useEffect(() => {
    client.get('/')
      .then(() => setStatus('ok'))
      .catch(() => setStatus('error'));
  }, []);

  const retry = () => {
    setStatus('checking');
    client.get('/')
      .then(() => setStatus('ok'))
      .catch(() => setStatus('error'));
  };

  return (
    <SafeAreaView style={s.safe}>
      {/* Hero */}
      <View style={s.hero}>
        <Text style={s.icon}>🚍</Text>
        <Text style={s.title}>Smart Bus</Text>
        <Text style={s.subtitle}>Monitoring System</Text>

        {/* Connection indicator */}
        <View style={s.connRow}>
          {status === 'checking' && (
            <>
              <ActivityIndicator size="small" color="rgba(255,255,255,0.7)" />
              <Text style={s.connText}>  Connecting to backend...</Text>
            </>
          )}
          {status === 'ok' && (
            <Text style={[s.connText, { color: '#A5D6A7' }]}>
              ● Backend connected  ({API_URL})
            </Text>
          )}
          {status === 'error' && (
            <Text style={[s.connText, { color: '#EF9A9A' }]}>
              ● Cannot reach backend  ({API_URL})
            </Text>
          )}
        </View>
      </View>

      {/* Role buttons */}
      <View style={s.body}>
        <Text style={s.prompt}>Select your role to continue</Text>

        {ROLES.map((r) => (
          <Btn
            key={r.screen}
            title={r.label}
            color={r.color}
            disabled={status !== 'ok'}
            onPress={() => navigation.navigate(r.screen)}
          />
        ))}

        {status === 'error' && (
          <>
            <Text style={s.errText}>
              Make sure the backend is running:{'\n'}
              <Text style={s.errCmd}>uvicorn app.main:app --reload</Text>
              {'\n\n'}
              Then check API_URL in src/config.js:{'\n'}
              <Text style={s.errCmd}>
                Android emulator → 10.0.2.2{'\n'}
                Physical device  → your PC's IP
              </Text>
            </Text>
            <Btn title="Retry Connection" color={COLORS.warning} onPress={retry} />
          </>
        )}
      </View>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe:    { flex:1, backgroundColor:COLORS.primary },
  hero:    { flex:1, justifyContent:'center', alignItems:'center', paddingHorizontal:20 },
  icon:    { fontSize:70, marginBottom:12 },
  title:   { fontSize:34, fontWeight:'800', color:'#fff', letterSpacing:1 },
  subtitle:{ fontSize:16, color:'rgba(255,255,255,0.8)', marginTop:4 },
  connRow: { flexDirection:'row', alignItems:'center', marginTop:20 },
  connText:{ fontSize:13, color:'rgba(255,255,255,0.7)' },
  body:    { backgroundColor:COLORS.bg, borderTopLeftRadius:28, borderTopRightRadius:28, padding:24, paddingBottom:40 },
  prompt:  { fontSize:15, color:COLORS.textLight, marginBottom:12, textAlign:'center' },
  errText: { fontSize:13, color:COLORS.danger, marginTop:12, lineHeight:22 },
  errCmd:  { fontFamily:'monospace', backgroundColor:'#FFF3E0', paddingHorizontal:4 },
});