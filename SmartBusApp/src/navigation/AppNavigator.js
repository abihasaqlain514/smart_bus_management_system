import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { ActivityIndicator, View } from 'react-native';
import { useAuth } from '../context/AuthContext';
import { COLORS } from '../config';

import WelcomeScreen       from '../screens/WelcomeScreen';
import PassengerAuthScreen from '../screens/auth/PassengerAuthScreen';
import DriverAuthScreen    from '../screens/auth/DriverAuthScreen';
import AdminAuthScreen     from '../screens/auth/AdminAuthScreen';
import ParentAuthScreen    from '../screens/auth/ParentAuthScreen';

import PassengerNavigator    from './PassengerNavigator';
import RouteDetailScreen     from '../screens/passenger/RouteDetailScreen';
import LiveMapScreen         from '../screens/passenger/LiveMapScreen';
import BookingQRScreen       from '../screens/passenger/BookingQRScreen';

import DriverDashboard from '../screens/driver/DriverDashboard';
import AdminDashboard  from '../screens/admin/AdminDashboard';
import ParentDashboard from '../screens/parent/ParentDashboard';

const Stack = createStackNavigator();

const hdr = (title, bg = COLORS.primary) => ({
  title,
  headerStyle: { backgroundColor: bg },
  headerTintColor: '#fff',
  headerTitleStyle: { fontWeight: '700' },
});

export default function AppNavigator() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color={COLORS.primary} />
      </View>
    );
  }

  return (
    <NavigationContainer>
      <Stack.Navigator>
        {!user ? (
          <>
            <Stack.Screen name="Welcome"       component={WelcomeScreen}       options={{ headerShown: false }} />
            <Stack.Screen name="PassengerAuth" component={PassengerAuthScreen} options={hdr('Passenger')} />
            <Stack.Screen name="DriverAuth"    component={DriverAuthScreen}    options={hdr('Driver', '#00897B')} />
            <Stack.Screen name="AdminAuth"     component={AdminAuthScreen}     options={hdr('Admin', '#6A1B9A')} />
            <Stack.Screen name="ParentAuth"    component={ParentAuthScreen}    options={hdr('Parent', '#E65100')} />
          </>
        ) : user.role === 'passenger' ? (
          <>
            {/* Bottom-tab home for passengers */}
            <Stack.Screen name="PassengerMain" component={PassengerNavigator} options={{ headerShown: false }} />
            {/* Detail screens pushed on top of tabs (hide tab bar) */}
            <Stack.Screen name="RouteDetail" component={RouteDetailScreen} options={hdr('Route Details')} />
            <Stack.Screen name="LiveMap"     component={LiveMapScreen}     options={{ title: '📍 Live Tracking', headerStyle: { backgroundColor: '#1A237E' }, headerTintColor: '#fff', headerTitleStyle: { fontWeight: '700' } }} />
            <Stack.Screen name="BookingQR"   component={BookingQRScreen}   options={hdr('🎫 Your Ticket')} />
          </>
        ) : user.role === 'driver' ? (
          <Stack.Screen name="Dashboard" component={DriverDashboard} options={hdr('🚗 Driver Dashboard', '#00897B')} />
        ) : user.role === 'admin' ? (
          <Stack.Screen name="Dashboard" component={AdminDashboard}  options={hdr('🛠 Admin Dashboard', '#6A1B9A')} />
        ) : (
          <Stack.Screen name="Dashboard" component={ParentDashboard} options={hdr('👨‍👧 Parent Dashboard', '#E65100')} />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}