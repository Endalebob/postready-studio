---
doc: campaign-posts-checklist
status: approved
updated: 2026-11-12
---
# Reviewed campaign posts

Fast mode. Accepted campaign setup is committed as `dd3b36f`.

## Boundary

Turn a saved campaign into an advertisement the owner can review and then explicitly schedule for Telegram. Keep the existing daily, weekly and monthly recurrence rules. Automatic paid preparation, campaign-wide auto-publish, dynamic all-approved scope, analytics and LangGraph selection remain later work.

In this milestone the owner selects a product from the campaign and explicitly requests each generation. No background paid generation starts merely because a campaign exists. The owner approves an exact saved revision, channel and future time for each scheduled post. A draft campaign itself remains inactive: it does not authorize recurring unattended publication. The next milestone can build automatic preparation around tested post contracts and an explicit budget.

## Slices

- [ ] **1. Prepare a campaign advertisement for review**
  Becomes usable: Open a campaign, choose one of its eligible products, explicitly generate an ad, and reopen the prepared result without uploading the source again.
  Why now: Proves the full gallery-to-ad path and server-rendered English/Amharic output before a scheduler depends on it.
  PRD ref: `scheduled-campaigns-plan.md > Prepare an upcoming post`, `Review-every-post mode`
  Spec ref: `scheduled-campaigns-plan.md > Architecture`, `Failure behavior`
  Build: Durable owner-scoped preparation job; campaign/gallery/profile snapshots; campaign language and theme; validated bounded copy instructions; private source lookup; existing image provider; deterministic server-side PNG with the bundled Ethiopic font, exact prices, contacts and logo; existing saved-ad editor integration. Recheck eligibility before starting paid work and before making a result available. Idempotent command and durable phase state prevent duplicate jobs and blind resubmission after uncertain provider calls.
  Verify (mechanical): Owner isolation, stale or unapproved sources, snapshot facts, duplicate requests and worker recovery, confirmed failure versus uncertain generation, no automatic paid retry after an ambiguous request, storage recovery, text fitting and representative English/Amharic renders; regression suite and frontend build; browser preparation/reopen with provider doubles. Agent verification must not silently make paid requests.
  Learner check: Request one preparation, inspect the product/facts and independent caption, edit and save it, then reopen the saved result.
  Commit: `Prepare reviewable campaign ads from approved gallery products`

- [ ] **2. Schedule one explicitly reviewed Telegram post**
  Becomes usable: Preview the exact saved ad, caption, channel and one future occurrence; approve that post for that time, or cancel before submission.
  Why now: Establishes owner authorization and delivery state before recurring automatic preparation is enabled.
  PRD ref: `scheduled-campaigns-plan.md > Review-every-post mode`, `Pause or delete`
  Spec ref: `scheduled-campaigns-plan.md > Architecture`, `Provider timeout`
  Build: Upcoming-post record and owner UI; selected future occurrence; immutable revision/destination/time approval snapshot; edit/reference changes invalidate approval; Telegram provider adapter around existing verified publication behavior; transactional handoff to existing durable publish attempts; due scanner and recovery of saved work after enqueue failure; exact occurrence uniqueness; expiration check; cancel and missed statuses. A late post is marked missed rather than silently moved to another time. A post whose provider submission may have happened is unknown and never automatically resent.
  Verify (mechanical): Competing scanners and workers, duplicate approval/submission, stale revisions, revoked channel/source, cancellation races, ad expiration and missing approval, restart/enqueue recovery, confirmed rejection and uncertain outcomes; existing Telegram regressions through adapter; controlled browser review with provider doubles. A real Telegram test is only sent when the owner explicitly requests that specific post.
  Learner check: Schedule a reviewed post for a chosen future occurrence, inspect Upcoming, cancel before submission, and review the truthful final status.
  Commit: `Schedule explicitly reviewed campaign posts for Telegram`

## Hands-on Checkpoints

- [ ] Review the first usable prepared ad before building timed submission.
- [ ] Review the integrated prepare/edit/approve/schedule/cancel journey.

## Final Review

- [ ] Owner feedback resolved and reviewed-post milestone accepted.

## Code Tour and App Map

- [ ] Document durable preparation phases, server rendering, exact-revision approval and the due-post worker.

## Revisions

- Renderer and provider contract are folded into usable preparation and scheduling slices rather than isolated infrastructure tasks.
- This milestone schedules individually authorized posts. It does not activate unattended recurring generation or posting; those require explicit campaign activation and spending controls in the following milestone.
- Owner approved the build order on 2026-11-12. Begin slice 1 in fast mode; pause at the planned prepared-ad review.

## Slice 1 verification - 2026-11-12

- Implemented owner-scoped durable preparation jobs, explicit confirmation, idempotent requests, canonical snapshots, source/campaign revision checks, 2-active/10-per-day guardrails, safe finalization retry and 30-day cleanup.
- Implemented server-side 1080px rendering using the bundled Ethiopic font and deterministic fact fields. Overflow keeps the generated artwork editable instead of charging for regeneration merely to shorten text.
- All 81 backend tests passed in Linux containers, including preparation phases, uncertain and stale provider calls, rejected requests, storage recovery, ownership, changed sources, snapshots, expiry, English/Amharic theme renders, and SDK transport reuse across worker event loops. The pinned SDK's sync transport runs in a worker thread; campaign requests do not use the existing general-generation retry wrapper.
- Production frontend build and TypeScript passed. Isolated migration 006 -> 007 -> 006 -> 007 preserved the existing account. Actual PostgreSQL is at 007_preparations.
- Real PostgreSQL duplicate commands returned one job ID; competing workers made exactly one copy request and one artwork request using in-process test doubles. MinIO stored source assets and the final PNG. API/container recreation retained the preparation and saved ad. Workers/beat were temporarily stopped during the controlled provider-double run and are now restored; local Telegram token remains disabled.
- Browser verified product selection, explicit charge acknowledgement, disabled generation without acknowledgement or while campaign edits are unsaved, opening the prepared ad, editing/saving and reopening the exact saved result. Screenshot comparisons confirmed caption edits leave the image unchanged and headline edits preserve the product region. Mobile editor/preparation checks at 390px and 320px showed no horizontal overflow.
- Screenshots: artifacts/campaign-preparation-review.png and artifacts/campaign-preparation-mobile.png. The ready example used the source product photo and fixed test copy, not a paid AI generation. Production was not changed; no paid provider requests or Telegram posts were made.
- Slice 1 mechanical verification is complete. Its planned owner hands-on checkpoint remains open before commit and before building slice 2. Open Campaigns, review/edit the saved campaign, and open the prepared ad; review the facts, edit text, save and reopen it. The owner may separately request a real generation through the explicit generation control.
