# Next milestone: product video advertisements

Status: idea captured; requirements and implementation approach not yet approved.

## User goal

Ethiopian business owners create an advertisement up to 15 seconds long featuring multiple selected products, suitable for TikTok and Instagram.

## Requested capabilities

- Select multiple products or upload multiple product photos for one video.
- Present those products in an attractive advertisement.
- Choose music or upload an audio track to include in the video.
- Upload voice audio for the advertisement.
- Preview the finished video before downloading or publishing.

Keep the existing business profile, contacts, visual themes and language experience as the starting point. The owner should not need video-editing expertise.

## Decisions to resolve before building

- Animated product photos with transitions, AI-generated motion, or both.
- First version's product count and supported video durations, up to 15 seconds.
- Editable scene order, text and timing controls.
- Music selection source and mixing behavior when voice audio is present.
- Video format and export size; vertical output is a proposed starting point.
- Generation provider, cost limits, background-job states and retry behavior.
- Whether the existing seven-day retention applies to video and uploaded audio.
- Download-first release or direct publishing; Instagram and TikTok integration are separate requirements, not implied by creating compatible video files.

## Suggested first proof

A business owner selects a small set of product photos, supplies product details and optionally uploads music and voice audio, then previews and downloads one vertical video of no more than 15 seconds. The choice of animated-photo composition versus generative video must be settled before technical planning.
