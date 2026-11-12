---
doc: campaign-setup-checklist
status: approved
updated: 2026-11-12
---
# Campaign setup — next usable step

Fast mode. Persistent gallery and visual review accepted; foundation commit: `0897ea5`.

## Boundary

An owner creates and maintains paused campaign drafts with daily, weekly or monthly schedules. A draft records its name, explicitly selected approved products, verified Telegram destination, frequency, weekday or day of month where applicable, local time, IANA timezone, language, theme and optional instructions. The screen previews the next three scheduled times, clearly labelled as a preview. Saving a draft does not enable a scheduler, incur generation charges or publish anything.

Defaults: Africa/Addis_Ababa timezone, weekly selected as the default frequency, review-every-post mode. Owners can choose daily, weekly or monthly before saving. Select specific products; no dynamic all-approved scope or auto-publish switch in this step. Maximum 10 retained drafts per owner and 100 selected gallery items per draft. Deleted drafts do not count. These limits are application guardrails, not pricing.

Existing ad generation, editing and manual Telegram publishing remain available. Generation/preparation, server-side PNG rendering, budget reservation, activation/pause of running campaigns and timed publication are later steps. The UI must not suggest that a paused draft is running.

## Schedule controls

- Daily: local posting time and timezone.
- Weekly (default): weekday, local posting time and timezone.
- Monthly: day of month (1–31), local posting time and timezone.
- Approved short-month rule: use the last day of the month when the selected day does not exist (for example, day 31 becomes February 28 or 29). Show this beside the monthly control and reflect it in the preview.
- The owner can change frequency; weekly is only the initial selection.

## Slices

- [x] **1. Save and review a campaign draft**
  Becomes usable: Create, reopen, edit and delete a private paused campaign; view the next three proposed posting times.
  Why now: Proves the gallery, destination and timezone contract before paid generation or automated external actions.
  PRD ref: `scheduled-campaigns-plan.md > Create a campaign`, `Review-every-post mode`
  Spec ref: `scheduled-campaigns-plan.md > Architecture`, `Security, privacy and abuse controls`
  Build: Owner-scoped campaign records/migration with selected-item IDs in validated JSON; validated daily/weekly/monthly schedules with ZoneInfo; owner-scoped draft API; revision conflicts and idempotent creation; campaign navigation and responsive form/list; selected-source and destination warnings when approval or connections change. Backend rechecks selected ownership and eligibility on save. Edits never implicitly approve products or activate publishing.
  Verify (mechanical): Two-user isolation, stale revisions, duplicate save/retry, invalid gallery/destination rejection, retained draft limits, timezone and daily/weekly/monthly next-run calculations including DST gaps/repeats, leap years and short months, no worker or provider submission from draft creation; real PostgreSQL persistence/migration and production frontend build; desktop/mobile browser create/edit/reload and schedule-preview checks.
  Learner check: Create a draft using an approved product and connected channel; switch between daily, weekly and monthly and inspect the preview times. Save, reload and reopen it, then edit the time. Confirm it stays paused.
  Commit: `Add paused campaign setup and schedule previews`

## Hands-on Checkpoints

- [x] Owner tries the working campaign setup and reports what needs changing.

## Final Review

- [x] Observations resolved; owner accepts the draft workflow.

## Code Tour and App Map

- [x] Add campaign draft records, schedule preview and explicit inactive boundary to the app map.

## Revisions

- This narrows the large proposed campaign slice into an independently usable setup step. Server-side rendering and social provider adapters must be proven before automatic preparation/publication.
- Dynamic gallery scope, automatic publishing, generation budgets, analytics and LangGraph remain outside this draft-only step.
- Owner approved this build order after adding daily and monthly choices on 2026-11-12.

- Owner clarified that daily, weekly and monthly must all be available; weekly is only the default. Updated the draft scope and verification accordingly.

- Scheduling semantics: skip nonexistent daylight-saving wall times; use only the first occurrence of a repeated wall time. Monthly dates clamp to the last day. Preview three strictly future occurrences.

## Mechanical verification - 2026-11-12

- All 70 backend tests passed in the Linux container. Nine new tests cover recurrence, DST gaps/repeats, leap years, short-month clamping, validation, authentication, owner isolation, draft conflicts, duplicate create/replay, limits and reference changes. Draft creation produced no generation or publication records.
- Production frontend build and TypeScript passed. API started against real PostgreSQL at migration 006_campaigns.
- Real PostgreSQL concurrent creates returned one draft ID; simultaneous edits returned one 200 and one 409. Deleted draft replay returned 410. Gallery products remained intact.
- Isolated migration 005 -> 006 -> 005 -> 006 passed and preserved a pre-existing account. PostgreSQL/API restart retained the browser-created monthly draft.
- Browser verified weekly default, daily previews, monthly day-31 clamping, product selection, save/reopen, and changing local time to 11:30. Mobile form widths 320px/390px had no horizontal overflow.
- Local QA account uses a clearly labelled simulated Telegram channel fixture. The local bot token remains disabled. This verifies draft selection/persistence only, not real channel verification or publication. Production configuration is unchanged.
- No paid AI requests, Telegram publications or production changes were made. Owner hands-on review and milestone commit remain pending.

- Final browser checks: updated aria labels locate frequency controls directly; daily/weekly/monthly previews use the saved 11:30 time. Delete confirmation and Keep draft worked. The saved monthly example remains paused. Screenshot: artifacts/campaign-schedule-review.png (desktop schedule), artifacts/campaign-setup-mobile.png (mobile full form). Owner review requested next.

## Accepted - 2026-11-12

Owner confirmed the campaign draft workflow is good and requested continuation. All pending owner-review statements above are superseded by this acceptance. App map updated with draft persistence and recurrence semantics.
