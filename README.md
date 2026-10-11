# PostReady Studio

Create an advertisement from one product photo, with Amharic or English copy. Built with Next.js, FastAPI, and Gemini.

## Run locally

1. Install/start Docker Desktop with Linux containers.
2. Copy `.env.example` to `.env` and set `GEMINI_API_KEY`, a strong `POSTGRES_PASSWORD`, `MINIO_ACCESS_KEY`, and `MINIO_SECRET_KEY` locally. Never commit the key. Model names can be adjusted to models available to your account.
3. Run `docker compose up --build`.
4. Open http://localhost:3010.

The key stays in FastAPI. Accounts and business profiles are now stored in PostgreSQL, with private business logos in MinIO. Generated artwork and editable copy are saved to a private seven-day library; use Save advertisement to commit edits and the current PNG. Google receives the photo and relevant details for generation. Live generation requires available API quota and may incur provider charges.

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

My Ads lists active advertisements. Generation fixes the expiry date at seven days; edits never renew it. Save advertisement stores the editable revision and its PNG. Reopening an ad restores its source artwork and logo snapshot. Conflicting saves are rejected rather than overwriting another tab. Delete requires confirmation and hides the ad immediately. Expired ads are denied on all access routes, with Celery/Redis cleanup every five minutes removing private assets and content. Profile logos are retained independently.

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

Jobs persist in PostgreSQL, with private inputs and outputs in MinIO. The existing Celery worker processes them; reload and reopen through recent videos to preview or download. Videos expire seven days after successful completion. Failed-job assets are cleaned up after one day; interrupted local rendering can be safely resumed. A maximum of two active video jobs per account limits accidental duplicate workload. AI motion is the remaining slice in `devpost/video-checklist.md`.

Backend images now install FFmpeg and DejaVu fonts from Debian; the bundled Ethiopic font retains its OFL license in `backend/assets/fonts/OFL.txt`. Initial image builds download those packages. Rebuild through `docker compose up --build` so the API migration and worker use the new video code together.

## Video music and voice

Choose no music, one of five previewable original synthesized instrumentals, or upload music. Optional voice starts at the beginning; music lowers during speech and recovers afterward using FFmpeg sidechain compression. Music loops/trims and fades to fit. Upload MP3/WAV/M4A/OGG/WebM up to 20 MB; music must be at most 60 seconds and voice must fit the selected video length. Invalid audio is rejected before a job is created, preserving the form. Inputs are decoded into bounded mono WAV snapshots stored privately alongside the video and removed at the same expiry. The exported MP4 uses AAC audio.

The original preset recordings and reproducible composition script are in `backend/assets/music`, under the repository MIT license. They are synthesized instrument styles, not licensed commercial or live recordings. Use only audio you have permission to include.
