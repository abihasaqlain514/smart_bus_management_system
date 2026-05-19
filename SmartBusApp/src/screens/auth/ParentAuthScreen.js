import { useState } from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, Alert } from 'react-native';
import { useAuth } from '../../context/AuthContext';
import { authApi } from '../../api/index';
import { Btn, Input, showError } from '../../components/UI';
import { COLORS } from '../../config';

const C = '#E65100';

export default function ParentAuthScreen() {
  const [tab, setTab]         = useState('login');
  const { login }             = useAuth();
  const [showPwd, setShowPwd] = useState(false);
  const [busy, setBusy]       = useState(false);

  const [loginForm, setLogin] = useState({ email: '', password: '' });
  const [regForm,   setReg]   = useState({
    full_name: '', email: '', password: '', phone_number: '+92',
  });

  // ── Login ────────────────────────────────────────────────────────────────

  const doLogin = async () => {
    const email    = loginForm.email.trim().toLowerCase();
    const password = loginForm.password.trim();

    if (!email || !password)
      return Alert.alert('Missing fields', 'Enter both email and password.');

    setBusy(true);
    try {
      const { data } = await authApi.parentLogin({ email, password });
      await login({
        access_token: data.access_token,
        role:         data.role || 'parent',
        id:           data.id,
        full_name:    data.full_name,
        email:        data.email,
      });
    } catch (e) {
      showError(e);
    } finally {
      setBusy(false);
    }
  };

  // ── Register ─────────────────────────────────────────────────────────────

  const doRegister = async () => {
    const email    = regForm.email.trim().toLowerCase();
    const password = regForm.password.trim();
    const phone    = regForm.phone_number.trim();

    if (!regForm.full_name || !email || !password || !phone)
      return Alert.alert('Missing fields', 'Fill all required fields.');
    if (!phone.startsWith('+'))
      return Alert.alert('Phone error', 'Phone must start with country code e.g. +92');
    if (password.length < 8)
      return Alert.alert('Password error', 'Password must be at least 8 characters.');

    setBusy(true);
    try {
      await authApi.parentRegister({ ...regForm, email, password, phone_number: phone });
      const { data } = await authApi.parentLogin({ email, password });
      await login({
        access_token: data.access_token,
        role:         data.role || 'parent',
        id:           data.id,
        full_name:    data.full_name,
        email:        data.email,
      });
    } catch (e) {
      showError(e);
    } finally {
      setBusy(false);
    }
  };

  // ── UI ───────────────────────────────────────────────────────────────────

  return (
    <ScrollView style={styles.root} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <View style={[styles.tabs, { backgroundColor: '#FFF3E0' }]}>
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
            label="Email"
            value={loginForm.email}
            onChangeText={(v) => setLogin({ ...loginForm, email: v })}
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
            placeholder="parent@family.com"
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
                placeholder="Parent@1234"
              />
            </View>
            <TouchableOpacity onPress={() => setShowPwd(!showPwd)} style={styles.eyeBtn}>
              <Text style={styles.eyeText}>{showPwd ? '🙈' : '👁'}</Text>
            </TouchableOpacity>
          </View>
          <Btn title="Login as Parent" onPress={doLogin} loading={busy} color={C} />

          <View style={styles.hintBox}>
            <Text style={[styles.hintTitle, { color: C }]}>New to the system?</Text>
            <Text style={styles.hint}>Register first, then link your child using their University ID.</Text>
          </View>
        </>
      ) : (
        <>
          <Input label="Full Name *"    value={regForm.full_name}    onChangeText={(v) => setReg({ ...regForm, full_name: v })}    autoCorrect={false} placeholder="Mr. Ali" />
          <Input label="Email *"        value={regForm.email}        onChangeText={(v) => setReg({ ...regForm, email: v })}        keyboardType="email-address" autoCapitalize="none" autoCorrect={false} />
          <Input label="Password * (min 8)" value={regForm.password} onChangeText={(v) => setReg({ ...regForm, password: v })}    secureTextEntry autoCapitalize="none" autoCorrect={false} />
          <Input label="Phone * (+92...)" value={regForm.phone_number} onChangeText={(v) => setReg({ ...regForm, phone_number: v })} keyboardType="phone-pad" />
          <Btn title="Register as Parent" onPress={doRegister} loading={busy} color={C} />
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
  hintBox:   { marginTop: 20, backgroundColor: '#FFF3E0', padding: 14, borderRadius: 10 },
  hintTitle: { fontWeight: '700', marginBottom: 6, fontSize: 13 },
  hint:      { fontSize: 12, color: COLORS.text, lineHeight: 20 },
});