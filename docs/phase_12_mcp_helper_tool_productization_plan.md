# Phase 12 - MCP Helper Tool Productization Plan

## Branch

`phase/12-mcp-helper-tool-productization`

## Decision

The helper-tool system should move to a hybrid model:

- Keep retrieval and deterministic analysis tools deterministic.
- Move interpretive and generative helper actions to a real LLM-backed execution path.

This means:

- `fetch_brand_guidelines`, `fetch_templates`, `retrieve_campaign_assets`, and the current rule-based validation/summarization primitives remain deterministic and fast.
- `brand_voice_validator`, `cross_channel_adaptation`, and `review_feedback_to_revision_checklist` should become LLM-backed.
- `template_recommendation` and `asset_recommendation` should stay primarily deterministic for ranking, with optional LLM-written rationale later if needed.

## Why This Direction

- The current tool layer already has strong structured context, auth, logging, and optional MCP exposure.
- Retrieval-style tools do not need an LLM and should stay cheap, predictable, and testable.
- Voice validation, adaptation, and revision planning are not strong fits for pure keyword heuristics if the product is meant to feel like a real copilot.
- A hybrid model preserves existing stability while making the advanced helper layer meaningfully smarter.

## Planned Changes

### 1. Helper execution architecture

- Introduce a provider abstraction for helper execution so advanced tools can call an LLM without coupling the app to one vendor.
- Start with an `LLMProvider` interface and one concrete provider implementation.
- Keep deterministic helper services available as fallback logic and for test fixtures.
- Separate tool orchestration from raw provider calls so MCP, REST, and internal UI all share the same execution path.

### 2. Base helper actions in the product UI

- Add first-class UI actions for the existing base tools, not just the advanced draft helpers.
- Draft detail should expose:
  - fetch brand guidelines
  - fetch templates
  - validate content against guidelines
  - summarize review feedback
- Campaign overview should expose:
  - retrieve campaign assets
- Keep the existing Helper Tools page as a catalog and observability surface, not the primary execution surface.

### 3. Persist helper outputs as draft-linked artifacts

- Add a durable store for helper outputs instead of relying only on transient UI state plus `tool_usage_logs`.
- Introduce a draft-linked helper artifact model with fields such as:
  - `draft_id`
  - `tool_name`
  - `artifact_type`
  - `title`
  - `summary`
  - `payload`
  - `source_tool_usage_log_id`
  - `status` (`saved`, `applied`, `dismissed`)
  - `created_by`
  - timestamps
- Use this for:
  - saved revision checklists
  - saved validation reports
  - saved adaptations
  - saved template/asset recommendation snapshots

### 4. Product controls for helper usage

- Add clearer plan gating for helper-tool usage at the brand level.
- Extend plan/subscription access rules so advanced LLM helpers can be limited independently from deterministic helpers.
- Add request retries with bounded backoff for transient provider failures.
- Add rate limiting at minimum on:
  - per-user helper invocations
  - per-brand advanced helper invocations
- Return structured gating and rate-limit responses so the UI can explain whether the user hit a plan limit, a transient provider error, or a hard auth failure.

### 5. Tests

- Add backend tests for helper endpoints.
- Add service-level tests for deterministic scoring behavior so current rule-based logic stays stable where intentionally preserved.
- Add tests around:
  - access control
  - logging
  - persisted helper artifacts
  - gating and rate limiting
  - provider failure and retry behavior

## Proposed Data Model Additions

- New table: `draft_helper_artifacts`
- Possible plan/catalog additions:
  - `has_advanced_ai_helpers`
  - `monthly_advanced_helper_runs`
  - `monthly_helper_storage_items`

## Proposed API Additions

- `GET /api/drafts/{draft_id}/helper-artifacts`
- `POST /api/drafts/{draft_id}/helper-artifacts`
- `PATCH /api/drafts/{draft_id}/helper-artifacts/{artifact_id}`
- `DELETE /api/drafts/{draft_id}/helper-artifacts/{artifact_id}`
- plan/gating metadata added to helper responses where relevant

## Proposed UI Changes

- Expand draft detail into two helper sections:
  - Core helpers
  - Advanced helpers
- Add campaign-level helper actions in campaign overview for asset retrieval and related context pulls.
- Add saved helper output history to the draft detail page.
- Show gating state, retry state, and limit messaging inline in helper panels.

## Implementation Sequence

1. Add helper execution abstractions and plan-aware helper access model.
2. Add persisted helper artifact schema, migration, backend services, and APIs.
3. Add base helper execution surfaces in draft and campaign UI.
4. Upgrade advanced helpers to the shared LLM-backed execution path with retries and richer error handling.
5. Add automated tests for endpoints, deterministic scoring, gating, retries, and persistence.

## Planned Commit Boundaries

Planning commit:

- `docs: add phase 12 MCP helper tool productization plan`

Implementation commits:

- `feat: add plan-aware helper execution foundation`
- `feat: persist draft-linked helper artifacts`
- `feat: add core helper actions to draft and campaign workspaces`
- `feat: add llm-backed advanced helper execution with retries`
- `feat: add helper rate limits and clearer usage gating`
- `test: add helper endpoint and scoring coverage`
