# Authentication & Authorization (RBAC) Audit Report

**Date:** 2026-08-14  
**Source Codebase:** `frontend/src/` (Next.js 16 + NextAuth v4 + Prisma)  
**Target Backend:** FastAPI + SQLAlchemy 2.0 + Pydantic + PostgreSQL  

---

## 1. Executive Summary

This document audits the existing authentication, session management, user modeling, and Role-Based Access Control (RBAC) implementation in the Next.js application to design an identical, 100% compatible, and secure architecture in the new FastAPI backend.

---

## 2. Existing Authentication Model & Schema

The existing authentication schema consists of 6 interconnected tables defined in Prisma:

### 2.1 User Entity (`User`)
- **Primary Key:** `id` (UUID string)
- **Identifiers:** `username` (unique, indexed), `email` (unique, nullable), `mobile` (unique, nullable)
- **Credentials:** `password` (bcrypt hashed string)
- **Role Association:** `roleId` (foreign key -> `Role.id`, `ON DELETE RESTRICT`)
- **Status:** `status` (`ACTIVE`, `INACTIVE`, `SUSPENDED` — default: `ACTIVE`)
- **Metadata:** `name`, `photo` (Cloudinary URL), `preferences` (JSON string: date format, timezone), `lastLogin` (datetime), `createdAt`, `updatedAt`

### 2.2 Role Entity (`Role`)
- **Fields:** `id` (UUID), `name` (unique: e.g., `Super Admin`, `Admin`, `Manager`, `Cashier`, `Employee`), `description`, `createdAt`, `updatedAt`
- **Relations:** One-to-many with `User`, many-to-many with `Permission` via `RolePermission`

### 2.3 Permission Entity (`Permission`)
- **Fields:** `id` (UUID), `module` (e.g., `Members`, `Donors`, `Loans`, `Grants`, `Groups`, `Settings`, `Users`, `Roles & Permissions`, `Dashboard`), `action` (e.g., `View`, `Add`, `Create`, `Edit`, `Delete`, `Approve`, `Manage`), `description`
- **Constraint:** `UNIQUE(module, action)`

### 2.4 Role Permission (`RolePermission`)
- **Composite Primary Key:** `(roleId, permissionId)`
- **Foreign Keys:** Cascade delete on both `Role` and `Permission`

### 2.5 User Permission (`UserPermission`)
- **Composite Primary Key:** `(userId, permissionId)`
- **Purpose:** Grants custom per-user permission overrides independent of their base role

### 2.6 User Session (`UserSession`)
- **Fields:** `id` (UUID), `userId` (FK -> `User.id`, cascade delete), `jti` (unique session token ID), `device`, `browser`, `os`, `ipAddress`, `lastActive`, `expiresAt`, `createdAt`
- **Purpose:** Server-side device tracking, multi-device management, and instant token revocation

### 2.7 Audit Log (`AuditLog`)
- **Fields:** `id`, `userId` (FK -> `User.id`), `action` (e.g., `LOGIN`, `UNAUTHORIZED_ACCESS`), `module` (`AUTHENTICATION`, etc.), `ipAddress`, `device`, `browser`, `remarks`, `createdAt`

---

## 3. Existing Authentication Workflow

Located in [`frontend/src/lib/auth.ts`](file:///workspaces/foundation-backend-migration/frontend/src/lib/auth.ts):

1. **Credentials Authorization:**
   - Accepts `username` (can be either the username or email address) and `password`.
   - Query: `prisma.user.findFirst({ where: { OR: [{ username }, { email }] } })`.
   - Checks `user.status === "ACTIVE"`.
   - Compares password hash using `bcrypt.compare(password, user.password)`.
2. **Session Lifespan & Remember Me:**
   - If `rememberMe === true`: Session valid for **30 days** (`30 * 24 * 60 * 60 * 1000` ms).
   - If `rememberMe === false`: Session valid for **24 hours** (`24 * 60 * 60 * 1000` ms).
3. **Session Token & Device Tracking:**
   - Generates a UUID `jti` (JWT ID).
   - Extracts User-Agent (browser, OS, device) and Client IP (`x-forwarded-for` / `x-real-ip`).
   - Inserts session into `UserSession` table with the `jti` identifier.
   - Inserts an `AuditLog` entry (`LOGIN`, `AUTHENTICATION`).
   - Updates `user.lastLogin = new Date()`.
4. **Cookie Configuration:**
   - Cookie Name: `next-auth.session-token` (or `__Secure-next-auth.session-token` on HTTPS).
   - `HttpOnly: true`, `SameSite: "lax"`, `Path: "/"`.

---

## 4. Existing RBAC & Super Admin Rules

Located in [`frontend/src/lib/rbac.ts`](file:///workspaces/foundation-backend-migration/frontend/src/lib/rbac.ts) and [`frontend/src/lib/rbac-client.ts`](file:///workspaces/foundation-backend-migration/frontend/src/lib/rbac-client.ts):

1. **Super Admin Bypass (Hardcoded Rule #1):**
   - Helper `isSuperAdminRole(roleName)` checks if the normalized role name matches:
     `superadmin`, `adminsuper`, `Super Admin`, or `SUPER_ADMIN`.
   - **Crucial Invariant:** Any user with a Super Admin role automatically bypasses **all** permission checks and is granted wildcard `["*"]` permissions.
2. **Permission Aggregation:**
   - For non-Super Admin users, active permissions are computed as:
     `Role Permissions` $\cup$ `Custom User Permissions`.
   - Formatted as strings: `"{module}:{action}"` (e.g., `"Members:View"`, `"Loans:Approve"`).
3. **Synonym & Wildcard Matching:**
   - Wildcard `"*"` matches any module or action.
   - Action `"Manage"` matches any action in that module.
   - Synonyms: `create` $\leftrightarrow$ `add`, `view` matches any `view*` action prefix.
4. **Unauthorized Handling:**
   - Server Actions record `AuditLog` (`action: "UNAUTHORIZED_ACCESS"`) and redirect to `/unauthorized`.

---

## 5. Backend Authentication Architecture for FastAPI

To achieve clean separation of concerns and full parity:

```text
backend/app/
├── auth/
│   ├── router.py         # HTTP endpoints: /login, /logout, /me, /refresh
│   ├── schemas.py        # LoginRequest, TokenResponse, UserProfileResponse, SessionInfo
│   ├── service.py        # Authentication business logic & session persistence
│   ├── dependencies.py   # FastAPI Depends: get_current_user, get_current_active_user
│   └── security.py       # Password hashing (bcrypt), JWT generation/decoding, token extraction
│
├── rbac/
│   ├── dependencies.py   # require_role, require_permission, require_super_admin
│   ├── service.py        # RBAC permission resolver & synonym evaluation
│   └── constants.py      # Standard system roles, modules, and actions
│
├── models/
│   └── auth.py           # SQLAlchemy 2.0 ORM models for User, Role, Permission, UserSession, AuditLog
│
└── repositories/
    ├── user_repo.py      # UserRepository
    ├── role_repo.py      # RoleRepository
    └── session_repo.py   # SessionRepository
```

---

## 6. Password & Token Compatibility

- **Algorithm:** Standard `bcrypt` (Blowfish crypt).
- **Work Factor:** Salt rounds 10-12 (matching Next.js `bcrypt.hash(password, 10)`).
- **JWT Payload Standard:**
  ```json
  {
    "sub": "user-uuid",
    "name": "User Full Name",
    "username": "admin",
    "role": "Super Admin",
    "jti": "session-uuid",
    "exp": 1755162237,
    "iat": 1723626237
  }
  ```
- **Dual Transport:**
  1. Secure `HttpOnly` cookie (for browser navigation / SSR).
  2. `Authorization: Bearer <token>` header (for API client calls).
