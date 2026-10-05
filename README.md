# PostReady Studio

Create an advertisement from one product photo, with Amharic or English copy. Built with Next.js, FastAPI, and Gemini.

## Run locally

1. Install/start Docker Desktop with Linux containers.
2. Copy `.env.example` to `.env` and set `GEMINI_API_KEY` locally. Never commit the key. Model names can be adjusted to models available to your account.
3. Run `docker compose up --build`.
4. Open http://localhost:3010.

The key stays in FastAPI. No business accounts or persistent upload storage are used. Working data clears on reload; Google receives the photo and relevant details for generation. Live generation requires available API quota and may incur provider charges.

Home imagery is labeled as illustrative. The app must complete live generation for a real proof of concept; simulated results are not proof of the core flow.

## Checks

`docker compose exec api python -m unittest discover -s tests`

`docker compose exec web npm run typecheck`

Build progress and acceptance criteria are in `devpost/checklist.md`.

## Try the complete flow

Upload a product, enter details, choose language and a theme, then generate. Edit the headline, ad description, price, address, or contacts beneath the preview. Edit the social caption independently. Download PNG saves the current 1080 × 1080 advertisement; invalid prices or text that cannot fit must be corrected first. Text edits use the existing artwork without another AI request.
