# Reywal — Bureaucracy Decoder

Paste or upload an official document — a tenancy termination notice, an insurance denial, a medical
bill, a government letter — and Reywal extracts *your* specific facts, retrieves the
*current* governing rule for your jurisdiction, checks whether the document is even lawful,
cites every claim to a real source passage, and drafts your response. Demo jurisdiction:
Ireland (RTB, Citizens Information, gov.ie).

## Why this isn't "just ChatGPT"

A general chatbot can summarize a letter and guess whether it sounds fishy. Reywal does
four things a chat window can't:

1. **Extraction** — pulls out the case-specific facts (notice period, dates, amounts) with
   the exact source span each one came from, not a generic explainer.
2. **Live grounding** — searches for and scrapes the actual current governing-rule page
   (Citizens Information / RTB / gov.ie), not the model's stale training memory.
3. **Verification** — runs entailment between what *your* document asserts and what the rule
   *actually* says, and renders an explicit verdict: `matches`, `mismatch`, or
   `cannot_determine`.
4. **Per-claim receipts** — every claim and verification is tied to a real `Source` object
   (url, title, verbatim quote, retrieved-at timestamp). If no passage can be verified to
   genuinely support a claim, the claim is marked `unverifiable`/`cannot_determine` instead —
   **no citation is ever invented.**
5. **Generated action** — an appeal letter / RTB dispute form / deadline notice that cites the
   exact rule that was verified, ready to send.

The centerpiece is the **verification panel**: "here's what they got wrong, and here's your
appeal" — not "here's what this document means."

## Stack

- Frontend: Vite + React + Tailwind
- Backend: FastAPI + SQLite (SQLAlchemy)
- OCR: Tesseract (layout-preserving; PDF/image uploads rendered via PyMuPDF)
- External services: Qwen (LLM), Exa (search), Firecrawl (scrape) — each with a canned-fixture
  mock fallback so the whole product runs offline (see `DEMO_MODE` below).
- In production the compiled Vite bundle is served by the same FastAPI process (no separate
  static server needed).

## Setup

**Backend:**

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # DEMO_MODE=1 by default — no real API keys needed
```

**Frontend:**

```bash
cd frontend
npm install
```

## Run

From the repo root:

```bash
./dev.sh
```

This starts the FastAPI backend (`uvicorn`, reload on, using `backend/.venv` if present) and
the Vite dev server together, with `DEMO_MODE=1` by default, and prints both URLs:

```
Backend:  http://127.0.0.1:8000   (docs at /docs, health at /api/health)
Frontend: http://localhost:5173
```

Press `Ctrl-C` to stop both — `dev.sh` traps the signal and kills both processes.

The Vite dev server proxies `/api/*` to `http://localhost:8000` (see
`frontend/vite.config.ts`), and the backend's CORS middleware allows the
`http://localhost:5173` origin (see `backend/app/main.py`), so the frontend can call
relative `/api/...` paths in dev with no CORS errors either way.

To exercise the **live** path instead (real Qwen/Exa/Firecrawl calls), fill in the API keys in
`backend/.env` and run `DEMO_MODE=0 ./dev.sh`.

## `DEMO_MODE`

`DEMO_MODE=1` (the default) makes every external client (`app/clients/qwen.py`,
`app/clients/exa.py`, `app/clients/firecrawl.py`) skip the network entirely and return canned
fixtures from `backend/fixtures/` instead. This means:

- A clean checkout runs the **full eight-stage pipeline** (classify → identify → extract →
  retrieve → ground → verify → act → refer) end-to-end with **no API keys, no network access,
  and no rate limits** — the demo can never die on a flaky scrape or an expired key.
- The results are deterministic and reproducible: the same input document always produces the
  same extracted facts, verification verdicts, and generated actions.

Set `DEMO_MODE=0` (and populate `QWEN_API_KEY` / `EXA_API_KEY` / `FIRECRAWL_API_KEY` in
`backend/.env`) to hit the real APIs instead.

## The demo script

This is the money demo: a **defective RTB termination notice** whose stated notice period is
shorter than the statutory minimum, so the verification panel fires a live **MISMATCH**.

1. Run `./dev.sh`, open `http://localhost:5173`.
2. Paste in the contents of `backend/fixtures/sample_docs/defective_rtb_notice.txt` — a notice
   dated 1 June 2026, for a tenancy that started 1 March 2021 (so it has run over 3 years),
   giving the tenant only **14 days** to vacate.
3. When prompted to confirm the governing body, select **RTB** (Residential Tenancies Board).
4. Click decode. The audience sees:
   - **Extracted facts**: `notice_period_days = 14`, `tenancy_start = 2021-03-01`,
     `notice_date = 2026-06-01`, `landlord_name = Kelly Properties Ltd` — each traceable to
     the exact sentence in the pasted notice.
   - **Verification panel**: a flagged **MISMATCH** —
     - assertion: *"Notice gives 14 days to vacate the property"*
     - rule value: *"90 days minimum notice for a tenancy of 3 years or more"*
     - a cited source: Citizens Information, *"Ending a tenancy"*, with the verbatim quoted
       passage *"notice period of 90 days where the tenancy has lasted 3 years or more"*.
   - **Generated action**: a drafted appeal letter to the landlord citing the exact 90-day
     rule and asserting the notice is invalid, plus an RTB-contact action.
5. The punchline: this isn't a vibe — every number on screen is either lifted verbatim from
   the pasted document or from a quoted, timestamped source passage. Nothing is invented.

Alternatively, hit `POST /api/decode/demo` to run the money demo entirely without a request
body — the backend returns a pre-wired `DecodeResult` straight from the canned fixtures.

### Verifying this offline, headlessly (no browser)

```bash
cd backend
DEMO_MODE=1 .venv/bin/python -m pytest tests/test_smoke.py -v
```

This posts the same defective-notice fixture straight to `/api/decode` (with `institution:
{"body_id": "rtb"}` to bypass the institution-identification prompt) and asserts the response
contains a `verification` item with `verdict == "mismatch"` backed by a real, non-null
`source` — the automated proof that the money demo is safe to run live.

## Document input

Two input paths share the same pipeline and response schema:

| Path | Method | Notes |
|---|---|---|
| `POST /api/decode` | JSON `{"text": "..."}` | Paste or programmatic |
| `POST /api/decode/upload` | `multipart/form-data` | PDF or image (max 20 MB); Tesseract OCR extracts layout-preserving text |

Both return `DecodeResponse`. Both have streaming siblings (`POST /api/decode/stream`,
`POST /api/decode/upload/stream`) that emit Server-Sent Events (one JSON frame per pipeline
stage) so the frontend can show live progress. A client that disconnects mid-stream can
reconnect via `GET /api/decode/stream/{job_id}` — the job keeps running server-side and
replays all buffered frames on reconnect.

## Institution identification

After classification, the pipeline tries to identify the issuing authority automatically.
When it can't (no governing body found in the text), it returns
`status="needs_institution"` with a list of candidate bodies. The client re-submits with
`institution: {"body_id": "..."}` (or `"display_name": "..."`) to continue. This applies to
both the paste and upload paths.

## Profile autofill

A saved profile (`POST /api/profile`) stores personal details (name, address, PPS, etc.)
**encrypted at rest** using Fernet symmetric encryption. Supply `profile_id` in a decode
request and the appeal letters are personalised — no placeholder tokens.

Generate an encryption key for production:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
In `DEMO_MODE` (or when `PROFILE_ENCRYPTION_KEY` is unset), an ephemeral key is
auto-generated on startup — fine for demo, not for persistence.

## API surface

| Method | Path | Body / Params | Returns |
|---|---|---|---|
| `POST` | `/api/decode` | `DecodeRequest` | `DecodeResponse` |
| `POST` | `/api/decode/demo` | — | `DecodeResult` |
| `POST` | `/api/decode/upload` | `multipart/form-data` | `DecodeResponse` |
| `POST` | `/api/decode/stream` | `DecodeRequest` | SSE stream |
| `POST` | `/api/decode/upload/stream` | `multipart/form-data` | SSE stream |
| `GET` | `/api/decode/stream/{job_id}` | — | SSE stream (reconnect) |
| `GET` | `/api/documents` | — | `list[DecodeResult]` |
| `GET` | `/api/documents/{id}` | — | `DecodeResult` |
| `POST` | `/api/lawyers/recommend` | `LawyerRecommendRequest` | `LawyerRecommendResponse` |
| `POST` | `/api/profile` | `UserProfileCreate` | `UserProfile` (201) |
| `GET` | `/api/profile/{id}` | — | `UserProfile` |
| `PUT` | `/api/profile/{id}` | `UserProfileUpdate` | `UserProfile` |
| `DELETE` | `/api/profile/{id}` | — | 204 |
| `GET` | `/api/health` | — | `{status, demo_mode, tls_enabled, profile_encryption}` |

## Repo layout

See `CLAUDE.md` for the full contract (frozen response schema, pipeline stage signatures,
external client mock-fallback rules). Key paths:

- `backend/app/schemas.py` / `frontend/src/types.ts` — the frozen response contract (kept in
  lockstep).
- `backend/app/pipeline/` — the eight-stage pipeline:
  - `classify.py` — doc type + jurisdiction
  - `identify.py` — issuing authority / governing body
  - `extract.py` — case-specific facts + plain summary
  - `retrieve.py` — Exa neural search for current governing rules
  - `ground.py` — Firecrawl scrape + passage chunking
  - `verify.py` — entailment against retrieved passages
  - `act.py` — draft appeal letters / deadlines
  - `refer_lawyers.py` — eligibility heuristic for lawyer referrals
  - `ingest.py` — Tesseract OCR for uploaded PDFs and images
  - `run.py` — orchestrates all stages; degrades gracefully per stage
- `backend/app/clients/` — Qwen/Exa/Firecrawl clients, each with a `DEMO_MODE` fixture
  fallback.
- `backend/fixtures/` — canned demo documents and their Qwen/Exa/Firecrawl responses,
  including the defective RTB notice fixture used above.
- `backend/tests/test_smoke.py` — the end-to-end smoke test described above.
- `dev.sh` — boots both dev servers together.

## Environment reference

```
# LLM — DashScope (default) or AWS Bedrock OpenAI-compatible endpoint
QWEN_API_KEY=
QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus
EXA_API_KEY=
FIRECRAWL_API_KEY=
DEMO_MODE=1

# Profile PII encryption at rest (auto-generated ephemeral key in DEMO_MODE)
PROFILE_ENCRYPTION_KEY=

# Optional TLS (local dev with self-signed cert)
SSL_KEYFILE=
SSL_CERTFILE=
FORCE_HTTPS=0

# Comma-separated allowed CORS origins (default: localhost:5173)
CORS_ORIGINS=http://localhost:5173,https://localhost:5173
```

For AWS Bedrock, set `QWEN_BASE_URL=https://bedrock-mantle.<region>.api.aws/v1` and use a
Bedrock API key as `QWEN_API_KEY`.

## Disclaimer

Reywal always populates a `disclaimer` field: *"Information, not legal advice."* It asserts
rights by quoting the source it retrieved, not in its own voice.
