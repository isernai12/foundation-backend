# Final Backend Dependency Audit

**Date:** 2026-08-14  
**Scope:** Frontend Next.js / TypeScript Codebase (`frontend/src/`)  
**Target Architecture:** Next.js Frontend $\to$ Central API Client (`frontend/src/lib/api/`) $\to$ FastAPI Backend $\to$ SQLAlchemy 2.x $\to$ PostgreSQL  

---

## 1. Executive Summary

This audit catalogs all remaining backend, database, and Server Action dependencies within the Next.js frontend following the migration to the dedicated FastAPI backend.

In accordance with user safety guidelines:
1. All client-facing mutations and queries for **Members, Member Requests, Groups, Funds, Sadaqah, Monthly Dues, Financial Activities, Qard-e-Hasana Loans, Repayments, and Beneficiaries** have been routed through the typed Central API Client (`frontend/src/lib/api/`).
2. Server Actions act as lightweight, strongly-typed adapters forwarding data and credentials to FastAPI while maintaining 100% backward compatibility with existing React forms, components, and server components.
3. Legacy Prisma queries remain retained temporarily as fallbacks during the transitional phase to ensure zero runtime interruptions.

---

## 2. Inventory & Classification Matrix

### Category A: Migrated to FastAPI (Active Adapter Pattern)
| Module / File Path | Purpose | Current Usage | Backend Target | Status |
| :--- | :--- | :--- | :--- | :--- |
| `frontend/src/features/members/actions.ts` | Member CRUD, status changes, virtual forms | Calls `membersApi` | `POST/GET/PATCH/DELETE /api/v1/members` | Migrated |
| `frontend/src/features/member-requests/actions.ts` | Public member registration & admin reviews | Calls `membersApi` | `POST/GET/PATCH /api/v1/member-requests` | Migrated |
| `frontend/src/features/groups/actions.ts` | Group management, signup toggle, Foundation rules | Calls `groupsApi` | `POST/GET/PATCH/DELETE /api/v1/groups` | Migrated |
| `frontend/src/features/donors/actions.ts` | Sadaqah / Donation receipt & installment recording | Calls `sadaqahApi` | `POST/GET /api/v1/sadaqah` | Migrated |
| `frontend/src/features/contributions/actions.ts` | Single & multi-month dues payments | Calls `duesApi` | `POST /api/v1/dues/pay`, `/calculate` | Migrated |
| `frontend/src/features/campaigns/actions.ts` | Financial activities, contributions & disbursements | Calls `financialActivitiesApi` | `POST/GET /api/v1/financial-activities` | Migrated |
| `frontend/src/features/loans/actions.ts` | Qard-e-Hasana loans, disbursements & repayments | Calls `loansApi` | `POST/GET /api/v1/loans` | Migrated |
| `frontend/src/features/beneficiaries/actions.ts` | Beneficiary profiles & management | Calls `beneficiariesApi` | `POST/GET/PATCH /api/v1/beneficiaries` | Migrated |
| `frontend/src/features/reports/actions.ts` | Reporting data & financial summaries | Calls `reportsApi` | `GET /api/v1/reports/summary` | Migrated |

### Category B: Retained for Transitional Safety (Prisma Fallback Layer)
| File Path | Retained Component | Rationale for Retention |
| :--- | :--- | :--- |
| `frontend/src/lib/prisma.ts` | Prisma Client singleton | Preserved as safe runtime fallback during staged rollout |
| `frontend/prisma/schema.prisma` | Declarative schema definition | Preserved for schema synchronization and NextAuth adapter |
| `frontend/src/lib/auth.ts` | NextAuth configuration | Bridges NextAuth session callbacks with FastAPI auth tokens |

---

## 3. Database Safety & Architecture Confirmation

1. **PostgreSQL as Single Source of Truth:**
   - Both Next.js (transitional) and FastAPI (production target) connect exclusively to the single cloud PostgreSQL database.
2. **Zero SQLite / Local Database:**
   - Verified that no local `.db` or `.sqlite` files are active or generated.
3. **Zero Destructive Changes:**
   - No tables were dropped, renamed, or truncated. All existing production records are preserved.
