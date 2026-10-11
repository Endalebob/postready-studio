# Next milestone: product video advertisements

Status: feature choices confirmed on 2026-10-11; remaining requirements and technical approach pending.

## User goal

Ethiopian business owners create product advertisements up to 15 seconds long, suitable for TikTok and Instagram, without video-editing expertise. Reuse business profile information, contacts, visual themes and language preferences.

## Confirmed choices

- Upload or select 1–10 product photos per video. Reject an eleventh photo with a clear message while retaining the existing selection.
- Choose one of two modes: Photos with transitions, or AI-generated motion.
- Photo transitions offer 5, 10 or 15 seconds. AI motion offers the selected provider/model's supported durations, which need not match 5/10/15.
- Suggest a duration based on selected-photo count; let the owner choose another supported duration.
- Offer up to five built-in classical instrumental music presets as selectable sample cards, similar to visual themes. Selecting a preset automatically adds its audio to the video.
- Allow optional music upload instead of a preset, and allow no music.
- Allow optional uploaded voice audio.
- Preview and download the finished video. Direct video publishing is deferred to a later milestone.
- Keep the five proposed music preset styles for now; specific recordings remain to be selected.
- Automatically lower background music while uploaded voice audio is speaking so speech stays clear.

## Proposed duration recommendations

| Selected photos | Suggested duration |
| --- | --- |
| 1–2 | 5 seconds |
| 3–5 | 10 seconds |
| 6–10 | 15 seconds |

These thresholds are a proposed default, not a confirmed timing algorithm. Display the approximate average time per photo when the owner changes duration. Ten photos in five seconds is fast; offer a helpful suggestion without silently dropping products. Transitions and any closing frame must fit inside the selected total duration. AI-motion feasibility and provider constraints still need investigation.

## Accepted music preset styles

The labels describe classical instrumental styles; recordings have not yet been selected or bundled.

| Preset | Sound | Suggested use |
| --- | --- | --- |
| Elegant Piano | Gentle solo piano | Cosmetics, jewelry, premium products |
| Bright Strings | Light, lively chamber strings | Clothing and cheerful product collections |
| Warm Acoustic | Soft classical guitar | Food, cafes and everyday products |
| Grand Showcase | Confident orchestral instrumental | Launches and promotional offers |
| Calm Classical | Slow piano and strings | Beauty and relaxed product presentation |

Each card should have a short audio preview, a clear selected state and a descriptive label. Exactly one background source is active: a preset, uploaded music, or none. Use recordings licensed for the intended user exports; a composition's status alone does not establish permission for a particular recording. Selecting a preset should reproduce that selected audio rather than asking a model to imitate it.

## Proposed audio behavior

- Trim or loop preset music to the selected video duration and use short fades.
- Confirmed: automatically lower background music while voice audio is speaking so speech remains clear.
- Preserve voice audio without speeding it up. If it exceeds the selected duration, ask the owner to choose a longer supported duration or provide a shorter clip before generation.
- Preview the final mixed audio with the video.

Automatic music lowering is confirmed. Trimming, looping, fades and long-voice handling remain proposed for review.

## Decisions to resolve before building

- Photo ordering, scene text, timing and editing controls.
- Final music recordings and upload formats, file-size limits and trimming controls.
- Video format and export size; vertical output is the proposed starting point.
- AI-motion provider, product fidelity, multi-photo support, cost limits and progress/retry states.
- Whether seven-day retention applies to video and uploaded audio.
- Download-first release is confirmed. Direct video publishing, including TikTok and Instagram integrations, is outside this milestone.

## First proof

The owner selects up to ten photos, chooses mode and duration, chooses optional preset/uploaded music and voice audio, then generates, previews and downloads one video. Both modes are in the requested scope; the technical plan must explicitly verify AI-motion capabilities before implementation.

## Provider direction — 2026-10-11

The owner wants provider flexibility. BFL_API_KEY is configured locally, and the existing Gemini key may also be used for video. Keep credentials server-side and do not copy their values into planning documents.

Plan separate provider integrations for BFL and Google, with a provider choice in technical configuration. Do not silently switch to another paid provider after failure; retries and cost behavior must be specified before implementation. Photo-transition composition remains local.

Read-only Gemini model listing returned veo-3.1-generate-preview. This proves model visibility, not successful generation, paid quota or availability of Fast/Lite variants. No paid video generation was performed during this check.

Published prices checked on 2026-10-11: Google Veo 3.1 Lite 720p $0.05/second, Fast 720p $0.10/second, Standard 720p/1080p $0.40/second; BFL FLUX 3 HD full render $0.17/second and draft $0.06/second; Runway Gen-4 Turbo $0.05/second. Prices are per generated second; provider duration constraints, scene count, retries and final composition affect total advertisement cost.

Sources: https://ai.google.dev/gemini-api/docs/pricing ; https://docs.bfl.ai/flux_3/flux3_overview ; https://docs.dev.runwayml.com/guides/pricing/
