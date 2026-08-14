# Foundation ERP — FastAPI Backend

Modern, high-performance, asynchronous REST API backend for the Foundation ERP and Financial Management System.

## Architecture

- **Language & Runtime:** Python 3.12+
- **Web Framework:** [FastAPI](https://fastapi.tiangolo.com/) (v0.141+)
- **Data Validation:** [Pydantic v2](https://docs.pydantic.dev/)
- **ORM & Database Layer:** [SQLAlchemy 2.0](https://www.sqlalchemy.org/) with `psycopg3` driver
- **Migrations:** [Alembic](https://alembic.sqlalchemy.org/)
- **Database Engine:** PostgreSQL (Neon Serverless Pooler)

## Directory Structure

```text
backend/
├── app/
│   ├── main.py                 # FastAPI application factory & lifespan
│   ├── core/
│   │   ├── config.py           # Pydantic Settings & environment parsing
│   │   ├── database.py         # SQLAlchemy engine, sessionmaker, and get_db dependency
│   │   ├── logging.py          # Structured safe logging with secret filters
│   │   └── errors.py           # Global exception handlers
│   ├── api/
│   │   ├── router.py           # Top-level API router
│   │   └── v1/
│   │       ├── router.py       # API v1 Router
│   │       └── endpoints/
│   │           └── health.py   # Health check endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   └── base.py             # DeclarativeBase and common mixins
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── common.py           # Reusable Pydantic response/request models
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── base.py             # Generic CRUD repository pattern
│   └── services/
│       ├── __init__.py
│       └── base.py             # Business service pattern
├── alembic/                    # Alembic migration environment
├── docs/
│   └── database-audit.md       # PostgreSQL schema audit & Prisma comparison
├── tests/
│   ├── test_config.py          # Configuration loading & masking tests
│   ├── test_database.py        # Database connectivity & session tests
│   └── test_health.py          # Health endpoints test suite
├── pyproject.toml
├── requirements.txt
├── .env.example
└── README.md
```

## Getting Started

### 1. Environment Setup

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configuration

Copy `.env.example` to `.env` and configure your PostgreSQL connection string:

```bash
cp .env.example .env
```

### 3. Run Development Server

```bash
PYTHONPATH=.. uvicorn app.main:app --reload --port 8000
```

### 4. Endpoints

- **Root Health Check:** `GET http://localhost:8000/health`
- **Database Health Check:** `GET http://localhost:8000/health/db`
- **API v1 Health:** `GET http://localhost:8000/api/v1/health`
- **Interactive OpenAPI Documentation:** `GET http://localhost:8000/api/v1/docs`

### 5. Running Tests

```bash
PYTHONPATH=.. pytest tests -v
```
