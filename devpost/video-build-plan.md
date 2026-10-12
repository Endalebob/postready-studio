---
status: approved
---
# Core video build plan

The owner approved provider-native AI durations and proceeding with the core build on 2026-10-11. This document makes the build order and remaining defaults reviewable. Completed image-ad work stays intact.

## Product journey

Create video → upload 1–10 photos → edit each product's name, price and optional description → choose transitions or AI motion → choose supported duration → optional music and voice → generate → preview → download.

Reuse business profile information, language and themes. Keep five music styles: Elegant Piano, Bright Strings, Warm Acoustic, Grand Showcase and Calm Classical. Lower music automatically during voice speech. Direct video publication is deferred.

## Proposed defaults

- Vertical MP4 at 720 × 1280, with H.264 video and AAC audio.
- Move-up/down and remove controls for product photos; no detailed timeline editor.
- Seven-day private retention from successful completion for video and source uploads, following the existing ad-library behavior.
- Music can loop or trim to the video duration. Voice starts at the beginning; if too long, request a longer supported duration or shorter voice clip rather than silently cutting speech.
- Compose exact product text and business logo outside the AI-generated frames.

## Technical approach

Reuse Next.js, FastAPI, PostgreSQL, MinIO, Celery, Redis and Docker Compose. Add FFmpeg to the backend/worker images for photo transitions, MP4 encoding and voice-driven music lowering. Use Pillow for exact Amharic/English text overlays.

Store private input/output assets in MinIO and owner-scoped job records in PostgreSQL. The worker processes durable jobs while the UI polls progress. Recheck ownership and expiration on every media route. Validate photo/audio contents and bound processing time and file size. Invoke FFmpeg with argument arrays, without a shell.

Separate BFL and Google video adapters expose supported durations/image constraints and submit/poll/download methods. Provider task IDs persist before polling continues. Never silently switch paid providers or automatically resubmit an ambiguous paid request. Show provider and estimated cost before submission.

Ten photos is the app upload limit; it does not mean every provider accepts ten images in one request. BFL keyframes and Google's multi-product scene assembly need controlled live validation. Only expose verified configurations. Five original synthesized instrumental miniatures are bundled under MIT, with a reproducible score/synthesis script. Uploaded music remains optional.

References: https://ffmpeg.org/ffmpeg-filters.html ; https://docs.bfl.ai/flux_3/flux3_overview ; https://ai.google.dev/gemini-api/docs/veo

## Build order

1. **Photo-transition videos:** upload, product editing, duration, owner-scoped background jobs, persistence, preview and MP4 download. Verify one/two/ten-photo exports, text, duration, dimensions, owner isolation and restart recovery. Hands-on check here.
2. **Music and voice:** five previewable presets, optional uploads, audio validation, mixing and music lowering during speech. Verify by listening and checking exported streams/levels.
3. **AI motion:** independent BFL/Google adapters, provider-dependent options, durable polling and exact overlays/audio. Verify failure/restart behavior and controlled real generations; final hands-on review.

Fast mode continues. Each working slice is tested and committed; the first and final slices include learner feedback. Existing image-ad and Telegram tests remain regression checks.

## Completion criteria

The owner can generate and download a real video with all selected products and chosen audio. Provider-specific limits are explained before generation. Failures preserve useful inputs and never claim success or silently spend on another provider. Preview and download match. The app map is updated after final review.

## Outstanding validation

Live BFL Draft and Google Veo Standard access were confirmed by successful small generations and downloads on 2026-10-11. Google multi-product composition uses one four-second generation per product; the UI displays the full generation estimate before creation. Five original music presets are bundled. BFL keyframes use explicit label-aligned timestamps. Final learner review of fidelity, audio and the integrated journey remains pending.

- Owner approved the displayed build order and defaults on 2026-10-11.
