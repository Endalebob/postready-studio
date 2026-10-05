---
doc: prd
status: approved
---

# PostReady Studio — Product Requirements

A mobile-friendly photo-to-ad app for Ethiopian small-business owners.
Source: `scope.md > Who It's For`, `The Unique Kernel`, and `The Core Loop`.

## The Core Journey
1. Open a home page explaining the app and showing inspirational example advertisements.
2. Tap the create-ad button and upload one product photo.
3. Move to the details page. Enter product and business information and choose Amharic or English before generating.
4. Submit and see an in-progress state while the advertisement is created.
5. Review the generated ad with two separate editors: image text and social-post caption. Editing image text updates the ad while preserving the product artwork; social-caption edits are independent.
6. Download the current advertisement for sharing.

Source: `scope.md > The Core Loop` and `What "Working" Looks Like`.

## Screens and Layout
- **Home:** explain the outcome, show example advertisements, and provide a prominent create-ad action.
- **Photo upload:** a clear upload field for one product image; a valid upload leads to the details page.
- **Details:** product name, product description, price, optional discount information, shop address, contact details, and language choice.
- **Generation/result:** generation progress followed by the ad preview, independent image-text and social-caption editors, and download action. Errors offer recovery in this flow.

These are steps/surfaces, not a requirement for separate browser routes. Source: `scope.md > The POC Boundary`.

## Look and Feel
Warm cream backgrounds, charcoal lettering, restrained green and gold accents, and subtle borders inspired by Ethiopian woven textiles. Amharic lettering must be clear and readable. The app should feel connected to Ethiopian owners, and advertisements should have clean backgrounds and appealing product presentation. These are approved design directions, not a claim to represent every Ethiopian cultural tradition.

Source: `scope.md > Inspiration & Identity` and `The Unique Kernel`.

## Features and Behavior

### Photo Upload
Accept one usable product photo. If the photo cannot be used, explain the problem and ask for a replacement. The uploaded product must remain recognizable in the generated artwork.

Acceptance: a shoe photo can enter the creation flow; an unusable file produces a clear replacement message instead of proceeding.

### Product and Business Details
Collect details during each creation; no business profile is required.
- Required: product name, current price, and at least one contact method.
- Optional: description, shop address, and old price.
- Allow adding and removing up to four contact methods; each added row must have a value. Contact may be a phone number or social account, including Telegram or TikTok; this is display information, not an account integration.
- Old price, when supplied, must be greater than current price. Calculate the discount from these prices. Without old price, show no discount.

Acceptance: missing required values or an old price not greater than current price prevent generation and show a field-specific message. Current price, calculated discount when applicable, address when provided, and contact details are readable on the finished image and match the inputs. Missing optional details are omitted; generation does not invent business facts.

### Language Choice
Choose Amharic or English before generation. The generated caption uses the selected language, with readable lettering in the image. Owner-entered names and factual contact details should retain their meaning.

Acceptance: both language choices lead to editable text and a downloadable image displaying that text legibly.

### Advertisement Generation
Show an in-progress message during generation. Produce one clean product advertisement, combining artwork and readable text. Keep editable text separate from the product artwork so editing words preserves the picture.

Acceptance: the result visibly includes the uploaded product and supplied business details; changing text leaves the artwork unchanged.

### Caption Editing and Download
Provide separate editable image text and social-post caption on the result screen. Image-text edits appear inside the ad; social-caption edits do not change the image. Download must include the currently displayed image-text edits.

Acceptance: edit a phrase, see it change in the preview, download, and confirm the downloaded image contains the new phrase with unchanged artwork.

Acceptance: editing either text leaves the other unchanged.

Source for these behaviors: `scope.md > The Core Loop`, `What "Working" Looks Like`, and `The POC Boundary`.

## States and Boundaries
- **First use:** home explanation, example ads, and create action; no business profile is required.
- **Invalid photo:** explain that another image is needed and allow replacement.
- **Invalid details:** identify missing required fields or an invalid old price, preserve entered values, and allow correction before generation.
- **Generating:** show that creation is in progress; do not present unfinished work as a completed advertisement.
- **Generation failure:** retry internally first. If it still fails, retain the photo and entered details, show “We couldn’t create your ad. Please try again,” and offer Retry. Do not promise proactive contact.
- **Success:** show the ad preview, independent image-text and social-caption editors, and download action.
- **Within-flow preservation:** generation failure retains inputs. Closing or reloading may clear the working session, as approved for this demo.

## Product Decisions
- Home explanation and example advertisements help owners understand the outcome before creating.
- Photo upload precedes a details page.
- Business profiles were considered and deferred for the demo; enter fields for each ad instead.
- Language is chosen before generation.
- Product name, current price, and contact are required; description, address, and old price are optional.
- Optional old price must exceed current price and supplies the basis for calculating a discount.
- Image text and social-post caption are separate, independently editable texts.
- Caption editing changes words inside the ad; the learner accepted separating editable text from artwork.
- The proposed cream/charcoal/green/gold and textile-inspired visual direction was accepted.
- Automatic retry, preserved inputs, clear failure messages, and manual Retry were accepted.
- The learner suggested Nano Banana and reported already having credentials. Provider selection belongs in the technical spec; no credentials were requested or recorded.

## What We're Building
The home-to-download journey above, one product photo, one ad, owner-provided details, Amharic or English text, editable text inside the ad, the agreed visual direction, and recoverable generation failure. Demonstrate with a shoe photo and verify that the downloaded ad reflects edits.

## Deferred From the POC
- Business profiles, accounts, and syncing: the learner chose per-ad entry for this demo.
- People wearing or using the product, with Ethiopian representation: explicitly deferred in scope.
- Multiple design alternatives and automatic social posting: deferred in the approved scope.

## Non-Goals
A full advertising campaign tool or social-platform publishing workflow. The proof is a downloadable ad, not campaign management.

## Open Questions
No product-defining questions remain. The session-persistence boundary below was approved with the plan.

Resolve during technical planning without changing product intent:
- Image provider/model and access setup; never request credentials in chat.
- Supported image formats, file limits, output size, and bounded retry policy.
- Text fitting and Amharic rendering approach.

Approved demo boundary: inputs do not need to survive a reload or closed browser. Within-flow preservation after generation failure is required.




## Approved Ad Themes
The details step offers three illustrative selectable previews: Ethiopian Warmth (default cream/charcoal/green/gold), Bold Contrast (black, green headline, white details, red contacts), and Clean Modern (white/charcoal/blue). One selection guides artwork generation and sets exact renderer colors; samples indicate direction rather than guaranteeing identical AI composition. Selection is preserved on retry. This produces one ad, not multiple generated alternatives.
