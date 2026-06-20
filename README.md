# 🧾 TaxFlow – Full Stack GST SaaS

**Tech Stack:** Oracle DB (PL/SQL) + Python Flask + HTML/CSS/JS

---

## 📁 Project Structure

```
taxflow/
├── database/
│   ├── 01_schema.sql       ← Tables, sequences, constraints
│   ├── 02_packages.sql     ← PL/SQL stored procedures & packages
│   └── 03_triggers.sql     ← Oracle triggers
├── backend/
│   ├── app.py              ← Flask REST API
│   ├── requirements.txt    ← Python dependencies
│   └── .env.example        ← Environment variables template
└── frontend/
    └── index.html          ← Complete UI (landing + dashboard)
```

---

## ⚙️ Setup Instructions

### Step 1: Oracle Database Setup

1. Install **Oracle Database XE** (free): https://www.oracle.com/database/technologies/xe-downloads.html
2. Open SQL*Plus or SQL Developer and connect as admin
3. Create a new user for TaxFlow:

```sql
CREATE USER taxflow IDENTIFIED BY taxflow123;
GRANT CONNECT, RESOURCE, CREATE VIEW TO taxflow;
GRANT UNLIMITED TABLESPACE TO taxflow;
```

4. Connect as `taxflow` user and run the SQL files **in order**:

```bash
sqlplus taxflow/taxflow123@localhost:1521/XEPDB1

-- Inside SQL*Plus:
@database/01_schema.sql
@database/02_packages.sql
@database/03_triggers.sql
```

---

### Step 2: Python Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env and set your Oracle DB credentials

# Run the server
python app.py
```

Flask server starts at: **http://localhost:5000**

---

### Step 3: Frontend

The frontend is served by Flask automatically.
Open: **http://localhost:5000**

---

## 🔌 API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register` | ❌ | Register new user |
| POST | `/api/auth/login` | ❌ | Login & get token |
| POST | `/api/auth/logout` | ✅ | Logout |
| GET  | `/api/auth/me` | ✅ | Get current user |
| POST | `/api/leads/demo` | ❌ | Request a demo |
| POST | `/api/leads/contact` | ❌ | Contact form |
| GET  | `/api/products` | ❌ | List all products |
| GET  | `/api/dashboard` | ✅ | Dashboard stats |
| GET  | `/api/dashboard/conversions` | ✅ | Bank conversion history |
| GET  | `/api/dashboard/filings` | ✅ | GST filing history |

---

## 🗄️ PL/SQL Summary (for interviews)

### Packages (3)
- **PKG_AUTH** — Register, Login, Logout, Session Validation
- **PKG_LEADS** — Demo requests, Contact form
- **PKG_DASHBOARD** — User stats, Conversions

### Stored Procedures (8)
- `SP_REGISTER_USER` — Validates email uniqueness, creates user + trial subscription
- `SP_LOGIN_USER` — Verifies credentials, creates session token
- `SP_LOGOUT_USER` — Invalidates session
- `SP_GET_USER_BY_TOKEN` — Validates token & returns user info
- `SP_SUBMIT_DEMO_REQUEST` — Prevents duplicate requests
- `SP_SUBMIT_CONTACT` — Saves contact messages
- `SP_GET_USER_DASHBOARD` — Aggregates stats from 3 tables
- `SP_SAVE_BANK_CONVERSION` — Logs bank statement conversion

### Functions (1)
- `FN_VALIDATE_SESSION` — Returns user_id if token valid, else 0

### Triggers (5)
- `TRG_USERS_UPDATED_AT` — Auto-updates `updated_at` on USERS
- `TRG_USERS_AUDIT` — Logs role/status changes to AUDIT_LOGS
- `TRG_EXPIRE_OLD_SESSIONS` — Cleans sessions older than 30 days
- `TRG_SUBSCRIPTION_DATES` — Auto-sets end_date based on plan type
- `TRG_DEMO_REQUEST_LOG` — Logs every new demo request

### Tables (9)
`USERS` `USER_SESSIONS` `PRODUCTS` `SUBSCRIPTIONS` `DEMO_REQUESTS` `CONTACT_MESSAGES` `GST_FILINGS` `BANK_CONVERSIONS` `AUDIT_LOGS`

---

## 🚀 Production Deployment

```bash
# Use Gunicorn instead of Flask dev server
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

---

## 🔐 Security Features

- Passwords hashed with **bcrypt** (Python side)
- Session tokens stored in DB (Oracle `SYS_GUID()`)
- All sensitive routes require **Bearer token**
- Complete **audit logging** of user actions
- SQL injection prevented via **bind variables**
