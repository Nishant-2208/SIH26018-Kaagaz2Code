# SIH26018 — Pipeline Upgrade Plan

> Grounded in: live test run (9.7s, OCR conf 94.76%), architecture plan, problem statement fields, and current codebase gaps.

---

## The One-Line Summary

> **The OCR is excellent. The extraction is the gap. The architecture is half-built. The demo-winning piece (review UI) doesn't exist yet.**

---

## Issue Category 1 — LLM Extraction Quality 🔴 Critical

### Issue 1.1 — Mock regex fails on multi-line OCR output
**Observed in live test:**
```
Survey No.:   → split as "Survey\nNo.:\n142/2" by PaddleOCR
Khata Number: → split as "Khata\nKhata Number:\nNumber\n00214"
```
Mock regex expects single-line labels. Result: `survey_number=null`, `khata_number=null`.

**Fix:** Plug in a real LLM (GPT-4o-mini or Gemini 1.5 Flash). The full OCR text is already passed — the LLM reads context across lines trivially.

**Files to change:** `.env` only — `LLM_PROVIDER=openai` + `LLM_API_KEY=sk-...`

---

### Issue 1.2 — Regex captures field labels instead of values
**Observed:** `landowner_name = "Owner (Bhumidhar):"` instead of `"Ram Prasad Yadav"`

**Fix:** Real LLM understands label vs value semantics. Until then, tighten the mock regex lookahead to skip the label token itself.

**Files:** `extractor.py` → `MockExtractor._PATTERNS` (quick fix) or LLM (permanent fix)

---

### Issue 1.3 — No Devanagari numeral normalisation
Hindi land records write `१८७` not `187`. The architecture plan mentions `postprocess.py` but **that file does not exist in the codebase.**

**Fix:** Create `postprocess.py` with Devanagari→ASCII digit mapping:
```python
_DEVA = str.maketrans("०१२३४५६७८९", "0123456789")
def normalise_numerals(text: str) -> str:
    return text.translate(_DEVA)
```
Run this on `ocr.full_text` before passing to the LLM.

**Files:** Create `postprocess.py`, call it in `main.py` step 2→3

---

### Issue 1.4 — No document type auto-detection
Currently `doc_type` defaults to `"land_record"` and the caller must set it manually.
Real documents may be Khatauni, Jamabandi, Mutation Order, or Sale Deed — each needs a different extraction prompt.

**Fix:** Add a simple classifier based on keywords in the first 10 OCR lines:
```python
def detect_doc_type(ocr_text: str) -> str:
    if re.search(r"mutation|namantaran|नामांतरण", ocr_text, re.I): return "mutation_order"
    if re.search(r"jamabandi|जमाबंदी", ocr_text, re.I): return "jamabandi"
    return "land_record"  # default
```

**Files:** `extractor.py` or new `classifier.py`

---

### Issue 1.5 — Single LLM prompt for all document variants
One prompt template for all Indian land record types causes hallucinations on unfamiliar formats.

**Fix:** Separate prompt files per doc type (already planned in architecture):
```
prompts/
  land_record_v1.md
  mutation_order_v1.md
  jamabandi_v1.md
```

**Files:** Create `prompts/` dir, update `extractor.py` to load by `doc_type`

---

## Issue Category 2 — OCR & Preprocessing 🟠 High

### Issue 2.1 — PaddleOCR over-segments dense tables
**Observed:** 96 OCR lines from a simple 11-row table. Each cell gets split into 2–4 fragments. This is why regex fails and why the LLM prompt gets cluttered.

**Fix (short term):** Post-process OCR lines — group fragments that share the same Y-band into logical rows:
```python
def group_by_row(lines: list[OcrLine], band_px=15) -> list[str]:
    # sort by top, bin into rows, join each row left-to-right
```

**Fix (long term):** Switch PaddleOCR to table mode for structured form documents.

**Files:** `ocr_engine.py` → add `group_by_row()`, called in `extract_text()`

---

### Issue 2.2 — No PDF support
**Noted in backlog.** `PyMuPDF` (`fitz`) is **already installed** in the Docker image.

**Fix:** 3 changes:
1. `preprocessor.py` → add `pdf_to_images(raw: bytes) -> list[np.ndarray]` using `fitz`
2. `main.py` → add `"application/pdf"` to `ACCEPTED_MIME`, loop over pages
3. `main.py` → merge multi-page OCR text, aggregate confidence scores

**Files:** `preprocessor.py`, `main.py`

---

### Issue 2.3 — OCR weights not baked into Docker image
**Observed during build:** `pyclipper` zlib error crashed weight prefetch → weights download on every cold start (~30–60s delay).

**Fix:** Pre-download weights via direct URL in the Dockerfile before importing paddleocr:
```dockerfile
RUN python -m pip install pyclipper==1.3.0.post3 --force-reinstall && \
    python -c "from paddleocr import PaddleOCR; ..."
```

**Files:** `Dockerfile`

---

### Issue 2.4 — Handwritten Devanagari degrades accuracy
Printed records: PaddleOCR ≥90% confidence. Handwritten entries (mutation dates, owner names added by hand): often 40–60%.

**Fix:**
- Flag lines with `conf < 0.55` as `handwritten_suspect` in the OCR result
- Route documents where `>30%` of lines are low-confidence to `OCR_INPUT=clahe` path (already exists)
- Longer term: fine-tune PaddleOCR on Hindi handwriting dataset (IIIT-HW-Dev)

**Files:** `ocr_engine.py` → add `handwritten_suspect` flag to `OcrLine`

---

### Issue 2.5 — Blur detection threshold too aggressive
`BLUR_THRESHOLD=60.0` flags mobile camera scans as `likely_illegible=True`, which caps `overall_confidence` at 0.8× even when text is readable.

**Fix:** Raise default to `100.0`, or compute threshold relative to image resolution.

**Files:** `preprocessor.py`, `.env.example`

---

## Issue Category 3 — Architecture Gaps 🔴 Critical

### Issue 3.1 — No main backend (FastAPI API service)
The AI microservice is complete. The **main backend** (`apps/api/`) — which handles auth, job management, storage, and frontend-facing REST API — **does not exist yet.**

Without it: no auth, no job tracking, no file storage, no audit log, frontend has nothing to call.

**Fix (Priority 1):** Scaffold `apps/api/` with FastAPI minimum viable:
```
routes/records.py   — POST /api/v1/records/upload, GET /jobs/:id
routes/auth.py      — POST /register, POST /login → JWT
services/ai_client.py — calls AI microservice at :8001
models/             — SQLModel: User, Document, Job, AuditLog
```

---

### Issue 3.2 — No frontend
No UI exists. The demo needs:
- Upload page (drag & drop scan)
- Job polling / progress indicator
- Side-by-side view: original scan ↔ extracted fields
- Flagged fields highlighted amber
- Inline correction → PATCH → audit log
- Verifier queue filtered by confidence

**Fix:** React + Vite SPA (`apps/web/`) — architecture plan already specifies this fully.

---

### Issue 3.3 — No database
No persistence layer. Extractions are returned in the HTTP response and lost.

**Fix:** PostgreSQL via SQLModel. Three core tables:
```sql
documents (id, filename, s3_key, doc_type, uploaded_by, created_at)
jobs      (id, document_id, status, extraction JSONB, ocr_confidence, llm_mode)
audit_log (id, job_id, field, old_value, new_value, corrected_by, corrected_at)
```

---

### Issue 3.4 — No file storage
Uploaded images are read into memory and discarded. Original scans must be stored for the review UI and re-processing.

**Fix:** MinIO (local dev) / Cloudflare R2 (prod) — same S3 SDK, one env var swap.

**Files:** `apps/api/services/storage.py`

---

### Issue 3.5 — No docker-compose.yml for the full stack
Only the AI microservice has a Dockerfile. Running the full system requires starting 4 services manually.

**Fix:** `infra/docker-compose.yml`:
```yaml
services:
  postgres:   image: postgres:16
  minio:      image: minio/minio
  ai-service: build: ./files        # port 8001
  api:        build: ./apps/api     # port 8080
```

---

## Issue Category 4 — Data Integrity & Business Rules 🟠 High

### Issue 4.1 — No duplicate survey number detection
Same document uploaded twice = duplicate land record. No dedup check exists.

**Fix:** On job completion, check DB for existing `survey_number + district + tehsil` combo. Flag as `DUPLICATE_SUSPECT`.

**Files:** `apps/api/validation/business_rules.py`

---

### Issue 4.2 — No tehsil ↔ district cross-validation
If OCR reads `tehsil=Sadar, district=Kanpur` but Sadar is only in Varanasi — that's an OCR error with no flag.

**Fix:** Ship a reference JSON of valid tehsil→district mappings. Score mismatch as `reason: regex_mismatch`.

**Files:** `apps/api/validation/business_rules.py`, `data/tehsil_district_map.json`

---

### Issue 4.3 — Plot area unit inconsistency
Records mix Hectare, Acre, Bigha, Biswa, Sq.m. Extractor returns raw string with no normalisation.

**Fix:** Parse and normalise to canonical unit (Hectare):
```python
def normalise_area(raw: str) -> dict:
    return {"value": 0.486, "unit": "hectare", "display": "0.486 Hectare"}
```

**Files:** New `unit_parser.py`, called from `extractor.py`

---

### Issue 4.4 — Immutable audit log not enforced
Field corrections must be append-only for legal admissibility. Not built yet.

**Fix:** PostgreSQL RULE or application enforcement — only INSERT allowed on `audit_log`, no UPDATE or DELETE.

---

## Issue Category 5 — Security 🟠 High

### Issue 5.1 — LLM_API_KEY in plain .env
In production, use Docker secrets or a secret manager. Never commit `.env` to git.

### Issue 5.2 — Unredacted PII sent to cloud LLM
Owner names and registration numbers cross jurisdictional boundary to OpenAI/Gemini. Violates DPDP Act 2023 for production.

**Fix (proto):** Redact `landowner_name` before LLM call.
**Fix (prod):** `LLM_PROVIDER=local` (Ollama) — PII never leaves the machine.

### Issue 5.3 — No HTTPS in local dev
Fine for demo. For any public URL, add Nginx + Let's Encrypt or Cloudflare proxy.

---

## Issue Category 6 — Demo Readiness 🟡 Medium

### Issue 6.1 — No sample land record images in repo
`README.md` references `samples/khatauni_01.jpg` — that folder doesn't exist.

**Fix:** Add `samples/` with: 1 clean, 1 skewed, 1 blurry, 1 handwritten. These are the demo images.

### Issue 6.2 — No DEMO_SCRIPT.md
Step-by-step narration for judges:
1. Upload clean scan → `status: ok`
2. Upload blurry scan → `status: needs_review`, show flagged fields
3. Correct a field → audit log
4. Show `mode: local` badge

### Issue 6.3 — No pre-recorded video fallback
Venue Wi-Fi dies at every hackathon. 90-second screen recording is non-negotiable.

### Issue 6.4 — /docs Swagger UI unprotected
Disable or password-protect before any public deployment.

---

## Upgrade Priority Table

| Priority | Upgrade | Impact | Effort |
|---|---|---|---|
| 🔴 P0 | Connect real LLM (GPT/Gemini) | All 11 fields extracted correctly | 10 min |
| 🔴 P0 | Scaffold main backend (FastAPI API) | Enables frontend + persistence | 2 days |
| 🔴 P0 | PostgreSQL + job table | Extraction persists | 1 day |
| 🔴 P0 | docker-compose.yml full stack | One command to run everything | 2 hrs |
| 🟠 P1 | OCR row-grouping (fix multi-line splits) | Regex mock works, LLM prompt cleaner | 3 hrs |
| 🟠 P1 | PDF support | Accepts real govt documents | 4 hrs |
| 🟠 P1 | Devanagari numeral normalisation (`postprocess.py`) | Fixes numeric field extraction | 1 hr |
| 🟠 P1 | MinIO file storage | Originals preserved for review UI | 3 hrs |
| 🟠 P1 | React frontend skeleton | Upload + job poll + field display | 2 days |
| 🟡 P2 | Review UI (side-by-side + inline edit) | **The demo differentiator** | 1 day |
| 🟡 P2 | Doc type auto-detection | No manual `doc_type` param needed | 2 hrs |
| 🟡 P2 | Tehsil↔district cross-validation | Catches OCR geography errors | 3 hrs |
| 🟡 P2 | Plot area unit normaliser | Consistent area values | 2 hrs |
| 🟡 P2 | Sample images in `samples/` | Demo images + test fixtures | 1 hr |
| 🟢 P3 | Ollama local LLM adapter | Air-gap demo story | 3 hrs |
| 🟢 P3 | Bake OCR weights into Docker image | Eliminate 30–60s cold start | 2 hrs |
| 🟢 P3 | DEMO_SCRIPT.md + screen recording | Judge-facing polish | 2 hrs |
| 🟢 P3 | PII redaction before cloud LLM | DPDP Act 2023 compliance | 3 hrs |

---

## What Actually Wins SIH — The Three Things That Matter

```
1. A working end-to-end vertical slice (upload → extraction → display)
   Even with mock LLM if needed. Judges care that it WORKS, not that it's perfect.

2. The review UI with flagged fields
   Side-by-side scan + amber highlights + inline correction = visible AI value.
   This is what no other team will build in time.

3. The air-gap story
   "Flip one env var and no PII ever leaves the building."
   Say it with the mode badge visible on screen.
```
