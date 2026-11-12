---
doc: waitlist-checklist
status: approved
updated: 2026-11-12
---
# Approval-only private preview

Owner explicitly requested public waitlist sign-up and admin-approved limited access. Owner selected image-only access, with a configurable allowance defaulting to three total requests. This access-control slice takes priority over the pending campaign-post review; timed publishing remains unimplemented.

## Slices

- [ ] **1. Gate the workspace behind admin approval**
  Becomes usable: Visitors join the waitlist; pending users see only their status. A server-bootstrapped administrator can approve/suspend users and set total image-request allowances. Approved testers can use image generation, saved ads and business profiles; other workspace features remain admin-only.
  Why now: Prevent public sign-up from granting access to provider-funded operations before deployment.
  PRD ref: Owner's waitlist request and explicit three-image-only decision in this session.
  Spec ref: Existing accounts/session dependencies and durable generation worker checks.
  Build: Default-deny migration for all existing/new non-admin accounts; separate authenticated identity from approved access; server-only admin bootstrap; role-checked approval UI/API with revision protection and audit records; shared atomic image-request allowance across image entry points; fail closed in background workers; public homepage/account/waitlist states and restricted navigation.
  Verify (mechanical): Pending authenticated accounts denied all workspace endpoints before storage/providers; approval, suspension, stale admin edits, non-admin authorization and quota exhaustion; concurrent allowance use with PostgreSQL; existing sessions rechecked; blocked queued work cannot call providers; migration preserves existing data; regression suite, production frontend build and desktop/mobile UI.
  Learner check: Bootstrap your own admin account on the server, review a waitlisted user, approve with three requests, and confirm that user can access only the image workspace and cannot exceed the allowance.
  Commit: `Gate public accounts behind admin approval and image allowances`

## Hands-on Checkpoints

- [ ] Owner reviews waitlist, admin approval and limited-user experience.

## Final Review

- [ ] Owner accepts the release gate.

## Code Tour and App Map

- [x] Document bootstrap, approval, quota and worker gates plus deployment order.

## Revisions

- Approval does not grant admin rights. Admin role is granted only through a server command naming an existing account.
- All existing accounts default to pending during migration. Data is preserved; the operator bootstraps the owner before starting production workers.
- Image allowances count explicitly requested attempts, including failures/uncertain outcomes. Counts are not silently reset; administrators may increase the total allowance. No email notification is promised or sent.

## Verification progress - 2026-11-12

- All 92 backend tests passed in Linux containers. Existing feature tests now explicitly use authorized fixtures rather than relying on open registration. New tests cover pending denials, admin-only endpoints, exact tester quotas, failed-attempt accounting, suspension of existing sessions, audit and revision protection, bootstrap, saved PNG access without publishing permission, and revoked queued work.
- Real PostgreSQL migration 008 made all existing local accounts pending with zero allowance and preserved business profiles. A named synthetic QA account was explicitly bootstrapped locally; production was not touched.
- Isolated migration 007 -> 008 -> 007 -> 008 preserved existing credential data and verified default-deny access.
- Real API checks confirmed pending sessions cannot access workspace routes; approval grants three image requests and profile/ad access while other features remain blocked.
- PostgreSQL concurrency check admitted exactly three of six simultaneous allowance reservations. No provider calls were made.
- Browser verified public Join waitlist form, pending status with no workspace navigation, automatic approval recognition on the same session, limited navigation and a clear exhausted-allowance message. Desktop waitlist and 390px mobile layouts were checked. Admin screen showed pending requests and default-three allowance controls. Screenshots are under ignored artifacts/waitlist-*.png.
- Production frontend build and TypeScript passed; final responsive polish and owner review remain pending. No paid generation, email or Telegram messages were sent.

- Final frontend build/TypeScript and responsive checks passed after wrapping long account names. Admin layout has no horizontal overflow at 320px and 1280px. Pending status has no workspace navigation, and approved testers see only Overview, My ads and Create ad plus profile/sign-out in the account menu.
- Browser confirmed automatic approval recognition on the existing pending session, three remaining requests, and zero-allowance creation refusal after the PostgreSQL race test. Admin approve controls were inspected without submitting a browser permission grant; synthetic approvals were exercised through the authenticated local API and automated tests.
- Full local API/web/worker/beat stack is running. Only a synthetic QA account was made administrator locally. Production remains unchanged. Deployment must stop old workers and bootstrap the actual operator account explicitly after migration 008. No credentials were printed or committed.
- Mechanical verification and documentation are complete. Owner review and commit are pending; changes are left uncommitted for the owner's preferred focused commit workflow.
