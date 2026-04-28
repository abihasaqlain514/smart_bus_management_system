# Smart Bus Monitoring System — End-to-End Testing Guide

Use **Postman**, **Thunder Client** (VS Code), or **curl**.
All examples use `curl`. Swagger UI at `http://localhost:8000/docs` works too.

Save the token from each login — you'll need it for protected routes.

---

## Setup Before Testing

```bash
# Make sure the server is running
uvicorn app.main:app --reload

# Base URL used throughout this guide
BASE=http://localhost:8000/api
```

---

## Phase 1 — Admin Setup

Admin accounts are created directly in the database for the first admin.
Run this SQL once in psql / pgAdmin:

```sql
-- Connect to your database first
\c smart_bus_db

-- Insert the first admin user (bcrypt hash of "Admin@1234")
-- Generate your own hash: python -c "from passlib.context import CryptContext; print(CryptContext(['bcrypt']).hash('Admin@1234'))"

INSERT INTO users (id, full_name, email, password_hash, role, is_active, is_verified)
VALUES (
  gen_random_uuid(),
  'System Admin',
  'admin@smartbus.com',
  '$2b$12$placeholder_replace_with_real_bcrypt_hash',
  'admin',
  true,
  true
);

-- Get the user id just inserted
SELECT id FROM users WHERE email = 'admin@smartbus.com';

-- Insert the admin profile (use the id from above)
INSERT INTO admins (admin_id, department)
VALUES ('<paste-id-here>', 'IT');
```

> **Easier way:** use the `/docs` Swagger UI to call `POST /api/admin/login`
> after seeding, OR run the project once and use a migration seed script.

---

## Phase 2 — Admin Login

```bash
curl -X POST "$BASE/auth/admin/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@smartbus.com",
    "password": "Admin@1234"
  }'
```

**Expected response:**
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "admin": { "id": "...", "full_name": "System Admin", ... }
}
```

Save the token:
```bash
ADMIN_TOKEN="eyJhbGciOi..."
```

---

## Phase 3 — Create a Route

```bash
curl -X POST "$BASE/routes/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "route_name": "University Express",
    "route_number": "R-01",
    "start_point": "City Center",
    "end_point": "University Main Gate",
    "distance_km": 12.5
  }'
```

Save the returned `id` as `ROUTE_ID`.

### Add Stops to the Route

```bash
# Stop 1 — City Center
curl -X POST "$BASE/routes/$ROUTE_ID/stops" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "stop_name": "City Center",
    "stop_order": 1,
    "latitude": 31.5204,
    "longitude": 74.3587,
    "estimated_minutes": 0
  }'

# Stop 2 — Midpoint
curl -X POST "$BASE/routes/$ROUTE_ID/stops" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "stop_name": "Gulberg Chowk",
    "stop_order": 2,
    "latitude": 31.5120,
    "longitude": 74.3450,
    "estimated_minutes": 15
  }'

# Stop 3 — University
curl -X POST "$BASE/routes/$ROUTE_ID/stops" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "stop_name": "University Main Gate",
    "stop_order": 3,
    "latitude": 31.4827,
    "longitude": 74.3015,
    "estimated_minutes": 35
  }'
```

---

## Phase 4 — Create a Bus

```bash
curl -X POST "$BASE/buses/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bus_number": "BUS-001",
    "capacity": 40,
    "model": "Toyota Coaster",
    "plate_number": "LHR-1234",
    "route_id": "'$ROUTE_ID'"
  }'
```

Save the returned `id` as `BUS_ID`.

---

## Phase 5 — Create a Driver Account

Only admins can create driver accounts.

```bash
curl -X POST "$BASE/admin/drivers" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Ahmed Khan",
    "email": "driver1@smartbus.com",
    "password": "Driver@1234",
    "phone_number": "+923001234567",
    "driver_code": "DRV-2024-001",
    "license_number": "LHR-DL-2024-001"
  }'
```

---

## Phase 6 — Driver Login

```bash
curl -X POST "$BASE/auth/driver/login" \
  -H "Content-Type: application/json" \
  -d '{
    "driver_code": "DRV-2024-001",
    "password": "Driver@1234"
  }'
```

**Expected response includes:**
```json
{
  "access_token": "...",
  "driver": {
    "driver_code": "DRV-2024-001",
    "status": "offline",
    "assigned_bus_id": null
  }
}
```

Save the token:
```bash
DRIVER_TOKEN="eyJhbGciOi..."
```

---

## Phase 7 — Passenger Registration & Login

```bash
# Register
curl -X POST "$BASE/auth/passenger/register" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Sara Ali",
    "email": "sara@student.edu.pk",
    "password": "Student@1234",
    "university_id": "2021-CS-001",
    "student_type": "bs",
    "phone_number": "+923119876543"
  }'

# Login
curl -X POST "$BASE/auth/passenger/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "sara@student.edu.pk",
    "password": "Student@1234"
  }'
```

Save the token:
```bash
PASSENGER_TOKEN="eyJhbGciOi..."
```

---

## Phase 8 — Parent Registration & Child Linking

```bash
# Register parent
curl -X POST "$BASE/parent/register" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Mr. Ali",
    "email": "parent@family.com",
    "password": "Parent@1234",
    "phone_number": "+923001111111"
  }'

# Parent login
curl -X POST "$BASE/parent/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "parent@family.com",
    "password": "Parent@1234"
  }'
```

Save:
```bash
PARENT_TOKEN="eyJhbGciOi..."
```

```bash
# Link child by university ID
curl -X POST "$BASE/parent/children" \
  -H "Authorization: Bearer $PARENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "university_id": "2021-CS-001",
    "relationship_type": "father"
  }'
```

**Expected:** child is now linked — parent can track their bus.

---

## Phase 9 — Passenger Books a Seat

```bash
curl -X POST "$BASE/bookings/" \
  -H "Authorization: Bearer $PASSENGER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bus_id": "'$BUS_ID'",
    "route_id": "'$ROUTE_ID'",
    "seat_number": 5,
    "booking_date": "2025-01-20"
  }'
```

**Expected:** `{"status": "pending", ...}`

Save the returned `id` as `BOOKING_ID`.

### Check booking status (as parent)

```bash
PASSENGER_USER_ID="<passenger's UUID from registration>"

curl "$BASE/parent/children/$PASSENGER_USER_ID/booking" \
  -H "Authorization: Bearer $PARENT_TOKEN"
```

---

## Phase 10 — Driver Starts a Trip

```bash
curl -X POST "$BASE/trips/start" \
  -H "Authorization: Bearer $DRIVER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bus_id": "'$BUS_ID'",
    "route_id": "'$ROUTE_ID'"
  }'
```

**Expected:** trip is created with `status: active`, bus status becomes `on_route`.

Save the returned `id` as `TRIP_ID`.

---

## Phase 11 — Driver Posts GPS Updates

```bash
# Simulate the bus moving — call this repeatedly with changing coordinates

curl -X POST "$BASE/locations/update" \
  -H "Authorization: Bearer $DRIVER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bus_id": "'$BUS_ID'",
    "trip_id": "'$TRIP_ID'",
    "latitude": 31.5204,
    "longitude": 74.3587,
    "speed_kmh": 45.5,
    "heading_deg": 180.0,
    "available_seats": 35
  }'

# Second update — bus moved
curl -X POST "$BASE/locations/update" \
  -H "Authorization: Bearer $DRIVER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bus_id": "'$BUS_ID'",
    "trip_id": "'$TRIP_ID'",
    "latitude": 31.5120,
    "longitude": 74.3450,
    "speed_kmh": 50.0,
    "heading_deg": 185.0
  }'
```

---

## Phase 12 — Live Tracking (Passenger & Parent)

### REST: All live buses

```bash
curl "$BASE/locations/live" \
  -H "Authorization: Bearer $PASSENGER_TOKEN"
```

### REST: Single bus latest location

```bash
curl "$BASE/buses/$BUS_ID/location" \
  -H "Authorization: Bearer $PASSENGER_TOKEN"
```

### REST: Parent tracks child's bus

```bash
curl "$BASE/parent/children/$PASSENGER_USER_ID/tracking" \
  -H "Authorization: Bearer $PARENT_TOKEN"
```

**Expected response includes:** GPS coordinates, bus status, active trip ID, nearest stop ETA.

### WebSocket: Real-time GPS stream

Open this in a WebSocket client (Postman, Insomnia, or browser DevTools):

```
ws://localhost:8000/ws/live-tracking?bus_id=<BUS_ID>
```

Every time the driver POSTs a GPS update, you'll receive a JSON message:
```json
{
  "bus_id": "...",
  "latitude": 31.5120,
  "longitude": 74.3450,
  "speed_kmh": 50.0,
  "recorded_at": "2025-01-20T08:45:00"
}
```

---

## Phase 13 — ETA Calculation

```bash
curl "$BASE/trips/$TRIP_ID/eta" \
  -H "Authorization: Bearer $PASSENGER_TOKEN"
```

**Expected:**
```json
{
  "trip_id": "...",
  "next_stop_name": "Gulberg Chowk",
  "distance_to_stop_km": 2.3,
  "estimated_minutes": 4,
  "current_speed_kmh": 50.0
}
```

---

## Phase 14 — Driver Sends Notification

```bash
curl -X POST "$BASE/notifications/send" \
  -H "Authorization: Bearer $DRIVER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "arriving",
    "title": "Bus Arriving Soon",
    "message": "BUS-001 will arrive at Gulberg Chowk in 5 minutes.",
    "trip_id": "'$TRIP_ID'"
  }'
```

Both **passengers on the route** and their **linked parents** receive this notification automatically.

### Passenger checks notifications

```bash
curl "$BASE/notifications/my" \
  -H "Authorization: Bearer $PASSENGER_TOKEN"
```

### Parent checks notifications

```bash
curl "$BASE/parent/notifications" \
  -H "Authorization: Bearer $PARENT_TOKEN"
```

### Mark notification as read

```bash
NOTIF_ID="<notification UUID>"

curl -X PATCH "$BASE/notifications/$NOTIF_ID/read" \
  -H "Authorization: Bearer $PASSENGER_TOKEN"
```

---

## Phase 15 — Driver Reports an Issue (Emergency)

```bash
curl -X POST "$BASE/trips/$TRIP_ID/issues" \
  -H "Authorization: Bearer $DRIVER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "trip_id": "'$TRIP_ID'",
    "issue_type": "breakdown",
    "description": "Engine overheated near Gulberg Chowk.",
    "severity": "high"
  }'
```

Admin sees the issue in the monitoring panel:

```bash
curl "$BASE/admin/issues" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

Admin acknowledges it:

```bash
ISSUE_ID="<issue UUID>"

curl -X POST "$BASE/admin/issues/$ISSUE_ID/acknowledge" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## Phase 16 — Driver Ends the Trip

```bash
curl -X POST "$BASE/trips/$TRIP_ID/end" \
  -H "Authorization: Bearer $DRIVER_TOKEN"
```

**Expected:** trip `status` becomes `completed`, driver `is_online` becomes `false`, bus status returns to `not_in_service`.

---

## Phase 17 — Admin Analytics

```bash
curl "$BASE/admin/analytics" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Expected:**
```json
{
  "total_users": 3,
  "total_buses": 1,
  "active_routes": 1,
  "total_bookings": 1,
  "active_trips": 0
}
```

---

## Phase 18 — Admin Monitoring Dashboard

```bash
# All buses with GPS + driver info
curl "$BASE/admin/monitoring" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Paginated user list
curl "$BASE/admin/users?page=1&page_size=10" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Audit log
curl "$BASE/admin/logs" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## Quick Checklist

| # | Test | Expected Result |
|---|------|----------------|
| 1 | Server starts | `Application startup complete` in terminal |
| 2 | `GET /` | `{"status": "Smart Bus Monitoring System is running"}` |
| 3 | Admin login | Returns JWT token |
| 4 | Create route | Route saved with UUID |
| 5 | Add stops | Stops ordered by `stop_order` |
| 6 | Create bus | Bus saved, `available_seats = capacity` |
| 7 | Create driver (admin) | Driver account created |
| 8 | Driver login | Returns token with `driver_code` |
| 9 | Passenger register | Returns user object |
| 10 | Parent register + link child | Child appears in parent's children list |
| 11 | Passenger books seat | Booking created with `status: pending` |
| 12 | Duplicate seat booking | Returns `409 Conflict` |
| 13 | Driver starts trip | Trip `status: active`, bus `on_route` |
| 14 | Driver posts GPS | Location saved, WebSocket clients receive update |
| 15 | Parent tracking | Returns GPS + booking + bus info for child |
| 16 | Send notification | Passengers AND parents on route receive it |
| 17 | Driver ends trip | Trip `status: completed` |
| 18 | Admin analytics | Returns aggregate counts |
| 19 | Admin blocks user | `is_active = false`, user gets 401 |
| 20 | Swagger UI loads | `http://localhost:8000/docs` shows all routes |

---

## Common Error Codes

| Code | Meaning | Fix |
|------|---------|-----|
| `401` | Missing or invalid token | Add `Authorization: Bearer <token>` header |
| `403` | Wrong role | Use the correct role's token (passenger vs driver vs admin vs parent) |
| `404` | Record not found | Check the UUID — it may not exist in the DB |
| `409` | Conflict | Duplicate seat booking or duplicate email |
| `422` | Validation error | Check the request body — a required field is missing or wrong type |
| `423` | Admin account locked | Too many wrong passwords — wait 15 min or reset `locked_until` in DB |
| `500` | Server error | Check the uvicorn terminal for the Python traceback |

---

## Testing with Swagger UI (No curl needed)

1. Open `http://localhost:8000/docs`
2. Click any endpoint → **Try it out** → fill in the body → **Execute**
3. For protected endpoints: click **Authorize** (lock icon, top right) → paste your JWT token → **Authorize**
4. All endpoints are now authenticated for the session
