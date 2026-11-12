---
doc: campaign-foundation-checklist
status: approved
updated: 2026-11-12
---
# Campaign foundation build

Fast mode continues. Owner approved starting with new image-ad retention and the persistent approved gallery on 2026-11-12. The larger campaign document remains proposed outside this foundation.

## Slices

- [x] **1. Retain new image ads for 30 days and maintain an approved product gallery**
  Becomes usable: Owners save, edit, approve, deactivate and delete reusable product photos and facts, independently of generated ads.
  Why now: Establishes durable owner-approved inputs before scheduled generation and publishing.
  PRD ref: `scheduled-campaigns-plan.md > Create the persistent gallery`, `Generated advertisement expiration`
  Spec ref: `scheduled-campaigns-plan.md > gallery_assets`, `Architecture`
  Build: Owner-scoped gallery model/migration, private normalized MinIO images, fact validation, approval reset after edits, revision conflict protection, UI, retryable deletion and new-ad retention.
  Verify (mechanical): Ownership, upload validation, approval/deactivation, conflicts, storage failure/cleanup recovery, fixed new expiry and preserved legacy deadlines, real MinIO round-trip, PostgreSQL migration, frontend build and local UI checks.
  Learner check: Save several products, approve one, leave one unapproved, edit an approved product and confirm it needs approval again; refresh and reopen the gallery.
  Commit: `Add persistent approved product gallery and 30-day image ads`

## Hands-on Checkpoints

- [x] Gallery review after the working foundation

## Final Review

- [x] Improve gallery button spacing, consistent sizing and card-button alignment; owner requested during review.

- [x] Owner observations resolved and foundation accepted

## Code Tour and App Map

- [x] Add gallery route and retention policy to the app map

## Revisions

- Existing stored ad deadlines are preserved. Videos remain seven days. Gallery files persist until deletion.
- Scheduling, automatic publishing, analytics and LangGraph are outside this first foundation.
- Initial technical guardrail: maximum 100 retained gallery items per account; deleted files pending cleanup count until removal succeeds. The UI discloses this limit.

## Verification progress - 2026-11-12

- Production frontend build and TypeScript compilation passed.
- 45 local backend tests passed: gallery, image-ad retention/recovery, accounts, API validation, generation validation and Telegram regression tests. These use SQLite and storage doubles; they do not establish real PostgreSQL locking or MinIO persistence.
- Isolated SQLite migration 004 -> 005 -> 004 -> 005 passed and preserved an existing seven-day ad deadline.
- Docker Desktop cannot start: stale userAnalyticsOtlpHttp.sock. Normal startup/restart and graceful/forced shutdown were attempted without resetting data. Renaming the stale socket failed. Automatic approval review rejected its removal; no deletion or factory reset was performed. Owner was asked to restore the local engine.
- A localhost-only UI test backend was started with isolated SQLite and a filesystem storage double, then stopped. Automatic approval review rejected starting the companion frontend, so browser verification was not completed.
- Real PostgreSQL/MinIO checks, deployed-service migration, UI review and the slice commit remain pending. No production changes or external posts were made.

## Resumed after Docker reset - 2026-11-12

- Owner restored/reset Docker Desktop; engine 28.0.1 responds. No existing project containers or named volumes remained in this Docker instance. Rebuilding a fresh local stack; production was not accessed or changed.
- Full native Windows regression run passed 61 tests, including real FFmpeg composition. The harness mapped the Linux DejaVu font lookup to Windows Arial; this is not a substitute for the pending Linux-container regression run.
- New image downloads initially hit a Docker Hub TLS timeout; retry progressed successfully. PostgreSQL image and source-built MinIO dependencies are downloading.

- Docker PostgreSQL and Redis are running with loopback-only verification ports. Native FastAPI applied migration 005 to the real PostgreSQL database, retaining normal authentication. No authentication overrides are used in the current verification app.
- Browser verified sign-in, gallery navigation, photo preview, preserved form after unavailable storage and mobile layout without horizontal overflow. Status feedback now scrolls into view after a save error; frontend production rebuild passed.

## Real-service verification completed - 2026-11-12

- Full Linux-container suite passed all 61 tests with the pinned backend dependencies and actual container fonts/FFmpeg.
- Real PostgreSQL/MinIO/API checks passed: concurrent edits returned one 200 and one 409; simultaneous duplicate uploads created only one item and retry returned it; private normalized images/thumbnails loaded; another authenticated account was denied image access.
- Real ad generation persistence fixed the new deadline at exactly 30 days. Expired-ad cleanup retained the gallery source. Gallery cleanup removed a deleted test item and retained the approved source.
- Browser saved and approved an Amharic product photo through the normal authenticated app. Editing an approved item required approval again; deactivation cleared eligibility. The delete confirmation and Keep action worked.
- PostgreSQL and MinIO restart preserved gallery rows and private images. The full Docker stack is running, and browser reload retained the gallery. Telegram is disabled in local verification workers to avoid competing with the live app bot.
- Fresh npm installation exposed Next.js advisories GHSA-2464-fhr4-w9xw, GHSA-p3m5-59mp-jv5r and GHSA-673q-mjm6-r5xr. Upgraded within major version 16 to 16.4.6; npm audit reports zero vulnerabilities. Patched frontend container build and TypeScript checks passed. Running Docker web version confirmed as 16.4.6; browser reload retained the gallery and all three private thumbnails loaded. Dependency-only security update committed as 480be50.
- No paid AI requests or social posts were made. Production deployment remains unchanged. Owner hands-on review and foundation commit remain pending.

## Ready for owner review

- Complete local Docker stack is running at http://localhost:3010/. Native verification servers have been stopped. Browser review is open in the generated QA workspace with approved, unapproved and inactive examples.
- Owner review was requested: add/save/approve a product, edit its price and confirm approval clears. Awaiting the report before the foundation commit and map completion.
- Mechanical screenshot: ignored local `artifacts/gallery-foundation-review.png`.

- Owner review: gallery behavior is nice; requested improved button alignment. Grouped toolbar/approval controls and bottom-aligned card actions, with full-width stacked controls on narrow screens. Visual recheck pending.
- Button refinement verified: production frontend build and TypeScript passed; desktop toolbar and editor actions share a 56px height with 12px gaps, and all three card actions share the same bottom edge. At 390px, toolbar buttons stack at equal width without horizontal overflow. Screenshot: artifacts/gallery-buttons-review.png. Owner retry remains pending.

- [x] Owner requested a broader visual polish: replace wrapping header with clear workspace navigation and account menu; standardize form, button and card styling across the app. Mechanical responsive checks and owner review pending.

- Workspace polish verified: production Docker build and TypeScript passed. Browser checked overview, gallery and product editor, saved-ad empty state, profile, video form and social connection state. Navigation active state, account menu, mobile menu collapse and Create ad flow worked. No horizontal overflow in tested 320px, 390px and 1280px layouts; tablet navigation checked at 768px. Updated screenshots: artifacts/workspace-polish-desktop.png and artifacts/workspace-polish-mobile.png. Production untouched; visual acceptance remains pending.

## Accepted - 2026-11-12

Owner confirmed the revised app looks good and asked to move to the next step. Gallery behavior, button alignment and broader workspace styling are accepted. App map updated. All prior pending-review entries above are historical verification notes superseded by this acceptance.
