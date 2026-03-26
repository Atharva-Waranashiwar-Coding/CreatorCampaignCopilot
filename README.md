# Creator Campaign Copilot

Creator Campaign Copilot is a multi-brand campaign operations workspace for teams planning, producing, reviewing, scheduling, and improving creator or brand content across channels. Instead of splitting planning, drafts, approvals, collaboration, analytics, and helper tooling across disconnected products, it keeps the full campaign lifecycle inside one system.

This repository currently reflects the Phase 11 implementation of the product: brand workspaces, projects, campaigns, briefs, flexible draft workflows, milestones, dependencies, reviews, collaboration, analytics, templates, billing controls, and optional MCP-assisted helper tools.

## Product Overview

### What the product does

Creator Campaign Copilot is designed to help a marketing or content team answer four operational questions in one place:

1. What are we launching, for which brand, and why?
2. What content is in progress, blocked, under review, approved, or scheduled?
3. Who owns the work, what feedback exists, and what is at risk?
4. Which helper tools or analytics should we use to improve execution quality?

### Who it is for

- Brand and marketing leads managing multiple campaigns across one or more brands
- Editors and content operators creating drafts, assets, and reusable templates
- Reviewers approving or rejecting content with traceable feedback
- Campaign managers coordinating launch readiness, milestone tracking, and assignments
- Teams that want optional MCP-compatible helper tools without making AI tooling a hard dependency of the core workflow

### Core product areas

- Multi-brand workspace management with memberships and brand-level RBAC
- Project and campaign planning with briefs, milestones, and dependencies
- Draft production with configurable workflow stages, review loops, and version history
- Campaign planning views across board, list, and calendar formats
- Collaboration through threaded comments, mentions, assignments, and notifications
- Operational analytics for campaign health, workload, approval performance, and content mix
- Internal helper tools exposed through REST and optionally through MCP
- Subscription and usage controls at the brand level

## End-to-End Product Flow

The product is intentionally structured around the way a campaign team actually works.

1. A user creates an account and enters the workspace.
2. The user creates or joins a brand workspace with role-based access.
3. Inside a brand, the team creates projects that group related campaigns.
4. Each campaign is created with dates, audience, objectives, and campaign metadata.
5. The team writes the campaign brief, adds reference material, and defines launch expectations.
6. The brand configures its preferred draft workflow when the default stage model does not match the team process.
7. Campaign milestones are tracked and dependencies are added so blocked work is explicit.
8. Drafts are created for specific platforms and content types.
9. Editors work in the draft detail experience, use quick writing tools, and preview copy in channel-specific layouts.
10. Reviewers comment, approve, or reject drafts, and editors resubmit after revisions.
11. Assignments, mentions, and notifications keep ownership and follow-up visible.
12. Approved work is scheduled, surfaced on the calendar, and tracked against campaign timelines.
13. The dashboard highlights campaign health, workload pressure, bottlenecks, review turnaround, and content mix trends.
14. Helper tools can validate tone, adapt copy across channels, recommend templates or assets, and convert review feedback into structured revision checklists.

## Main User Journeys

### 1. Workspace setup

- Register or sign in
- Create a brand
- Add members with roles: `owner`, `admin`, `editor`, `reviewer`, `viewer`
- Review plan and usage posture from billing

### 2. Campaign planning

- Create a project inside a brand
- Create one or more campaigns inside the project
- Add a campaign brief
- Define milestones and milestone target dates
- Add dependencies between milestones or workflow stages

### 3. Content production

- Create drafts for LinkedIn, Instagram, email, article/blog, and other channel/content combinations
- Move drafts through the brand workflow
- Save versions and maintain revision context
- Reuse templates and campaign assets

### 4. Review and collaboration

- Submit drafts for review
- Add review comments and threaded discussion
- Mention teammates using `@email`
- Approve, reject, revise, and resubmit
- Assign campaigns, drafts, or review tasks to specific users

### 5. Launch and optimization

- Schedule approved work
- Use board, list, and calendar views to manage execution
- Watch due-soon reminders and notifications
- Review campaign health scoring and operational analytics
- Use advanced helper tools when extra drafting support or validation is needed

## Implemented Product Capabilities

### Workspace and access

- Email and password authentication with JWT access tokens
- Brand-scoped memberships and permissions
- Project and campaign CRUD
- Audit logging for key events

### Planning and execution

- Campaign briefs with structured messaging inputs
- Brand-level configurable draft workflows with custom labels, colors, transitions, and initial stages
- Campaign milestones for key readiness checkpoints
- Dependency modeling between milestones and draft stages
- Blocked-state visibility in workflow and planner interactions

### Draft operations

- Draft CRUD mapped to the brand workflow
- Review queue and draft review history
- Approval, rejection, and editor resubmission loop
- Draft versions and scheduled publish timing
- Platform previews for LinkedIn, Instagram captions, email, and article/blog layouts

### Collaboration

- Threaded comments on campaigns and drafts
- Mention parsing using `@email`
- Assignments for campaigns, drafts, and review tasks
- Notification center for mentions, review events, assignments, and due-soon reminders
- Collaboration-aware campaign activity feed

### Intelligence and reuse

- Reusable content templates
- Dashboard analytics for campaigns, drafts, reviews, schedule, workload, and content mix
- Campaign health scoring with transparent penalty factors
- Helper tool catalog and execution visibility
- Advanced content-operation helpers for tone validation, cross-channel adaptation, template recommendation, asset recommendation, and revision checklist generation

### Billing and controls

- Brand plans and subscriptions
- Usage metering and upgrade prompts
- Brand-level checks for members, active campaigns, scheduled work, and template counts

## Product Design Principles

The project design follows a few practical rules:

- Multi-brand first: all meaningful operational data is scoped to brands and memberships.
- Workflow before automation: content movement, review rules, and blocked states stay explicit even when helper tools are available.
- Human accountability stays visible: assignments, reviewers, comments, and audit events remain first-class.
- AI is optional, not foundational: MCP and helper tools extend the product but do not replace the base workflow.
- Analytics are operational, not vanity metrics: the dashboard emphasizes health, bottlenecks, review speed, and workload.
- Configuration lives close to execution: workflow rules, plans, and permissions are attached to the brand instead of being global assumptions.

## System Design

### Application architecture

- Frontend: React, TypeScript, Vite, Tailwind CSS, TanStack Query, Zustand
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic
- Database: PostgreSQL
- Local development: Docker Compose

### Runtime shape

- The frontend provides the authenticated workspace UI and route-based page structure.
- The backend exposes REST APIs under `/api`.
- PostgreSQL stores workspace, campaign, draft, review, collaboration, and analytics source data.
- The MCP helper layer is mounted separately and can be enabled or disabled without breaking the core app.

### Frontend navigation model

- Overview: dashboard and notifications
- Workspace: brands, projects, campaigns, calendar
- Production: drafts, reviews, templates
- Intelligence: AI assist/helper tools and billing

### Backend domain model

Identity and workspace:

- `users`
- `brands`
- `brand_memberships`
- `plans`
- `brand_subscriptions`

Planning and execution:

- `projects`
- `campaigns`
- `content_briefs`
- `campaign_milestones`
- `campaign_dependencies`
- `calendar_items`

Production:

- `content_drafts`
- `draft_versions`
- `draft_reviews`
- `campaign_assets`
- `content_templates`

Collaboration and observability:

- `collaboration_comments`
- `mentions`
- `assignments`
- `notifications`
- `audit_logs`
- `tool_usage_logs`

## Project Design Process

This product was intentionally designed and implemented in phases so each layer of the system had stable foundations before more advanced workflow or AI-assisted behavior was added.

### Phase breakdown

1. Foundation: authentication, brands, memberships, projects, campaigns, and initial app shell
2. Content core: briefs, drafts, campaign workspace, search, and filters
3. Review loop: comments, approvals, rejections, and review queue
4. Production support: assets, version history, and calendar scheduling
5. Reuse and controls: templates, analytics baseline, plans, subscriptions, and usage checks
6. MCP helper foundation: helper tools, isolated MCP exposure, and tool usage logging
7. Collaboration layer: threaded comments, mentions, assignments, notifications, and richer activity history
8. Planning UX: board view, platform previews, stronger campaign workspace ergonomics
9. Operational intelligence: campaign health, workload analytics, approval analytics, and content-mix reporting
10. Workflow realism: configurable brand workflows, milestones, and dependency-aware planning
11. Advanced content ops: brand voice validation, adaptation, recommendations, and revision checklist helpers

### Why the project was designed this way

- Early phases established durable entities such as brands, campaigns, and drafts before UX polish or AI tooling.
- Review and collaboration were added before advanced automation so human workflow remained the system backbone.
- Analytics were introduced after enough operational data existed to make them meaningful.
- Flexible workflows came after fixed-status flows proved the product shape, allowing migration toward more realistic brand-specific processes.
- MCP was kept modular and isolated so the application still works as a normal campaign platform if helper tooling is disabled.

## Local Development

### Quick start

1. Copy the environment file:

   ```bash
   cp .env.example .env
   ```

2. Start the stack:

   ```bash
   docker compose up --build
   ```

   Or:

   ```bash
   make up
   ```

3. Open the application:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000/api`
- Health check: `http://localhost:8000/api/healthz`
- MCP mount: `http://localhost:8000/mcp`

The backend container runs `alembic upgrade head` before starting the FastAPI server.

### Environment variables

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `FRONTEND_ORIGIN`
- `VITE_API_BASE_URL`

### Useful commands

- `make up`
- `make down`
- `make logs`
- `make ps`

### Optional demo data workflow

1. Start the stack.
2. Create an account from the login page.
3. Seed a realistic demo workspace for that account:

   ```bash
   docker compose exec backend python scripts/seed_demo_workspace.py --email your-email@example.com
   ```

The seed script attaches demo brands, projects, campaigns, briefs, drafts, templates, assignments, and notifications to the specified existing user.

## MCP Helper Configuration

- `MCP_HELPERS_ENABLED=true` keeps the helper MCP server mounted
- `MCP_MOUNT_PATH=/mcp` controls the shared mount path
- `MCP_ENABLE_HTTP_TRANSPORT=true` enables streamable HTTP transport
- `MCP_ENABLE_SSE_TRANSPORT=false` keeps SSE disabled unless explicitly needed
- The helper REST endpoints remain available under `/api/tools/helpers/*` even if MCP is disabled

## Key API Areas

### Auth and workspace

- `/api/auth`
- `/api/brands`
- `/api/brands/{brand_id}/memberships`
- `/api/brands/{brand_id}/audit-logs`
- `/api/brands/{brand_id}/billing`
- `/api/brands/{brand_id}/subscription`
- `/api/projects`
- `/api/campaigns`

### Campaign operations

- `/api/campaigns/{campaign_id}/overview`
- `/api/campaigns/{campaign_id}/brief`
- `/api/campaigns/{campaign_id}/comments`
- `/api/campaigns/{campaign_id}/assignments`
- `/api/campaigns/{campaign_id}/milestones`
- `/api/campaigns/{campaign_id}/dependencies`
- `/api/campaigns/{campaign_id}/assets`

### Draft operations

- `/api/drafts`
- `/api/drafts/review-queue`
- `/api/drafts/{draft_id}/comments`
- `/api/drafts/{draft_id}/assignments`
- `/api/drafts/{draft_id}/reviews`
- `/api/drafts/{draft_id}/versions`
- `/api/drafts/{draft_id}/move-stage`
- `/api/drafts/{draft_id}/submit`
- `/api/drafts/{draft_id}/approve`
- `/api/drafts/{draft_id}/reject`
- `/api/drafts/{draft_id}/resubmit`

### Analytics, templates, and tools

- `/api/dashboard/summary`
- `/api/dashboard/analytics`
- `/api/dashboard/campaign-health`
- `/api/dashboard/campaign-health/{campaign_id}`
- `/api/calendar-items`
- `/api/templates`
- `/api/notifications`
- `/api/notifications/summary`
- `/api/assignments/mine`
- `/api/tools/helpers`
- `/api/tools/catalog`
- `/api/tools/usage`

## Implementation Notes

- Each campaign can have one brief and many drafts.
- Brands own their workflow configuration, including stage labels, transition rules, colors, and initial entry stages.
- Planner stage moves intentionally route through workflow and dependency checks rather than bypassing them.
- Reviewer approval actions only apply to drafts currently in the configured review stage.
- Campaign health starts at `100` and subtracts capped penalties for overdue drafts, pending approvals, missing assets, unassigned work, and near-term deadline pressure.
- Approval turnaround is measured from submission or resubmission to the next approval or rejection event.
- Usage checks currently focus on member count, active campaigns, upcoming scheduled items, and template count.
- Invitation records exist without outbound email sending.
- The frontend stores the JWT token locally and restores the session on reload.
- The MCP layer is optional; the base REST product remains functional even if MCP support is disabled or unavailable.
