import { createContext, useContext, useState, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null);
  const [loading, setLoading] = useState(true);

  // Restore session from storage on app launch
  useEffect(() => {
    AsyncStorage.getItem('user')
      .then((raw) => { if (raw) setUser(JSON.parse(raw)); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  /**
   * Call this after a successful login / register.
   * userData must contain at minimum:
   *   { access_token, role, id, full_name, email }
   */
  const login = async (userData) => {
    if (!userData?.access_token) {
      console.warn('AuthContext.login: missing access_token', userData);
      return;
    }
    const stored = { ...userData };
    await AsyncStorage.setItem('token', userData.access_token);
    await AsyncStorage.setItem('user', JSON.stringify(stored));
    setUser(stored);
  };

  const logout = async () => {
    await AsyncStorage.multiRemove(['token', 'user']);
    setUser(null);
  };

  /**
   * Update FCM token or any profile field without a full re-login.
   */
  const updateUser = async (patch) => {
    const updated = { ...user, ...patch };
    await AsyncStorage.setItem('user', JSON.stringify(updated));
    setUser(updated);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);