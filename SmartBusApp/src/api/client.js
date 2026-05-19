import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_URL } from '../config';

const client = axios.create({
  baseURL: API_URL,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Attach JWT token to every request ────────────────────────────────────────
client.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Normalize all errors into a single readable message ──────────────────────
client.interceptors.response.use(
  (res) => res,
  (err) => {
    let msg = 'Request failed';

    if (err.response) {
      // Server responded with a non-2xx status
      const detail = err.response.data?.detail;
      if (typeof detail === 'string') {
        msg = detail;
      } else if (Array.isArray(detail)) {
        // FastAPI validation errors (422) → show all field errors
        msg = detail
          .map((d) => {
            const field = d.loc?.slice(1).join(' > ') || 'field';
            return `${field}: ${d.msg}`;
          })
          .join('\n');
      } else {
        msg = `HTTP ${err.response.status}: ${err.response.statusText || 'Server error'}`;
      }
    } else if (err.request) {
      // Request was sent but no response — server not reachable
      msg = 'Cannot connect to server. Make sure the backend is running and API_URL is correct.';
    } else {
      msg = err.message || 'Unknown error';
    }

    return Promise.reject(new Error(msg));
  }
);

export default client;