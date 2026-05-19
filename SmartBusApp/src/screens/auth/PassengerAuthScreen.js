import { useState } from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, Alert } from 'react-native';
import { useAuth } from '../../context/AuthContext';
import { authApi } from '../../api/index';
import { Btn, Input, showError } from '../../components/UI';
import { COLORS } from '../../config';

const STUDENT_TYPES = ['bscs','bsse','bsit','bsee','bs','bba','ms','mscs','mba','mphil','phd','faculty','staff'];

export default function PassengerAuthScreen() {
  const [tab,     setTab]     = useState('login');
  const { login }             = useAuth();
  const [showPwd, setShowPwd] = useState(false);
  const [busy,    setBusy]    = useState(false);

  const [lf, setLf] = useState({ email: '', password: '' });
  const [rf, setRf] = useState({
    full_name: '', email: '', password: '',
    phone_number: '+92', university_id: '',
    student_type: 'bscs', gender: 'male',
  });

  const doLogin = async () => {
    const email    = lf.email.trim().toLowerCase();
    const password = lf.password.trim();
    if (!email || !password) return Alert.alert('Missing', 'Enter email and password.');
    setBusy(true);
    try {
      const { data } = await authApi.passengerLogin({ email, password });
      await login({
        access_token: data.access_token,
        role:         data.user.role,
        id:           data.user.id,
        full_name:    data.user.full_name,
        email:        data.user.email,
        phone_number: data.user.phone_number,
        is_active:    data.user.is_active,
      });
    } catch (e) { showError(e); } finally { setBusy(false); }
  };

  const doRegister = async () => {
    const email    = rf.email.trim().toLowerCase();
    const password = rf.password.trim();
    const phone    = rf.phone_number.trim();
    if (!rf.full_name || !email || !password || !phone || !rf.university_id)
      return Alert.alert('Missing', 'Fill all required fields.');
    if (!phone.startsWith('+'))
      return Alert.alert('Phone', 'Must start with country code, e.g. +92');
    if (password.length < 8)
      return Alert.alert('Password', 'Minimum 8 characters.');
    setBusy(true);
    try {
      await authApi.passengerRegister({ ...rf, email, password, phone_number: phone });
      const loginRes = await authApi.passengerLogin({ email, password });
      const ld = loginRes.data;
      await login({
        access_token: ld.access_token,
        role:         ld.user.role,
        id:           ld.user.id,
        full_name:    ld.user.full_name,
        email:        ld.user.email,
        phone_number: ld.user.phone_number,
        is_active:    ld.user.is_active,
        gender:       rf.gender,
      });
    } catch (e) { showError(e); } finally { setBusy(false); }
  };

  return (
    <ScrollView style={s.root} contentContainerStyle={s.content} keyboardShouldPersistTaps="handled">
      {/* Tabs */}
      <View style={s.tabs}>
        {['login','register'].map(t => (
          <TouchableOpacity key={t} style={[s.tab, tab===t && s.tabOn]} onPress={() => setTab(t)}>
            <Text style={[s.tabTxt, tab===t && s.tabTxtOn]}>{t==='login' ? 'Login' : 'Register'}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {tab === 'login' ? (
        <>
          <Input label="Email" value={lf.email} onChangeText={v => setLf({...lf,email:v})}
            keyboardType="email-address" autoCapitalize="none" autoCorrect={false} placeholder="sara@student.edu.pk" />
          <View style={s.pwdRow}>
            <View style={{flex:1}}>
              <Input label="Password" value={lf.password} onChangeText={v => setLf({...lf,password:v})}
                secureTextEntry={!showPwd} autoCapitalize="none" autoCorrect={false} placeholder="Sara@1234" />
            </View>
            <TouchableOpacity onPress={() => setShowPwd(!showPwd)} style={s.eye}>
              <Text style={s.eyeTxt}>{showPwd ? '🙈' : '👁'}</Text>
            </TouchableOpacity>
          </View>
          <Btn title="Login as Passenger" onPress={doLogin} loading={busy} />
          <View style={s.hint}>
            <Text style={s.hintTitle}>Test accounts (seeded)</Text>
            <Text style={s.hintLine}>sara@student.edu.pk  →  Sara@1234</Text>
            <Text style={s.hintLine}>fatima@student.edu.pk  →  Fatima@1234</Text>
            <Text style={s.hintLine}>usman@student.edu.pk  →  Usman@1234</Text>
          </View>
        </>
      ) : (
        <>
          <Input label="Full Name *"        value={rf.full_name}     onChangeText={v => setRf({...rf,full_name:v})}     autoCorrect={false} placeholder="Ali Hassan" />
          <Input label="Email *"            value={rf.email}         onChangeText={v => setRf({...rf,email:v})}         keyboardType="email-address" autoCapitalize="none" autoCorrect={false} />
          <Input label="Password * (min 8)" value={rf.password}      onChangeText={v => setRf({...rf,password:v})}      secureTextEntry autoCapitalize="none" />
          <Input label="Phone * (+92...)"   value={rf.phone_number}  onChangeText={v => setRf({...rf,phone_number:v})}  keyboardType="phone-pad" />
          <Input label="University ID *"    value={rf.university_id} onChangeText={v => setRf({...rf,university_id:v})} autoCapitalize="characters" placeholder="2023-CS-100" />

          {/* Gender selector */}
          <Text style={s.fieldLabel}>Gender *</Text>
          <View style={s.genderRow}>
            {[
              { val: 'male',   label: '👨 Male',   bg: '#E3F2FD', active: '#1565C0' },
              { val: 'female', label: '👩 Female', bg: '#FCE4EC', active: '#C2185B' },
            ].map(g => (
              <TouchableOpacity
                key={g.val}
                style={[s.genderBtn, { borderColor: rf.gender === g.val ? g.active : '#E0E0E0', backgroundColor: rf.gender === g.val ? g.bg : '#fff' }]}
                onPress={() => setRf({...rf, gender: g.val})}
              >
                <Text style={[s.genderTxt, { color: rf.gender === g.val ? g.active : COLORS.textLight }]}>{g.label}</Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Student type picker */}
          <Text style={s.fieldLabel}>Student Type *</Text>
          <View style={s.typeGrid}>
            {STUDENT_TYPES.map(t => (
              <TouchableOpacity
                key={t}
                style={[s.typeChip, rf.student_type === t && s.typeChipOn]}
                onPress={() => setRf({...rf, student_type: t})}
              >
                <Text style={[s.typeChipTxt, rf.student_type === t && s.typeChipTxtOn]}>{t.toUpperCase()}</Text>
              </TouchableOpacity>
            ))}
          </View>

          <Btn title="Create Passenger Account" onPress={doRegister} loading={busy} />
        </>
      )}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  root:    { flex:1, backgroundColor:COLORS.bg },
  content: { padding:20, paddingBottom:40 },
  tabs:    { flexDirection:'row', backgroundColor:'#E3F2FD', borderRadius:12, marginBottom:20, padding:4 },
  tab:     { flex:1, padding:12, alignItems:'center', borderRadius:10 },
  tabOn:   { backgroundColor:COLORS.primary },
  tabTxt:  { color:COLORS.primary, fontWeight:'600' },
  tabTxtOn:{ color:'#fff' },
  pwdRow:  { flexDirection:'row', alignItems:'flex-end' },
  eye:     { paddingBottom:12, paddingLeft:8 },
  eyeTxt:  { fontSize:22 },
  hint:    { marginTop:20, backgroundColor:'#E8F5E9', padding:14, borderRadius:10 },
  hintTitle:{ fontWeight:'700', color:COLORS.secondary, marginBottom:6, fontSize:13 },
  hintLine: { fontSize:12, color:COLORS.text, lineHeight:22 },

  fieldLabel: { fontSize:13, fontWeight:'600', color:COLORS.textLight, marginBottom:8, marginTop:12 },

  genderRow:   { flexDirection:'row', gap:12, marginBottom:4 },
  genderBtn:   { flex:1, borderWidth:2, borderRadius:12, paddingVertical:14, alignItems:'center', justifyContent:'center' },
  genderTxt:   { fontSize:16, fontWeight:'700' },

  typeGrid:    { flexDirection:'row', flexWrap:'wrap', gap:8, marginBottom:16 },
  typeChip:    { paddingHorizontal:12, paddingVertical:7, borderRadius:20, backgroundColor:'#fff', borderWidth:1, borderColor:COLORS.border },
  typeChipOn:  { backgroundColor:COLORS.primary, borderColor:COLORS.primary },
  typeChipTxt: { fontSize:12, fontWeight:'600', color:COLORS.textLight },
  typeChipTxtOn:{ color:'#fff' },
});
