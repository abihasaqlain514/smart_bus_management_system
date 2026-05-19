import { Platform } from 'react-native';

// ─── Server IP ────────────────────────────────────────────────────────────────
// __DEV__ = true  → debug APK, loaded via Metro + USB ADB reverse tunnel
// __DEV__ = false → release APK, bundle is embedded, connects over WiFi
const WIFI_IP = '192.168.10.4';   // PC's IPv4 on home/university WiFi (run: ipconfig)

const HOST = __DEV__
  ? 'localhost'            // USB cable: adb reverse tcp:8000 tcp:8000 handles routing
  : WIFI_IP;               // Release APK: direct WiFi connection to PC

export const API_URL = `http://${HOST}:8000`;
export const WS_URL  = `ws://${HOST}:8000`;

// ─── Theme ────────────────────────────────────────────────────────────────────
export const COLORS = {
  primary:    '#1565C0',
  primaryLight:'#1E88E5',
  secondary:  '#00897B',
  success:    '#43A047',
  warning:    '#FB8C00',
  danger:     '#E53935',
  bg:         '#F5F7FA',
  card:       '#FFFFFF',
  border:     '#E0E0E0',
  text:       '#212121',
  textLight:  '#757575',
  white:      '#FFFFFF',
};
