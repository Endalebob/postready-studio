---
doc: post-mvp-spec
status: approved
---

# PostReady Studio — first-release technical plan

## Proposed stack

Retain Next.js, FastAPI and Docker Compose. Add PostgreSQL (requires learner agreement) for durable ownership/session/profile/ad/job records; MinIO (confirmed) for private image assets. Use SQLAlchemy and migrations for schema evolution; choose compatible pinned versions during implementation. Add Redis/Celery for durable-work orchestration when cleanup/publishing is implemented, using the learner's original worker preference. Application database records remain authoritative for job outcomes.

## Initial product defaults for approval

One owner and one business per account. Registration requires username, email, password and confirmation; sign-in accepts username or email. No verification/recovery UI or notices. Optional logo and address; include the uploaded logo in new ads by default, with an ad-specific opt-out. Generation initially remains a foreground request; resumable generation is deferred. These defaults were approved before implementation.

## Accounts and profiles

Database: users with normalized unique usernames/emails and Argon2 password hashes; hashed opaque session tokens with expiry/revocation; profiles keyed by owner with contacts/address/language/theme/logo asset reference. Use HttpOnly session cookies, secure in HTTPS deployment, same-origin mutation checks/CSRF protection, login rate limits and generic errors. Every query and asset route enforces owner scope. Credentials stay on the backend.

Introduce /auth/register, /auth/login, /auth/logout, /auth/me and /profile routes. Keep future social identity linking separate from the business profile. Do not treat an unverified email as ownership proof. Existing generation becomes authenticated. Tests must cover direct unauthorized calls, not just hidden navigation.

MinIO uses private buckets and persistent Docker volumes. Validate logo content/size, serve through an authorized endpoint, and compose the exact logo in the shared renderer. New drafts copy profile values into a snapshot; editing the draft never mutates the profile. Avoid broken logo references in older ads when profile logos are replaced.

## Saved ads and expiration

Records reference original photo, generated artwork, business/logo snapshot, details, separate copy fields, renderer version and revisions. expires_at is fixed at successful generation plus seven days. Save current rendered PNG for each committed revision; preserve editable source assets. Use optimistic revision checks to reject stale concurrent saves.

Persist generation output before claiming Saved; return a recoverable unsaved result on storage failure. Explicit Save is the initial implementation choice for deterministic UX; automatic saving can be added after conflict/error behavior is proven. Library supports open, save, download and confirmed delete.

Owner and expiry checks apply to library, detail, download, image and publish routes. Authorize before reading MinIO objects. Do not expose long-lived object URLs. Scheduled cleanup deletes all expired ad assets/content with retryable progress; profile logos remain. Shared snapshot assets need reference-aware cleanup. Test boundary time using an injected clock.

## Telegram

Use an app-managed bot configured in ignored server environment. Choose a platform-authenticated channel-linking challenge, prove channel ownership/admin status, and check bot posting rights; a handle alone is insufficient. Determine polling versus webhook only after the local deployment/callback decision. No token or personal Telegram credential is requested in chat.

Publishing operates on an immutable saved revision after preview and explicit confirmation. Persist an attempt with a unique idempotency key before sending. Use states queued/publishing/published/failed/unknown; Telegram timeouts can be ambiguous, so do not automatically repeat potentially accepted requests. Record returned message ID and link where available. Validate caption/media limits from current official API documentation during implementation. Enforce expiry before provider submission, and disconnect stops future work.

## Local run and external dependencies

Compose will add database, MinIO and later worker/broker services, with named volumes. Local settings remain in ignored .env; .env.example contains only empty placeholders or safe nonsecret defaults. Keep existing app ports and avoid unrelated running services. No public deployment is authorized by this build plan.

Real Telegram linking/publishing requires a configured bot and controlled channel. Implement and test locally with provider doubles first; live proof waits for the learner to configure these outside chat. No claim of working integration until real linking and publishing are verified.

## Verification

Run builds/type checks and backend tests per slice. Test auth isolation with two users, persistence across restart, profile defaults/overrides, exact logo composition and both language exports. Exercise storage failure, revision conflict and exact seven-day deadline. Telegram checks include channel ownership, revoked rights, duplicate submission and uncertain provider outcome. Hands-on review after profiles and after the complete flow.

- 2026-10-10: Learner approved the technical proposal, PostgreSQL, initial account/profile defaults and three-slice build order.
