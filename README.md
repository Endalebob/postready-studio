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

Local app origin defaults to `http://localhost:3010`. Set `APP_ORIGIN` to the exact frontend origin and `COOKIE_SECURE=true` before an HTTPS deployment. The current work is local development, not a completed public-release hardening audit. Generation requires authentication. Telegram publishing is the remaining slice in `devpost/post-mvp-checklist.md`.

## Saved ads

My Ads lists active advertisements. Generation fixes the expiry date at seven days; edits never renew it. Save advertisement stores the editable revision and its PNG. Reopening an ad restores its source artwork and logo snapshot. Conflicting saves are rejected rather than overwriting another tab. Delete requires confirmation and hides the ad immediately. Expired ads are denied on all access routes, with Celery/Redis cleanup every five minutes removing private assets and content. Profile logos are retained independently.

If MinIO is unavailable, a temporary database copy keeps the generated source recoverable until saving succeeds or the fixed deadline arrives. A database outage returns an unsaved result with a signed deadline for a saving retry; downloading the current preview remains available. Storage errors never claim that edits or a PNG have been saved.
