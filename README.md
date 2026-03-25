# Creator Campaign Copilot

Phase 10 workspace for multi-brand campaign planning, configurable draft workflows, campaign milestones, dependency-aware board operations, campaign intelligence analytics, platform previews, collaboration workflows, helper tools, MCP exposure, templates, and subscription-aware usage controls.

## Stack

- Frontend: React, TypeScript, Vite, Tailwind CSS, TanStack Query, Zustand
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic
- Database: PostgreSQL
- Dev environment: Docker Compose

## Phase 10 scope

- Email/password auth scaffold with JWT access tokens
- Core backend modules for users, brands, memberships, projects, campaigns, and audit logs
- Brand-level RBAC roles: `owner`, `admin`, `editor`, `reviewer`, `viewer`
- Frontend shell with dashboard, brands, projects, and campaigns pages
- CRUD flows for brands, projects, and campaigns
- Membership listing and invite-ready structure
- Content brief model and CRUD, one brief per campaign
- Brand-level configurable draft workflow schemas with custom stage labels, colors, transitions, and initial stages
- Content draft model and CRUD mapped onto brand-specific workflow stages instead of a fixed global status list
- Draft review model and APIs with reviewer comments
- Approval and rejection workflow with role checks and editor resubmission loop
- Campaign workspace overview, review queue, activity timeline, draft detail workflow, and search/filtering
- Campaign assets, draft versions, and calendar scheduling
- Default campaign milestone tracking for brief approval, first drafts ready, review completion, launch readiness, and campaign completion
- Campaign dependency modeling between milestones and draft stages, including blocked-state handling in workflow moves
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
- Stage-based board interactions that map onto each brand's configured workflow
- Platform preview surfaces for LinkedIn, Instagram captions, email, and blog/article layouts
- Lightweight draft-editor enhancements with quick-insert writing tools and content stats
- Campaign health scoring with transparent per-factor penalties
- Team workload analytics for draft ownership, reviewer queues, and bottlenecks by status
- Approval turnaround analytics covering review timing, rejection rate, and repeat revision cycles
- Content mix analytics by platform, content type, campaign status, and week/month volume
- Alembic migrations for Phases 1 through 10

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

## Phase 10 workflow

1. Create an account from the login page.
2. Create a brand workspace.
3. Review the starter subscription and usage posture from the billing page.
4. Create projects inside the brand.
5. Create campaigns inside a project.
6. Add or update a campaign brief in the campaign workspace.
7. Save reusable templates for campaign briefs, draft copy, review notes, or launch copy.
8. Configure brand-specific draft stages from the brand settings page when the default workflow does not match the team's process.
9. Create drafts for the campaign and place them into one of the brand's allowed initial stages.
10. Track milestone targets and completion from the campaign workspace.
11. Add campaign dependencies so milestone or draft-stage work waits on prerequisite steps.
12. Submit drafts into review from the draft detail page.
13. Reviewers add comments, approve drafts, or reject them with feedback.
14. Editors revise rejected drafts and resubmit them for review.
15. Track campaign activity from the campaign workspace timeline and use the review queue to process pending items.
16. Use the dashboard analytics view to monitor campaign status, draft throughput, review actions, blocked work, and schedule pressure.
17. Filter drafts by campaign, platform, status, or search term.
18. Invite additional members from the brand page.
19. Upgrade or rebalance the brand plan as usage approaches current limits.
20. Review the helper tool catalog and recent tool activity from the Helper Tools page.
21. Use the helper routes directly or through the MCP mount when an MCP client is configured.
22. Assign campaign, draft, or review-task ownership directly from the workspace pages.
23. Use `@email` mentions in draft discussion, campaign discussion, and review notes.
24. Follow collaboration events from the notifications center and campaign activity feed.
25. Switch the campaign planner between board, list, and calendar views depending on the planning task.
26. Move drafts across the planner board using the brand workflow while blocked states remain visible.
27. Use the draft detail preview panel to inspect LinkedIn, Instagram, email, and article layouts while editing copy.
28. Use the dashboard to identify which campaigns are healthy, slipping, or critical and inspect the exact penalty factors behind each score.
29. Review team workload, reviewer queues, revision churn, and content-mix trends before reallocating work.

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
- `campaign_milestones`
- `campaign_dependencies`
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
- `/api/dashboard/campaign-health`
- `/api/dashboard/campaign-health/{campaign_id}`
- `/api/brands`
- `/api/brands/{brand_id}/billing`
- `/api/brands/{brand_id}/subscription`
- `/api/projects`
- `/api/campaigns`
- `/api/campaigns/{campaign_id}/overview`
- `/api/campaigns/{campaign_id}/comments`
- `/api/campaigns/{campaign_id}/assignments`
- `/api/campaigns/{campaign_id}/brief`
- `/api/campaigns/{campaign_id}/milestones`
- `/api/campaigns/{campaign_id}/milestones/{milestone_id}`
- `/api/campaigns/{campaign_id}/dependencies`
- `/api/campaigns/{campaign_id}/dependencies/{dependency_id}`
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
- Each brand owns its draft workflow configuration, including custom stages, stage colors, transition rules, and initial entry stages.
- Board stage moves intentionally route through the configured workflow and review rules rather than bypassing them.
- Campaign milestones are seeded per campaign and can be targeted, annotated, and marked complete from the workspace.
- Dependencies can block milestone completion or draft stage transitions until the prerequisite step is satisfied.
- Draft previews render from the existing `ContentDraft` fields instead of a separate preview-only model.
- Campaign health starts at `100` and subtracts capped penalties for overdue drafts, pending approvals, missing assets, unassigned work, and deadline pressure inside the next 7 days.
- Approval turnaround is measured from `submitted` or `resubmitted` to the next approval or rejection event.
- Content mix trends are based on draft creation volume and can be grouped by week or month from the dashboard.
- Reviewer approvals only operate on drafts currently mapped to the workflow's review stage.
- New brands receive the seeded `starter` plan by default.
- Plan changes and template actions are recorded in the existing audit log stream.
- Usage checks are currently enforced for member count, active campaigns, upcoming scheduled items, and template count.
- The MCP layer is optional. Base product routes remain available even if MCP is disabled or `fastapi-mcp` is unavailable at runtime.
- Helper tool usage is recorded in `tool_usage_logs` with request, result summary, success state, and target metadata.
- Collaboration permissions stay aligned to the existing brand-level RBAC model.
- Assignment creation uses workspace-management roles, while assignees can complete their own open assignments.
- Due-soon notifications are generated from open assignments with due dates inside the notification sync window.
