# Foundation ERP — Python FastAPI Backend

High-performance, asynchronous REST API service powering the Foundation ERP ecosystem built with **Python 3.12**, **FastAPI**, **SQLAlchemy 2.0**, **Pydantic 2**, and **PostgreSQL**.

The backend operates as an independent microservice that manages database operations, business transactions, authentication, role-based authorization, ledgers, and financial reports.

---

## Architecture Overview

```text
Next.js Frontend (HTTPS / JSON)
              │
              ▼
   FastAPI REST API Router (/api/v1)
              │
    ┌─────────┴─────────┐
    ▼                   ▼
Auth & RBAC      Service Layer (Business Logic & Transactions)
                        │
                        ▼
                Repository Layer (SQLAlchemy 2.0)
                        │
                        ▼
          PostgreSQL Database (psycopg3 pool)
```

- **Independent Deployment**: Can be hosted on Render, Railway, Fly.io, AWS ECS, or any standard Linux VPS.
- **Standalone Package**: Fully self-contained Python package (`app.*`) requiring no monorepo parent or Docker container.
- **Async & Connection Pooling**: Built with `psycopg` (v3) async/sync drivers with connection pooling and automated health recovery.
- **Automated Interactive Docs**: Swagger UI (`/api/v1/docs`) and ReDoc (`/api/v1/redoc`) available out of the box.

---

## Technology Stack

- **Framework**: FastAPI (v0.115+) & Starlette
- **Language**: Python 3.12+
- **ASGI Server**: Uvicorn
- **ORM / Database Access**: SQLAlchemy 2.0 (mapped column models with explicit defaults)
- **Database Driver**: `psycopg` v3 (binary)
- **Data Validation & Settings**: Pydantic v2 & Pydantic Settings
- **Authentication & Security**: Passlib (Bcrypt), Python-Jose / PyJWT, HTTP Bearer & Cookie auth
- **Database Migrations**: Alembic
- **Testing**: Pytest, HTTPX, AnyIO

---

## Folder Structure

```text
backend/
├── app/
│   ├── api/                      # REST API routes and endpoints
│   │   ├── auth.py               # Login, session, token refresh, active devices
│   │   ├── members.py            # Members CRUD, profile, and dues status
│   │   ├── member_requests.py    # Public registration requests & review workflow
│   │   ├── groups.py             # Foundation groups and balances
│   │   ├── funds.py              # Dedicated funds management
│   │   ├── sadaqah.py            # Sadaqah & general donations collection
│   │   ├── loans.py              # Qard Hasan (interest-free loan) lifecycle
│   │   ├── grants.py             # Beneficiary assistance & grant disbursement
│   │   ├── campaigns.py          # Campaigns & campaign contributions
│   │   ├── donors.py             # Donor directory & contributions
│   │   ├── settings.py           # Organization settings, roles, permissions
│   │   ├── reports.py            # Financial summaries, income/expense reports
│   │   └── health.py             # Service & database health checks
│   ├── auth/                     # Authentication utilities & token handlers
│   ├── core/                     # Application configuration & database engine
│   │   ├── config.py             # Pydantic Settings (.env loader)
│   │   └── database.py           # SQLAlchemy Engine, SessionLocal, get_db, poolers
│   ├── models/                   # SQLAlchemy ORM declarative models
│   │   ├── auth.py               # User, Role, Permission, UserRole, DeviceSession
│   │   ├── organization.py       # Organization, Group, FoundationBranch
│   │   ├── member.py             # Member, MemberProfile, MemberLedger
│   │   ├── member_request.py     # MemberRegistrationRequest
│   │   ├── fund.py               # Fund, FundTransaction
│   │   ├── donor.py              # Donor, SadaqahContribution
│   │   ├── loan.py               # Loan, LoanSchedule, LoanRepayment
│   │   ├── beneficiary.py        # Beneficiary, GrantDisbursement
│   │   ├── campaign.py           # Campaign, CampaignContribution
│   │   ├── ledger.py             # GeneralLedger, FinancialActivity
│   │   └── document.py           # Document attachments & Cloudinary references
│   ├── rbac/                     # Role-Based Access Control dependencies
│   ├── repositories/             # Data access patterns and transactional queries
│   ├── schemas/                  # Pydantic request/response validation schemas
│   ├── services/                 # Business logic and cross-entity transactions
│   └── main.py                   # FastAPI app factory, CORS middleware, route mounting
├── alembic/                      # Database migration scripts
├── tests/                        # Comprehensive Pytest test suite (73 tests)
│   ├── conftest.py               # Fixtures, test database session, test clients
│   ├── test_auth.py              # Authentication and JWT tests
│   ├── test_health.py            # Health & database probe tests
│   ├── test_members.py           # Member workflows and validations
│   ├── test_member_requests.py   # Public application and approval tests
│   ├── test_groups_funds_sadaqah.py # Financial entities and contributions tests
│   ├── test_dues_and_financial_activities.py # Dues, ledgers, transactions tests
│   └── test_qard_hasana_and_reports.py # Loans and financial reporting tests
├── .env.example                  # Template environment variables
├── pyproject.toml                # Project metadata & pytest configuration
└── requirements.txt              # Production and development Python dependencies
```

---

## Requirements

- **Python**: `3.12.x` or higher
- **PostgreSQL**: Version 14, 15, 16, 17, or 18 (e.g. Neon, Supabase, RDS, self-hosted)
- **Virtual Environment Tool**: `venv` or `uv`

---

## Python Environment Setup

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv .venv
   ```

3. **Activate the virtual environment**:
   - **Linux / macOS**:
     ```bash
     source .venv/bin/activate
     ```
   - **Windows**:
     ```bash
     .venv\Scripts\activate
     ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure Environment Variables**:
   Copy the example `.env` template:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and provide your PostgreSQL connection string and secret key.

---

## Environment Variables

| Variable | Required | Default / Example | Description |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | **Yes** | `postgresql+psycopg://user:pass@host:5432/dbname` | Full PostgreSQL connection URI using the `psycopg` driver. Supports `sslmode=require`. |
| `SECRET_KEY` | **Yes** | *32+ character random string* | Secret key for signing and verifying JWT tokens. |
| `CORS_ORIGINS` | **Yes** | `http://localhost:3000,https://your-frontend.vercel.app` | Comma-separated list of allowed frontend origins for CORS. |
| `ENVIRONMENT` | No | `development` | Environment mode (`development`, `staging`, `production`). |
| `DEBUG` | No | `False` | Enable debug logs and detailed error traces. Set to `False` in production. |
| `APP_NAME` | No | `Foundation API` | Name of the application displayed in documentation. |
| `API_V1_STR` | No | `/api/v1` | URL prefix for API version 1 endpoints. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `1440` | JWT access token lifespan in minutes (default: 24 hours). |

---

## PostgreSQL Database Configuration

The backend connects directly to PostgreSQL using SQLAlchemy 2.0 connection pooling with `psycopg3`.

### Connection String Format
```text
postgresql+psycopg://<username>:<password>@<host>:<port>/<database>?sslmode=require
```

### Connection Verification
Verify that your database connection is active and healthy:
```bash
python -c "from app.core.database import check_database_connection; print(check_database_connection())"
```
Or run the schema audit script:
```bash
python audit_schema.py
```

### Running Migrations (Alembic)
To apply database migrations:
```bash
alembic upgrade head
```

---

## Local Development

Start the FastAPI application with auto-reload:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The service will be accessible at:
- **API Root**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **Database Health**: [http://127.0.0.1:8000/health/db](http://127.0.0.1:8000/health/db)
- **Interactive Swagger UI**: [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)
- **Interactive ReDoc UI**: [http://127.0.0.1:8000/api/v1/redoc](http://127.0.0.1:8000/api/v1/redoc)

---

## Running Automated Tests

Run the full Pytest test suite:

```bash
pytest
```

Run specific test modules:
```bash
pytest tests/test_auth.py
pytest tests/test_health.py
pytest tests/test_members.py
pytest tests/test_roles_and_permissions.py
```

---

## Health Check & Monitoring Endpoints

| Method | Endpoint | Purpose | Sample Response |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Liveness check (instant response without DB query) | `{"status":"ok"}` |
| `GET` | `/health/db` | Readiness check (executes `SELECT 1` on PostgreSQL) | `{"status":"ok","database":"connected","detail":null}` |
| `GET` | `/api/v1/health` | Versioned API liveness check | `{"status":"ok"}` |
| `GET` | `/api/v1/health/db` | Versioned API database readiness probe | `{"status":"ok","database":"connected","detail":null}` |

---

## CORS Configuration

FastAPI includes built-in `CORSMiddleware`. Configure allowed origins via the `CORS_ORIGINS` environment variable:

```env
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,https://foundation-frontend.vercel.app
```

The middleware automatically enables:
- Allowed Methods: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`
- Allowed Headers: `Authorization`, `Content-Type`, `Accept`, `Origin`, `X-Requested-With`
- Credentials: `allow_credentials=True` (for cookies and Bearer tokens)

---

## Production Deployment Guides

### Deploying to Render (Web Service)

1. Create a new **Web Service** on [Render](https://render.com).
2. Set configuration:
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`
3. Add Environment Variables:
   - `DATABASE_URL`: *Your PostgreSQL connection string*
   - `SECRET_KEY`: *Generated secure key*
   - `CORS_ORIGINS`: `https://your-frontend.vercel.app`
   - `ENVIRONMENT`: `production`
   - `DEBUG`: `false`

### Deploying to Railway / Fly.io / VPS

- **Build / Run Command**: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4`
- **Recommended Workers**: `(2 x $NUM_CORES) + 1`

---

## Troubleshooting Common Issues

### 1. Database Connection Timeout or SSL Error
- **Cause**: Missing SSL parameters for hosted databases like Neon or AWS RDS.
- **Fix**: Append `?sslmode=require` to your `DATABASE_URL`. Ensure you are using `postgresql+psycopg://`.

### 2. ModuleNotFoundError: No module named 'app'
- **Cause**: Running uvicorn outside of the `backend` directory without `pythonpath` set.
- **Fix**: Run commands from inside `/backend` or ensure `PYTHONPATH=.` is exported.

### 3. Pytest Fixture Rollback Warnings
- **Cause**: Database transaction closing asynchronously during cleanup.
- **Fix**: The idempotent `conftest.py` handles commit/rollback boundaries safely. Ensure PostgreSQL is accessible during test execution.

---

## Security Best Practices

1. **Password Hashing**: Passwords are saved as one-way Bcrypt hashes; plain-text passwords are never logged or stored.
2. **JWT Security**: Tokens are signed using HMAC-SHA256 (`HS256`) with strict expiration timestamps.
3. **Database Sanitization**: SQLAlchemy ORM and parameterized statements protect against SQL injection vulnerabilities.
4. **Least-Privilege RBAC**: Every endpoint enforces granular permission checks (e.g. `MEMBER_VIEW`, `FINANCE_MANAGE`).
5. **No Docker Secrets**: Credentials must always be injected at runtime via environment variables, never hardcoded in repository files.
