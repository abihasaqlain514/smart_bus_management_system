import client from './client';

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  passengerRegister: (d) => client.post('/api/auth/passenger/register', d),
  passengerLogin:    (d) => client.post('/api/auth/passenger/login', d),
  driverRegister:    (d) => client.post('/api/auth/driver/register', d),
  driverLogin:       (d) => client.post('/api/auth/driver/login', d),
  adminRegister:     (d) => client.post('/api/auth/admin/register', d),
  adminLogin:        (d) => client.post('/api/auth/admin/login', d),
  parentRegister:    (d) => client.post('/api/parent/register', d),
  parentLogin:       (d) => client.post('/api/parent/login', d),
};

// ── Passenger ─────────────────────────────────────────────────────────────────
export const passengerApi = {
  getProfile:       () => client.get('/api/passenger/profile'),
  updateProfile:    (d) => client.patch('/api/passenger/profile', d),
  getLiveBuses:     () => client.get('/api/locations/live'),
  getActiveTrips:   () => client.get('/api/trips/active'),
  getRoutes:        () => client.get('/api/routes/'),
  getRouteBuses:    (routeId) => client.get(`/api/routes/${routeId}/buses`),
  getRouteStops:    (routeId) => client.get(`/api/routes/${routeId}/stops`),
  bookSeat:         (d) => client.post('/api/bookings/', d),
  myBookings:       (page = 1) => client.get(`/api/bookings/my?page=${page}`),
  cancelBooking:    (id, d) => client.patch(`/api/bookings/${id}/cancel`, d),
  myNotifications:  (page = 1) => client.get(`/api/notifications/my?page=${page}`),
  markRead:         (id) => client.patch(`/api/notifications/${id}/read`),
  getBusSeats:      (busId) => client.get(`/api/buses/${busId}/seats`),
  getETA:           (tripId) => client.get(`/api/trips/${tripId}/eta`),
  getBusLocation:   (busId) => client.get(`/api/buses/${busId}/location`),
  getNearestStops:  (lat, lng) => client.get(`/api/locations/nearest?lat=${lat}&lng=${lng}`),
  getBusBookingsByDate: (busId, date) => client.get(`/api/bookings/bus/${busId}?date=${date}`),
  searchRoutes:     (q) => client.get(`/api/routes/?search=${encodeURIComponent(q)}`),
};

// ── Driver ────────────────────────────────────────────────────────────────────
export const driverApi = {
  getProfile:      () => client.get('/api/driver/profile'),
  getActiveTrip:   () => client.get('/api/driver/active-trip'),   // own trip only
  startTrip:       (d) => client.post('/api/trips/start', d),
  endTrip:         (id) => client.post(`/api/trips/${id}/end`),
  updateStatus:    (id, d) => client.patch(`/api/trips/${id}/status`, d),
  updateSeats:     (id, d) => client.patch(`/api/trips/${id}/seats`, d),
  postLocation:    (d) => client.post('/api/locations/update', d),
  reportIssue:     (d) => client.post('/api/driver/issues', d),
  sendNotif:       (d) => client.post('/api/notifications/send', d),
  getBusBookings:  (busId) => client.get(`/api/bookings/bus/${busId}`),
};

// ── Admin ─────────────────────────────────────────────────────────────────────
export const adminApi = {
  getAnalytics:    () => client.get('/api/admin/analytics'),
  getMonitoring:   () => client.get('/api/admin/monitoring'),
  getSelectorData: () => client.get('/api/admin/selector-data'),
  assignBus:       (d) => client.post('/api/admin/assign-bus', d),
  getUsers:        (page = 1) => client.get(`/api/admin/users?page=${page}`),
  blockUser:       (id) => client.patch(`/api/admin/users/${id}/block`),
  deleteUser:      (id) => client.delete(`/api/admin/users/${id}`),
  createBus:       (d) => client.post('/api/buses/', d),
  updateBus:       (id, d) => client.put(`/api/buses/${id}`, d),
  getBuses:        () => client.get('/api/buses/'),
  createDriver:    (d) => client.post('/api/admin/drivers', d),
  createRoute:     (d) => client.post('/api/routes/', d),
  updateRoute:     (id, d) => client.put(`/api/routes/${id}`, d),
  getRoutes:       () => client.get('/api/routes/'),
  addStop:         (routeId, d) => client.post(`/api/routes/${routeId}/stops`, d),
  getLogs:         (page = 1) => client.get(`/api/admin/logs?page=${page}`),
  broadcast:       (d) => client.post('/api/notifications/broadcast', d),
  acknowledgeIssue:(id) => client.post(`/api/admin/issues/${id}/acknowledge`),
  getActiveTrips:  () => client.get('/api/trips/active'),
  getAllBookings:   (page = 1) => client.get(`/api/bookings/?page=${page}`),
};

// ── Parent ────────────────────────────────────────────────────────────────────
export const parentApi = {
  getProfile:        () => client.get('/api/parent/me'),
  updateProfile:     (d) => client.put('/api/parent/me', d),
  linkChild:         (d) => client.post('/api/parent/children', d),
  getChildren:       () => client.get('/api/parent/children'),
  unlinkChild:       (id) => client.delete(`/api/parent/children/${id}`),
  trackChild:        (id) => client.get(`/api/parent/children/${id}/tracking`),
  childBooking:      (id) => client.get(`/api/parent/children/${id}/booking`),
  myNotifications:   (page = 1) => client.get(`/api/parent/notifications?page=${page}`),
  markRead:          (id) => client.patch(`/api/parent/notifications/${id}/read`),
};