# SurplusBite

A serverless photo pipeline for surplus-food sellers. A seller photographs
surplus food on a phone, uploads it from a mobile browser, and the cloud
automatically produces a web-ready thumbnail set plus suggested food-category
labels for the seller to review.

- **Region:** `af-south-1` (Cape Town)
- **Stack:** Python 3.12 · Pillow · Amazon S3 · AWS Lambda · Amazon Rekognition (optional)
- **Status:** in active development (Milestone 1)

## Problem

Restaurants, takeaways and farmers discard food they can no longer sell, while
households look for cheaper food nearby. Listing surplus food online is fiddly:
photos are large, inconsistent and unnamed, so listings look poor and load
slowly. SurplusBite solves the photo-to-listing step so the rest of the
marketplace becomes possible.

**Validation note:** the difficulty above is a hypothesis. It must be confirmed
by interviewing 3–5 restaurants, takeaways or farmers before being presented
as fact.

## What this build is (and is not)

**Is:** a low-complexity, event-driven AWS pipeline that resizes one photo into
two thumbnails and (optionally) suggests food-category labels using Amazon
Rekognition.

**Is not (deferred):** accounts, reservations, pickup codes, payments, email
notifications, a database, API Gateway, a map view, a full marketplace UI.

Full scope is in `docs/proposal.md` (added at Milestone 7).

## Milestones

- [x] **M1 — Core resize logic (local, no AWS)** ← you are here
- [ ] **M2 — IAM + AWS setup** (buckets, Lambda deployment)
- [ ] **M3 — Upload front door** (presigned URL + static upload page)
- [ ] **M4 — Catalogue index + static page**
- [ ] **M5 — AI extension** (Rekognition + food taxonomy)
- [ ] **M6 — Test suite + metrics**
- [ ] **M7 — Docs + architecture diagram + cost analysis**

## Repository layout
surplusbite/
├── README.md
├── requirements.txt
├── .gitignore
├── src/
│ └── lambda_function.py # image processing (M1: pure logic)
├── tests/
│ ├── test_local.py # M1 harness
│ ├── generate_test_images.py # builds synthetic test photos
│ └── test_images/ # generated photos (git-ignored)
└── results/ # metrics CSV (added M6)

Later milestones add `src/upload_url_lambda.py`, `web/upload.html`,
`web/catalogue.html`, `architecture/`, and `docs/`.

## Running Milestone 1

1. `Ctrl+Shift+P` → **Python: Create Environment** → **Venv**
2. Open `tests/generate_test_images.py` → click ▶ — creates four test files
3. Open `tests/test_local.py` → click ▶ — runs the acceptance tests

Expected end of output: `PASSED — 4 file(s) checked`

## Acceptance criteria — Milestone 1

- [ ] `tests/test_local.py` produces two thumbnails per valid image
      (card ≤ 300×300, pin ≤ 96×96), both preserving aspect ratio within 2%
- [ ] `corrupt-file.jpg` is rejected with reason `unidentified_image`
- [ ] Files with unsupported extensions are rejected with reason `extension`
- [ ] No AWS calls, no credentials required — runs offline in under 2 seconds

## Cost

Milestone 1 costs R0. Milestone 2 onwards will incur small AWS charges; cost
management is documented in `docs/cost-analysis.md` (added at M7).

## Licence and privacy

No credentials, no personal photos. Test images are synthesised by
`tests/generate_test_images.py`.