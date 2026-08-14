# Turso & SQLite Complete Removal Audit

**Date:** 2026-08-14  
**Worktree:** `/workspaces/foundation-backend-migration`  
**Database Target:** Single Cloud PostgreSQL (`ep-dark-bar-azxfwau3-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb`)  

---

## 1. Executive Summary

This audit identifies all legacy Turso, libSQL, and SQLite references across the project in preparation for complete deprecation and transition to PostgreSQL exclusively.

---

## 2. Inventory of Turso / libSQL / SQLite References

### 2.1 Prisma Schema & Database Configuration
| File Path | Reference Found | Action Required |
| :--- | :--- | :--- |
| `frontend/prisma/schema.prisma` | `datasource db { provider = "sqlite" }` & `driverAdapters` | Switch `provider` to `"postgresql"`, remove `previewFeatures = ["driverAdapters"]` |
| `frontend/prisma/schema_old.prisma` | Legacy backup schema with `sqlite` provider | Remove obsolete file |
| `frontend/src/lib/prisma.ts` | `PrismaLibSQL` adapter from `@prisma/adapter-libsql` | Switch to standard `new PrismaClient()` with PostgreSQL connection string |

### 2.2 Application Scripts (`frontend/scripts/`)
| File Path | Purpose / Description | Action Required |
| :--- | :--- | :--- |
| `frontend/scripts/cleanup-turso.ts` | Turso database cleanup utility | Remove obsolete script |
| `frontend/scripts/deploy-schema.js` | Direct libSQL schema deployment script | Remove obsolete script |
| `frontend/scripts/migrate.ts` | Turso SQL migration runner invoked in `npm run build` | Update `build` script in `frontend/package.json` to remove Turso migration invocation |
| `frontend/scripts/migrate-prisma-sqlite.js` | Utility that converted postgresql schema to sqlite | Remove obsolete script |
| `frontend/scripts/seed-superadmin.ts` | Turso-specific superadmin seed script | Remove obsolete script (FastAPI handles seed/auth) |
| `frontend/scripts/update-readme.js` | Script that injected Turso into README | Remove obsolete script |

### 2.3 Package Dependencies (`frontend/package.json`)
| Package Name | Current Version | Action Required |
| :--- | :--- | :--- |
| `@libsql/client` | `^0.17.4` | Remove from `dependencies` |
| `@prisma/adapter-libsql` | `^6.19.3` | Remove from `dependencies` |

### 2.4 Environment Files & Configurations
| File Path | Reference Found | Action Required |
| :--- | :--- | :--- |
| `frontend/.env` | `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`, `dev.db` | Remove Turso variables, set `DATABASE_URL` to PostgreSQL |
| `frontend/.env.example` | `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN` | Remove Turso variables, keep only PostgreSQL `DATABASE_URL` |
| `Dockerfile` | `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN` args/envs | Remove Turso arguments and envs |
| `README.md` | Turso setup and instructions | Update to PostgreSQL setup |

---

## 3. Post-Removal Architecture
```
Next.js (Frontend)
       ↓
Central API Client
       ↓
FastAPI (Backend)
       ↓
SQLAlchemy 2.x
       ↓
Neon PostgreSQL (Single source of truth)
```
There are zero SQLite, Turso, or local database fallbacks.
