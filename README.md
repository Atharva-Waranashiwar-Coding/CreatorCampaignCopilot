# Creator Campaign Copilot

Phase 3 foundation for a multi-brand campaign operations workspace.

## Stack

- Frontend: React, TypeScript, Vite, Tailwind CSS, TanStack Query, Zustand
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic
- Database: PostgreSQL
- Dev environment: Docker Compose

## Phase 3 scope

- Email/password auth scaffold with JWT access tokens
- Core backend modules for users, brands, memberships, projects, campaigns, and audit logs
- Brand-level RBAC roles: `owner`, `admin`, `editor`, `reviewer`, `viewer`
- Frontend shell with dashboard, brands, projects, and campaigns pages
- CRUD flows for brands, projects, and campaigns
- Membership listing and invite-ready structure
- Content brief model and CRUD, one brief per campaign
- Content draft model and CRUD with statuses: `idea`, `draft`, `in_review`, `approved`, `scheduled`, `published`, `rejected`
- Draft review model and APIs with reviewer comments
- Approval and rejection workflow with role checks and editor resubmission loop
- Campaign workspace overview, review queue, activity timeline, draft detail workflow, and search/filtering
- Alembic migrations for the initial schema plus Phase 2 and Phase 3 review workflow additions

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

## Phase 3 workflow

1. Create an account from the login page.
2. Create a brand workspace.
3. Create projects inside the brand.
4. Create campaigns inside a project.
5. Add or update a campaign brief in the campaign workspace.
6. Create drafts for the campaign and manage their statuses.
7. Submit drafts into review from the draft detail page.
8. Reviewers add comments, approve drafts, or reject them with feedback.
9. Editors revise rejected drafts and resubmit them for review.
10. Track campaign activity from the campaign workspace timeline and use the review queue to process pending items.
11. Filter drafts by campaign, platform, status, or search term.
12. Invite additional members from the brand page.

## Backend entities in this phase

- `users`
- `brands`
- `brand_memberships`
- `projects`
- `campaigns`
- `content_briefs`
- `content_drafts`
- `draft_reviews`
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
- `/api/drafts/review-queue`
- `/api/drafts/{draft_id}/reviews`
- `/api/drafts/{draft_id}/submit`
- `/api/drafts/{draft_id}/approve`
- `/api/drafts/{draft_id}/reject`
- `/api/drafts/{draft_id}/resubmit`

## Notes

- Membership invitations are stored without outbound email sending in Phases 1 through 3.
- Owner membership updates and ownership transfer are intentionally deferred.
- The frontend stores the JWT token locally and restores the session on reload.
- Each campaign can have one brief and many drafts.
- Reviewer approvals only operate on drafts already in `in_review`.
