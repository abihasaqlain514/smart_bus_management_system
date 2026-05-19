import { useState } from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, Alert } from 'react-native';
import { useAuth } from '../../context/AuthContext';
import { authApi } from '../../api/index';
import { Btn, Input, showError } from '../../components/UI';
import { COLORS } from '../../config';

const C = COLORS.secondary;

export default function DriverAuthScreen() {
  const [tab, setTab]         = useState('login');
  const { login }             = useAuth();
  const [showPwd, setShowPwd] = useState(false);
  const [busy, setBusy]       = useState(false);

  const [loginForm, setLogin] = useState({ driver_code: '', password: '' });
  const [regForm,   setReg]   = useState({
    full_name: '', email: '', password: '', phone_number: '+92',
    driver_code: 'DRV-', license_number: '', license_expiry_date: '2029-12-31',
    experience_years: '0',
  });

  const storeLogin = (data) => login({
    access_token:    data.access_token,
    role:            'driver',
    id:              data.driver_id,
    full_name:       data.full_name,
    email:           data.email,
    driver_code:     data.driver_code,
    bus_number:      data.bus_number   || null,
    bus_route_id:    data.bus_route_id || null,
    route_name:      data.route_name   || null,
    route_number:    data.route_number || null,
    assigned_bus_id: data.assigned_bus_id || null,
  });

  // ── Login ────────────────────────────────────────────────────────────────

  const doLogin = async () => {
    const driver_code = loginForm.driver_code.trim().toUpperCase();
    const password    = loginForm.password.trim();

    if (!driver_code || !password)
      return Alert.alert('Missing fields', 'Enter driver code and password.');

    setBusy(true);
    try {
      const { data } = await authApi.driverLogin({ driver_code, password });
      await storeLogin(data);
    } catch (e) {
      showError(e);
    } finally {
      setBusy(false);
    }
  };

  // ── Register ─────────────────────────────────────────────────────────────

  const doRegister = async () => {
    const email       = regForm.email.trim().toLowerCase();
    const password    = regForm.password.trim();
    const phone       = regForm.phone_number.trim();
    const driver_code = regForm.driver_code.trim().toUpperCase();

    if (!regForm.full_name || !email || !password || !phone || !driver_code || !regForm.license_number)
      return Alert.alert('Missing fields', 'Fill all required fields.');
    if (!phone.startsWith('+'))
      return Alert.alert('Phone error', 'Phone must start with country code e.g. +92');
    if (password.length < 8)
      return Alert.alert('Password error', 'Password must be at least 8 characters.');

    setBusy(true);
    try {
      await authApi.driverRegister({
        ...regForm,
        email, password, phone_number: phone, driver_code,
        experience_years: Number(regForm.experience_years) || 0,
      });
      const { data } = await authApi.driverLogin({ driver_code, password });
      await storeLogin(data);
    } catch (e) {
      showError(e);
    } finally {
      setBusy(false);
    }
  };

  // ── UI ───────────────────────────────────────────────────────────────────

  return (
    <ScrollView style={styles.root} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <View style={[styles.tabs, { backgroundColor: '#E8F5E9' }]}>
        {['login', 'register'].map((t) => (
          <TouchableOpacity key={t} style={[styles.tab, tab === t && { backgroundColor: C }]} onPress={() => setTab(t)}>
            <Text style={[{ color: C, fontWeight: '600' }, tab === t && { color: '#fff' }]}>
              {t === 'login' ? 'Login' : 'Register'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {tab === 'login' ? (
        <>
          <Input
            label="Driver Code  (auto-uppercased)"
            value={loginForm.driver_code}
            onChangeText={(v) => setLogin({ ...loginForm, driver_code: v.toUpperCase() })}
            autoCapitalize="characters"
            autoCorrect={false}
            placeholder="DRV-001"
          />
          <View style={styles.pwdRow}>
            <View style={{ flex: 1 }}>
              <Input
                label="Password"
                value={loginForm.password}
                onChangeText={(v) => setLogin({ ...loginForm, password: v })}
                secureTextEntry={!showPwd}
                autoCapitalize="none"
                autoCorrect={false}
                placeholder="Driver@1234"
              />
            </View>
            <TouchableOpacity onPress={() => setShowPwd(!showPwd)} style={styles.eyeBtn}>
              <Text style={styles.eyeText}>{showPwd ? '🙈' : '👁'}</Text>
            </TouchableOpacity>
          </View>

          <Btn title="Login as Driver" onPress={doLogin} loading={busy} color={C} />

          <View style={styles.hintBox}>
            <Text style={[styles.hintTitle, { color: C }]}>Test accounts (already seeded)</Text>
            <Text style={styles.hint}>DRV-001  →  Driver@1234  (Ahmed Khan)</Text>
            <Text style={styles.hint}>DRV-002  →  Driver@1234  (Bilal Hussain)</Text>
          </View>
        </>
      ) : (
        <>
          <Input label="Full Name *"             value={regForm.full_name}          onChangeText={(v) => setReg({ ...regForm, full_name: v })}          autoCorrect={false} placeholder="Hassan Raza" />
          <Input label="Email *"                 value={regForm.email}              onChangeText={(v) => setReg({ ...regForm, email: v })}              keyboardType="email-address" autoCapitalize="none" autoCorrect={false} />
          <Input label="Password * (min 8)"      value={regForm.password}           onChangeText={(v) => setReg({ ...regForm, password: v })}           secureTextEntry autoCapitalize="none" autoCorrect={false} />
          <Input label="Phone * (+92...)"        value={regForm.phone_number}       onChangeText={(v) => setReg({ ...regForm, phone_number: v })}       keyboardType="phone-pad" />
          <Input label="Driver Code *"           value={regForm.driver_code}        onChangeText={(v) => setReg({ ...regForm, driver_code: v.toUpperCase() })} autoCapitalize="characters" autoCorrect={false} placeholder="DRV-003" />
          <Input label="License Number *"        value={regForm.license_number}     onChangeText={(v) => setReg({ ...regForm, license_number: v })}     autoCorrect={false} placeholder="LHR-DL-2024-003" />
          <Input label="Expiry Date (YYYY-MM-DD)" value={regForm.license_expiry_date} onChangeText={(v) => setReg({ ...regForm, license_expiry_date: v })} placeholder="2029-12-31" />
          <Input label="Experience (years)"      value={regForm.experience_years}   onChangeText={(v) => setReg({ ...regForm, experience_years: v })}   keyboardType="numeric" placeholder="3" />
          <Btn title="Register as Driver" onPress={doRegister} loading={busy} color={C} />
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root:      { flex: 1, backgroundColor: COLORS.bg },
  content:   { padding: 20, paddingBottom: 40 },
  tabs:      { flexDirection: 'row', borderRadius: 12, marginBottom: 20, padding: 4 },
  tab:       { flex: 1, padding: 12, alignItems: 'center', borderRadius: 10 },
  pwdRow:    { flexDirection: 'row', alignItems: 'flex-end' },
  eyeBtn:    { paddingBottom: 12, paddingLeft: 8 },
  eyeText:   { fontSize: 22 },
  hintBox:   { marginTop: 20, backgroundColor: '#E8F5E9', padding: 14, borderRadius: 10 },
  hintTitle: { fontWeight: '700', marginBottom: 6, fontSize: 13 },
  hint:      { fontSize: 12, color: COLORS.text, lineHeight: 22, fontFamily: 'monospace' },
});