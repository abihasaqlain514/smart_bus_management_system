# 🚌 SmartBus — University Bus Monitoring System

> **Final Year Project** — University of Jhang, Pakistan  
> A full-stack real-time bus tracking and management platform for university transport.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Features by Role](#3-features-by-role)
4. [Tech Stack](#4-tech-stack)
5. [Project Structure](#5-project-structure)
6. [Prerequisites](#6-prerequisites)
7. [Backend Setup](#7-backend-setup)
8. [Frontend Setup](#8-frontend-setup)
9. [Running the App](#9-running-the-app)
10. [Testing on a Physical Phone](#10-testing-on-a-physical-phone)
11. [Team / Sharing Setup](#11-team--sharing-setup)
12. [API Reference](#12-api-reference)
13. [Seeding Test Data](#13-seeding-test-data)
14. [GPS Simulation (No Real Bus Needed)](#14-gps-simulation-no-real-bus-needed)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Project Overview

SmartBus solves the daily pain points of university transport at the University of Jhang:

- **Passengers** (students) can see exactly where their bus is on a live map, book seats, and get ETA for their stop.
- **Drivers** start/end trips with one tap, stream their GPS location in real time, and report issues.
- **Parents** link their child's student ID and track which bus their child is on at any moment.
- **Admins** manage buses, routes, drivers, bookings, and view live analytics from a dashboard.

All location data flows through WebSockets so every connected client sees the bus move on the map with zero page refresh.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Mobile App (React Native)                 │
│  Passenger  │  Driver  │  Parent  │  Admin                  │
└──────┬──────┴────┬─────┴────┬─────┴────┬────────────────────┘
       │           │          │          │
       │    HTTP REST (axios) + WebSocket (ws://)
       │           │          │          │
┌──────▼───────────▼──────────▼──────────▼────────────────────┐
│                  FastAPI Backend (Python)                     │
│  Auth │ Trips │ Bookings │ Routes │ Buses │ Notifications     │
│                                                              │
│  WebSocket Connection Manager ──► broadcast to subscribers  │
│  Trip Watchdog (asyncio) ──► auto-close timed-out trips      │
└────────────────────────┬────────────────────────────────────┘
                         │ asyncpg (async)
                ┌────────▼────────┐
                │   PostgreSQL    │
                │  (local / prod) │
                └─────────────────┘
```

**Communication protocols:**

| Type | Protocol | Port |
|---|---|---|
| REST API | HTTP | 8000 |
| Live GPS stream | WebSocket (`ws://`) | 8000 |
| JS bundle (dev) | HTTP (Metro) | 8081 |

---

## 3. Features by Role

### 🎓 Passenger
- Register / login with university email
- Browse all active routes and their stops
- Book a seat on a bus for a specific date
- View live bus location on an OpenStreetMap (Leaflet) map
- See real-time ETA to their chosen stop
- Cancel bookings
- Receive push notifications when bus departs / arrives

### 🚌 Driver
- Login with driver code
- Start and end trips with one tap
- Automatic GPS streaming every 3 seconds
- View today's passenger manifest (who is booked on their bus)
- Report mechanical issues or incidents
- Demo GPS mode for testing without a moving vehicle

### 👨‍👧 Parent
- Register independently (no student account required)
- Link a child by their university student ID
- See child's booking status for today
- Track the live GPS position of the bus their child is on
- View bus number, route, seat number, speed, and next stop ETA

### 🛠 Admin
- Full CRUD for buses, routes, stops, and drivers
- Assign drivers to buses
- Block / unblock user accounts
- Live monitoring dashboard (all active trips + GPS positions)
- Broadcast notifications to all passengers
- View audit logs of all system actions
- Analytics: passenger counts, trip statistics

---

## 4. Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Mobile frontend | React Native (Expo bare workflow) | SDK 51 / RN 0.74 |
| Maps | Leaflet.js via WebView | 1.9.4 |
| Navigation | React Navigation (Stack + Bottom Tabs) | v6 |
| HTTP client | Axios | 1.7 |
| Backend framework | FastAPI | 0.136 |
| ASGI server | Uvicorn | 0.45 |
| Database ORM | SQLAlchemy (async) | 2.0 |
| Database | PostgreSQL | 14+ |
| Auth | JWT (python-jose + bcrypt) | — |
| Real-time | WebSockets (native FastAPI) | — |
| Migrations | Alembic | 1.13 |
| GPS simulation | Custom asyncio service | — |

---

## 5. Project Structure

```
FYP_SmartBus/
│
├── BMS_backend/                 ← Python FastAPI backend
│   ├── app/
│   │   ├── main.py              ← FastAPI app, router registration, lifespan
│   │   ├── database.py          ← SQLAlchemy async engine + session
│   │   ├── deps.py              ← JWT auth dependencies (require_driver, etc.)
│   │   ├── config.py            ← Pydantic settings (reads .env)
│   │   ├── models/              ← ORM table definitions
│   │   ├── routers/             ← One file per feature (auth, trips, bookings …)
│   │   ├── schemas/             ← Pydantic request/response models
│   │   ├── services/            ← Business logic (auth, GPS sim, watchdog …)
│   │   └── websockets/          ← WebSocket connection manager
│   ├── alembic/                 ← Database migration files
│   ├── requirements.txt
│   ├── seed.py                  ← Minimal seed (admin + buses)
│   ├── seed_university_routes.py← 10 real Jhang university routes + drivers
│   └── .env.example             ← Copy to .env and fill in values
│
├── SmartBusApp/                 ← React Native app
│   ├── src/
│   │   ├── api/                 ← Axios client + per-role API wrappers
│   │   ├── components/          ← Shared UI (LeafletMap, Btn, Card …)
│   │   ├── context/             ← AuthContext (JWT storage + user state)
│   │   ├── hooks/               ← useLiveTracking (WebSocket hook)
│   │   ├── navigation/          ← Stack + tab navigators per role
│   │   └── screens/             ← One folder per role
│   ├── android/                 ← Native Android project
│   ├── app.json                 ← Expo config (package: com.smartbus.app)
│   └── src/config.js            ← API_URL / WS_URL (edit for your network)
│
├── START-PHONE.bat              ← One-click: opens firewall + starts backend + Expo
├── INSTALL-ON-PHONE.ps1         ← Install built APK via USB ADB
├── FIX-FIREWALL.ps1             ← Opens ports 8000 & 8081 in Windows Firewall
├── build-apk.bat                ← Builds the Android APK
└── .gitignore
```

---

## 6. Prerequisites

Install these before anything else.

| Tool | Min. Version | Download |
|---|---|---|
| Python | 3.11 | [python.org](https://python.org) |
| PostgreSQL | 14 | [postgresql.org](https://postgresql.org) |
| Node.js | 18 LTS | [nodejs.org](https://nodejs.org) |
| Git | any | [git-scm.com](https://git-scm.com) |
| Android Studio | Hedgehog+ | [developer.android.com](https://developer.android.com/studio) |

> **Windows users:** Android Studio ships with a JDK. Point Gradle at it by setting  
> `org.gradle.java.home=C:\\Program Files\\Android\\Android Studio\\jbr`  
> in `SmartBusApp/android/gradle.properties` (already done in this repo).

---

## 7. Backend Setup

All commands run from the **`BMS_backend/`** folder unless noted.

### 7.1 — Clone and enter the folder

```bash
git clone https://github.com/your-username/FYP_SmartBus.git
cd FYP_SmartBus
```

### 7.2 — Create the PostgreSQL database

```sql
-- Run in psql or pgAdmin
CREATE DATABASE smart_bus_db;
```

### 7.3 — Create and activate the virtual environment

```bash
# From the repo root (not inside BMS_backend)
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Windows CMD
.\.venv\Scripts\activate.bat

# macOS / Linux
source .venv/bin/activate
```

### 7.4 — Install dependencies

```bash
pip install -r BMS_backend/requirements.txt
```

### 7.5 — Configure environment variables

```bash
cd BMS_backend
copy .env.example .env        # Windows
# cp .env.example .env        # macOS / Linux
```

Edit `.env` with your values:

```env
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/smart_bus_db
SECRET_KEY=replace-with-a-long-random-string-at-least-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

Generate a secure `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 7.6 — Start the backend

```bash
cd BMS_backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

On first run, SQLAlchemy **auto-creates all tables** via the `lifespan` hook — no manual migration needed.

Verify it works:
```
http://localhost:8000/          → {"status": "Smart Bus Monitoring System is running"}
http://localhost:8000/docs      → Swagger interactive API docs
```

---

## 8. Frontend Setup

All commands run from the **`SmartBusApp/`** folder.

### 8.1 — Install Node dependencies

```bash
cd SmartBusApp
npm install
```

### 8.2 — Configure the backend URL

Open `src/config.js` and set the correct mode for your situation:

```javascript
// src/config.js
const MODE = 'wifi';           // 'usb' | 'wifi' | 'ngrok'

const WIFI_IP    = '192.168.x.x';   // ← your PC's IPv4 (run: ipconfig)
const NGROK_HOST = 'xxxx.ngrok-free.app'; // only needed for MODE='ngrok'
```

**Which mode to use:**

| Situation | Mode | Requirement |
|---|---|---|
| Phone connected via USB cable | `usb` | ADB running (`adb reverse`) |
| Phone on same WiFi as laptop | `wifi` | Both on same network |
| Teammate on different network | `ngrok` | ngrok running on your laptop |

### 8.3 — Start Metro bundler

```bash
npx expo start --port 8081 --clear
```

---

## 9. Running the App

### Option A — Android Emulator (quickest for development)

```bash
# Start emulator from Android Studio, then:
cd SmartBusApp
npx expo start --port 8081

# Press 'a' in the Metro terminal to launch on emulator
```

### Option B — Physical Phone via USB (best performance)

```bash
# 1. Enable USB Debugging on your phone:
#    Settings → About Phone → tap Build Number 7× → Developer Options → USB Debugging ON

# 2. Connect phone via USB cable, then run from repo root:
adb reverse tcp:8000 tcp:8000
adb reverse tcp:8081 tcp:8081

# 3. Set MODE = 'usb' in SmartBusApp/src/config.js

# 4. Start Metro
cd SmartBusApp && npx expo start --port 8081

# 5. Build and install APK (first time only):
cd SmartBusApp/android
.\gradlew.bat assembleDebug --no-daemon
adb install -r app\build\outputs\apk\debug\app-debug.apk
```

### Option C — One-click Windows launcher

From the repo root, double-click **`START-PHONE.bat`** — it opens the firewall, starts the backend, and starts Expo automatically. Requires running as Administrator.

---

## 10. Testing on a Physical Phone

### Build a standalone APK (no Metro needed)

This embeds the JS bundle into the APK so the phone only needs WiFi to reach the backend — no USB cable.

```powershell
# 1. Set WIFI_IP in SmartBusApp/src/config.js to your PC's IPv4
#    Run `ipconfig` to find it

# 2. Build
cd SmartBusApp\android
.\gradlew.bat assembleDebug --no-daemon

# APK output:
# SmartBusApp\android\app\build\outputs\apk\debug\app-debug.apk

# 3. Install via USB (one time only)
adb install -r "SmartBusApp\android\app\build\outputs\apk\debug\app-debug.apk"

# Or run the helper script:
.\INSTALL-ON-PHONE.ps1
```

After installation, the app runs **cable-free** as long as the phone is on the same WiFi as the laptop running the backend.

> **Firewall note (Windows):** Run `FIX-FIREWALL.ps1` as Administrator once to open ports 8000 and 8081 in Windows Firewall. Without this, the phone cannot reach the backend over WiFi.

---

## 11. Team / Sharing Setup

### For developer teammates (same codebase)

```bash
# Clone and set up backend (same steps as Section 7)
git clone <repo-url>

# Set the ngrok tunnel URL in config.js
# MODE = 'ngrok'
# NGROK_HOST = 'xxxx.ngrok-free.app'   ← get this from the project owner

cd SmartBusApp && npm install && npx expo start --port 8082
```

### For supervisors (non-developers, just want to test the app)

1. Receive the `app-debug.apk` file (via Google Drive / WhatsApp)
2. On Android phone: **Settings → Install Unknown Apps → Chrome → Allow**
3. Open the APK file to install
4. Open SmartBus app — make sure you are on the same WiFi as the laptop running the backend

### Expose the backend publicly (ngrok)

```bash
# Install: winget install ngrok.ngrok
ngrok http 8000
# Prints: https://xxxx.ngrok-free.app

# Update SmartBusApp/src/config.js:
# MODE = 'ngrok'
# NGROK_HOST = 'xxxx.ngrok-free.app'
```

The app will then work on **any internet connection**, not just your local WiFi.

---

## 12. API Reference

The full interactive API reference is available at:

```
http://localhost:8000/docs      ← Swagger UI (try all endpoints live)
http://localhost:8000/redoc     ← ReDoc (clean read-only reference)
```

### Base URL
```
http://localhost:8000/api
```

### Authentication

All protected endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Obtain a token by calling any login endpoint.

### Key endpoints

| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/api/auth/passenger/register` | — | Register passenger |
| POST | `/api/auth/passenger/login` | — | Passenger login |
| POST | `/api/parent/register` | — | Register parent |
| POST | `/api/parent/login` | — | Parent login |
| POST | `/api/auth/driver/login` | — | Driver login |
| POST | `/api/auth/admin/login` | — | Admin login |
| GET | `/api/routes/` | Any | List all routes |
| GET | `/api/locations/live` | Any | All active buses with GPS |
| POST | `/api/trips/start` | Driver | Start a trip |
| POST | `/api/locations/update` | Driver | Push GPS coordinate |
| GET | `/api/parent/children/{id}/tracking` | Parent | Child's live bus location |
| WS | `/api/locations/ws/live-tracking?bus_id=` | Any | Subscribe to live GPS stream |

---

## 13. Seeding Test Data

The database starts empty. Run these scripts to populate realistic test data.

```bash
cd BMS_backend

# Activate your virtual environment first (.venv or venv)
.\.venv\Scripts\Activate.ps1   # Windows

# Option A — Minimal seed (1 admin, a few buses)
python seed.py

# Option B — Full university data (recommended for full testing)
# Seeds 10 real routes from Jhang to University of Jhang,
# 10 buses (101–900), 10 drivers, stops with GPS coordinates
python seed_university_routes.py
```

### Test credentials after seeding

| Role | Login | Password |
|---|---|---|
| Admin | `admin@smartbus.com` | `Admin@1234` |
| Driver 1 | `DRV-JHG-01` (driver code) | `Driver@1234` |
| Driver 2 | `DRV-JHG-02` | `Driver@1234` |
| … Driver 10 | `DRV-JHG-10` | `Driver@1234` |
| Passenger | Register via app | your choice |
| Parent | Register via app | your choice |

---

## 14. GPS Simulation (No Real Bus Needed)

During development, you can simulate a bus moving along a real route without a physical vehicle.

### Start a simulation via Swagger

```
1. Open http://localhost:8000/docs
2. Login as admin → copy the access_token
3. Click Authorize (top-right) → paste token
4. Start a trip as a driver first (POST /api/trips/start)
5. Use the returned trip_id in:
   POST /api/debug/simulate/preset/city_loop?trip_id=<id>&speed_kmh=40
```

### Available route presets

| Preset | Route |
|---|---|
| `city_loop` | Short loop around Jhang city centre |
| `1-M` | Chiniot → University of Jhang (full route) |
| `2-M` | Toba Tek Singh → University of Jhang |

### Stop a simulation

```
DELETE /api/debug/simulate/{trip_id}
```

### Watch it live

On the passenger HomeScreen or the parent tracking screen, the bus marker will move across the map every 3 seconds while the simulation is running.

---

## 15. Troubleshooting

### Backend

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` on startup | Virtual environment not activated — run `.venv\Scripts\Activate.ps1` |
| `connection refused` to PostgreSQL | PostgreSQL service not running — `net start postgresql-x64-14` |
| `column does not exist` error | Missing migration — run `python add_stop_time.py` from `BMS_backend/` |
| `401 Unauthorized` on all requests | Token expired (24h TTL) — log in again |
| `403 Not a driver account` | Logged in with wrong role — use the correct login endpoint |

### Mobile App

| Symptom | Fix |
|---|---|
| "Retry Connection" on WelcomeScreen | Backend not running, or wrong IP in `config.js` |
| App crashes immediately on phone | Wrong CPU architecture — rebuild with `reactNativeArchitectures=arm64-v8a,x86_64` |
| Map is blank / not loading | No internet — Leaflet tiles require internet access |
| GPS not posting (driver screen) | Location permission denied — grant in Android Settings |
| `BUILD FAILED` with OOM error | Reduce JVM heap: set `org.gradle.jvmargs=-Xmx1536m` in `android/gradle.properties` |
| Metro not found from phone | Firewall blocking port 8081 — run `FIX-FIREWALL.ps1` as Administrator |

### Connection (Phone ↔ Backend)

```
Phone shows "Cannot reach backend (http://192.168.x.x:8000)"

Checklist:
  ✅ Backend started with --host 0.0.0.0 (not 127.0.0.1)
  ✅ Phone and laptop on the SAME WiFi network
  ✅ WIFI_IP in config.js matches output of `ipconfig`
  ✅ Firewall allows port 8000 (run FIX-FIREWALL.ps1 as Admin)
  ✅ config.js MODE is set correctly ('wifi' / 'usb' / 'ngrok')
```

---

## Contributors

| Name | Role |
|---|---|
| Abiha Saqlain | Full-stack Developer (Backend + Mobile) |

**Supervisor:** University of Jhang  
**Institution:** University of Jhang, Pakistan  

---

## License

This project is developed as a Final Year Project for academic purposes at the University of Jhang.
