---
doc: checklist
status: approved
---

# PostReady Studio — Build Checklist

Build mode: fast

## Slices

- [x] **1. Upload a product and generate a real ad preview**
  Becomes usable: A local Docker Compose app where an owner uploads a photo, supplies required details, chooses language, and receives live Gemini artwork and readable ad text.
  Why now: Proves the distinctive photo-to-ad behavior and provider access before investing in editing polish. Bootstrapping is included in this usable flow.
  PRD ref: `prd.md > The Core Journey`, `Photo Upload`, `Product and Business Details`, `Language Choice`, `Advertisement Generation`
  Spec ref: `spec.md > Journey UI`, `Details Validation`, `Generation API`, `Gemini Adapter`, `Ad Renderer and Export`, `Where It Runs and How Someone Tries It`
  Build: Create Next.js/FastAPI services, pinned dependencies, Compose wiring and backend-only environment configuration. Implement home examples, upload/details steps, validated generation API, provider calls, progress and error recovery, and initial canvas preview with the bundled Ethiopic font. Check runtime and model access early; preserve work on failure.
  Verify (mechanical): Validate Compose configuration without printing resolved secrets; start both services; run frontend build/type checks and backend tests for required fields, prices, image validation, and retry/error behavior. Complete a live photo-to-preview request, inspect the result in both languages, and verify mobile layout and backend-only key handling.
  Learner check: Open localhost:3010, upload your product photo, enter a name/current price/contact, choose language, and generate. Inspect the product likeness, readable details, and how easy the flow feels; report what you would change.
  Commit: `Add live product photo to advertisement flow`

- [x] **2. Edit image text and social copy, then download the current ad**
  Becomes usable: Separate image-text and social-caption editors, validated factual edits, and a PNG download that matches the preview.
  Why now: Builds on verified live artwork and early usability feedback to complete the central editing/export promise.
  PRD ref: `prd.md > Caption Editing and Download`, `Look and Feel`, `Product and Business Details`
  Spec ref: `spec.md > Ad Renderer and Export`, `Data Model`, `Details Validation`
  Build: Add independent editors, price/discount validation on edits, wrapped text with overflow messages, and download using the shared canvas renderer. Preserve artwork while editing and wait for fonts/image decoding before export.
  Verify (mechanical): Run frontend build/type checks and applicable backend tests. Edit English and Amharic text; inspect downloaded PNGs for updated words, readable glyphs, no clipping, correct optional fields and discounts, and unchanged artwork. Verify social-caption edits leave image text unchanged and vice versa; check awkward long inputs and phone-width layout.
  Learner check: Generate an ad, edit its image words and social caption separately, download it, and confirm the file reflects only the intended image edits.
  Commit: `Add independent ad text editing and PNG export`

## Hands-on Checkpoints

Slice 1 mechanical evidence: both Docker builds and frontend typecheck passed; 12 backend tests passed; live Amharic browser generation and English API generation succeeded with Gemini 3.8 Flash copy and Nano Banana artwork. Phone-width checks found no horizontal overflow. Failure recovery preserves input. Early learner feedback requested multiple contacts; the fix is implemented, built, and checked in the browser (add/remove preserves values, no phone-width overflow). Learner accepted multiple contacts. Three approved theme presets are implemented: Docker builds and typecheck pass, 13 backend tests pass, a live Bold Contrast request produced black artwork with green headline and red contacts, selection survives returning to details, and phone-width layout has no horizontal overflow. Learner accepted the themed demo and approved proceeding to editing/export.

- [x] Early usable behavior explored — after slice 1, before export/editing is finalized
- [x] Final kick-the-tires exploration and feedback completed — complete journey after slice 2

Slice 2 mechanical evidence: Docker production build and TypeScript checks passed; 13 backend tests passed. Live Amharic generation followed by Amharic and English image edits produced inspected 1080-square PNG downloads. Artwork-region screenshot comparison was identical after edits; social-caption changes left the canvas screenshot identical. Price edits recalculated discount (900 from 1250 = 28%); removing old price omitted discount. Invalid old price and overflowing text blocked export and recovered after correction. Phone viewport had no horizontal overflow. Learner tested the complete journey and accepted the demo; no further changes requested.

## Final Review

- [x] Final review complete — feedback resolved and learner confirms ready to ship

## Code Tour and App Map

- [x] Learning activity complete — focused investigation of a real usability/verification decision or prior practice connected
- [x] Optional edit and transfer reflection addressed — offered/declined/already covered/not applicable as appropriate
- [x] `devpost/app-map.html` generated from finished code, checked, and shown, including a project-grounded practice to reuse

Activity and evidence: brief evidence-based recap of the approved theme refinement, fixed prompt/palette implementation, and live verification, connected to predictable user controls. No additional hands-on learning exercise claimed.
Route and stops: reference route in app map: ResultEditor → Page state → renderAd/export.
Edit outcome: not applicable to focused recap; approved theme change already implemented and reviewed.
Reflection: optional transfer question offered at handoff; no response required.
Activity mode: focused alternative, evidence-based recap.
Map evidence: source paths/anchors checked and HTML parsed; no script or external asset dependencies. File opened in Codex and linked at handoff. Browser visual check unavailable because file URLs are blocked.

## Revisions


- Local web port changed to 3010 and API diagnostics port to 8010 because another application already occupies 3000; container ports and architecture remain unchanged.
- Live calls proved image generation works, but Google rejects gemini-2.5-flash for new users despite listing it. Text generation now runs before artwork so text-model failures do not trigger a wasted image call. Replacement text model requires learner agreement; slice 1 remains unchecked.
- Learner approved Gemini 3.8 Flash for caption generation after Google rejected the planned text model; Nano Banana image generation remains unchanged.

- Early learner feedback requested multiple contacts. Added up to four add/remove contact rows using the existing API list, with one readable line per contact in the ad.


- Learner approved three selectable ad theme previews, with Ethiopian Warmth as default. Selection controls the fixed artwork prompt and rendered colors while preserving one output per generation.
