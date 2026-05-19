import { Text } from 'react-native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { COLORS } from '../config';

import HomeScreen    from '../screens/passenger/HomeScreen';
import RoutesScreen  from '../screens/passenger/RoutesScreen';
import MyTripsScreen from '../screens/passenger/MyTripsScreen';
import AlertsScreen  from '../screens/passenger/AlertsScreen';

const Tab = createBottomTabNavigator();

export default function PassengerNavigator() {
  return (
    <Tab.Navigator
      screenOptions={{
        tabBarActiveTintColor:   COLORS.primary,
        tabBarInactiveTintColor: '#9E9E9E',
        tabBarStyle: {
          backgroundColor: '#fff',
          borderTopColor: '#F0F0F0',
          borderTopWidth: 1,
          height: 62,
          paddingBottom: 8,
          paddingTop: 4,
          elevation: 12,
          shadowColor: '#000',
          shadowOpacity: 0.1,
          shadowRadius: 10,
        },
        tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
        headerShown: false,
      }}
    >
      <Tab.Screen
        name="HomeTab"
        component={HomeScreen}
        options={{ title: 'Home',     tabBarIcon: ({ color }) => <Text style={{ fontSize: 22 }}>🏠</Text> }}
      />
      <Tab.Screen
        name="RoutesTab"
        component={RoutesScreen}
        options={{ title: 'Routes',   tabBarIcon: ({ color }) => <Text style={{ fontSize: 22 }}>🚌</Text> }}
      />
      <Tab.Screen
        name="MyTripsTab"
        component={MyTripsScreen}
        options={{ title: 'My Trips', tabBarIcon: ({ color }) => <Text style={{ fontSize: 22 }}>🎫</Text> }}
      />
      <Tab.Screen
        name="AlertsTab"
        component={AlertsScreen}
        options={{ title: 'Alerts',   tabBarIcon: ({ color }) => <Text style={{ fontSize: 22 }}>🔔</Text> }}
      />
    </Tab.Navigator>
  );
}
