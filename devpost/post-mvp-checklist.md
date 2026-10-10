---
doc: post-mvp-checklist
status: approved
---

# First-release build checklist

Build mode: fast (carried forward)

## Slices

- [x] **1. Sign in and reuse a business profile**
  Becomes usable: Returning owners save contacts, address, logo and defaults once, then create an ad with those values prefilled.
  Why now: Establishes ownership and the main repeat-use improvement before storing user ads.
  PRD ref: `post-mvp-requirements.md > R1 — Accounts and ownership`, `R1a — Deferred verification and recovery`, `R2 — Business profile and defaults`
  Spec ref: `post-mvp-spec.md > Accounts and profiles`, `Local run and external dependencies`
  Build: Add PostgreSQL migrations, authenticated sessions, MinIO logo storage, registration/login/logout, profile editor, generation authentication, profile-prefilled drafts and exact logo composition.
  Verify (mechanical): Frontend build/type checks; backend authentication/ownership/validation tests; two-user access isolation; restart persistence; profile override independence; inspect logo in preview and PNG.
  Learner check: Register, save your business information, start an ad, verify defaults and logo, change an ad-specific contact, sign out/in and confirm the profile is unchanged.
  Commit: `Add accounts and reusable business profiles`
  Verification evidence (2026-10-10): 20 backend tests passed in the production API container; Docker frontend production build and TypeScript checks passed; PostgreSQL migration `001_accounts` applied. Live registration, two contacts, MinIO logo upload, logout/login and profile/logo persistence across API/PostgreSQL/MinIO restarts passed. Browser verified profile-prefilled language/theme/address/contacts, ad-specific contact independence, live generation with the exact logo and 1080 × 1080 PNG export. Learner tested the flow and approved continuing on 2026-10-10.

- [x] **2. Reopen saved ads until their seven-day deadline**
  Becomes usable: Owners return to a private ad library, edit/save/download ads, and see expiration dates.
  Why now: Builds on authenticated ownership and storage to deliver persistence.
  PRD ref: `post-mvp-requirements.md > R3 — Durable ad library`
  Spec ref: `post-mvp-spec.md > Saved ads and expiration`
  Build: Persist generation source assets and profile snapshots, explicit save/revisions/PNG export, library, ownership/expiry checks, confirmed deletion and scheduled cleanup.
  Verify (mechanical): Storage failures and stale revision tests; reload and service restart; boundary-time expiry on every access path; cleanup retry and preservation of active profile logos; English/Amharic saved exports.
  Learner check: Generate, save, refresh, reopen and edit an ad; download it and inspect the expiration date.
  Commit: `Add private saved ads and seven-day expiration`
  Verification evidence (2026-10-10): 27 backend tests, production frontend build and TypeScript checks passed. Live Amharic and English generation, explicit Save, My Ads, refresh/reopen and saved PNG downloads passed. Saved edits survived PostgreSQL/MinIO/API restarts. Real PostgreSQL concurrent saves returned one success and one conflict. Expiry, storage recovery, signed retry deadlines, owner isolation, deletion and cleanup retry were covered by tests; Celery beat dispatched its scheduled cleanup through Redis successfully.

- [ ] **3. Connect a Telegram channel and publish a reviewed ad**
  Becomes usable: Owners authorize a channel and publish an exact saved image/caption without leaving the app for every post.
  Why now: Requires durable ownership and immutable ad revisions.
  PRD ref: `post-mvp-requirements.md > R4 — Connected social destinations`, `R5 — Publish a saved revision`
  Spec ref: `post-mvp-spec.md > Telegram`
  Build: Verified channel linking, readiness/disconnect UI, durable publishing attempts, worker, explicit preview/confirmation and truthful outcome statuses.
  Verify (mechanical): Permission/link challenge, account isolation, duplicate attempts, revoked access, expiry and ambiguous timeout tests. Live controlled-channel linking and publishing require configured bot/channel.
  Learner check: Connect your test channel, review an ad, publish once and verify the image/caption and published link.
  Commit: `Add verified Telegram channel publishing`

## Hands-on Checkpoints

- [x] Early profile/defaults flow reviewed after slice 1
- [ ] Complete saved-ad/publishing flow reviewed after slice 3

## Final Review

- [ ] All requested fixes verified and learner confirms the first-release build is ready for deployment preparation

## Code Tour and App Map

- [ ] Update map for authentication, persistence, expiration and publishing routes; provide a focused technical handoff

## Revisions

- Completed hackathon documents are preserved; these documents govern the new first-release work.
- Database and initial product defaults were approved before implementing slice 1.

- 2026-10-10: Learner approved the technical proposal, PostgreSQL, initial account/profile defaults and three-slice build order.

- Official prebuilt MinIO images could not be pulled from Docker Hub or Quay. Build the pinned official MinIO source release locally instead; same storage API and product choice, no third-party substitute.
- Live startup exposed an Alembic import-path issue; setting its project import path repaired startup, and the PostgreSQL migration and restart checks passed afterward.

- Generated-source persistence uses a temporary database fallback when MinIO fails; a signed generation receipt permits saving retries after a database outage while preserving the original seven-day deadline. This keeps the planned recovery behavior without regenerating artwork.
