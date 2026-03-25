# Creator Campaign Copilot

Phase 1 foundation for a multi-brand campaign operations workspace.

## Stack

- Frontend: React, TypeScript, Vite, Tailwind CSS, TanStack Query, Zustand
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic
- Database: PostgreSQL
- Dev environment: Docker Compose

## Phase 1 scope

- Email/password auth scaffold with JWT access tokens
- Core backend modules for users, brands, memberships, projects, campaigns, and audit logs
- Brand-level RBAC roles: `owner`, `admin`, `editor`, `reviewer`, `viewer`
- Frontend shell with dashboard, brands, projects, and campaigns pages
- CRUD flows for brands, projects, and campaigns
- Membership listing and invite-ready structure
- Alembic migration for the initial schema

## Quick start

1. Copy the environment file:

   ```bash
   cp .env.example .env
   ```

2. Start the application:

   ```bash
   docker compose up --build
   ```

3. Open:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000/api`
- Health check: `http://localhost:8000/api/healthz`

The backend container runs `alembic upgrade head` before starting the FastAPI server.

## Phase 1 workflow

1. Create an account from the login page.
2. Create a brand workspace.
3. Create projects inside the brand.
4. Create campaigns inside a project.
5. Invite additional members from the brand page.

## Backend entities in this phase

- `users`
- `brands`
- `brand_memberships`
- `projects`
- `campaigns`
- `audit_logs`

## API areas

- `/api/auth`
- `/api/dashboard`
- `/api/brands`
- `/api/projects`
- `/api/campaigns`

## Notes

- Membership invitations are stored without outbound email sending in Phase 1.
- Owner membership updates and ownership transfer are intentionally deferred.
- The frontend stores the JWT token locally and restores the session on reload.
