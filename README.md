# Foundation ERP — Python FastAPI Backend Guide

High-performance, asynchronous REST API service powering the Foundation ERP ecosystem. Built with **Python 3.12**, **FastAPI**, **SQLAlchemy 2.0**, **Pydantic 2**, and **PostgreSQL (psycopg3)**.

The backend operates as an independent microservice responsible for database persistence, transactional integrity, double-entry financial ledgers, member registries, authentication, and role-based authorization.

---

## 1. What the Backend Is

The **Foundation ERP Backend** is a modular RESTful web service that handles all server-side operations for the foundation management platform.

### Core Capabilities
- **Authentication & RBAC**: JWT token issuance, password hashing via Bcrypt, device session tracking, and granular role/permission enforcement (e.g. `SUPER_ADMIN`, `ADMIN`, `MEMBER`).
- **Member Management**: Comprehensive member lifecycle tracking, custom ID generation (`MEM-YYYY-XXXX`), duplicate mobile/NID verification, and public member registration request workflows.
- **Financial Ledgers & Double-Entry Accounting**: General ledger entries (`LedgerTransaction`, `LedgerEntry`), transaction rollback protection, and automatic account balance maintenance.
- **Dedicated Fund Management**: Specific funds (e.g. Education, Emergency, Healthcare) with balance isolation and donation intake.
- **Sadaqah & Donors**: Donor registry and anonymous/member contribution processing with multi-method payment verification.
- **Qard Hasan (Benevolent Loans)**: Loan applications, approval pipeline, installment scheduling, repayment recording, and loan account ledgers.
- **Grants & Beneficiary Welfare**: Vulnerable beneficiary registry, assistance records, and grant disbursement tracking.
- **Reports & Analytics**: Aggregate income/expense statements, collection summaries, and financial balance sheets.

---

## 2. Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Framework** | FastAPI (v0.115+) & Starlette | High-performance asynchronous API framework with automatic OpenAPI docs |
| **Language & Runtime** | Python 3.12+ | Modern Python with typed hints and standard library async features |
| **ASGI Server** | Uvicorn (v0.34+) | Asynchronous server gateway interface for production and development |
| **ORM & Database Layer**| SQLAlchemy 2.0 | Declarative mapped column models, connection pooling, and transactional units |
| **Database Driver** | `psycopg` (v3.2+ binary) | Modern, native PostgreSQL driver with pooler support |
| **Data Validation & Config**| Pydantic v2 & Pydantic Settings | Strict schema validation, request deserialization, and `.env` management |
| **Security & Cryptography** | Passlib (Bcrypt) & Python-Jose / PyJWT | Cryptographic password hashing and HMAC-SHA256 JWT signature verification |
| **Database Migrations** | Alembic (v1.14+) | Schema version control and database migration pipeline |
| **Automated Testing** | Pytest, HTTPX, AnyIO | Comprehensive test suite (73 automated unit and integration tests) |

---

## 3. Project Structure

```text
.
├── app/
│   ├── api/                      # REST API routing layer
│   │   ├── v1/                   # Version 1 API endpoints
│   │   │   ├── endpoints/        # Feature-specific route handlers
│   │   │   │   ├── upload.py             # Cloudinary media upload (images/PDFs) & deletions
│   │   │   │   ├── members.py            # Members CRUD, profile, and dues status
│   │   │   │   ├── member_requests.py    # Public registration and review workflows
│   │   │   │   ├── groups.py             # Foundation groups and group ledgers
│   │   │   │   ├── funds.py              # Dedicated funds and balances
│   │   │   │   ├── sadaqah.py            # Sadaqah & general donations collection
│   │   │   │   ├── dues.py               # Monthly member dues collection
│   │   │   │   ├── loans.py              # Qard Hasan benevolent loans & schedules
│   │   │   │   ├── grants.py             # Beneficiary assistance & disbursements
│   │   │   │   ├── beneficiaries.py      # Beneficiary profiles and history
│   │   │   │   ├── campaigns.py          # Fundraising campaigns & contributions
│   │   │   │   ├── donors.py             # Donor directory & contributions
│   │   │   │   ├── roles.py              # Roles management
│   │   │   │   ├── permissions.py        # System permissions catalog
│   │   │   │   ├── reports.py            # Financial reports & aggregation
│   │   │   │   ├── settings.py           # Organization settings & rules
│   │   │   │   └── health.py             # Health check endpoints
│   │   │   └── router.py         # Main v1 router aggregating all endpoints
│   │   └── router.py             # Top-level API router
│   ├── auth/                     # Authentication utilities & token handlers
│   │   ├── dependencies.py       # Current user injection, Bearer/Cookie extractors
│   │   ├── router.py             # Login, logout, session refresh, active devices
│   │   ├── schemas.py            # LoginRequest, TokenResponse, UserDto schemas
│   │   ├── security.py           # Bcrypt hashing & JWT encode/decode functions
│   │   └── service.py            # AuthService (session persistence, verification)
│   ├── core/                     # Core infrastructure & configuration
│   │   ├── config.py             # Pydantic Settings class (reads .env variables)
│   │   ├── database.py           # SQLAlchemy Engine, SessionLocal, get_db fixture
│   │   └── errors.py             # Standard AppException classes and error handlers
│   ├── models/                   # SQLAlchemy ORM declarative models (31 tables)
│   │   ├── auth.py               # User, Role, Permission, RolePermission, UserSession
│   │   ├── organization.py       # Organization, Group, Foundation
│   │   ├── member.py             # Member, MemberProfile, MemberStatusHistory
│   │   ├── member_request.py     # MemberRegistrationRequest
│   │   ├── fund.py               # Fund, FundTransaction, FundAllocation
│   │   ├── donor.py              # Donor, SadaqahContribution
│   │   ├── loan.py               # Loan, LoanSchedule, LoanRepayment
│   │   ├── beneficiary.py        # Beneficiary, GrantDisbursement, BeneficiaryPayment
│   │   ├── campaign.py           # Campaign, CampaignContribution
│   │   ├── ledger.py             # GeneralLedger, LedgerTransaction, FinancialActivity
│   │   ├── document.py           # Document attachments & Cloudinary metadata
│   │   └── settings.py           # Settings, FoundationProfile
│   ├── rbac/                     # Role-Based Access Control
│   │   ├── dependencies.py       # require_permission, require_role route guards
│   │   └── service.py            # RBACService (permission resolution)
│   ├── repositories/             # Data access layer (SQLAlchemy query abstractions)
│   │   ├── member_repo.py        # Member data queries & lookups
│   │   ├── group_repo.py         # Group data queries
│   │   ├── fund_repo.py          # Fund queries & balance updates
│   │   ├── ledger_repo.py        # Double-entry ledger query handlers
│   │   ├── loan_repo.py          # Loan & repayment repository
│   │   └── user_repo.py          # User & role queries
│   ├── schemas/                  # Pydantic request and response schemas
│   │   ├── member_request.py     # Member request creation & review DTOs
│   │   └── financial_activity.py # Campaign and donation transaction schemas
│   ├── services/                 # Business logic layer (transactions, workflows)
│   │   ├── member_service.py     # Member registration and updates
│   │   ├── member_request_service.py # Registration review & approval workflow
│   │   ├── dues_service.py       # Monthly dues calculation & ledger posting
│   │   ├── loan_service.py       # Loan disbursement & installment tracking
│   │   ├── fund_service.py       # Dedicated fund management
│   │   ├── sadaqah_service.py    # Sadaqah donation intake
│   │   └── reports_service.py    # Financial statement generators
│   └── main.py                   # FastAPI application factory, exception handlers
├── alembic/                      # Database migrations
│   ├── versions/                 # Revision scripts
│   └── env.py                    # Alembic migration environment
├── tests/                        # Pytest automated test suite (73 tests)
│   ├── conftest.py               # Database session fixtures, mock users, test clients
│   ├── test_auth.py              # Login, token issuance, device sessions
│   ├── test_health.py            # Service and database health check tests
│   ├── test_config.py            # Settings validation tests
│   ├── test_database.py          # Database connection and engine tests
│   ├── test_rbac.py              # Permission checks & Super Admin bypass
│   ├── test_roles_and_permissions.py # Role CRUD and assignment tests
│   ├── test_members.py           # Member workflows and validations
│   ├── test_member_requests.py   # Public application and approval tests
│   ├── test_groups_funds_sadaqah.py # Groups, funds, and donation tests
│   ├── test_dues_and_financial_activities.py # Dues, ledgers, transactions tests
│   └── test_qard_hasana_and_reports.py # Loan schedules, repayments, financial reports
├── .env.example                  # Environment variable template
├── audit_schema.py               # Schema introspection verification utility
├── pyproject.toml                # Project metadata & pytest configuration
└── requirements.txt              # Production and development dependencies
```

---

## 4. API Architecture

The backend implements a clean **Layered Architecture**:

```text
HTTP Request (Client)
        │
        ▼
Router / Endpoints (FastAPI)  ──► Schema Validation (Pydantic)
        │
        ▼
Dependency Layer (Auth / RBAC / Database Session)
        │
        ▼
Service Layer (Business Logic & Atomic Transactions)
        │
        ▼
Repository Layer (SQLAlchemy 2.0 Queries)
        │
        ▼
PostgreSQL Database (psycopg3)
```

- **Separation of Concerns**: Routes handle HTTP parsing and status codes; services orchestrate business logic; repositories handle SQL queries.
- **Atomic Transactions**: Complex operations (such as approving a member request and creating corresponding ledger accounts) use database transactions with automated rollback on error.
- **Standardized Responses**: Responses use typed Pydantic models with automated JSON serialization.

---

## 5. PostgreSQL Database Configuration

The backend connects directly to PostgreSQL using SQLAlchemy 2.0 connection pooling with `psycopg3`.

### Connection URL Format
```text
postgresql+psycopg://<username>:<password>@<hostname>:<port>/<database>?sslmode=require
```

### Key Engine Settings (`app/core/database.py`)
- **Pool Size**: `pool_size=10` with `max_overflow=20` for concurrent request handling.
- **Connection Recycling**: `pool_recycle=1800` (30 minutes) to prevent stale connections on cloud providers like Neon or AWS RDS.
- **Pre-ping**: `pool_pre_ping=True` ensures dropped connections are automatically replaced before query execution.

### Verifying Database Connection
Run the connection check utility:
```bash
python -c "from app.core.database import check_database_connection; print(check_database_connection())"
```
Or run the complete schema audit:
```bash
python audit_schema.py
```

---

## 6. Environment Variables

Create a `.env` file in the project root based on `.env.example`:

```env
# =============================================================================
# Application Settings
# =============================================================================
ENVIRONMENT=development
DEBUG=True
APP_NAME="Foundation API"
API_V1_STR=/api/v1
LOG_LEVEL=INFO

# =============================================================================
# Security & JWT Configuration
# =============================================================================
# Secure random 32+ character string used to sign JWT access tokens
SECRET_KEY=change-this-in-production-to-a-secure-random-secret-key-at-least-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REMEMBER_ME_EXPIRE_MINUTES=43200
SESSION_COOKIE_NAME=foundation_session

# =============================================================================
# PostgreSQL Database Connection
# =============================================================================
# Full PostgreSQL connection URL with psycopg driver
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/foundation_db

# =============================================================================
# Cloudinary CDN Configuration (Media Storage)
# =============================================================================
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name
CLOUDINARY_FOLDER=foundation-erp
```

---

## 7. Authentication & Authorization (RBAC)

### 1. Authentication
- Endpoint: `POST /api/v1/auth/login` accepts `{ email, password, remember_me }`.
- Password verification uses Bcrypt.
- Returns a signed JWT token containing `sub` (User ID), `email`, `role`, and expiration timestamp.

### 2. Role-Based Access Control (RBAC)
FastAPI dependencies in `app/rbac/dependencies.py` enforce permissions:
- `require_permission("MEMBER_CREATE")`: Verifies user has explicit permission or belongs to `SUPER_ADMIN` role.
- `require_role("SUPER_ADMIN")`: Verifies role membership.

```python
@router.post("/members", response_model=MemberDto)
async def create_member(
    data: MemberCreatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("MEMBER_CREATE"))
):
    return member_service.create_member(db, data, current_user.id)
```

---

## 8. How to Install Dependencies

### Prerequisites
- **Python**: `3.12.x` or higher
- **Virtual Environment Tool**: `venv` or `uv`

### Installation Steps
```bash
git clone https://github.com/isernai12/foundation-backend.git
cd foundation-backend

# 1. Create virtual environment
python3 -m venv .venv

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 9. How to Run Locally

### Start FastAPI with Auto-Reload
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The service starts at `http://127.0.0.1:8000`:
- **API Root**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger Documentation**: [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/api/v1/redoc](http://127.0.0.1:8000/api/v1/redoc)

---

## 10. Health Check Endpoints

| Endpoint | Method | Purpose | Response Format |
| :--- | :--- | :--- | :--- |
| `/health` | `GET` | Instant liveness check (no database query) | `{"status": "ok"}` |
| `/health/db` | `GET` | Readiness probe (executes `SELECT 1` on PostgreSQL) | `{"status": "ok", "database": "connected", "detail": null}` |
| `/api/v1/health` | `GET` | Versioned API liveness probe | `{"status": "ok"}` |
| `/api/v1/health/db` | `GET` | Versioned API database readiness check | `{"status": "ok", "database": "connected", "detail": null}` |

---

## 11. Automated Tests (Pytest)

The backend includes a comprehensive 73-test suite covering all critical workflows.

```bash
# Run all tests
pytest

# Run tests with detailed output
pytest -v

# Run specific test modules
pytest tests/test_auth.py
pytest tests/test_health.py
pytest tests/test_members.py
pytest tests/test_dues_and_financial_activities.py
```

---

## 12. Database Migrations (Alembic)

```bash
# Apply pending migrations
alembic upgrade head

# Create a new migration revision
alembic revision --autogenerate -m "describe_changes"

# Rollback last migration
alembic downgrade -1
```

---

## 13. Production Deployment & Hosting

### Deploying to Render (Web Service)
1. Create a new **Web Service** on [Render](https://render.com) from `isernai12/foundation-backend`.
2. Configure settings:
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`
3. Configure environment variables in the Render Dashboard:
   - `DATABASE_URL`: `postgresql+psycopg://...`
   - `SECRET_KEY`: *Secure random key*
   - `ENVIRONMENT`: `production`
   - `DEBUG`: `false`

### Deploying to Linux VPS with Gunicorn & Systemd
```bash
git clone https://github.com/isernai12/foundation-backend.git
cd foundation-backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## 14. Common Troubleshooting

### 1. `ModuleNotFoundError: No module named 'app'`
- **Cause**: Running uvicorn or pytest without the repository root in `PYTHONPATH`.
- **Fix**: Run commands from inside the project root or export `PYTHONPATH=.`.

### 2. Database Connection Error / SSL Handshake Failure
- **Cause**: Connecting to cloud databases (like Neon or AWS RDS) without SSL mode.
- **Fix**: Ensure your `DATABASE_URL` ends with `?sslmode=require` and uses the `postgresql+psycopg://` scheme.

### 3. Starlette Deprecation Warning on TestClient
- **Context**: Warning regarding `httpx` with `starlette.testclient`.
- **Status**: Harmless warning in test execution. Tests execute and assert status codes reliably.

---

## 15. Security Notes

1. **Password Encryption**: All passwords are encrypted with one-way Bcrypt hashes using Passlib.
2. **SQL Injection Defense**: All database operations use SQLAlchemy ORM with parameterized queries.
3. **Secret Isolation**: Secrets, tokens, and database credentials must never be committed to Git; inject them via environment variables.

---

## 16. Important Development Notes

- **Package Imports**: All backend files use standard `from app...` package imports (e.g. `from app.models.member import Member`).
- **Timestamp Defaults**: SQLAlchemy models explicitly configure `default=func.now()` and `onupdate=func.now()` to ensure timestamp columns satisfy PostgreSQL `NOT NULL` constraints.
- **Transactional Rollback**: Always wrap multi-step financial operations in a transaction context to ensure atomic balance consistency.
