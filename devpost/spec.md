---
doc: spec
status: approved
---

# PostReady Studio — Technical Spec

## How This Works, In Plain Language
Next.js shows the owner the home page, upload and details steps, and result. FastAPI receives the photo and details and calls Google's Gemini API using a key kept on the backend. Gemini creates the product artwork and advertising copy. The browser adds editable text to the artwork and downloads the combined image. Image text and the social-post caption can be edited independently.

Two Docker Compose services run this locally. There is no database or background worker. The owner waits on the creation screen while one request completes; failed generation preserves their inputs for retry.

## The Core Journey Through the System
1. Next.js shows labeled example advertisements and a create action.
2. The browser retains one uploaded file and previews it locally.
3. The details form validates product name, price, contact methods, optional old price, description/address, and language.
4. Submit a multipart request to FastAPI. Show indeterminate generation progress, not a fabricated percentage.
5. FastAPI validates the image and fields, computes discount, and requests text-free artwork from Gemini using the photo. Request copy separately using the same provider, in the selected language.
6. Return artwork bytes and structured copy. The browser draws the artwork and text with a shared canvas renderer used for both preview and export.
7. Independent editors update image text or social caption. Export the current canvas as PNG; the social caption remains selectable text for copying.

Implements `prd.md > The Core Journey`, `Caption Editing and Download`.

## Stack
- Next.js App Router, React, TypeScript, and ordinary CSS: learner's frontend preference. [Next.js installation](https://nextjs.org/docs/app/getting-started/installation), [React](https://react.dev/learn), [TypeScript](https://www.typescriptlang.org/docs/).
- Python 3.12, FastAPI, Uvicorn, Pydantic, python-multipart, and Pillow: learner's FastAPI preference; validation and decoded-image checks. [FastAPI uploads](https://fastapi.tiangolo.com/tutorial/request-files/), [Uvicorn](https://www.uvicorn.org/), [Pydantic](https://docs.pydantic.dev/), [Pillow](https://pillow.readthedocs.io/).
- Official google-genai Python SDK: server-side Gemini integration. [SDK](https://googleapis.github.io/python-genai/).
- Native Canvas API for preview and PNG export; locally bundled Noto Sans Ethiopic with its license. [Canvas](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API), [font source](https://github.com/notofonts/ethiopic).
- Docker Compose, Node 22 runtime: learner's local orchestration preference. [Compose](https://docs.docker.com/compose/).

Pin exact compatible package versions and commit lockfiles during the first build step. Installed runtimes, Docker availability, font artifacts, and account model access are not verified yet.

## Where It Runs and How Someone Tries It
Requires Docker Desktop with Compose and Linux containers, internet access for Gemini, and an API-enabled Google AI Studio key. Create a local `.env` from the secret-free `.env.example` and set `GEMINI_API_KEY` there; never put it in frontend variables or chat.

Start from the repository root: `docker compose up --build`. Open `http://localhost:3010`. FastAPI listens in its container on port 8000; publish it only to loopback for local diagnostics. Next.js proxies `/api/backend/*` to `http://api:8000/*` so the browser uses one origin. Docker build context must exclude `.env`, personal learner context, and generated caches.

Record the shoe upload, details, generation, independent edits, and PNG download. Submission needs a short demo video and public GitHub repository. Local running is sufficient. Future hosting on the learner's VPS behind their Cloudflare domain is deferred; public exposure needs a separate review of credentials, access, and request limits.

## Look and Feel
Implements `prd.md > Look and Feel`. Use cream `#F6F2E7`, charcoal `#252E28`, green `#326348`, and gold `#B08B3B` as implementation starting values. Use spacious mobile layouts, visible labels, a prominent green primary action, subtle textile-inspired borders, and bundled Ethiopic lettering. Gold is an accent; body text uses charcoal. Stack form fields on small screens; scale the preview without changing export dimensions.

## Components

### Journey UI
One client-side flow: home, upload, details, generating, result/error. Keep the draft in the top-level client component so step transitions and failed requests preserve inputs. Disable duplicate submission while running. Implements `prd.md > Screens and Layout`, `States and Boundaries`.

### Details Validation
Validate on client and server. Required: nonempty product name, positive current price, one to four nonempty phone/social contacts with add/remove controls. Optional description/address and positive old price; if supplied, old price must exceed current price. Use Decimal on the backend. Discount percent is `(old-current)/old*100`, displayed rounded to a whole percent while retaining exact supplied prices. Use ETB as the documented demo currency. No fabricated claims or contact details. Implements `prd.md > Product and Business Details`.

### Generation API
`POST /generate`, multipart fields `photo` and `details` (JSON string). Details: `product_name`, `description?`, `current_price` decimal string, `old_price?`, `address?`, `contacts` list of `{kind, value}`, and `language` (`am` or `en`). Success: `{artwork:{mime_type,base64},image_text:{headline,tagline},social_caption,details,discount_percent}`. Facts in `details` remain authoritative for the rendered price/contact/address blocks.

Return 422 field errors, 413 oversize upload, 415 unsupported format, and sanitized 502/503/504 generation errors. `GET /health` reports readiness without revealing secrets. Implements `prd.md > Photo Upload`, `Advertisement Generation`.

### Gemini Adapter
Use `google-genai` asynchronously with a configured image model, initially `gemini-2.5-flash-image` (original Nano Banana), and a configurable text model, `gemini-3.8-flash` (replacement approved after the original text model rejected new-user requests). Verify both against the account before depending on them. Any model change with material cost or behavior implications is raised with the learner.

Request artwork with the uploaded photo and a product-preserving, clean-background instruction; ask for no embedded text and no people. Text generation returns schema-validated `headline`, `tagline`, and `social_caption` in the selected language. Do not accept instructions embedded in product descriptions as overrides of the output contract. Do not include contact/address data in the image prompt when unnecessary. Implements `prd.md > Language Choice`, `Advertisement Generation`.

### Ad Renderer and Export
Use one 1080 × 1080 canvas layout: clean artwork region and readable text area with headline, short tagline, price, optional old price/discount, optional address, and contacts. The square format is a demo implementation default, not platform-specific optimization. Wait for the bundled font to load before drawing/export. Wrap text with measured widths; shrink within a readable minimum, then show a shortening message rather than silently clipping. Image-text editors expose headline/tagline and the factual text blocks; price/discount changes remain validated together. Social-caption changes never alter image text. Export with `canvas.toBlob('image/png')`; use the returned image bytes locally so remote-image CORS cannot taint the canvas. Implements `prd.md > Caption Editing and Download`, `Look and Feel`.

## Data Model
- Browser memory: upload File/object URL, draft details, selected language, flow step, generation status/error, returned artwork, image-text edits, independent social-caption edits. Revoke object URLs when replaced/unmounted.
- Backend request memory: validated details and decoded image, provider responses. Close temporary upload resources after each request; no application upload archive or database.
- Browser downloads: exported PNG stored by the owner. Reload/close clears the working session, as approved.
- Configuration: backend-only key and model names in ignored local environment. Google receives submitted photo and relevant content for generation; application-local non-persistence does not imply provider non-retention.

## File Structure
```text
learn-ai/
├── compose.yaml                 # web + api services and environment wiring
├── .env.example                 # empty key + configurable model names
├── .gitignore                   # secrets, learner profile, build caches
├── README.md                    # local setup, live demo, repository instructions
├── frontend/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── package.json / package-lock.json
│   ├── tsconfig.json / next-env.d.ts
│   ├── next.config.ts           # same-origin backend proxy
│   ├── app/layout.tsx
│   ├── app/page.tsx             # journey and in-memory draft
│   ├── app/globals.css
│   ├── components/Home.tsx
│   ├── components/UploadStep.tsx
│   ├── components/DetailsForm.tsx
│   ├── components/ResultEditor.tsx
│   ├── lib/types.ts
│   ├── lib/api.ts
│   ├── lib/validation.ts
│   ├── lib/render-ad.ts         # common preview/export drawing
│   └── public/fonts/            # Ethiopic font + license
├── backend/
│   ├── Dockerfile / .dockerignore
│   ├── requirements.txt         # pinned dependencies
│   ├── app/__init__.py
│   ├── app/main.py              # health + generation endpoints
│   ├── app/schemas.py           # input/output validation
│   ├── app/images.py            # upload inspection and normalization
│   ├── app/gemini.py            # provider calls + bounded retries
│   └── tests/                   # meaningful validation/provider error tests
└── devpost/                     # canonical plans + HTML companions
```

## External Services and Dependencies
Gemini through Google AI Studio, authenticated with `x-goog-api-key` via the backend SDK. Underlying request: `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`. Image payload: `contents` with text and image `inline_data` (MIME + base64); response contains candidate parts with image `inline_data`. Inspect returned MIME, absence of image, and block/error responses. Text request uses supplied facts, language, JSON schema, and structured response config; validate parsed output before returning it.

[Image generation/editing](https://ai.google.dev/gemini-api/docs/image-generation), [structured outputs](https://ai.google.dev/gemini-api/docs/structured-output), [API reference](https://ai.google.dev/api/generate-content), [pricing](https://ai.google.dev/gemini-api/docs/pricing), [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits).

Documentation was consulted during planning. Account billing, quota, exact cost per chosen model, and model availability remain unverified and must be checked before the first live generation. Do not assume AI Studio access establishes usable API quota. No extra hosting or storage service is required.

## Important Failure Modes
- **Invalid upload/details:** accept JPEG, PNG, WebP up to 10 MiB; decode and normalize, bound decoded size to 20 megapixels, reject unusable images with actionable messages. These are proposed implementation limits. Preserve other draft fields.
- **Provider failure:** retry transient network/429/5xx failure once with a short delay (honor Retry-After within the time budget); do not retry bad credentials, invalid input, or policy refusal. Cap total generation at 180 seconds with a longer local proxy timeout. Return the approved failure message and manual Retry; retain browser inputs. No worker means closing the page does not provide resumable jobs.
- **Text/export failure:** await fonts and artwork decoding, prevent stale exports, surface a shortening message for overflow, and retain editable work. Verify actual PNG pixels in both languages.

## Verification Approach
First verify Docker/runtime prerequisites and live Gemini model access. Check upload validation, required fields, old-price ordering, discount rounding, and provider failure behavior with meaningful automated tests. Verify the happy path in the browser at phone width and desktop width. Compare preview and downloaded PNG after English and Amharic edits; confirm artwork unchanged, independent social caption, optional fields omitted, and no clipped text. Exercise one failure/retry path. Sample ads on home are visibly labeled examples; simulation may assist development but does not replace live proof of the photo-to-ad kernel.

## What Was Simplified and Why
- One in-flight FastAPI request; Celery/Redis deferred by learner agreement.
- In-memory draft and per-ad fields; profiles/accounts/database deferred by the approved PRD.
- Local Docker Compose plus recording; public VPS/Cloudflare deployment deferred.
- Browser-rendered text over AI artwork; learner accepted this to make editing independent of image regeneration.

## Decisions and Open Issues
Learner selected Next.js/FastAPI/Docker Compose, Google AI Studio access, local execution, and independent browser text composition. No learner uncertainty remained after discussing this approach; the learner said it was clear. Amharic font fitting/export is an engineering uncertainty to verify early, not a claimed learner knowledge gap.

Approved implementation defaults: square PNG, ETB demo currency, upload limits, one transient retry, and timeout above. Package pins, actual API access/quota, model availability, and font rendering are build checks. No further product feature or service is implied.





## Approved Ad Themes
The details step offers three illustrative selectable previews: Ethiopian Warmth (default cream/charcoal/green/gold), Bold Contrast (black, green headline, white details, red contacts), and Clean Modern (white/charcoal/blue). One selection guides artwork generation and sets exact renderer colors; samples indicate direction rather than guaranteeing identical AI composition. Selection is preserved on retry. This produces one ad, not multiple generated alternatives.
Request details include `theme`: `ethiopian-warmth`, `bold-contrast`, or `clean-modern`, defaulting to the first for compatibility. The server validates this enum and maps it to fixed artwork instructions; the frontend palette registry supplies canvas and sample colors.
