# Smart Bus Monitoring System — How to Run

## Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.11+ (project uses 3.14) | python.org |
| PostgreSQL | 14+ | postgresql.org |
| Git | any | git-scm.com |

---

## 1. Clone / Open the Project

```bash
# If cloning fresh
git clone <your-repo-url>
cd BMS_backend

# Or just open the existing folder in VS Code
```

---

## 2. Create & Activate Virtual Environment

```bash
# Create
python -m venv venv

# Activate — Windows CMD
venv\Scripts\activate

# Activate — Windows PowerShell
venv\Scripts\Activate.ps1

# Activate — Mac / Linux
source venv/bin/activate

# Confirm — you should see (venv) at the start of your prompt
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `firebase-admin` is commented out in requirements.txt.
> Install it only when you have a `firebase-credentials.json` file:
> ```bash
> pip install firebase-admin==6.5.0
> ```

---

## 4. Set Up PostgreSQL

### 4a. Create the database

Open **pgAdmin** or **psql** and run:

```sql
-- Create the database
CREATE DATABASE smart_bus_db;

-- Optional: create a dedicated user
CREATE USER smart_bus WITH PASSWORD 'postgres123';
GRANT ALL PRIVILEGES ON DATABASE smart_bus_db TO smart_bus;

-- Enable the UUID extension (required for gen_random_uuid())
\c smart_bus_db
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
```

### 4b. Confirm connection string

Your `DATABASE_URL` in `.env` should match the credentials above:
```
postgresql+asyncpg://postgres:postgres123@localhost:5432/smart_bus_db
```
Adjust the username/password to whatever you created.

---

## 5. Configure Environment Variables

```bash
# Copy the example file
copy .env.example .env       # Windows
cp .env.example .env         # Mac/Linux
```

Edit `.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres123@localhost:5432/smart_bus_db
SECRET_KEY=replace-this-with-a-long-random-string-minimum-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
```

Generate a strong `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 6. Run Database Migrations

### Option A — Alembic (recommended for production)

```bash
# Apply the initial migration (creates all tables)
alembic upgrade head
```

### Option B — Auto create (development shortcut)

Tables are also created automatically when the server starts
(`Base.metadata.create_all` runs in the FastAPI lifespan).
No manual step needed if you just want to test quickly.

---

## 7. Start the Server

```bash
# Development (auto-reload on file changes)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## 8. Verify It's Running

Open your browser:

| URL | What you see |
|-----|-------------|
| `http://localhost:8000` | `{"status": "Smart Bus Monitoring System is running"}` |
| `http://localhost:8000/docs` | Swagger UI — interactive API docs |
| `http://localhost:8000/redoc` | ReDoc — alternative docs |

---

## 9. Project Structure (quick reference)

```
BMS_backend/
├── app/
│   ├── main.py          ← FastAPI app entry point
│   ├── config.py        ← Reads .env variables
│   ├── database.py      ← Async SQLAlchemy engine + session
│   ├── deps.py          ← Auth dependencies (get_current_user, require_*)
│   ├── models/          ← SQLAlchemy ORM models (DB tables)
│   ├── schemas/         ← Pydantic v2 request/response schemas
│   ├── routers/         ← API route handlers (one file per role/feature)
│   ├── services/        ← Business logic (auth, GPS, notifications, etc.)
│   ├── middleware/       ← Audit logging, auth middleware
│   └── websockets/      ← WebSocket connection manager (live tracking)
├── alembic/             ← Database migration scripts
├── alembic.ini
├── .env                 ← Your local secrets (never commit this)
├── .env.example         ← Template for .env
└── requirements.txt
```

---

## 10. API Base URL

All REST endpoints live under:
```
http://localhost:8000/api/
```

WebSocket live tracking:
```
ws://localhost:8000/ws/live-tracking?bus_id=<UUID>
```

---

## Common Issues

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'app'` | Run uvicorn from the `BMS_backend/` root directory, not from inside `app/` |
| `could not connect to server` (PostgreSQL) | Make sure PostgreSQL service is running: `net start postgresql-x64-16` (Windows) |
| `(venv) not showing` | Activate the virtual environment — see Step 2 |
| `git not recognized in cmd.exe` | Close and reopen VS Code, or switch terminal to PowerShell |
| `gen_random_uuid() does not exist` | Run `CREATE EXTENSION IF NOT EXISTS "pgcrypto";` inside your database |
| `422 Unprocessable Entity` | Check the request body format — open `/docs` to see required fields |
| `401 Unauthorized` | Pass the JWT token in the `Authorization: Bearer <token>` header |
