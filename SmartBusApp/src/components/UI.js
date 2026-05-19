// Minimal shared UI primitives used across all screens
import React from 'react';
import {
  View, Text, TextInput, TouchableOpacity, ActivityIndicator,
  StyleSheet, Alert,
} from 'react-native';
import { COLORS } from '../config';

export const Btn = ({ title, onPress, color = COLORS.primary, style, disabled, loading }) => (
  <TouchableOpacity
    style={[styles.btn, { backgroundColor: disabled ? '#B0BEC5' : color }, style]}
    onPress={onPress}
    disabled={disabled || loading}
  >
    {loading
      ? <ActivityIndicator color="#fff" />
      : <Text style={styles.btnText}>{title}</Text>}
  </TouchableOpacity>
);

export const Input = ({ label, ...props }) => (
  <View style={styles.inputWrap}>
    {label ? <Text style={styles.label}>{label}</Text> : null}
    <TextInput
      style={styles.input}
      placeholderTextColor="#9E9E9E"
      autoCapitalize="none"
      {...props}
    />
  </View>
);

export const Card = ({ children, style }) => (
  <View style={[styles.card, style]}>{children}</View>
);

export const SectionTitle = ({ children }) => (
  <Text style={styles.sectionTitle}>{children}</Text>
);

export const Badge = ({ label, color = COLORS.primary }) => (
  <View style={[styles.badge, { backgroundColor: color }]}>
    <Text style={styles.badgeText}>{label}</Text>
  </View>
);

export const Row = ({ children, style }) => (
  <View style={[styles.row, style]}>{children}</View>
);

export const showError = (err) =>
  Alert.alert('Error', err?.message || String(err));

export const statusColor = (status) => {
  const map = {
    on_route: COLORS.success, active: COLORS.success, confirmed: COLORS.success,
    delayed: COLORS.warning, pending: COLORS.warning,
    breakdown: COLORS.danger, cancelled: COLORS.danger, offline: COLORS.danger,
    not_in_service: COLORS.textLight, available: COLORS.secondary,
    completed: COLORS.secondary,
  };
  return map[status] || COLORS.primary;
};

const styles = StyleSheet.create({
  btn: {
    padding: 14, borderRadius: 10, alignItems: 'center', marginVertical: 6,
  },
  btnText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  inputWrap: { marginVertical: 6 },
  label: { fontSize: 13, color: COLORS.textLight, marginBottom: 4, fontWeight: '600' },
  input: {
    borderWidth: 1, borderColor: COLORS.border, borderRadius: 10,
    padding: 12, fontSize: 15, backgroundColor: COLORS.white, color: COLORS.text,
  },
  card: {
    backgroundColor: COLORS.white, borderRadius: 14, padding: 16,
    marginVertical: 8, elevation: 2, shadowColor: '#000',
    shadowOpacity: 0.08, shadowRadius: 4, shadowOffset: { width: 0, height: 2 },
  },
  sectionTitle: {
    fontSize: 17, fontWeight: '700', color: COLORS.text, marginTop: 18, marginBottom: 4,
  },
  badge: {
    borderRadius: 20, paddingHorizontal: 10, paddingVertical: 3, alignSelf: 'flex-start',
  },
  badgeText: { color: '#fff', fontSize: 11, fontWeight: '700' },
  row: { flexDirection: 'row', alignItems: 'center' },
});