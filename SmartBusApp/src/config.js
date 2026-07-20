import { Platform } from 'react-native';

// ─── Network host selection ───────────────────────────────────────────────────
//
//  Android emulator  → 10.0.2.2   (QEMU built-in alias for host localhost)
//                       No ADB reverse needed. Works out of the box.
//
//  Physical phone    → localhost   (debug/USB) or WIFI_IP (release/WiFi)
//  debug + USB         ADB reverse handles:  adb reverse tcp:8000 tcp:8000
//
//  Release APK       → WIFI_IP    (direct WiFi, no cable needed)
//
// ─────────────────────────────────────────────────────────────────────────────

const WIFI_IP = '172.20.0.1';   // your PC's IPv4 — update if WiFi changes

// Platform.constants.isEmulator is built into React Native 0.63+
// true  → Pixel emulator / AVD running on your laptop
// false → real physical phone
const IS_EMULATOR =
  Platform.OS === 'android' && !!Platform.constants?.isEmulator;

const HOST = IS_EMULATOR
  ? '10.0.2.2'    // emulator: QEMU routes this to host machine — no setup needed
  : __DEV__
    ? 'localhost'  // physical phone + USB cable: adb reverse tcp:8000 tcp:8000
    : WIFI_IP;     // release APK + WiFi: direct connection to PC

// ─── Backend URLs ─────────────────────────────────────────────────────────────
//
// REPLIT DEPLOYMENT: Replace with your actual Replit backend URL
// Format: https://[project-name]--[username].replit.dev
//
// Example:
//   export const API_URL = `https://smartbus-backend--yourname.replit.dev`;
//   export const WS_URL = `wss://smartbus-backend--yourname.replit.dev`;
//
// LOCAL DEVELOPMENT:
//   export const API_URL = `http://${HOST}:8000`;
//   export const WS_URL = `ws://${HOST}:8000`;
//

// ✅ UPDATED FOR REPLIT DEPLOYMENT
const REPLIT_BACKEND_URL = 'https://smartbusmanagementsystem--abihasaqlain514.replit.app';
const LOCAL_BACKEND_URL = `http://${HOST}:8000`;

// Use LOCAL_BACKEND_URL during development, REPLIT_BACKEND_URL for production
const backendBaseURL = __DEV__ ? LOCAL_BACKEND_URL : REPLIT_BACKEND_URL;

export const API_URL = backendBaseURL;
export const WS_URL = backendBaseURL.replace('http://', 'ws://').replace('https://', 'wss://');

// ─── Theme ────────────────────────────────────────────────────────────────────
export const COLORS = {
  primary:     '#1565C0',
  primaryLight:'#1E88E5',
  secondary:   '#00897B',
  success:     '#43A047',
  warning:     '#FB8C00',
  danger:      '#E53935',
  bg:          '#F5F7FA',
  card:        '#FFFFFF',
  border:      '#E0E0E0',
  text:        '#212121',
  textLight:   '#757575',
  white:       '#FFFFFF',
};
