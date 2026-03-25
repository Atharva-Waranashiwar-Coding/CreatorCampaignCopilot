# Creator Campaign Copilot

Phase 2 foundation for a multi-brand campaign operations workspace.

## Stack

- Frontend: React, TypeScript, Vite, Tailwind CSS, TanStack Query, Zustand
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic
- Database: PostgreSQL
- Dev environment: Docker Compose

## Phase 2 scope

- Email/password auth scaffold with JWT access tokens
- Core backend modules for users, brands, memberships, projects, campaigns, and audit logs
- Brand-level RBAC roles: `owner`, `admin`, `editor`, `reviewer`, `viewer`
- Frontend shell with dashboard, brands, projects, and campaigns pages
- CRUD flows for brands, projects, and campaigns
- Membership listing and invite-ready structure
- Content brief model and CRUD, one brief per campaign
- Content draft model and CRUD with statuses: `idea`, `draft`, `in_review`, `approved`, `scheduled`, `published`, `rejected`
- Campaign workspace overview, draft list, draft detail/edit page, and basic search/filtering
- Alembic migrations for the initial schema and Phase 2 planning/drafts schema

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

## Phase 2 workflow

1. Create an account from the login page.
2. Create a brand workspace.
3. Create projects inside the brand.
4. Create campaigns inside a project.
5. Add or update a campaign brief in the campaign workspace.
6. Create drafts for the campaign and manage their statuses.
7. Filter drafts by campaign, platform, status, or search term.
8. Invite additional members from the brand page.

## Backend entities in this phase

- `users`
- `brands`
- `brand_memberships`
- `projects`
- `campaigns`
- `content_briefs`
- `content_drafts`
- `audit_logs`

## API areas

- `/api/auth`
- `/api/dashboard`
- `/api/brands`
- `/api/projects`
- `/api/campaigns`
- `/api/campaigns/{campaign_id}/overview`
- `/api/campaigns/{campaign_id}/brief`
- `/api/drafts`

## Notes

- Membership invitations are stored without outbound email sending in Phase 1 and Phase 2.
- Owner membership updates and ownership transfer are intentionally deferred.
- The frontend stores the JWT token locally and restores the session on reload.
- Each campaign can have one brief and many drafts.
