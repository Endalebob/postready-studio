# PostReady Studio

Create an advertisement from one product photo, with Amharic or English copy. Built with Next.js, FastAPI, and Gemini.

## Run locally

1. Install/start Docker Desktop with Linux containers.
2. Copy `.env.example` to `.env` and set `GEMINI_API_KEY`, a strong `POSTGRES_PASSWORD`, `MINIO_ACCESS_KEY`, and `MINIO_SECRET_KEY` locally. Never commit the key. Model names can be adjusted to models available to your account.
3. Run `docker compose up --build`.
4. Open http://localhost:3010.

The key stays in FastAPI. Accounts and business profiles are now stored in PostgreSQL, with private business logos in MinIO. Generated artwork and editable copy are saved to a private 30-day image-ad library; use Save advertisement to commit edits and the current PNG. Google receives the photo and relevant details for generation. Live generation requires available API quota and may incur provider charges.

Home imagery is labeled as illustrative. The app must complete live generation for a real proof of concept; simulated results are not proof of the core flow.

## Checks

`docker compose exec api python -m unittest discover -s tests`

`docker compose exec web npm run typecheck`

The completed demo checklist is in `devpost/checklist.md`. First-release progress and acceptance criteria are in `devpost/post-mvp-checklist.md`.

## Try the complete flow

Create an account and save a business profile, then upload a product. Review the prefilled contacts, address, language and theme, enter product details, then generate. Edit the headline, ad description, price, address, or contacts beneath the preview. Edit the social caption independently. Download PNG saves the current 1080 × 1080 advertisement; invalid prices or text that cannot fit must be corrected first. Text edits use the existing artwork without another AI request.

## License

Project code is available under the [MIT License](LICENSE). The bundled Noto Sans Ethiopic font retains its separate [SIL Open Font License](frontend/public/fonts/OFL.txt).

## Accounts and business profiles

Create an account with username, email, password (at least 10 characters), and password confirmation. Save your business name, contacts, optional address/logo, default language and theme. New ad forms reuse those values; changes inside an ad do not update the profile. Logos accept PNG/JPEG/WebP up to 2 MiB and 4 megapixels and are composed directly into preview/export.

PostgreSQL and MinIO use persistent named volumes; normal service restarts retain accounts and profiles. Database migrations run on API startup. The local MinIO container is built from a pinned official source release because prebuilt official images were unavailable. Its initial build downloads Go dependencies and may take longer than later builds.

Local app origin defaults to `http://localhost:3010`. Set `APP_ORIGIN` to the exact frontend origin and `COOKIE_SECURE=true` before an HTTPS deployment. The current work is local development, not a completed public-release hardening audit. Generation requires authentication. Telegram linking and reviewed publishing are implemented; the live channel check is tracked in `devpost/post-mvp-checklist.md`.

## Saved ads

My Ads lists active advertisements. New image generation fixes expiry at 30 days; existing stored deadlines are preserved and edits never renew them. Save advertisement stores the editable revision and its PNG. Reopening an ad restores its source artwork and logo snapshot. Conflicting saves are rejected rather than overwriting another tab. Delete requires confirmation and hides the ad immediately. Expired ads are denied on all access routes, with Celery/Redis cleanup every five minutes removing private assets and content. Profile logos are retained independently.

If MinIO is unavailable, a temporary database copy keeps the generated source recoverable until saving succeeds or the fixed deadline arrives. A database outage returns an unsaved result with a signed deadline for a saving retry; downloading the current preview remains available. Storage errors never claim that edits or a PNG have been saved.

## Telegram publishing

1. Create a dedicated Telegram bot using BotFather and put its token in local `.env` as `TELEGRAM_BOT_TOKEN`. Restart API, worker and beat after changing it. The bot must have no existing webhook; local workers poll Telegram without a public URL.
2. In the app, open Social channels and Start connection. Follow the bot link and press Start in Telegram.
3. Add that bot as an administrator of a test channel with permission to post. Post the displayed connection command in that channel within 20 minutes.
4. Wait for the app to show your verified identity and channel name, then confirm the connection. Both your Telegram account and the bot must have posting permission.
5. Open a saved ad in My Ads, save any edits, and select Review Telegram post. Check the exact saved image, caption and destination, then press Publish now. The app reports queued, sending, published, failed or uncertain, and provides a link after confirmed success.

Caption length is limited to 1024 characters. A confirmed failed attempt can be reviewed and retried. An uncertain outcome is never automatically resent: check the channel first. Repeated clicks do not create another attempt for the same saved revision and connection. Disconnect stops queued posts; permissions and the ad's original expiration are checked again before sending. Published Telegram messages remain in Telegram after the app's stored ad expires.

## Product videos — first build slice

Create video accepts 1–10 JPEG/PNG/WebP product photos (10 MB and 20 megapixels maximum per image). Edit product names, optional ETB prices and descriptions; reorder photos, choose 5/10/15 seconds and a visual theme, then generate. Local FFmpeg composition creates a vertical 720 × 1280 MP4 with crossfade transitions, exact product labels and a snapshot of business contacts/address/logo. This mode makes no paid AI video request.

Jobs persist in PostgreSQL, with private inputs and outputs in MinIO. The existing Celery worker processes them; reload and reopen through recent videos to preview or download. Videos expire seven days after successful completion. Failed-job assets are cleaned up after one day; interrupted local rendering can be safely resumed. A maximum of two active video jobs per account limits accidental duplicate workload. Music/voice and AI motion are implemented; final learner review is tracked in `devpost/video-checklist.md`.

Backend images now install FFmpeg and DejaVu fonts from Debian; the bundled Ethiopic font retains its OFL license in `backend/assets/fonts/OFL.txt`. Initial image builds download those packages. Rebuild through `docker compose up --build` so the API migration and worker use the new video code together.

## Video music and voice

Choose no music, one of five previewable original synthesized instrumentals, or upload music. Optional voice starts at the beginning; music lowers during speech and recovers afterward using FFmpeg sidechain compression. Music loops/trims and fades to fit. Upload MP3/WAV/M4A/OGG/WebM up to 20 MB; music must be at most 60 seconds and voice must fit the selected video length. Invalid audio is rejected before a job is created, preserving the form. Inputs are decoded into bounded mono WAV snapshots stored privately alongside the video and removed at the same expiry. The exported MP4 uses AAC audio.

The original preset recordings and reproducible composition script are in `backend/assets/music`, under the repository MIT license. They are synthesized instrument styles, not licensed commercial or live recordings. Use only audio you have permission to include.

## AI product motion

Select AI product motion and choose BFL FLUX 3 Draft or Google Veo 3.1 Standard. Keys remain in server `.env` (`BFL_API_KEY` and `GEMINI_API_KEY`). BFL supports 5–20 seconds at draft pricing, with product keyframes pinned to label timings; Google supports 4/6/8 seconds. For multiple Google products, each gets a separate four-second generation that is trimmed into the requested total video length. The UI shows the total estimated USD cost and requires acceptance before creation. Estimates use the documented rates at implementation time, not a billing guarantee.

Paid task references persist in private job assets. Workers perform short submit/poll/download/compose actions and resume saved references after restarts. A pre-send marker prevents blind repeat submissions if a worker crashes before saving the provider response. Uncertain submissions require checking the provider dashboard before another request; the app never silently switches providers. Provider audio is removed, then the selected soundtrack/voice is mixed locally. Exact product names/prices and profile details/logo are rendered locally around the generated footage. AI product fidelity and timing still need preview review before sharing. Provider jobs have a two-hour processing window; unsuccessful assets are cleaned after one day, uncertain assets after seven days, and completed videos seven days after success.

Provider contracts: https://docs.bfl.ai/api-reference/utility/generate-a-video-with-flux-3 and https://ai.google.dev/gemini-api/docs/veo. Pricing: https://docs.bfl.ai/flux_3/flux3_overview and https://ai.google.dev/gemini-api/docs/pricing.

## Campaign gallery foundation

Campaign Gallery stores reusable product photos and validated facts privately, independently of generated-ad expiry. Add a photo, name, description, price, optional old price, contacts, address, language/theme and optional campaign notes. Review the saved photo/facts and explicitly approve it for future campaign use. Only active approved items are eligible. Editing facts/notes or changing active status clears approval; optimistic revisions reject stale edits and approvals. Deactivate excludes an item without removing it. Delete hides it immediately and background cleanup retries private-object removal. Gallery images persist until deletion; account deletion requires a separate reference-aware asset cleanup workflow when implemented.

The first foundation supports 100 retained items per account, including pending deletion cleanup. Each photo uses the existing JPEG/PNG/WebP limits of 10 MB and 20 megapixels. Source photos remain fixed for an item; upload a new item for a different photo. Campaign scheduling, automatic posting and analytics are not enabled by this foundation. Existing image-ad deadlines are preserved; newly generated image ads last 30 days, and video retention remains seven days. New signed save-recovery receipts include their original generation time; older seven-day receipts remain supported.


### Campaign drafts

Open **Campaigns** to save a paused draft with approved gallery products and a verified Telegram channel. Choose daily, weekly (default), or monthly, a local time and an IANA timezone; the screen previews the next three future occurrences. Monthly days clamp to the last day in shorter months. Nonexistent daylight-saving times are skipped and repeated times use only their first occurrence.

Drafts survive restarts and remain paused. This step does not generate ads, activate scheduled work or publish posts. Up to ten non-deleted drafts per account are supported. Product approval and channel availability are checked again on save; changed or deleted references are flagged when reopening a draft. Deleting a draft leaves gallery products intact. Migration `006_campaigns` adds owner-scoped draft records; selected product IDs remain in the validated settings so missing/deleted products can be reported.


### Prepare one campaign advertisement

Open a saved campaign and use **Prepare a post**. Select an approved campaign product, confirm the provider-charge notice, and request one ad. The worker captures the product facts, campaign language/theme/instructions and business logo, generates copy and artwork, then stores a server-rendered 1080px PNG with the existing editable ad. Open it for review, edit and save; its original 30-day expiration is unchanged.

Preparations persist across API/worker restarts. In-flight provider calls are never blindly resubmitted after an uncertain result. A confirmed artwork result can be saved again without another AI call; text that cannot fit remains accessible in the editor for correction. Changing the source approval or campaign before completion stops preparation. Guardrails allow two actively running preparations and ten requests per rolling 24 hours per owner. Private preparation snapshots are cleaned up after 30 days; ordinary ad expiry/cleanup is independent.

This step generates only after an explicit owner request. It does not schedule or publish campaign posts. Migration `007_preparations` and the `campaign-preparations` Celery Beat task add the durable preparation workflow. The existing ad editor reopens exact saved PNGs and preserves the product-image region when editing text.


### Waitlist and administrator approval

Public registration creates a pending waitlist account, not an active workspace. Pending/suspended users can sign in, inspect their access status and sign out; workspace APIs reject their requests. The public homepage offers **Join the waitlist**. Approval grants the image workspace only: business profile/logo, image creation, editing and saved ads. Video, gallery/campaign tools and Telegram integration/publishing are admin-only during this private preview.

Administrators use **Access requests** to approve/suspend users and set a total image-request allowance (default three in the form). Requests already used are never reset. The total cannot be set below usage; setting it equal to usage leaves zero remaining. Failed/uncertain generation attempts count, and quota is atomically reserved before calling a provider. Administrators have full workspace access and are not subject to tester allowances. Approvals never grant administrator rights, and every access change is recorded in the audit table.

**Deployment:** migration `008_waitlist` puts every existing non-bootstrapped account on the waitlist while preserving its credentials and content. No account is automatically selected as administrator. Back up PostgreSQL and MinIO, build the new images, and stop old web/API/worker/beat processes before applying the update so old workers cannot bypass the new gate. Start the updated API and confirm migration 008, then explicitly enable your own existing account on the server:

```sh
docker compose build api web worker beat
docker compose stop web worker beat api
docker compose up -d --no-deps api
docker compose exec -T api alembic current
docker compose exec -T api python -m app.admin bootstrap --username YOUR_EXISTING_USERNAME
docker compose up -d --no-deps web worker beat
```

Replace `YOUR_EXISTING_USERNAME` with your own account username. If you do not yet have an account, start web, join the waitlist, then run the bootstrap command for that account. Refresh/sign in and open **Access requests**. Keep the production `.env`/volumes and use the production compose file, not the ignored local verification override. Do not undo migration 008 while exposing the old application publicly: the old code has no approval gate.

Queued generation/video/publishing work rechecks account privileges; revocation blocks future work, including the next image-provider phase. A provider request already in flight cannot be recalled. Waitlist approval does not send email; users can sign in or check their status.


### Light and dark appearance

Use the sun/moon control in the header to switch the app appearance. It follows the device color preference initially, then remembers an explicit choice in this browser. The saved preference is applied before the page paints and synchronized between open tabs. App appearance does not change the selected advertisement palette or exported artwork.

Shared interface colors are CSS variables in `frontend/app/appearance.css`; `ThemeToggle.tsx` manages the preference and `app/layout.tsx` applies the initial selection. Production frontend build/TypeScript and desktop/mobile visual checks passed, including reload persistence, keyboard switching, native form controls, admin/gallery/media screens and saved-ad preview palettes. No backend behavior or database schema changed.
