# Next.js Backend Migration Audit & Frontend Integration Roadmap

This document outlines the complete audit of backend logic, Server Actions, database queries, and authorization layers currently in `frontend/`, their migration status into the new FastAPI backend (`backend/`), and the recommended safe integration plan.

---

## 1. Migration Inventory & Status

| Domain / Feature | Next.js Source | FastAPI Backend Implementation | Migration Status |
| :--- | :--- | :--- | :--- |
| **Authentication & Sessions** | `frontend/src/lib/auth.ts`, `auth-options.ts` | `backend/app/auth/` (`/api/v1/auth/login`, `/me`, `/logout`) | **Already Migrated** |
| **Role-Based Access Control (RBAC)** | `frontend/src/lib/rbac.ts`, `rbac-client.ts` | `backend/app/rbac/` (Super Admin bypass, wildcard, synonym resolution) | **Already Migrated** |
| **Members (CRUD & Demographics)** | `frontend/src/features/members/actions.ts` | `backend/app/api/v1/endpoints/members.py` | **Already Migrated** |
| **Member Public Registration & Approval** | `frontend/src/features/members/request-actions.ts` | `backend/app/api/v1/endpoints/member_requests.py` | **Already Migrated** |
| **Groups & Foundation Central HQ** | `frontend/src/features/groups/actions.ts` | `backend/app/api/v1/endpoints/groups.py` | **Already Migrated** |
| **Funds & Accounts** | `frontend/src/features/campaigns/actions.ts`, `ledger.ts` | `backend/app/api/v1/endpoints/funds.py` | **Already Migrated** |
| **Donations & Sadaqah** | `frontend/src/features/donors/actions.ts` | `backend/app/api/v1/endpoints/sadaqah.py` | **Already Migrated** |
| **Monthly Membership Dues** | `frontend/src/features/contributions/actions.ts` | `backend/app/api/v1/endpoints/dues.py` | **Already Migrated** |
| **Multi-Month Advance Collection** | `frontend/src/features/contributions/actions.ts` | `backend/app/api/v1/endpoints/dues.py` | **Already Migrated** |
| **Member Dues Ledger & Summary** | `frontend/src/features/members/due-actions.ts` | `backend/app/api/v1/endpoints/dues.py` | **Already Migrated** |
| **Financial Activities & Campaigns** | `frontend/src/features/campaigns/actions.ts` | `backend/app/api/v1/endpoints/financial_activities.py` | **Already Migrated** |
| **Beneficiaries (Assistance / Recipients)** | `frontend/src/features/beneficiaries/actions.ts` | `backend/app/api/v1/endpoints/beneficiaries.py` | **Already Migrated** |
| **Qard-e-Hasana (Disbursement & Repayment)** | `frontend/src/features/loans/actions.ts` | `backend/app/api/v1/endpoints/qard_hasana.py` | **Already Migrated** |
| **Double-Entry Ledger Engine** | `frontend/src/services/ledger.ts`, `finance.ts` | `backend/app/repositories/ledger_repo.py` | **Already Migrated** |
| **Financial Reports & Summaries** | `frontend/src/features/reports/actions.ts` | `backend/app/api/v1/endpoints/reports.py` | **Already Migrated** |
| **Settings & Dynamic Monthly Fee** | `frontend/src/features/settings/actions.ts` | `backend/app/repositories/settings_repo.py` | **Already Migrated** |
| **Cloudinary File Upload API Handler** | `frontend/src/app/api/upload/route.ts` | Frontend utility (signs uploads with Cloudinary CDN) | **Frontend-only (Keep)** |
| **UI Components, Views & Modals** | `frontend/src/components/`, `frontend/src/app/` | Pure React / Next.js presentation | **Frontend-only (Keep)** |

---

## 2. Categorization of Next.js Backend Code

### Category 1: Already Migrated to FastAPI
- [x] NextAuth username/email bcrypt password validation
- [x] UserSession cookie/JWT server-side validation
- [x] Sequential Member ID (`M-XXXX`) & Application Number (`MR-YYYY-XXXXX`) generators
- [x] Application transactional approval with document cloning and audit trail
- [x] Group registration enablement (`memberSignupEnabled`) and Foundation Group invariant
- [x] External Donor registration and Member voluntary Sadaqah isolation
- [x] Dynamic monthly fee resolution from `Settings` table
- [x] Multi-month cross-year advance dues processing with contiguous `paidUntil` calculation
- [x] Financial activity budget validation and atomic beneficiary disbursements
- [x] Qard-e-Hasana interest-free loan disbursement, installment repayment, and overpayment prevention
- [x] Double-entry balanced ledger posting (debit = credit) for all financial domains

### Category 2: Needs Migration (None Remaining)
All core business domains (Auth, Members, Member Requests, Groups, Funds, Sadaqah, Monthly Dues, Financial Activities, Qard-e-Hasana, Beneficiaries, Reports) are now complete in FastAPI.

### Category 3: Frontend-only and Should Remain
- UI components, page layouts, navigation sidebars, forms, and dialogs.
- `Cloudinary` direct client widget upload helpers (stores secure URLs in PostgreSQL via FastAPI).
- Client-side form schemas and formatting helpers (`i18n`, date formatters, Bangla digit conversion).

### Category 4: Safe to Remove Later (During Final Integration Phase)
- `frontend/prisma/` directory and `@prisma/client` dependency once Server Actions switch to HTTP fetch against FastAPI.
- Next.js Server Action files (`frontend/src/features/*/actions.ts`) replacing direct DB calls with API client calls.

### Category 5: Requires Special Handling
- **Cloudinary Assets**: File upload occurs directly from browser to Cloudinary CDN, then metadata (`cloudinaryPublicId`, `secureUrl`) is saved via FastAPI. The backend stores metadata only; no raw binaries in PostgreSQL.
- **Database Rollbacks & Concurrency**: Handled via PostgreSQL transaction isolation in FastAPI repositories.

---

## 3. Recommended Frontend Integration Order

1. **Step 1: Create Typed API Client in Frontend**
   - Create `frontend/src/lib/api-client.ts` pointing to `http://localhost:8000/api/v1` or `process.env.BACKEND_API_URL`.
   - Forward session cookies / Bearer tokens with requests.

2. **Step 2: Connect Read-Only APIs**
   - Switch `getMembers()`, `getGroups()`, `getFunds()`, `getCampaigns()`, `getReports()` from Prisma to FastAPI `GET` endpoints.

3. **Step 3: Connect Mutation APIs**
   - Switch form submissions (Member creation, Sadaqah receipt, Dues payment, Qard-e-Hasana repayment) to FastAPI `POST`/`PATCH` endpoints.

4. **Step 4: Remove Direct Prisma Dependencies from Frontend**
   - Verify all pages load with 0 direct DB queries.
   - Decommission Prisma from `frontend/package.json`.
