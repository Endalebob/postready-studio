---
doc: video-checklist
status: approved
---
# Video build checklist

Build mode: fast (carried forward). Owner approved order and defaults on 2026-10-11.

## Slices

- [x] **1. Create and download a product video with photo transitions**
  Becomes usable: Up to ten photos become a private vertical MP4 with editable product information, preview and download.
  Why now: Proves the complete core without paid provider dependence.
  PRD ref: `video-ads-target.md > Confirmed choices`
  Spec ref: `video-build-plan.md > Technical approach`, `Proposed defaults`
  Build: FFmpeg composition, exact labels/profile/logo, authenticated durable jobs and seven-day media storage, creation UI and recent videos.
  Verify (mechanical): Existing tests/build; real 1/2/10-photo render; duration/dimensions/text; owner isolation, byte-range media, duplicate submission, failure/restart and expiry checks; live browser preview/download.
  Learner check: Upload several product photos, edit their names/prices, choose duration, preview/download and report observations.
  Commit: `Add private product videos with photo transitions`
  Mechanical evidence (2026-10-11): Production frontend build and TypeScript compilation passed. Existing 39 tests and six video tests passed, including real two-scene rendering, ownership, byte ranges, duplicate submission, limits, failure/cleanup/restart recovery and profile/logo snapshots. Real one/two/ten-photo exports passed; ten photos produced exactly 15 seconds and all products were observed. Browser verified editing/reordering, live queued completion, 720 × 1280 H.264 preview and actual ten-second MP4 download. Migration 004_videos applied. Saved video and original expiry survived PostgreSQL/MinIO/API restart and browser reload. Learner tested and approved the transition flow on 2026-10-11; no changes requested.

- [x] **2. Include selectable music and uploaded voice**
  Becomes usable: Previewable five music choices or uploaded music, optional voice and automatic music lowering during speech.
  Why now: Audio composes onto a working video flow.
  PRD ref: `video-ads-target.md > Accepted music preset styles`, `Proposed audio behavior`
  Spec ref: `video-build-plan.md > Product journey`, `Technical approach`
  Build: Music assets/previews, uploads and validation, mixing/fades and voice-driven music lowering.
  Verify (mechanical): No music/voice-only/mixed exports, audio duration and audible lowering, invalid uploads and long voice behavior.
  Learner check: Select music, upload voice, export and listen.
  Commit: `Add selectable music and voice mixing to videos`
  Mechanical evidence (2026-10-11): All 49 tests and production frontend compilation passed. Real music-only, voice-only and mixed H.264/AAC exports retain the selected duration; spectral RMS checks confirm music lowers during speech and recovers afterward. Invalid/overlong audio creates no job, private audio snapshots expire with videos, and all five original previews decode. Live browser verified preset playback, voice preview/upload, a ten-second mixed video and downloaded AAC stream, overlong voice rejection with the form retained, and uploaded-music generation. Original synthesized recordings and reproducible scores are bundled under MIT. Final listening review remains at the planned final checkpoint.

- [ ] **3. Generate AI motion through BFL and Google**
  Becomes usable: Select an available provider and supported duration, generate a real product-motion video, preview and download.
  Why now: Reuses proven composition, storage and audio.
  PRD ref: `video-ads-target.md > Provider direction — 2026-10-11`
  Spec ref: `video-build-plan.md > Technical approach`, `Outstanding validation`
  Build: Independent adapters, supported options, durable provider polling, cost estimates, safe submission recovery and multi-product scene assembly.
  Verify (mechanical): Provider contracts/errors, restart/resume, supported duration/photo limits, controlled real generation and fidelity check.
  Learner check: Generate and inspect a motion ad with selected products/audio.
  Commit: `Add BFL and Google video generation integrations`

## Hands-on Checkpoints

- [x] Early transition-video review after slice 1
- [ ] Final video/audio/provider review after slice 3

## Final Review

- [ ] Learner observations resolved and integrated video journey accepted

## Code Tour and App Map

- [ ] Update map and focused technical handoff

## Revisions

- Photo transitions retain 5/10/15 seconds; AI duration follows provider support.
- Direct video publishing is deferred.

- FFmpeg 7 crossfade validation exposed a lost constant-frame-rate value after timestamp reset; explicitly applying the FPS filter repaired real rendering.
