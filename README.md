# Creator Campaign Copilot

Phase 8 workspace for multi-brand campaign planning, board-based draft operations, platform previews, collaboration workflows, helper tools, MCP exposure, templates, analytics, and subscription-aware usage controls.

## Stack

- Frontend: React, TypeScript, Vite, Tailwind CSS, TanStack Query, Zustand
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic
- Database: PostgreSQL
- Dev environment: Docker Compose

## Phase 8 scope

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
- Campaign assets, draft versions, and calendar scheduling
- Brand plan catalog and subscription state
- Brand-level usage metering and access checks for members, active campaigns, scheduled work, and templates
- Brand billing/settings page with plan details, upgrade prompts, and recent plan audit events
- Content template model and CRUD workflow
- Dashboard analytics for campaign status, draft pipeline, review activity, and schedule pressure
- Internal helper tools for brand guidelines, templates, content validation, campaign assets, and review summaries
- Optional FastAPI-MCP exposure isolated behind helper-tool routes
- Tool usage logging and admin visibility for helper tool availability and recent executions
- Collaboration comments with threaded replies on campaigns and drafts
- Mentions parsing for comments and review notes using `@email`
- Assignment workflows for campaigns, drafts, and review tasks
- In-app notifications for mentions, review requests, decisions, assignments, and due-soon reminders
- Notifications center plus collaboration-aware campaign activity feed updates
- Campaign planning workspace with board, list, and calendar switching
- Stage-based board interactions that map onto the existing review workflow
- Platform preview surfaces for LinkedIn, Instagram captions, email, and blog/article layouts
- Lightweight draft-editor enhancements with quick-insert writing tools and content stats
- Alembic migrations for Phases 1 through 7

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
- MCP HTTP mount: `http://localhost:8000/mcp`

The backend container runs `alembic upgrade head` before starting the FastAPI server.

## MCP helper configuration

- `MCP_HELPERS_ENABLED=true` keeps the helper MCP server mounted.
- `MCP_MOUNT_PATH=/mcp` controls the shared MCP mount path.
- `MCP_ENABLE_HTTP_TRANSPORT=true` enables streamable HTTP transport.
- `MCP_ENABLE_SSE_TRANSPORT=false` leaves SSE off unless you explicitly need it.
- The helper REST endpoints remain available under `/api/tools/helpers/*` even if the MCP layer is disabled.

## Phase 8 workflow

1. Create an account from the login page.
2. Create a brand workspace.
3. Review the starter subscription and usage posture from the billing page.
4. Create projects inside the brand.
5. Create campaigns inside a project.
6. Add or update a campaign brief in the campaign workspace.
7. Save reusable templates for campaign briefs, draft copy, review notes, or launch copy.
8. Create drafts for the campaign and manage their statuses.
9. Submit drafts into review from the draft detail page.
10. Reviewers add comments, approve drafts, or reject them with feedback.
11. Editors revise rejected drafts and resubmit them for review.
12. Track campaign activity from the campaign workspace timeline and use the review queue to process pending items.
13. Use the dashboard analytics view to monitor campaign status, draft throughput, review actions, and schedule pressure.
14. Filter drafts by campaign, platform, status, or search term.
15. Invite additional members from the brand page.
16. Upgrade or rebalance the brand plan as usage approaches current limits.
17. Review the helper tool catalog and recent tool activity from the Helper Tools page.
18. Use the helper routes directly or through the MCP mount when an MCP client is configured.
19. Assign campaign, draft, or review-task ownership directly from the workspace pages.
20. Use `@email` mentions in draft discussion, campaign discussion, and review notes.
21. Follow collaboration events from the notifications center and campaign activity feed.
22. Switch the campaign planner between board, list, and calendar views depending on the planning task.
23. Drag supported draft stages across the board to move ideas into review, approve work, and advance scheduled content.
24. Use the draft detail preview panel to inspect LinkedIn, Instagram, email, and article layouts while editing copy.

## Backend entities in this phase

- `users`
- `brands`
- `brand_memberships`
- `plans`
- `brand_subscriptions`
- `projects`
- `campaigns`
- `content_briefs`
- `content_drafts`
- `content_templates`
- `draft_reviews`
- `draft_versions`
- `calendar_items`
- `audit_logs`
- `tool_usage_logs`
- `collaboration_comments`
- `mentions`
- `assignments`
- `notifications`

## API areas

- `/api/auth`
- `/api/dashboard`
- `/api/dashboard/analytics`
- `/api/brands`
- `/api/brands/{brand_id}/billing`
- `/api/brands/{brand_id}/subscription`
- `/api/projects`
- `/api/campaigns`
- `/api/campaigns/{campaign_id}/overview`
- `/api/campaigns/{campaign_id}/comments`
- `/api/campaigns/{campaign_id}/assignments`
- `/api/campaigns/{campaign_id}/brief`
- `/api/drafts`
- `/api/drafts/review-queue`
- `/api/drafts/{draft_id}/comments`
- `/api/drafts/{draft_id}/assignments`
- `/api/drafts/{draft_id}/reviews`
- `/api/drafts/{draft_id}/move-stage`
- `/api/drafts/{draft_id}/submit`
- `/api/drafts/{draft_id}/approve`
- `/api/drafts/{draft_id}/reject`
- `/api/drafts/{draft_id}/resubmit`
- `/api/assignments`
- `/api/notifications`
- `/api/templates`
- `/api/tools/helpers`
- `/api/tools/catalog`
- `/api/tools/usage`

## Notes

- Membership invitations are stored without outbound email sending.
- Owner membership updates and ownership transfer are intentionally deferred.
- The frontend stores the JWT token locally and restores the session on reload.
- Each campaign can have one brief and many drafts.
- Campaign planning now supports board, list, and calendar views inside the campaign workspace.
- Board stage moves intentionally route through the existing review and editorial rules rather than bypassing them.
- Draft previews render from the existing `ContentDraft` fields instead of a separate preview-only model.
- Reviewer approvals only operate on drafts already in `in_review`.
- New brands receive the seeded `starter` plan by default.
- Plan changes and template actions are recorded in the existing audit log stream.
- Usage checks are currently enforced for member count, active campaigns, upcoming scheduled items, and template count.
- The MCP layer is optional. Base product routes remain available even if MCP is disabled or `fastapi-mcp` is unavailable at runtime.
- Helper tool usage is recorded in `tool_usage_logs` with request, result summary, success state, and target metadata.
- Collaboration permissions stay aligned to the existing brand-level RBAC model.
- Assignment creation uses workspace-management roles, while assignees can complete their own open assignments.
- Due-soon notifications are generated from open assignments with due dates inside the notification sync window.
