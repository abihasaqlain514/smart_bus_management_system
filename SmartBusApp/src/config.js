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

// NOTE: Platform.constants.isEmulator is NOT a real React Native API on
// Android (only exists on iOS-style checks people copy-paste from
// elsewhere). It's always undefined here, so the old check below always
// evaluated to false — meaning the app always fell through to 'localhost',
// which inside an Android emulator points at the emulator itself, not your
// PC. That's why API calls silently failed and screens showed empty lists.
//
// Real Android emulators (AVD / Android Studio) report a Build.FINGERPRINT
// or MODEL containing telltale strings like "generic", "sdk_gphone", or
// "emulator". This heuristic needs no extra native module (avoids another
// gradle rebuild) and is what most RN apps use in practice.
const _brand = Platform.constants?.Brand?.toLowerCase() ?? '';
const _model = Platform.constants?.Model?.toLowerCase() ?? '';
const _fingerprint = Platform.constants?.Fingerprint?.toLowerCase() ?? '';
const IS_EMULATOR =
  Platform.OS === 'android' &&
  (
    _brand === 'generic' ||
    _model.includes('sdk') ||
    _model.includes('emulator') ||
    _fingerprint.includes('generic') ||
    _fingerprint.includes('emulator')
  );

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
