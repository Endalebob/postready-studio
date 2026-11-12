---
doc: scheduled-campaigns-plan
status: proposed
updated: 2026-11-12
---

# PostReady Studio — scheduled campaigns and social insights plan

## Purpose

Add an optional campaign system that lets an authenticated business owner:

1. Upload and approve a persistent gallery of product images and facts.
2. Choose a social destination, posting schedule, language and campaign instructions.
3. Let PostReady select an eligible gallery item and prepare a post.
4. Review every post, or explicitly authorize automatic publishing for one campaign.
5. Pause, cancel and inspect upcoming posts.
6. View truthful provider-supported performance metrics.
7. Receive AI-written summaries only when they are grounded in collected metrics or comments.

Telegram is the first publishing provider because the existing application already supports verified Telegram channel connections and durable publication attempts. The design must allow additional providers later without pretending that all social platforms have identical authentication, content limits or analytics.

This work extends the current application. It does not replace the existing ad editor, renderer, saved-ad library, Telegram safety rules, Celery workers or provider integrations.

## Approved product decisions

- Generated advertisements expire 30 days after generation instead of seven days.
- Editing or saving an advertisement does not extend its original expiration.
- Gallery items are persistent until the owner deletes them, deletes the account or a future retention policy is explicitly accepted.
- Every gallery item is private and must be explicitly approved by its owner before campaign use.
- Telegram is the first complete provider implementation.
- Social publishing uses a provider interface so other platforms can be added independently.
- Review-every-post is the default approval mode.
- Auto-publish is an explicit per-campaign user setting.
- The AI model cannot enable auto-publish, modify consent or bypass approval.
- A campaign must complete a manually reviewed test post before auto-publish can be enabled.
- The existing rule for uncertain provider outcomes remains: never submit an automatic retry when the provider may already have accepted the post.

## Product boundary

PostReady should automate preparation and scheduling while keeping authorization and side effects under deterministic application control.

AI may:

- Rank a bounded set of eligible gallery items.
- Explain why an item fits the campaign.
- Generate validated English or Amharic advertisement copy.
- Generate or edit artwork through the configured provider.
- Summarize measured post performance.
- Classify retrieved comments by sentiment when the data source and sample are disclosed.

AI must not:

- Choose images outside the owner-approved candidate set.
- Invent prices, discounts, contacts, addresses, stock status or product claims.
- Turn on automatic publishing.
- Change the social destination.
- Read arbitrary storage objects.
- Publish directly to a provider.
- Retry an uncertain publication.
- Claim views, reactions, comments, reach or sentiment that were not collected.

The backend remains authoritative for ownership, eligibility, scheduling, consent, costs, content validation, idempotency and provider submission.

## Scope

### First complete release

- Increase generated-ad expiration to 30 days.
- Persistent owner-scoped product gallery.
- Gallery create, edit, approve, deactivate and delete operations.
- Campaign create, edit, pause and resume operations.
- Daily, weekly and selected-weekday schedules.
- IANA timezone and local posting time.
- Telegram destination selection.
- English or Amharic campaign language.
- Review-every-post and auto-publish approval modes.
- Upcoming-post queue.
- Generation approximately 24 hours before the planned publication.
- Cancellation before provider submission.
- Existing truthful publication statuses: queued, publishing, published, failed and unknown.
- Campaign history and basic operational counts.

### Later releases

- Additional social providers.
- Provider-supported engagement collection.
- Cross-post and campaign comparisons.
- Comment retrieval where officially supported and authorized.
- Sentiment summaries grounded in retrieved comments.
- Posting-time and content recommendations grounded in sufficient historical data.

### Explicit non-goals for the first release

- Arbitrary cron expressions.
- Multiple posts per campaign per day.
- Automatic paid promotion or advertisement buying.
- Autonomous replies to social comments.
- One model call with unrestricted access to every gallery image.
- Multi-agent orchestration.
- MCP servers for internal PostReady modules.
- Scraping private social data.
- Claiming that a Telegram view counter represents unique people.
- A single generic analytics promise across all providers.

## User journeys

### 1. Create the persistent gallery

1. The owner opens Campaign Gallery.
2. The owner uploads a product image.
3. PostReady applies the existing image size, type and decompression checks.
4. The owner supplies or confirms:
   - Product name
   - Description
   - Current price
   - Optional old price
   - Contacts
   - Optional address
   - Preferred language
   - Optional campaign notes
5. The owner previews the item and selects “Approve for campaigns.”
6. PostReady stores the normalized image privately in MinIO and its validated facts in PostgreSQL.
7. The item becomes eligible for campaign selection.

Unapproved and inactive items are never supplied to the model as candidates.

### 2. Create a campaign

The owner selects:

- Campaign name
- Social provider
- Verified destination
- Gallery items or “all approved items”
- Daily, weekly or selected weekdays
- Local posting time
- IANA timezone
- English or Amharic
- Theme
- Campaign instructions
- Maximum generation budget, when paid generation is involved
- Review-every-post or auto-publish

New campaigns start paused or in review mode. Before auto-publish becomes available, the owner must generate, review and successfully publish one test post to the selected destination.

### 3. Prepare an upcoming post

Approximately 24 hours before publication:

1. Celery finds the due campaign.
2. The backend locks the campaign row.
3. The backend creates one idempotent scheduled-post record.
4. The backend builds the eligible candidate list.
5. The bounded AI planner chooses one candidate from that list.
6. PostReady validates the returned gallery ID.
7. Copy and artwork are generated using canonical gallery and profile facts.
8. The existing deterministic renderer creates the final PNG.
9. The generated advertisement is stored with its fixed 30-day expiration.
10. The scheduled post stores the exact ad revision, caption, destination, publication time and approval-mode snapshot.

Generation failure must not silently publish an older or unrelated post. The scheduled post becomes failed or skipped with a user-readable reason.

### 4. Review-every-post mode

1. The prepared post appears in Upcoming with image, caption, destination and time.
2. The owner may edit through the existing ad editor.
3. Saving creates a new immutable ad revision.
4. The owner approves the exact revision for the scheduled post.
5. At publication time, PostReady confirms that the approved revision, connection and destination are unchanged.
6. The publication is queued.

Changing the ad after approval invalidates the previous approval and returns the scheduled post to awaiting approval.

### 5. Auto-publish mode

Auto-publish represents campaign-level human authorization, not AI authorization.

To enable it, the owner must:

- Have an active verified destination.
- Complete a successful manually reviewed test post.
- Review a clear disclosure of frequency, destination and eligible gallery scope.
- Confirm the setting explicitly.

The database records the consent timestamp and policy version. The model cannot access a tool that modifies these values.

When auto-publish is enabled, a prepared post may move directly from ready to queued only when all policy checks pass. It must still appear in Upcoming during the preparation window so the owner can cancel it.

Disabling auto-publish:

- Takes effect immediately for posts not yet submitted.
- Cancels or returns eligible upcoming posts to awaiting approval.
- Cannot guarantee cancellation after a provider request has started.
- Must never trigger a retry of an unknown publication.

Material campaign changes should invalidate auto-publish consent. At minimum:

- Destination change
- Provider change
- Frequency increase
- Gallery scope expansion
- Campaign ownership change
- Consent-policy version change

### 6. Pause or delete

Pausing a campaign prevents new scheduled posts and cancels future posts that have not entered provider submission.

Deleting a campaign:

- Stops future runs.
- Cancels unsubmitted posts.
- Preserves historical publication records needed for truthful status and auditing.
- Does not automatically delete shared gallery items.

Deleting a gallery item:

- Removes it from future selection immediately.
- Cancels upcoming posts that depend on it unless they have already entered publication.
- Deletes its private source after references are resolved.
- Does not remove social posts that were already published.

## Architecture

### Responsibility split

Use each component for one clear purpose:

- **FastAPI:** authenticated commands, validation, ownership, consent and API responses.
- **PostgreSQL:** authoritative gallery, campaign, scheduled-post, approval and metric state.
- **MinIO:** private persistent gallery images and generated assets.
- **Celery Beat:** periodic discovery of due campaign work.
- **Celery workers:** preparation, provider submission and metric collection.
- **Redis:** Celery broker; not authoritative application state.
- **LangChain/LangGraph:** bounded AI selection and preparation workflow.
- **Existing renderer:** exact text, price, contacts and logo composition.
- **Social provider adapters:** external API validation, publication and supported metrics.

Do not use LangGraph as a cron scheduler, durable media store or replacement for PostgreSQL/Celery.

### Proposed execution flow

```text
Celery Beat
    -> scan due campaigns
    -> claim campaign with a database lock
    -> create idempotent scheduled post
    -> enqueue preparation task

Preparation worker
    -> load owner/profile/campaign/gallery facts
    -> filter eligible candidates deterministically
    -> invoke bounded selection and generation workflow
    -> validate structured output
    -> render and persist exact revision
    -> awaiting_approval OR ready_for_auto_publish

Publication worker
    -> reload campaign, consent, scheduled post and destination
    -> verify exact revision and provider limits
    -> create durable publication attempt
    -> submit once
    -> published, failed or unknown
```

### Why one bounded agent is enough

The first release does not need multiple agents. Selection and copy preparation are one focused task with a small tool set.

Suggested tools:

- `list_eligible_assets(campaign_id)`
- `get_recent_campaign_posts(campaign_id)`
- `get_business_profile()`
- `prepare_post(asset_id, instructions)`

The model should not receive:

- A publish tool
- A consent-management tool
- Raw database access
- Arbitrary MinIO keys
- User credentials or provider tokens

The backend validates that the selected asset ID was one of the candidates supplied for that exact run.

### LangGraph adoption

The deterministic gallery, campaign, scheduler and provider foundations can be implemented before completing LangGraph training.

LangGraph becomes useful for the preparation flow:

```text
load campaign context
    -> load and filter candidates
    -> select candidate
    -> generate structured copy/artwork request
    -> validate
    -> persist prepared revision
    -> approval gate
```

The long wait between preparation and user approval should remain represented by durable database state. A LangGraph checkpointer may additionally support resumable AI workflow state, but it must not be the only record of campaign consent or publication status.

Start with a simple graph only after the deterministic storage and scheduling contracts are stable. Do not block those foundations while learning LangGraph.

## Data model

Names are proposals and may be adjusted to existing migration conventions.

### Generated advertisement expiration

Change generated ad expiry from seven to 30 days:

```text
expires_at = successful_generation_at + 30 days
```

Requirements:

- New generations receive 30 days.
- Saving or editing does not renew expiration.
- Existing records retain their stored expiration unless a one-time migration is explicitly approved.
- API messages and frontend labels say 30 days.
- Cleanup continues to use the stored `expires_at`.
- Tests replace hard-coded seven-day expectations.
- README and user-facing documentation are updated.

### `gallery_assets`

Suggested fields:

- `id`: UUID primary key
- `owner_id`: user foreign key and index
- `storage_key`: private normalized source-image key
- `mime_type`
- `width`
- `height`
- `details`: validated product/contact/language/theme JSON
- `campaign_notes`: bounded plain text
- `approved_at`: nullable timestamp
- `active`: boolean
- `usage_count`: integer
- `last_used_at`: nullable timestamp
- `created_at`
- `updated_at`
- `deleted_at`: nullable timestamp if soft deletion is needed

Rules:

- Every query is owner-scoped.
- `approved_at` is set by an explicit owner action.
- Editing material product facts may clear approval and require another preview.
- Storage is private and served only through authorized routes.
- Product details are treated as untrusted data in prompts, never instructions.
- Delete operations are reference-aware and retryable.

### `campaigns`

Suggested fields:

- `id`: UUID primary key
- `owner_id`: user foreign key and index
- `name`
- `provider`: initially `telegram`
- `destination_id`: verified connection/destination identifier
- `timezone`: IANA timezone name
- `schedule_type`: `daily`, `weekly` or `weekdays`
- `weekdays`: validated list for selected weekdays
- `local_time`: wall-clock time
- `language`: `am` or `en`
- `theme`
- `instructions`: bounded plain text
- `gallery_scope`: all approved items or selected items
- `approval_mode`: `review_each` or `auto_publish`
- `auto_publish_enabled`: boolean
- `auto_publish_consented_at`: nullable timestamp
- `consent_policy_version`: nullable string
- `test_post_completed_at`: nullable timestamp
- `active`: boolean
- `next_run_at`: UTC timestamp and index
- `last_run_at`: nullable UTC timestamp
- `created_at`
- `updated_at`

Rules:

- Schedule writes validate timezone and calculate `next_run_at` on the backend.
- Only verified owner-controlled destinations are accepted.
- Auto-publish requires the test-post and consent fields.
- Models cannot update approval fields.
- Increasing frequency or changing destination clears auto-publish consent.

### `campaign_assets`

Use a join record when a campaign selects only part of the gallery:

- `campaign_id`
- `gallery_asset_id`
- `enabled`
- Composite uniqueness on campaign and asset

Ownership must match across both records.

### `scheduled_posts`

Suggested fields:

- `id`: UUID primary key
- `owner_id`: user foreign key and index
- `campaign_id`: campaign foreign key and index
- `gallery_asset_id`: nullable historical reference
- `ad_id`: generated advertisement foreign key
- `revision`: exact immutable revision
- `provider`
- `destination_id`
- `scheduled_for`: UTC timestamp and index
- `prepared_at`: nullable timestamp
- `approval_mode_snapshot`
- `approved_at`: nullable timestamp
- `approved_revision`: nullable integer
- `status`
- `failure_code`: nullable bounded code
- `failure_detail`: nullable safe message
- `publish_attempt_id`: nullable unique reference
- `idempotency_key`: unique
- `created_at`
- `updated_at`

Suggested statuses:

- `preparing`
- `awaiting_approval`
- `ready`
- `queued`
- `publishing`
- `published`
- `failed`
- `unknown`
- `cancelled`
- `skipped`

Use one unique occurrence key per campaign and planned time. Repeated Celery scans must return the same scheduled post rather than create duplicates.

### `post_metric_snapshots`

Suggested fields:

- `id`
- `owner_id`
- `scheduled_post_id`
- `provider`
- `provider_message_id`
- `collected_at`
- `views`: nullable integer
- `reactions`: nullable structured data
- `forwards`: nullable integer
- `comments`: nullable integer
- `raw`: bounded provider response needed for audit/debugging

Missing provider metrics remain `null`, not zero.

Do not label a Telegram view counter as unique reach.

### Optional `comment_insights`

Add only after comment retrieval is proven:

- `scheduled_post_id`
- `window_start`
- `window_end`
- `comment_count`
- `language_distribution`
- `positive_count`
- `neutral_count`
- `negative_count`
- `uncertain_count`
- `summary`
- `model`
- `created_at`

Store aggregate insight by default. Retaining raw commenter identity or text requires a separate privacy and retention decision.

## Scheduling semantics

### Supported schedules

First release:

- Daily at one local time
- Weekly on one weekday at one local time
- Selected weekdays at one local time

Do not expose raw cron syntax initially.

### Timezones and daylight saving

- Store an IANA timezone such as `Africa/Addis_Ababa`.
- Store the user’s local posting time separately.
- Store `next_run_at` in UTC.
- Recalculate the next UTC occurrence from timezone and wall-clock rules after each run or schedule edit.
- Define behavior for ambiguous or missing daylight-saving times in tests.

### Due-work scanning

Celery Beat may run a small scanner every minute. The scanner:

1. Selects active campaigns where `next_run_at` is within the preparation window.
2. Uses row locking and `skip_locked` to prevent duplicate claims.
3. Creates the occurrence idempotently.
4. Advances `next_run_at`.
5. Enqueues preparation.

The scanner should remain fast and must not call AI providers directly.

### Preparation window

Default proposal: prepare 24 hours before publication.

Benefits:

- The owner can inspect Upcoming.
- Provider generation outages have time to recover.
- Invalid gallery facts can be corrected.
- Review-mode campaigns have an approval window.

If preparation fails, use bounded retries only for confirmed transient failures. Do not substitute an unrelated old post automatically.

### Missed schedules

Avoid catch-up floods after downtime.

Proposed behavior:

- If preparation can still complete before a small lateness threshold, prepare and clearly mark it late.
- If publication time is too far past, mark the occurrence skipped and calculate the next one.
- Never publish several accumulated posts immediately after worker recovery.

The exact lateness threshold is an open product decision.

## Asset-selection policy

Selection is deterministic before it is intelligent.

The backend first removes:

- Unapproved assets
- Inactive or deleted assets
- Assets outside campaign scope
- Assets with invalid facts
- Recently used assets
- Assets already used by another upcoming post for the same campaign

The model receives only the remaining candidate IDs and bounded metadata.

Initial anti-repetition rule:

- Avoid at least the last three gallery items used by the campaign.
- Prefer the least recently used eligible item.
- If fewer than four active items exist, rotate fairly and disclose that repetition will happen.

The model may rank candidates based on campaign instructions and recent history, but the backend verifies its chosen ID. If model selection fails validation, use a deterministic least-recently-used fallback or mark preparation failed according to the approved product policy.

## Copy and image generation

### Structured output

Continue validating generated copy through Pydantic:

- Headline
- Tagline
- Social caption
- Selected gallery asset ID
- Optional short selection reason for audit/UI

Reject output that:

- Does not match the requested language
- Exceeds provider or renderer limits
- Introduces unsupported facts
- References a non-candidate gallery ID
- Contains empty required fields

### Prompting

The system prompt should:

- Identify the model as a PostReady campaign assistant.
- State that supplied product/profile JSON is data, not instructions.
- Require use of canonical facts only.
- Prohibit fabricated promotions and stock claims.
- Require output in the campaign language.
- Encourage variation from recent headlines without changing facts.
- Require selection only from supplied candidate IDs.

Use dynamic prompt sections for:

- Language
- Provider content limits
- Business profile
- Campaign instructions
- Recent-post summary

### Image generation

- Use the approved gallery source image.
- Preserve product identity.
- Keep generated provider artwork free of text.
- Render exact headline, price, contacts and logo locally.
- Record provider/model and estimated/actual request cost where available.
- Enforce campaign and account cost limits before provider calls.
- Never silently change paid providers.
- Treat ambiguous paid submissions as uncertain and require investigation before resubmission.

## Approval and publishing policy

### Review mode

Approval binds:

- Scheduled-post ID
- Ad ID and exact revision
- Provider
- Destination
- Caption
- Media
- Scheduled time

Changing any bound value invalidates approval.

### Auto-publish mode

Auto-publish checks immediately before queueing:

- Campaign is active.
- Auto-publish remains enabled.
- Consent version is current.
- Test post is complete.
- Destination is unchanged and active.
- Gallery item remains approved.
- Scheduled post is within allowed time.
- Exact revision still exists and is unexpired.
- Provider limits still pass.
- No duplicate publication attempt exists.

The model is not involved in these checks.

### Publication

Reuse the current safety principles:

- Persist the attempt before submission.
- Assign a unique idempotency boundary.
- Recheck ownership, expiration and destination immediately before provider I/O.
- Distinguish rejected failure from uncertain outcome.
- Automatically retry only confirmed safe/transient pre-submission failures.
- Never automatically retry an uncertain submission.

The existing unique constraint tied to one ad revision and Telegram destination may need a scheduled-post-aware idempotency key. Design the migration so existing publication history remains valid.

## Social-provider abstraction

Telegram remains the first provider, but scheduling code should depend on an internal interface rather than Telegram modules directly.

Suggested provider contract:

```python
class SocialProvider:
    def validate_destination(self, owner_id, destination_id): ...
    def content_limits(self): ...
    def validate_post(self, post_snapshot): ...
    def publish(self, post_snapshot, idempotency_key): ...
    def check_status(self, provider_reference): ...
    def collect_metrics(self, provider_reference): ...
```

Provider results should distinguish:

- Confirmed success
- Confirmed rejection
- Safe retryable failure before submission
- Uncertain outcome after possible submission

### Telegram

Reuse:

- Verified user/channel connection
- Bot posting permission checks
- Caption limit validation
- Photo publication
- Message ID and post link
- Unknown-outcome handling

Full channel analytics are not available through the current Bot API publishing integration. Official detailed Telegram statistics use MTProto APIs, require additional authentication/authorization work and may depend on channel eligibility. Treat analytics as a separate integration decision.

### Future providers

Potential providers include Meta/Instagram, LinkedIn, TikTok and others. Each must receive:

- Its own OAuth/connection flow
- Backend-only token storage
- Destination ownership/permission checks
- Content validation
- Provider-specific status handling
- Officially supported analytics
- Disconnect and token-revocation behavior

Do not force all providers into Telegram’s image/caption or metric assumptions. Use a canonical internal post draft plus provider-specific validation.

## Analytics and insights

### Release order

1. Operational analytics:
   - Prepared
   - Awaiting approval
   - Published
   - Failed
   - Unknown
   - Cancelled
2. Provider-supported engagement:
   - Views where available
   - Reactions where available
   - Forwards/shares where available
   - Comment counts where available
3. Derived comparisons:
   - Performance by gallery item
   - Performance by posting day/time
   - Performance by language/theme
4. Comment sentiment:
   - Only from retrieved comments
   - Sample size and collection window shown
   - Positive, neutral, negative and uncertain categories

### Calculation boundary

Application code calculates counts, rates and comparisons. AI explains the resulting structured measurements.

AI must not perform the authoritative arithmetic or fill missing metrics.

Every insight should identify:

- Provider
- Time window
- Number of posts
- Number of comments when sentiment is used
- Missing metrics
- Whether counts are exact or provider-estimated

Avoid recommendations until the sample is meaningful. One high-view post is not enough evidence for a general posting strategy.

### Sentiment limitations

- Sentiment requires comment text, not view counts.
- Amharic and mixed-language comments need explicit evaluation.
- Sarcasm and short emoji-only comments may remain uncertain.
- Show aggregate counts and examples only when privacy rules permit.
- Do not use sentiment to reply automatically in the first release.

## API proposal

Exact paths may follow existing router conventions.

### Gallery

- `GET /gallery`
- `POST /gallery`
- `GET /gallery/{asset_id}`
- `PUT /gallery/{asset_id}`
- `POST /gallery/{asset_id}/approve`
- `POST /gallery/{asset_id}/deactivate`
- `DELETE /gallery/{asset_id}`
- `GET /gallery/{asset_id}/image`

### Campaigns

- `GET /campaigns`
- `POST /campaigns`
- `GET /campaigns/{campaign_id}`
- `PUT /campaigns/{campaign_id}`
- `POST /campaigns/{campaign_id}/pause`
- `POST /campaigns/{campaign_id}/resume`
- `POST /campaigns/{campaign_id}/test-post`
- `POST /campaigns/{campaign_id}/enable-auto-publish`
- `POST /campaigns/{campaign_id}/disable-auto-publish`
- `DELETE /campaigns/{campaign_id}`

### Scheduled posts

- `GET /scheduled-posts?status=upcoming`
- `GET /scheduled-posts/{post_id}`
- `POST /scheduled-posts/{post_id}/approve`
- `POST /scheduled-posts/{post_id}/cancel`
- `POST /scheduled-posts/{post_id}/retry-preparation`

Provider submission retries remain restricted to confirmed failed/safe states.

### Analytics

- `GET /campaigns/{campaign_id}/analytics`
- `GET /scheduled-posts/{post_id}/metrics`
- `POST /campaigns/{campaign_id}/refresh-metrics`

Metric refresh should be rate-limited and normally performed by workers.

## Frontend proposal

### Campaign Gallery

- Private thumbnail grid
- Product facts and approval status
- Add, edit, approve, deactivate and delete
- Usage count and last-used date
- Clear explanation that approved items may be selected automatically

### Campaign setup

- Provider and verified destination
- Gallery scope
- Schedule and timezone
- Language and theme
- Campaign instructions
- Approval mode
- Cost/frequency summary
- Test-post requirement

### Upcoming posts

- Exact preview
- Caption
- Product/gallery source
- Campaign and destination
- Scheduled local time and timezone
- Awaiting approval or auto-publish status
- Edit, approve and cancel actions where allowed

### Campaign dashboard

- Active/paused state
- Next planned run
- Auto-publish status
- Recent posts and truthful delivery states
- Pause control prominently available
- Analytics only when backed by provider data

### Consent UX

Auto-publish confirmation should state:

- Destination
- Maximum frequency
- Eligible gallery scope
- Whether paid generation may occur
- How to pause
- That uncertain submissions are not repeated automatically

Do not hide consent inside general terms or preselect auto-publish.

## Security, privacy and abuse controls

- Owner-scope every gallery, campaign, post, metric and asset query.
- Authorize before reading MinIO.
- Keep provider tokens and AI keys in backend environment or encrypted server-side storage.
- Never include secrets in model prompts, traces or errors.
- Treat gallery facts, campaign instructions and comments as untrusted input.
- Keep system instructions separate from user-provided text.
- Validate every tool argument and structured model response.
- Limit candidate count, agent turns, tool calls, tokens, retries and generation spend.
- Apply upload byte, pixel and type limits.
- Rate-limit campaign creation, generation and manual metric refresh.
- Log consent and approval changes without logging secrets.
- Redact private content from tracing unless the owner explicitly opts into a safe debugging mode.
- Disconnecting a provider stops future queued submissions.
- Account deletion removes persistent gallery assets, campaign data and provider connections according to an explicit cleanup process.

## Failure behavior

### No eligible gallery item

- Mark occurrence skipped.
- Explain why.
- Do not generate or publish.
- Keep the campaign active for its next occurrence unless the owner pauses it.

### Generation failure

- Retry only bounded confirmed transient failures.
- Preserve campaign and gallery data.
- Mark failed when exhausted.
- Do not substitute an old post silently.

### Approval missing at publication time

- Do not publish.
- Mark missed or awaiting approval according to policy.
- Do not move it to the next time silently.

### Destination revoked

- Stop publication.
- Mark failure clearly.
- Disable or flag the destination.
- Pause affected campaigns or require reconnection.

### Worker restart

- Recover from PostgreSQL state.
- Do not create duplicate occurrences.
- Resume safe preparation work.
- Convert stale in-flight publication attempts to unknown when submission may have happened.

### Provider timeout

- If failure occurred before submission, retry under the bounded policy.
- If the provider may have accepted the request, mark unknown.
- Require the owner to inspect the destination.
- Never automatically resend.

## Observability

Record:

- Campaign run ID
- Scheduled-post ID
- Provider and destination ID
- Selected gallery item ID
- AI model and provider
- Tool calls and validation failures
- Generation duration and cost where available
- Approval mode and consent-policy version
- Publication status transitions
- Metric collection status

Do not record:

- Passwords
- Session tokens
- Telegram bot tokens
- OAuth tokens
- MinIO credentials
- Full private asset content in normal logs

LangSmith may trace the AI preparation workflow after redaction. PostgreSQL remains authoritative for product state and publication outcomes.

## Implementation slices

### Slice 0 — 30-day advertisement expiration

Becomes usable: Generated ads remain available for 30 days.

Build:

- Change generation expiry calculation.
- Update UI text, README and tests.
- Preserve stored deadlines for existing ads unless migration is separately approved.

Verify:

- New generation receives exactly 30 days.
- Save/edit does not extend expiration.
- Access is denied at the boundary.
- Cleanup removes expired ads and retains persistent gallery assets.

### Slice 1 — persistent approved gallery

Becomes usable: Owners can create a private reusable product library.

Build:

- Migration and owner-scoped model.
- Private MinIO storage.
- Gallery API and UI.
- Validation, approval, deactivation and deletion.

Verify:

- Two-user isolation.
- Restart persistence.
- Approval required for eligibility.
- Delete/reference cleanup.
- English and Amharic product facts.

Learner review:

- Upload several products.
- Approve some and leave one unapproved.
- Confirm only approved items become eligible.

### Slice 2 — Telegram campaign with review mode

Becomes usable: A weekly campaign prepares an upcoming Telegram post for approval.

Build:

- Campaign and campaign-asset records.
- Schedule calculations.
- Due scanner and idempotent occurrence creation.
- Bounded selection/preparation workflow.
- Upcoming queue.
- Approval bound to exact revision.

Verify:

- Timezone and next-run calculations.
- Duplicate scanner runs.
- Fair image rotation.
- Invalid model-selected asset rejection.
- Approval invalidation after edits.
- Worker restart recovery.

Learner review:

- Create a weekly campaign.
- Inspect and edit an upcoming post.
- Approve and publish it.

### Slice 3 — explicit auto-publish

Becomes usable: A tested campaign can publish without per-post approval.

Build:

- Test-post prerequisite.
- Consent fields and confirmation UX.
- Policy checks and consent invalidation.
- Immediate pause/disable behavior.

Verify:

- Model cannot change consent.
- Destination/frequency changes invalidate consent.
- Disable cancels unsubmitted work.
- Exact-once and unknown-outcome behavior.

Learner review:

- Enable auto-publish after a test.
- Observe one upcoming post.
- Cancel one, allow another to publish, then pause.

### Slice 4 — provider abstraction

Becomes usable: Scheduling and post state no longer depend directly on Telegram modules.

Build:

- Internal provider contract.
- Telegram adapter around existing behavior.
- Canonical post snapshot and provider-specific limits.

Verify:

- Existing Telegram tests remain regression tests.
- Provider rejection, safe retry and uncertain outcomes map correctly.
- No behavior regression in manual publishing.

Do not add a second provider until the interface is proven by Telegram.

### Slice 5 — analytics foundation

Becomes usable: Owners see publication history and only proven engagement metrics.

Build:

- Metric snapshots.
- Provider collection task.
- Operational dashboard.
- Telegram analytics decision and controlled proof.

Verify:

- Missing metrics display as unavailable, not zero.
- Collection is owner-scoped and rate-limited.
- Repeated collection is idempotent.
- Exact/estimated labels are truthful.

### Slice 6 — insights and sentiment

Becomes usable: Owners receive grounded summaries and comparisons.

Build:

- Deterministic aggregations.
- Comment retrieval only through approved APIs.
- Structured sentiment classification.
- Sample size, window and uncertainty display.

Verify:

- No sentiment without comments.
- Mixed Amharic/English evaluation set.
- Arithmetic matches stored metrics.
- Small samples produce cautious or no recommendations.

## Mechanical verification

Backend:

- Unit tests for schedule calculations and daylight-saving behavior.
- Database tests with real PostgreSQL locking and uniqueness.
- Owner-isolation tests for every new route.
- Storage failure and cleanup retry tests.
- Provider doubles for success, rejection, timeout and uncertainty.
- Structured model-output validation tests.
- Prompt-injection cases in product descriptions and campaign instructions.
- Cost, retry and turn-limit tests.

Frontend:

- Production build and TypeScript checks.
- Gallery upload/edit/approve/delete.
- Campaign setup validation.
- Timezone and local-time display.
- Review and auto-publish consent flows.
- Upcoming cancel/edit/approve behavior.
- Mobile layout and accessibility labels.

Live controlled checks:

- Real Telegram test-post publication.
- One reviewed scheduled post.
- One explicitly authorized auto-published post.
- Pause before submission.
- Revoked Telegram permission behavior.
- Confirm that uncertain outcomes are not resent.

Regression:

- Existing ad generation and editing.
- 1080 × 1080 PNG rendering.
- Ad revision conflict behavior.
- Existing manual Telegram publishing.
- Video creation and cleanup.
- Account/profile ownership.

## Release completion criteria

The release is complete when:

- An owner can maintain a persistent approved gallery.
- A campaign can prepare posts on a timezone-aware schedule.
- Selection never escapes the approved eligible set.
- Generated copy uses canonical facts and validates successfully.
- Review mode publishes only an exact approved revision.
- Auto-publish works only after explicit campaign consent and a successful test post.
- Pausing prevents future unsubmitted posts.
- Duplicate scheduler runs do not create duplicate posts.
- Provider uncertainty never causes an automatic resend.
- Gallery assets survive generated-ad expiration.
- Generated ads expire at their fixed 30-day deadline.
- Telegram remains fully functional through the provider abstraction.
- Analytics display only metrics that were actually collected.
- AI summaries identify their data window and sample size.

## Open decisions before implementation

- Whether existing unexpired ads keep their original seven-day deadline or receive a one-time extension.
- Maximum gallery items per account and per campaign.
- Maximum active campaigns per account.
- Default preparation window; 24 hours is proposed.
- Allowed lateness before a missed post is skipped.
- Whether deterministic least-recently-used fallback is allowed when AI selection fails.
- Campaign-history and metric retention period.
- Whether paid image generation is allowed in auto-publish mode by default or needs a separate spending consent.
- Which second social provider should follow Telegram.
- Whether Telegram analytics will use MTProto, a reviewed third party, or remain unavailable.
- Raw comment retention and privacy policy before sentiment work.

## Recommended next step

Implement only Slice 0 and Slice 1 first:

1. Change new generated ads to a fixed 30-day expiration.
2. Add the persistent owner-approved gallery.

These changes are independent of LangGraph and establish the data boundary the later agent workflow requires. Continue learning LangGraph in parallel, then use a small graph for Slice 2 preparation and approval orchestration after the gallery and scheduling contracts are tested.
