# Kaagaz2Code — Implementation Document
### SIH26018 · Smart Land Record Digitization Platform

> **Purpose**: Complete technical blueprint to bring Kaagaz2Code from Phase 1 (foundation backend + mocked frontend) to a fully integrated fullstack application.
> **Audience**: Development team. Written for immediate execution.

---

## Table of Contents

1. [Current State Audit](#1-current-state-audit)
2. [Architecture Overview](#2-architecture-overview)
3. [Gap Analysis](#3-gap-analysis)
4. [Open Questions](#4-open-questions)
5. [Phase 2 — Backend: Domain Models and Schemas](#5-phase-2)
6. [Phase 3 — Backend: API Routes](#6-phase-3)
7. [Phase 4 — Backend: Service Layer](#7-phase-4)
8. [Phase 5 — OCR and AI Pipeline](#8-phase-5)
9. [Phase 6 — Frontend: Auth Wiring](#9-phase-6)
10. [Phase 7 — Integration](#10-phase-7)
11. [Phase 8 — Testing](#11-phase-8)
12. [Execution Order](#12-execution-order)
13. [File Change Index](#13-file-change-index)

---

## 1. Current State Audit

### 1.1 Frontend — Well Ahead (mock-only)

The frontend is a complete UI prototype. All 10 pages exist, all types are defined, and the service
layer already knows the real API URLs — guarded by VITE_USE_MOCKS=true.

| Area | File | Status |
|---|---|---|
| Routing | src/App.tsx | Complete — all 10 pages routed |
| Type system | src/api/types.ts | Complete — all domain types (430 lines) |
| Service layer | src/api/services.ts | Complete — all calls have real URLs, USE_MOCKS guarded |
| Mock data | src/api/mockData.ts | Complete — rich realistic data |
| Login page | src/pages/LoginPage.tsx | setTimeout only — no real API call, no token storage |
| Officer layout | src/components/shared/OfficerLayout.tsx | No auth guard, hardcoded user OP-001 |
| Auth context | — | MISSING |
| Token storage | — | MISSING |
| frontend/.env | — | MISSING |

**All 10 pages present:** LoginPage, UploadPage, QueuePage, ReviewPage, RecordDetailPage,
DiscrepancyPage, MultilingualPage, MapPage, AdminPage, LookupPage

**API config in services.ts:**
`
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';
const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== 'false';
`

**CRITICAL**: Frontend uses /api but backend is on /api/v1. The .env must set:
VITE_API_BASE_URL=http://localhost:8000/api/v1

---

### 1.2 Backend — Phase 1 Only (foundation)

| Area | File | Status |
|---|---|---|
| FastAPI app + middleware | app/main.py | Complete |
| Config | app/core/config.py | Complete |
| Security (JWT + bcrypt) | app/core/security.py | Complete |
| Logging | app/core/logging.py | Complete |
| DB session | app/db/database.py | Complete |
| User ORM model | app/db/models/user.py | Complete |
| Auth dependency + RBAC | app/api/dependencies.py | Complete |
| Auth routes | app/api/routes/auth.py | Complete |
| System/health routes | app/api/routes/system.py | Complete |
| Auth service | app/services/auth_service.py | Complete |
| Auth schemas | app/schemas/auth.py | Complete |
| Docker infra | docker-compose.yml | Complete |
| Alembic migrations | alembic/ | Complete — users table migrated |
| Domain ORM models | — | ALL MISSING |
| Domain API routes | — | ALL MISSING |
| Domain services | — | ALL MISSING |
| Domain schemas | — | ALL MISSING |
| OCR integration | app/integrations/ocr/ | Empty folder |
| AI integration | app/integrations/ai/ | Empty folder |

**Role mismatch (must resolve):**
- Backend: 4 roles — citizen, officer, reviewer, admin
- Frontend: 3 roles — citizen, officer, admin (reviewer missing)

---

## 2. Architecture Overview

`
Browser (React 19 + TypeScript + Vite + Tailwind) port 5173
  |
  | HTTPS REST + Bearer JWT
  v
FastAPI + Uvicorn (Python 3.x) port 8000
  /api/v1/auth/*          login, refresh, me
  /api/v1/records/*       CRUD + review + audit
  /api/v1/batches/*       upload + list
  /api/v1/queue           review queue
  /api/v1/discrepancies/* discrepancy detail
  /api/v1/parcels         map pins
  /api/v1/admin/*         stats + officers
  /api/v1/lookup          public citizen search
  |               |
  | SQLAlchemy     | boto3/S3
  v               v
PostgreSQL 16   MinIO (9000/9001)
`

**Document upload flow:**
1. User uploads file -> POST /api/v1/batches/upload
2. File saved to MinIO (batches/{batch_id}/{filename})
3. LandRecord stub created (status=pending_review)
4. OCR provider called -> ExtractedField rows created with confidence scores
5. Record appears in /queue for officer review

---

## 3. Gap Analysis

### 3.1 Missing API Endpoints

All 15 calls that frontend/src/api/services.ts already makes but backend does not serve:

| Function | Method | Path |
|---|---|---|
| getRecords() | GET | /records |
| getRecordById(id) | GET | /records/:id |
| getExtractedFields(recordId) | GET | /records/:id/fields |
| updateExtractedField(...) | PATCH | /records/:id/fields/:fieldId |
| submitReviewDecision(...) | PATCH | /records/:id/review |
| getAuditTrail(recordId) | GET | /records/:id/audit |
| getMultilingualFields(recordId) | GET | /records/:id/multilingual |
| getBatches() | GET | /batches |
| (UploadPage — inferred) | POST | /batches/upload |
| getDiscrepancy(id) | GET | /discrepancies/:id |
| getQueueItems() | GET | /queue |
| getParcels() | GET | /parcels |
| getAdminStats() | GET | /admin/stats |
| getOfficers() | GET | /admin/officers |
| getLookupResults() | GET | /lookup |

### 3.2 Frontend Gaps

| Gap | Location |
|---|---|
| No auth context / token storage | Global |
| No Authorization: Bearer header in request() | services.ts |
| LoginPage uses setTimeout not real API | LoginPage.tsx |
| OfficerLayout has hardcoded OP-001 user | OfficerLayout.tsx |
| No frontend/.env file (wrong base URL) | Root |
| reviewer role missing in UserRole type | types.ts |

---

## 4. Open Questions

Decide these before execution begins:

**Q1 — OCR Engine**
- A: Tesseract (open-source, offline, already referenced in LoginPage badge) — RECOMMENDED
- B: Google Cloud Vision API (better Hindi accuracy, paid)
- C: Azure AI Vision (paid)
The OCR_PROVIDER env var is already in config.py for easy switching.

**Q2 — AI Extraction Provider**
- A: Anthropic Claude — RECOMMENDED (ANTHROPIC_API_KEY already in .env.example)
- B: Google Gemini

**Q3 — Role Alignment (must decide)**
- A: Drop reviewer from backend, merge into officer
- B: Add reviewer to frontend UserRole type — RECOMMENDED (proper RBAC)

**Q4 — Production Object Storage**
- A: Keep MinIO (works offline for demo) — RECOMMENDED
- B: Point to AWS S3 / GCS

**Q5 — Multilingual Pipeline**
- A: Translation API (Google Translate / DeepL)
- B: Store OCR output as-is (no translation)
- C: Claude/Gemini outputs both source (Hindi) and normalized (English) in one pass — RECOMMENDED

---

## 5. Phase 2 — Backend: Domain Models and Schemas

### 5.1 New ORM Models

All in ackend/app/db/models/

#### land_record.py [NEW]
Table: land_records
- id: String(50) PK (e.g. "REC-8924")
- khasra_no: String(100) NOT NULL, indexed
- owner_name: String(255) NOT NULL, indexed
- area: String(50) NOT NULL
- area_unit: String(30) default "Hectares"
- registration_date: String(50) nullable
- village: String(100) NOT NULL, indexed
- tehsil: String(100) nullable
- district: String(100) nullable
- status: Enum(pending_review|in_review|verified|flagged|discrepancy|locked) indexed
- overall_confidence: Float nullable
- land_type: String(100) nullable
- source_image_url: Text nullable
- lat: Float nullable (for MapPage)
- lng: Float nullable (for MapPage)
- batch_id: String(50) FK -> batches.id, indexed
- assigned_officer_id: UUID FK -> users.id nullable
- created_at: DateTime(timezone=True)
- updated_at: DateTime(timezone=True) onupdate
- Relationships: fields (ExtractedField), audit_trail (AuditTrailEntry)

#### extracted_field.py [NEW]
Table: extracted_fields
- id: UUID PK
- record_id: String(50) FK -> land_records.id ON DELETE CASCADE, indexed
- field_id: String(50) slug e.g. "F_OWNER"
- label: String(100)
- value: Text
- edited_value: Text nullable
- confidence: Float (0-100)
- confidence_level: Enum(high|medium|low)
- verification_status: Enum(pending|verified|review_required|review_recommended|corrected) default "pending"
- warning: Text nullable
- source_language: String(50) nullable
- source_value: Text nullable (original script e.g. Hindi Devanagari)
- normalized_value: Text nullable (transliterated/translated English)
- bounding_box: JSONB nullable {x, y, width, height}

#### batch.py [NEW]
Table: atches
- id: String(50) PK e.g. "BATCH-042"
- name: String(255)
- document_count: Integer default 0
- processed_count: Integer default 0
- total_count: Integer default 0
- status: Enum(uploading|processing|completed|failed) default "uploading"
- created_at: DateTime(timezone=True)

#### audit_trail.py [NEW]
Table: udit_trail
- id: UUID PK
- record_id: String(50) FK -> land_records.id ON DELETE CASCADE, indexed
- action: String(100)
- actor: String(255)
- actor_role: String(50)
- timestamp: DateTime(timezone=True)
- details: Text nullable
- old_value: Text nullable
- new_value: Text nullable
- field_changed: String(100) nullable
- reason: Text nullable
- confidence: Float nullable
- model_version: String(50) nullable
- icon: String(50) default "history"
- RULE: INSERT ONLY — never update or delete rows

#### discrepancy.py [NEW]
Table: discrepancies
- id: String(50) PK e.g. "DISC-001"
- task_id: String(50)
- record_a: JSONB (scanned document side)
- record_b: JSONB (existing DB entry side)
- flagged_reason: Text
- flagged_fields: ARRAY(String)
- confidence_score: Float
- ocr_engine: String(100) nullable
- land_record_id: String(50) FK -> land_records.id nullable
- created_at: DateTime(timezone=True)

#### __init__.py [MODIFY]
`python
from app.db.models.user import User
from app.db.models.batch import Batch
from app.db.models.land_record import LandRecord
from app.db.models.extracted_field import ExtractedField
from app.db.models.audit_trail import AuditTrailEntry
from app.db.models.discrepancy import Discrepancy
__all__ = ["User","Batch","LandRecord","ExtractedField","AuditTrailEntry","Discrepancy"]
`

**Run migration after all models are written:**
`ash
cd backend
alembic revision --autogenerate -m "add core domain models"
alembic upgrade head
`

---

### 5.2 Pydantic Schemas — app/schemas/records.py [NEW]

All response schemas:
- Use camelCase field names to match frontend types.ts EXACTLY
- Include model_config = {"from_attributes": True} for ORM -> Pydantic mapping

Schemas needed:
- ExtractedFieldResponse: fieldId, label, value, editedValue, confidence, confidenceLevel, verificationStatus, warning, sourceLanguage, sourceValue, normalizedValue, boundingBox
- UpdateFieldRequest: value, updatedBy (optional), reason (optional)
- LandRecordResponse: id, khasraNo, ownerName, area, areaUnit, registrationDate, village, tehsil, district, status, overallConfidence, landType, sourceImageUrl, batchId, assignedOfficer, createdAt, updatedAt, fields: list[ExtractedFieldResponse]
- ReviewDecisionRequest: decision (approve|reject|request_changes), reviewerName, comment, reason
- BatchResponse: id, name, documentCount, processedCount, totalCount, status, createdAt
- QueueItemResponse: id, khasraNo, ownerName, village, district, status, confidence, assignedTo, createdAt, batchId
- AuditTrailEntryResponse: id, action, actor, actorRole, timestamp, details, oldValue, newValue, fieldChanged, icon
- DiscrepancyResponse: id, taskId, recordA, recordB, flaggedReason, flaggedFields, confidenceScore, ocrEngine
- MultilingualFieldResponse: fieldId, label, sourceLanguage, sourceValue, normalizedLanguage, normalizedValue, isVerified
- ParcelPinResponse: id, khasraNo, ownerName, lat, lng, status, area, village
- AdminStatsResponse: accuracyRate, accuracyTrend, totalRecords, pendingConflicts, monthlyVolume, trendData
- OfficerResponse: id, name, status, throughput
- LookupResultResponse: khasraNo, ownerName, area, village, tehsil, district, landType, status

---

## 6. Phase 3 — Backend: API Routes

Rule: Router files are thin. All logic goes in service functions.

### app/api/routes/records.py [NEW]
`
GET    /records                              List (filters: status, batch_id, search, skip, limit)
GET    /records/{record_id}                  Single record with embedded fields
GET    /records/{record_id}/fields           Extracted fields only
PATCH  /records/{record_id}/fields/{field_id}  Correct a field value
PATCH  /records/{record_id}/review           Submit approve/reject/request_changes
GET    /records/{record_id}/audit            Audit trail
GET    /records/{record_id}/multilingual     Multilingual field view
`
Auth: GET routes = get_current_user; PATCH routes = require_roles("officer","reviewer","admin")

### app/api/routes/batches.py [NEW]
`
GET   /batches           List all batches (newest first)
POST  /batches/upload    multipart/form-data: files+batch_name -> creates batch + triggers OCR
`
Upload validates: file size <= MAX_UPLOAD_SIZE_MB, extension in allowed list
Saves to MinIO: batches/{batch_id}/{filename}
Auth: require_roles("officer","admin")

### app/api/routes/queue.py [NEW]
`
GET  /queue   Records with status in [pending_review, in_review, flagged, discrepancy]
`
Order: created_at ASC (oldest first). Supports status filter + pagination.
Auth: require_roles("officer","reviewer","admin")

### app/api/routes/discrepancies.py [NEW]
`
GET  /discrepancies/{discrepancy_id}   Single discrepancy detail
`
Auth: require_roles("officer","reviewer","admin")

### app/api/routes/admin.py [NEW]
`
GET  /admin/stats     AdminStatsResponse
GET  /admin/officers  list[OfficerResponse]
`
Stats: totalRecords=COUNT(*), accuracyRate=AVG(overall_confidence) where verified,
       pendingConflicts=COUNT(*) where flagged/discrepancy, monthlyVolume=this month's count
Auth: require_roles("admin")

### app/api/routes/map.py [NEW]
`
GET  /parcels   list[ParcelPinResponse]   (records with lat/lng populated)
`
Auth: open or authenticated (decide)

### app/api/routes/lookup.py [NEW]
`
GET  /lookup?q={term}   list[LookupResultResponse]
`
Only verified records. Matches khasra_no (prefix) + owner_name (ILIKE).
Auth: PUBLIC — no token required

### app/main.py [MODIFY]
Register all new routers with prefix=settings.API_V1_PREFIX

---

## 7. Phase 4 — Backend: Service Layer

Rule: Route handlers call services. Services call DB and OCR/AI. No raw SQLAlchemy in routes.

### app/services/record_service.py [NEW]
- get_records(db, status, batch_id, search, skip, limit) -> list[LandRecord]
- get_record_by_id(db, record_id) -> LandRecord | None
- update_field(db, record_id, field_id, value, updated_by, reason) -> ExtractedField
  [find field -> set edited_value + verification_status="corrected" -> audit_service.log_event -> return field]
- submit_review(db, record_id, decision, reviewer, comment) -> LandRecord
  [find record -> map: approve->verified, reject->flagged, request_changes->pending_review -> audit -> return]
- get_multilingual_fields(db, record_id) -> list[ExtractedField]

### app/services/batch_service.py [NEW]
- get_batches(db) -> list[Batch]
- create_batch(db, name, files, settings) -> Batch
  [gen ID -> save to MinIO -> create Batch row -> create LandRecord stubs -> trigger OCR -> update status]

### app/services/admin_service.py [NEW]
- get_stats(db) -> AdminStats
- get_officers(db) -> list[Officer]  (users where role in officer/reviewer)

### app/services/audit_service.py [NEW]
- log_event(db, record_id, action, actor, icon, **kwargs) -> AuditTrailEntry
  [INSERT ONLY — never update/delete. kwargs: old_value, new_value, field_changed, details, confidence, model_version, reason]

### app/services/ocr_service.py [NEW]
- process_record(db, record, image_bytes, settings) -> list[ExtractedField]
  [load OCR provider -> extract() -> load AI provider -> structure() -> create ExtractedField rows -> update confidence -> audit log]

---

## 8. Phase 5 — OCR and AI Pipeline

Pattern: ABC interface + mock provider + factory function. Swap via env var.

### app/integrations/ocr/base.py [NEW]
`python
@dataclass
class OCRField:
    field_id: str; label: str; value: str; confidence: float
    warning: str | None = None; bounding_box: dict | None = None

@dataclass
class OCRResult:
    raw_text: str; fields: list[OCRField]

class BaseOCRProvider(ABC):
    @abstractmethod
    def extract(self, image_bytes: bytes, mime_type: str) -> OCRResult: ...
`

### app/integrations/ocr/mock_provider.py [NEW]
Returns the same 7 fields as mockExtractedFields in frontend/src/api/mockData.ts.
Used during development before a real OCR engine is integrated.

### app/integrations/ocr/factory.py [NEW]
`python
def get_ocr_provider(name: str) -> BaseOCRProvider:
    if name == "mock": return MockOCRProvider()
    # elif name == "tesseract": return TesseractProvider()
    raise ValueError(f"Unknown OCR provider: {name}")
`

### app/integrations/ai/ — same pattern [NEW]
AI provider receives OCRResult, returns structured fields with:
- source_value: original text (e.g. Hindi Devanagari)
- normalized_value: transliterated/translated English
This single pass produces all data needed for MultilingualPage.

---

## 9. Phase 6 — Frontend: Auth Wiring

### frontend/.env [NEW]
`
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_USE_MOCKS=true
`
Keep VITE_USE_MOCKS=true during development. Flip to false in Phase 7.

### src/contexts/AuthContext.tsx [NEW]
`	s
interface AuthContextValue {
  user: User | null;
  accessToken: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}
`
Implementation:
- Store accessToken + refreshToken in localStorage
- On mount: call GET /auth/me to rehydrate user state from stored token
- On any 401: attempt POST /auth/refresh with stored refreshToken
- If refresh fails: logout() + redirect to /login

### src/main.tsx [MODIFY]
Wrap App with AuthProvider.

### src/api/services.ts [MODIFY]
Change 1 — Add Authorization header in request():
`	s
const token = localStorage.getItem('accessToken');
headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: Bearer  } : {}) }
`
Change 2 — Add loginUser() and getMe() service functions calling real backend endpoints.

### src/api/types.ts [MODIFY]
- Add reviewer to UserRole: 'officer' | 'reviewer' | 'admin' | 'citizen'
- Add TokenResponse interface: {access_token, refresh_token, token_type}
- Add UserResponse interface: {id, email, full_name, role, is_active, created_at}

### src/pages/LoginPage.tsx [MODIFY]
Replace setTimeout mock with real API call:
`	s
// Before: setTimeout(() => { navigate(route); }, 400);
// After:
const tokens = await loginUser(userId, password);
localStorage.setItem('accessToken', tokens.access_token);
localStorage.setItem('refreshToken', tokens.refresh_token);
navigate(activeConfig.route);
`
NOTE: Form currently labels username field "Service ID / Pen No." — change to "Email Address"
since the backend expects an email for POST /auth/login.

### src/components/shared/OfficerLayout.tsx [MODIFY]
Add auth guard:
`	sx
const { isAuthenticated, user } = useAuth();
if (!isAuthenticated) return <Navigate to="/login" replace />;
`
Replace hardcoded "Revenue Officer" / "OP-001" with user.full_name and user.role.

---

## 10. Phase 7 — Integration

Steps:
1. Set VITE_USE_MOCKS=false in frontend/.env
2. cd backend && docker compose up --build
3. make seed  (creates test users)
4. cd frontend && npm run dev
5. Open http://localhost:5173

Verify each page (check DevTools Network — all 200s, no console errors):

| Page | Endpoints |
|---|---|
| LoginPage | POST /api/v1/auth/login |
| UploadPage | POST /batches/upload, GET /batches |
| QueuePage | GET /queue |
| ReviewPage | GET /records/:id, GET .../fields, PATCH .../fields/:id, PATCH .../review |
| RecordDetailPage | GET /records/:id, GET .../audit |
| DiscrepancyPage | GET /discrepancies/:id |
| MultilingualPage | GET /records/:id/multilingual |
| MapPage | GET /parcels |
| AdminPage | GET /admin/stats, GET /admin/officers |
| LookupPage | GET /lookup?q=... |

---

## 11. Phase 8 — Testing

### Backend Unit Tests (tests/unit/)
- test_record_service.py: get_records filters, update_field, submit_review decision mapping
- test_batch_service.py: create_batch saves file and creates LandRecord stub
- test_audit_service.py: log_event creates row, row is immutable
- test_ocr_mock.py: MockOCRProvider returns 7 expected fields with valid confidence levels

### Backend API Tests (tests/api/) — httpx + pytest
- test_auth.py: valid login, bad credentials 401, /auth/me with/without token, refresh token
- test_records.py: list, filter, single, PATCH field, PATCH review decision mapping
- test_batches.py: upload valid PDF, list batches
- test_queue.py: only returns pending/flagged/discrepancy records
- test_admin.py: stats computation, 403 for non-admin
- test_lookup.py: search returns verified records, no auth required

Run:
`ash
cd backend
make test
# or: pytest -v --tb=short
`

---

## 12. Execution Order

`
Phase 2 — ORM Models + Schemas              ~2-3 hours
  |
Phase 3 — API Routes (9 router files)       ~3-4 hours
  |
Phase 4 — Service Layer (5 service files)   ~2-3 hours
  |
  +-- Phase 5 (OCR/AI mock)  -- Phase 6 (Frontend auth)   ~2 hours each (parallel)
  |
Phase 7 — Integration (flip VITE_USE_MOCKS) ~1-2 hours
  |
Phase 8 — Tests                             ~2-3 hours
`

Total estimated: 14-18 hours.
Critical path: Phases 2 -> 3 -> 4 (complete these first).
Phases 5 and 6 can be developed in parallel.

---

## 13. File Change Index

### Backend — New Files

| File | Description |
|---|---|
| app/db/models/land_record.py | LandRecord ORM model |
| app/db/models/extracted_field.py | ExtractedField ORM model |
| app/db/models/batch.py | Batch ORM model |
| app/db/models/audit_trail.py | AuditTrailEntry ORM model |
| app/db/models/discrepancy.py | Discrepancy ORM model |
| app/schemas/records.py | All domain Pydantic schemas |
| app/api/routes/records.py | Records + fields + review + audit + multilingual |
| app/api/routes/batches.py | Batch list + file upload |
| app/api/routes/queue.py | Review queue |
| app/api/routes/discrepancies.py | Discrepancy detail |
| app/api/routes/admin.py | Admin stats + officers |
| app/api/routes/map.py | Parcel map pins |
| app/api/routes/lookup.py | Public citizen lookup |
| app/services/record_service.py | Record business logic |
| app/services/batch_service.py | Batch + upload business logic |
| app/services/admin_service.py | Stats + officer queries |
| app/services/audit_service.py | Immutable audit log writer |
| app/services/ocr_service.py | OCR orchestration |
| app/integrations/ocr/base.py | BaseOCRProvider ABC |
| app/integrations/ocr/mock_provider.py | Mock OCR for dev |
| app/integrations/ocr/factory.py | Provider loader |
| app/integrations/ai/base.py | BaseAIProvider ABC |
| app/integrations/ai/mock_provider.py | Mock AI for dev |
| app/integrations/ai/factory.py | Provider loader |
| alembic/versions/<hash>_add_core_domain_models.py | Migration |

### Backend — Modified Files

| File | Change |
|---|---|
| app/db/models/__init__.py | Export all new models for Alembic |
| app/main.py | Register 7 new routers |

### Frontend — New Files

| File | Description |
|---|---|
| src/contexts/AuthContext.tsx | JWT auth state, login, logout, auto-refresh |
| .env | VITE_API_BASE_URL + VITE_USE_MOCKS |

### Frontend — Modified Files

| File | Change |
|---|---|
| src/main.tsx | Wrap App with AuthProvider |
| src/api/services.ts | Authorization header + loginUser() + getMe() |
| src/api/types.ts | Add reviewer to UserRole, add TokenResponse + UserResponse |
| src/pages/LoginPage.tsx | Wire form to real login() API call |
| src/components/shared/OfficerLayout.tsx | Auth guard + dynamic user from context |

---

*Last updated: August 2026 - Kaagaz2Code SIH26018*
