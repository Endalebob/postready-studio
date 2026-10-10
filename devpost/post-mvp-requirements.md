---
doc: post-mvp-requirements
status: approved
updated: 2026-10-09
---

# PostReady Studio — profiles, saved ads, and social publishing

## Objective

Move from the reviewed hackathon demo toward an app Ethiopian small-business owners can return to. Owners enter business information once, reuse it when creating ads, recover their generated ads later, and publish a selected ad from within PostReady Studio.

This is a future-release plan. The completed MVP scope, PRD, spec, and checklist remain records of the demo. No implementation or release date is implied by this document.

## Requested scope and proposed defaults

Requested: business profiles with contacts, address and logo; default those fields into ad creation; persist generated images for each user; integrate social publishing without leaving the app for each post.

Confirmed: use MinIO for image storage and expire saved ads after seven days. The learner prefers the easiest supported publishing integration with account authorization or granted access. Selected planning direction: Telegram channel publishing using a bot granted posting permission. Approved defaults: one owner and one business per account, optional logo/address, and uploaded logos included by default with an ad-specific opt-out. PostReady Studio login is confirmed as username/email plus password. Publish now requires explicit confirmation.

## Journey

1. Sign up or sign in and create a business profile.
2. Save business name, contact methods, optional address/logo, preferred language and theme.
3. Start an ad: business fields are prefilled; enter product photo/name/price and optional description/old price.
4. Override business defaults for this ad if needed, without changing the saved profile.
5. Generate and edit image text and social caption independently.
6. Save and reopen the ad from My Ads after refreshing or signing in again.
7. Connect a supported publishing destination, review the exact image/caption/account, then confirm Publish.
8. See truthful publishing status and reopen the platform post when a link is available.

## R1 — Accounts and ownership

- Authenticate returning users; profile, files, ads and social connections belong to an authenticated owner.
- Enforce ownership on every read, write, download and publishing request, including file access.
- First release uses username/email plus password. Proposed registration fields: unique username, unique email, password and password confirmation; sign-in accepts either username or email plus password. Registration fields were approved with the build proposal.
- Store passwords only as salted hashes using a maintained password-hashing library; never log or return passwords. Use secure session cookies, login rate limits and generic authentication errors.
- Email verification and password recovery are deferred from the first release by learner decision. Registration/sign-in do not depend on email verification. A business profile is distinct from the login identity. Treat email as unverified; it does not prove ownership or authorize future account linking.
- Google sign-in and other identity providers are deferred. Keep identity records separate from business profiles so later providers can be linked without losing profiles or saved ads; do not auto-link accounts solely on an unverified email match.
- Expired sessions allow reauthentication without exposing another user's work.

Acceptance: user A cannot list, edit, download or publish user B's data by guessing identifiers. A returning user can recover their own profile and ads after logout/login.

## R1a — Deferred verification and recovery

First release intentionally excludes verification emails, resend-verification controls, Forgot password, reset links and transactional email integration. Registered users can sign in without verifying their email and use the app normally.

- Do not show nonfunctional verification/recovery controls or promise email-based recovery.
- Keep password hashing, secure sessions, login rate limits and ownership enforcement required.
- Email addresses remain unverified and must not establish ownership of an external account or be used for automatic Google-account linking later.
- Password recovery remains deferred internally; no registration notice about it is required. An administrative recovery process has not been agreed and is not implied.
- Design account identity records so verification and recovery can be added later without replacing business profiles or saved ads.

Acceptance: registration and sign-in work without email delivery; no verification gate blocks ad creation or publishing; no unusable Forgot password action appears. Account isolation and password security checks remain required.

## R2 — Business profile and defaults

Fields: required business name and at least one contact method; optional address and logo; default Amharic/English language and one existing theme. Keep the current limit of four contacts initially unless explicitly revised.

- Create, view and edit the profile in Settings or Business Profile.
- Validate logo uploads by decoded image format/size; define a logo-specific limit before implementation. Support replacing/removing the logo.
- New ads copy current profile defaults into an editable draft.
- Ad-specific overrides do not silently update the profile. Saving a profile remains an explicit action.
- Profile changes affect future drafts. Existing saved ads retain the business snapshot used to create them.
- Optional logo is composed as an exact image asset by the renderer, with contain sizing and no distortion; do not rely on the image model to reproduce branding. Verify that it appears in both preview and export.
- Missing optional address/logo is omitted cleanly. Keep product price and description per-ad.

Acceptance: save a phone and Telegram contact once; both appear in the next ad form. Change one contact for that ad and confirm the profile and older saved ads stay unchanged. Replace the profile logo and confirm only future ads default to the replacement.

## R3 — Durable ad library

- Store original uploaded photo, generated text-free artwork, image text, independent social caption, product facts, business snapshot, selected theme, timestamps and owner.
- Persist successful generation before presenting it as durably saved. Show a distinct unsaved/save-failed state if storage fails; retain the result for retry/download without regenerating.
- Save edits with visible Saving / Saved / Could not save states. Proposed: debounced saving plus an explicit retry; never claim success before acknowledgement.
- My Ads lists thumbnail, product name and last-updated time; supports opening, editing, downloading and confirmed deletion.
- Preserve exact final export bytes for a saved revision as well as editable source assets. Renderer version helps explain changes after later layout upgrades.
- Reload or service restart must not erase saved ads. Refreshing during an in-flight generation requires a separate job-resumption decision; persistence does not automatically solve this.
- Saved ads expire after seven days. Confirmed rule: seven days from successful generation, with an immutable `expires_at`; edits, downloads and publishing do not extend the deadline. Show the deadline in My Ads and on the result screen.
- At expiration, deny access and new publishing immediately; a cleanup job deletes the original product upload, generated artwork, exported revisions and editable ad content from MinIO/database. Cleanup retries safely if storage is unavailable.
- Business profile, profile logo and social connection remain available until changed/deleted by the owner; the seven-day rule applies to ads, not reusable business data.
- Expiration does not delete posts already published on Telegram. Keep only minimal publishing audit metadata under a separately defined retention policy; do not retain expired image/caption content accidentally in task payloads or logs.
- Block new publishing when an ad has expired; recheck before worker submission. Define handling for a provider request already in flight at expiration.
- Set storage quotas and document backup/versioned-object deletion behavior before release; a live-system expiry is not automatically proof that every backup copy is erased.

Acceptance: generate, edit, save, refresh and sign in again: artwork, theme, caption and business snapshot survive before expiration. Restart services and repeat. A save failure must not produce a falsely Saved entry. At the seven-day deadline, library/download/publish access is denied even if cleanup is delayed. Cleanup removes all ad asset revisions; profile/logo remain. External social posts remain unless separately deleted on their platform.

## R4 — Connected social destinations

- Connections are distinct from profile contact handles. Typing a Telegram or Instagram username is not authorization to publish.
- Use each platform's supported authorization/setup flow; show connected destination name, readiness, expiration and disconnect action.
- Store secrets/tokens only on the backend, encrypted at rest; keep them out of browser responses and logs. Choose key management before release.
- Initial authorization may require leaving the app temporarily for platform login/consent; subsequent publishing should start inside PostReady Studio.
- Check actual account eligibility, permissions, media requirements and app review requirements before advertising an integration as supported.

Acceptance: a displayed contact handle cannot be used to publish without connection verification. Expired/revoked access shows Reconnect and preserves the ad. Disconnect prevents further use of the connection.

## R5 — Publish a saved revision

- Select destination(s), display exact final image and independent social caption, and explicitly confirm Publish now.
- Freeze a revision of image/caption/account for each attempt. Edits made after confirmation do not change an in-flight post.
- Validate each platform's image format/dimensions, caption limits and required metadata; explain unsupported content before sending. Do not silently truncate text.
- Show queued, publishing, published, failed or outcome-unknown status as appropriate. Poll provider processing when needed; acceptance of an upload alone is not proof of publication.
- Disable duplicate clicks and persist an idempotency key/publishing attempt. Reconcile uncertain outcomes before retrying to avoid duplicate public posts.
- Track attempts per destination. One platform failing must not hide another platform's success.
- Record provider post ID and link when supplied. Retrying a failed post reuses the confirmed revision unless the user explicitly chooses an updated one.
- Download stays available even when a platform is disconnected or temporarily unavailable.

Acceptance: double-click publishes once. A timeout after provider acceptance is shown as uncertain and reconciled. A failed destination can retry without reposting to successful destinations. Changing the caption after publishing leaves the published history tied to its original revision.

## Platform discovery — checked 2026-10-09

- **Telegram, first integration direction:** Bot API supports sending photos and captions. Target a verified business channel with the bot granted appropriate posting rights; this is bot-mediated channel publishing, not posting as an arbitrary personal account. Use an app-managed bot as the proposed simplest onboarding: owner adds it to their business channel with permission to post. Verify the PostReady owner controls the channel with a short-lived linking challenge completed through a platform-authenticated interaction; a supplied handle alone is insufficient. The final verification flow is an implementation spike. No personal Telegram account password or session credential is collected. Source: https://core.telegram.org/bots/api#sendphoto and https://core.telegram.org/bots/api#chatmemberadministrator
- **Instagram:** investigate professional-account eligibility, supported login flow, publishing permissions, review requirements and accessible media delivery. Meta's official publishing page could not be fetched during this planning pass, so exact current requirements are an unresolved spike rather than a committed design. Reference: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/content-publishing
- **TikTok:** Direct Post requires registered app setup and authorization; unaudited clients have visibility restrictions, with an audit required to lift them. Verify photo-post support and required UX for this product before selecting it for the first release. Sources: https://developers.tiktok.com/docs/en/content-posting-api-get-started and https://developers.tiktok.com/docs/en/content-sharing-guidelines

Platform policies must be rechecked when implementing. Do not assume a successful developer-account test establishes eligibility to publish for public users.

## Technical direction to evaluate

Keep Next.js and FastAPI. Add a durable database for users/profiles/ad metadata and MinIO for private image storage (confirmed). PostgreSQL was approved for durable records. Keep MinIO credentials on the backend, use private buckets and ownership-checked downloads or short-lived signed URLs whose validity cannot exceed the ad deadline. Run an application cleanup worker for metadata and objects; MinIO lifecycle policies can be supplementary protection but do not replace exact application expiry checks. Store logos separately from expiring ad assets. Evaluate the VPS against disk durability, backups and restore requirements.

A Celery worker with Redis can handle publishing and resumable generation, matching the originally discussed preference. Add it when persistent jobs are introduced; queue acknowledgement and results still need durable application records.

Proposed entities: User, BusinessProfile, Asset, Ad, AdRevision, SocialConnection, PublishAttempt. Profile defaults are copied into an ad snapshot; revisions reference exact assets and text; publish attempts reference an immutable revision and destination. Backend renders or verifies the final publishing asset rather than accepting arbitrary inaccessible browser-local URLs.

Public hosting, HTTPS and platform callback URLs may be required for real connections. Choose the Cloudflare/VPS deployment approach before public-user integration tests. Do not expose the local Gemini endpoint publicly without authentication, per-user generation limits and appropriate cost controls.

## Ordered implementation todos

### 0. Resolve the minimum product and integration decisions

- [x] Choose username/email plus password for initial sign-in; defer Google and other providers.
- [x] Defer email verification and password recovery from the first release (latest learner decision).
- [x] Confirm one business per account and username/email/password/confirmation registration. Users can use the app without email verification.
- [x] Choose the easiest initial integration direction: Telegram business-channel publishing via granted bot access.
- [ ] Confirm the initial business owners have channels and validate the linking/permission flow with a controlled channel.
- [ ] Verify that platform's app setup, permissions, supported media and review path with a controlled test account/channel.
- [x] Choose MinIO for image storage and seven-day ad retention.
- [x] Confirm the expiry clock: seven days from successful generation, with no extension on edits.
- [ ] Choose database, backup retention and storage quotas.
- [ ] Decide whether interrupted generation must resume in this release.

### 1. Returning owner can save and reuse a profile

- [ ] Implement authenticated sessions, persistence migrations and ownership enforcement.
- [ ] Keep registration focused on account creation; omit deferred email-verification and password-recovery controls and notices.
- [ ] Verify password hashing, session handling, login throttling and account isolation without an email-verification gate.
- [ ] Build profile create/edit with multiple contacts, address, logo and language/theme defaults.
- [ ] Prefill new ad drafts and allow local overrides.
- [ ] Add exact logo composition to preview/export.
- [ ] Verify restart persistence, defaults/overrides, optional fields and two-user isolation.

### 2. Owner can reopen a saved advertisement

- [ ] Save generation assets/facts and immutable profile snapshot.
- [ ] Build My Ads and reopen/edit/save/download flows.
- [ ] Handle saving failures, edit conflicts and stale saves visibly.
- [ ] Store final export revisions and verify rendering consistency in both languages.
- [ ] Add MinIO persistence with separate profile-logo and ad-asset ownership.
- [ ] Display seven-day expiry, enforce it on every access path, and implement retryable deletion of expired ad content/assets.
- [ ] Test the exact deadline, signed URL expiry, delayed cleanup, multiple asset revisions and preserved profile logos.
- [ ] Verify browser reload, service restart, failed storage writes and unauthorized asset access.

### 3. Owner can connect and publish to one destination

- [ ] Implement chosen platform connection and server-only credential storage.
- [ ] Build preview/confirmation and platform-specific validation.
- [ ] Add durable publishing attempts, worker execution where needed, status reconciliation and duplicate prevention.
- [ ] Implement reconnect/disconnect and truthful failure/unknown states.
- [ ] Verify with a controlled destination, including revoked permissions and timeout-after-acceptance.
- [ ] Complete required platform reviews before enabling public-user publishing.

### 4. Prepare a limited user release

- [ ] Deploy with HTTPS and working callbacks; verify backup restore and logging redaction.
- [ ] Set generation/storage/publishing limits and visible user-facing errors.
- [ ] Test the complete mobile journey with a small group of Ethiopian business owners.
- [ ] Resolve usability feedback and verify account/data deletion.
- [ ] Add the next platform only after the first works reliably for real users.

## Deferred

Email verification, password recovery, transactional email integration, Google sign-in and other identity providers, scheduled posts, campaign analytics, team roles, multiple businesses per owner, bulk generation, paid ads, automatic cross-posting without confirmation, and automatic editing/deleting of already-published posts. These can be reconsidered after the core returning-owner and publish-now flows work.

## Decisions to settle next

Confirm registration fields. Email verification and password recovery are deferred; no email provider or token policy is needed for this release. Decide logo default inclusion, quotas and backup retention. Does generation need to continue if the browser closes?

Success means an owner enters business details once, returns to previously saved ads, and reliably publishes an explicitly reviewed ad to a supported destination.

## Decision log — 2026-10-09

- Learner requested the easiest platform integration, using login/authorization or granted account access. Telegram channel publishing is the selected planning direction because bot posting permission is a smaller initial integration than multi-platform publishing; platform-authenticated channel ownership verification is still required.
- Learner selected MinIO for storage.
- Learner selected seven-day ad retention. Reusable profiles/logos are treated separately. The expiry clock was confirmed on 2026-10-10.

- 2026-10-10: Learner confirmed expiration seven days after successful generation; editing does not renew the deadline.

- 2026-10-10: Learner selected username/email plus password for initial login. Google sign-in and other options are deferred to future versions.

- 2026-10-10: Learner confirmed email verification and password recovery are essential first-release features. Delivery provider and exact access/token defaults remain open.

- 2026-10-10 (supersedes earlier decision): Learner deferred password recovery and email verification from the first release. Removed their implementation tasks and verification gate; retained core authentication security and recorded the lack of recovery.

- 2026-10-10: Learner requested no forgotten-password notice in registration. Recovery remains deferred in the internal roadmap.

- 2026-10-10: Learner approved the technical proposal, PostgreSQL, initial account/profile defaults and three-slice build order.
