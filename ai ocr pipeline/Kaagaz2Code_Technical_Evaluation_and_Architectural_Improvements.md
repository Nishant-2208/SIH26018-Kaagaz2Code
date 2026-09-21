# Kaagaz2Code — SIH26018 Technical Evaluation & Required Architectural Improvements

## Executive Summary

If evaluated for **Smart India Hackathon (SIH)** or as an **enterprise solution**, Kaagaz2Code currently demonstrates a technically strong AI/OCR microservice, but the overall system is not yet a complete product.

The core AI engine is mature and well-designed, particularly in OCR preprocessing, semantic extraction, confidence scoring, and API engineering. However, the wider product architecture still has major gaps around asynchronous processing, table/layout understanding, Human-in-the-Loop (HITL), persistence, security/data sovereignty, deduplication, and the end-to-end government clerk workflow.

> **Key takeaway:**  
> **AI handles the scale; humans handle the uncertainty.**  
> The next phase should focus less on making OCR perfect and more on completing the operational workflow around it.

---

# 1. Core AI Engine — OCR + LLM

## Evaluation: 8.5 / 10

### What Is Good

#### 1.1 Correct AI Architecture

Using **PaddleOCR** for high-fidelity text extraction and then passing the extracted text to an **LLM** for semantic understanding is a modern approach to Intelligent Document Processing (IDP).

This avoids the alternative of maintaining hundreds of hard-coded regular expressions for every possible government document format.

The basic pipeline is:

```text
Scanned Document
       ↓
OpenCV Preprocessing
       ↓
PaddleOCR
       ↓
Raw OCR Text
       ↓
LLM Semantic Extraction
       ↓
Structured Land Record
       ↓
Validation + Confidence Scoring
```

This separation is useful because:

- OCR focuses on visual-to-text conversion.
- The LLM focuses on semantic interpretation.
- Business rules remain separate from both.
- The extraction layer can evolve independently from the OCR engine.

---

### 1.2 Confidence Scoring

The confidence-scoring approach is one of the strongest parts of the architecture.

A combined score such as:

```text
Final Confidence
    = OCR Confidence
    × Field Extraction Confidence
    + Business Rule Validation
```

acknowledges an important reality:

> OCR is probabilistic and should not automatically be treated as truth.

Low-confidence or conflicting records can therefore be routed to a human reviewer instead of being automatically accepted.

This supports the intended workflow:

```text
High Confidence + Valid
        ↓
    Auto Approve

Low Confidence / Conflict
        ↓
   Human Review
```

---

### 1.3 Image Preprocessing

The preprocessing pipeline demonstrates good engineering maturity.

Relevant techniques include:

- Skew correction
- CLAHE
- Adaptive thresholding
- Morphological operations
- Noise reduction
- Image normalization

Adaptive binarization techniques such as **Sauvola** or **Niblack** can be particularly useful for degraded government documents where lighting, paper quality, scanning quality, and background noise vary significantly.

The important principle is:

```text
Better Image
    ↓
Better OCR
    ↓
Better Extraction
    ↓
Better Validation
```

---

## What Needs Improvement

### 1.4 Table / Layout Understanding

The largest AI limitation is **document structure awareness**.

A government land document may contain tables such as:

- Khasra details
- Owner information
- Plot numbers
- Area measurements
- Mutation details
- Survey information

If PaddleOCR returns dozens of fragmented text lines from a table, the textual information may technically be correct while the relationships between rows and columns are destroyed.

For example:

```text
Original:

| Khasra | Owner | Area | Village |
|--------|-------|------|---------|
| 102/1  | Ram   | 1.25 | ABC     |
| 102/2  | Shyam | 0.75 | ABC     |
```

may become:

```text
102/1
Ram
1.25
ABC
102/2
Shyam
0.75
ABC
```

The text exists, but the structure has been lost.

### Required Improvement

Introduce a **layout analysis / table extraction stage before semantic extraction**.

Possible approaches include:

- PaddleOCR table recognition
- Layout-aware document models
- Table detection
- Cell detection
- LayoutLM-family approaches
- Specialized document-layout parsers

A stronger pipeline would be:

```text
Document
   ↓
Image Preprocessing
   ↓
Layout / Table Detection
   ↓
Region / Cell Detection
   ↓
OCR per Region / Cell
   ↓
Table Reconstruction
   ↓
Structured JSON
   ↓
LLM Semantic Normalization
   ↓
Validation
```

This reduces the amount of structural reconstruction the LLM has to perform.

---

# 2. Software Engineering & Microservices

## Evaluation: 7.5 / 10

## What Is Good

### 2.1 Clean API Design

The FastAPI implementation follows a sensible service-oriented structure.

Useful endpoints include:

```text
GET  /health
GET  /v1/meta
POST /process-document
```

The implementation also demonstrates attention to error handling, including cases such as:

- HTTP 415 — unsupported media type
- HTTP 400 — invalid request
- Structured response schemas
- Service health checks

This provides a strong foundation for integrating the AI service with the main application backend.

---

### 2.2 Dockerization

Containerizing the OCR service is the correct architectural direction because OCR dependencies can be heavy and version-sensitive.

Docker provides:

- Reproducible environments
- Dependency isolation
- Easier deployment
- Consistent development environments
- Separation between AI infrastructure and application infrastructure

This is particularly useful when dealing with Python/package compatibility issues.

---

### 2.3 Testing Strategy

A two-tier testing approach is a strong engineering signal.

### Fast Tests

Mock or unit-level tests that run quickly:

```text
Developer Change
      ↓
Fast Tests
      ↓
Immediate Feedback
```

### End-to-End Tests

Slower tests that verify the actual service pipeline:

```text
Upload
 ↓
OCR
 ↓
Extraction
 ↓
Validation
 ↓
Response
```

This separation makes development faster while preserving system-level validation.

---

## What Needs Improvement

### 2.4 State Management and Concurrent Processing

The current OCR service loads the OCR engine into the container's memory.

This works for development and limited testing, but it creates a scaling problem.

For example:

```text
User 1 ─┐
User 2 ─┤
User 3 ─┼──→ OCR Container
User 4 ─┤
User 5 ─┘
```

If several large documents arrive simultaneously, CPU/RAM usage can spike significantly.

Potential consequences include:

- High latency
- Memory exhaustion
- Container crashes
- Failed requests
- Poor user experience

The current design is therefore closer to a **single-service processing model** than a production-grade distributed processing system.

### Required Improvement

Introduce a job queue and worker architecture.

Possible technologies:

- Redis
- Celery
- RQ
- RabbitMQ
- Another lightweight message broker

For the current project, **Redis + Celery/RQ** would be a practical direction.

---

# 3. System Architecture & Product Completeness

## Evaluation: 3.5 / 10

This is currently the biggest weakness.

The existing:

```text
SIH26018_architecture_plan.md
```

describes a much broader product than what the current AI microservice actually implements.

## The Current Situation

The AI service is strong, but it currently behaves like an isolated component:

```text
                ┌────────────────────┐
                │    AI Service      │
                │                    │
Document ──────→│ OCR + LLM + Rules  │
                │                    │
                └────────────────────┘
```

What is missing is the surrounding application:

```text
Citizen / Officer
       ↓
React Frontend
       ↓
Main Backend / API
       ↓
Authentication + RBAC
       ↓
Job Management
       ↓
AI Processing Service
       ↓
Validation
       ↓
Human Review
       ↓
PostgreSQL
       ↓
Audit Logs
       ↓
Search / Verified Record
```

---

# 4. Missing Human-in-the-Loop Workflow

Human review is one of the most important parts of the proposed Kaagaz2Code product.

The system should not attempt to automatically trust every extracted value.

A proper workflow should be:

```text
Document Uploaded
       ↓
OCR + Extraction
       ↓
Validation
       ↓
Confidence Evaluation
       ↓
 ┌─────┴──────────┐
 ↓                ↓
High             Low
Confidence       Confidence
 ↓                ↓
Auto Approval    Human Review
 ↓                ↓
Verified Record  Correction
                  ↓
              Re-validation
                  ↓
              Verified Record
```

The reviewer should be able to see:

- Original document
- OCR text
- Extracted fields
- Confidence scores
- Validation errors
- Suspected conflicts
- Suggested corrections

The reviewer should then be able to:

```text
Accept
Edit
Reject
Request Reprocessing
```

Every correction should be recorded in the audit trail.

---

# 5. Critical Architectural Flaw #1 — Synchronous Processing

## Current Problem

The current:

```text
POST /process-document
```

performs OCR and LLM processing while the HTTP request remains open.

If processing takes 15+ seconds, the client waits for the complete operation.

This creates several problems:

- Long HTTP connections
- Poor UX
- Timeout risk
- Lost results if the connection drops
- Difficult scaling
- Poor handling of multiple concurrent documents

---

## Required Mend: Asynchronous Job Processing

The preferred architecture is:

### Step 1 — Upload

```http
POST /upload
```

Response:

```json
{
  "job_id": "123",
  "status": "processing"
}
```

The upload endpoint should return quickly.

---

### Step 2 — Background Worker

The backend places the job into a queue:

```text
Backend
   ↓
Redis / Message Queue
   ↓
Worker
   ↓
OCR
   ↓
LLM
   ↓
Validation
   ↓
Database
```

---

### Step 3 — Status Check

The frontend can request:

```http
GET /jobs/123
```

Example:

```json
{
  "job_id": "123",
  "status": "completed",
  "confidence": 0.91
}
```

Possible states:

```text
queued
processing
completed
review_required
failed
rejected
```

---

### Optional Real-Time Notification

Instead of polling continuously, the system can later support:

```text
WebSocket
```

or:

```text
Server-Sent Events
```

for real-time status updates.

---

# 6. Critical Architectural Flaw #2 — Table Extraction

Government land records are heavily dependent on structured information.

A simple OCR pipeline can identify text but may fail to preserve relationships.

Therefore:

```text
OCR ≠ Document Understanding
```

The system needs both:

```text
Text Recognition
+
Layout Understanding
```

## Recommended Pipeline

```text
Scanned Document
       ↓
Preprocessing
       ↓
Layout Detection
       ↓
Table Detection
       ↓
Cell / Region Detection
       ↓
OCR
       ↓
Table Reconstruction
       ↓
Structured JSON
       ↓
LLM Normalization
       ↓
Business Validation
```

This should be treated as an important AI-service enhancement.

---

# 7. Critical Architectural Flaw #3 — PII, Security & Data Sovereignty

Land records may contain sensitive information such as:

- Names
- Addresses
- Ownership details
- Registration information
- Land identifiers
- Government record numbers

Sending such information to a third-party cloud LLM introduces security, privacy, and data-sovereignty considerations.

For a government-oriented system, this must be treated as an architectural concern rather than an optional feature.

---

## Required Direction: Local LLM Support

The architecture already considers **Ollama**.

This should be elevated from an optional idea to a planned deployment mode.

Possible architecture:

```text
                 ┌─────────────────┐
                 │   FastAPI AI     │
                 └────────┬────────┘
                          ↓
                 ┌─────────────────┐
                 │ LLM Abstraction │
                 └────────┬────────┘
                          ↓
               ┌──────────┴──────────┐
               ↓                     ↓
        Local Ollama             Cloud LLM
        Deployment               Development
```

For an air-gapped deployment:

```text
Government Network
       │
       ├── React Frontend
       ├── Main Backend
       ├── PostgreSQL
       ├── Object Storage
       ├── FastAPI AI Service
       ├── PaddleOCR
       └── Local LLM
```

No external internet connection is required for the core processing workflow.

> **Important:** Local deployment can significantly reduce external-data-transfer concerns, but legal compliance should still be validated against the applicable government policies and laws rather than assumed solely from technical isolation.

---

# 8. Critical Architectural Flaw #4 — Deduplication & Fraud Checks

The current pipeline largely assumes that an uploaded document is genuine and unique.

This creates two problems.

## 8.1 Duplicate Documents

A user could upload the same document multiple times.

The system should detect visually identical or near-identical documents.

### Suggested Approach

Use:

```text
Perceptual Hashing (pHash)
```

during upload.

Example:

```text
Document
   ↓
Image Normalization
   ↓
pHash
   ↓
Compare Against Existing Hashes
   ↓
Duplicate?
 ┌─┴─┐
Yes  No
 ↓    ↓
Flag  Continue
```

---

## 8.2 Cross-Validation

Extracted information should also be validated against known relationships.

Examples:

```text
District ↔ Tehsil
Tehsil ↔ Village
Village ↔ Land Record
Khasra ↔ Area
Owner ↔ Ownership Record
```

For example:

```text
District = X
Tehsil = Y

Does Tehsil Y actually belong to District X?
```

If not:

```text
Validation Error
       ↓
Human Review
```

This is more useful than relying solely on the LLM's confidence.

---

# 9. Recommended End-to-End Architecture

The target architecture should look approximately like this:

```text
                         ┌───────────────────┐
                         │   React Frontend  │
                         └─────────┬─────────┘
                                   │
                                   ↓
                         ┌───────────────────┐
                         │ Main Backend API  │
                         │ Node.js / Express │
                         └─────────┬─────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ↓              ↓              ↓
             Authentication    Job Manager    Search API
               + RBAC              │
                                   ↓
                              Redis / Queue
                                   │
                                   ↓
                         ┌───────────────────┐
                         │ FastAPI AI Service│
                         └─────────┬─────────┘
                                   │
                     ┌─────────────┼─────────────┐
                     ↓             ↓             ↓
                Preprocessing   Layout/OCR    LLM Extraction
                     │             │             │
                     └─────────────┼─────────────┘
                                   ↓
                              Validation
                                   │
                         ┌─────────┴─────────┐
                         ↓                   ↓
                    High Confidence     Low Confidence
                         ↓                   ↓
                    Auto Approval      Human Review
                         │                   │
                         └─────────┬─────────┘
                                   ↓
                              PostgreSQL
                                   │
                         ┌─────────┴─────────┐
                         ↓                   ↓
                    Verified Data        Audit Log

Raw Documents
       ↓
Supabase Storage / MinIO
```

---

# 10. Recommended Development Priority

Do not attempt to perfect every component simultaneously.

The implementation should proceed in this order.

## Phase 1 — Complete the Product Skeleton

Build:

- React frontend
- Node.js/Express backend
- PostgreSQL database
- Supabase Storage / MinIO
- Authentication
- JWT
- RBAC

---

## Phase 2 — Connect the AI Service

Integrate:

```text
Backend
   ↓
AI Service
   ↓
OCR
   ↓
Extraction
   ↓
Validation
   ↓
Database
```

At this stage, the AI service stops being an isolated microservice and becomes part of the actual product.

---

## Phase 3 — Implement Asynchronous Processing

Add:

- Job IDs
- Queue
- Worker
- Job status
- Retry mechanism
- Failure handling

Example:

```text
Upload
 ↓
job_id
 ↓
Queued
 ↓
Processing
 ↓
Completed / Review Required / Failed
```

---

## Phase 4 — Build the Human Review Interface

Create the verifier dashboard.

Minimum UI:

```text
┌─────────────────────────────────────────┐
│ Document Preview                        │
├───────────────────┬─────────────────────┤
│ Original Document │ Extracted Fields    │
│                   │                     │
│                   │ Owner: ______       │
│                   │ Khasra: _____       │
│                   │ Area: ______        │
│                   │ Village: ____      │
│                   │                     │
│                   │ Confidence: 82%    │
└───────────────────┴─────────────────────┘

[Accept] [Edit] [Reject] [Reprocess]
```

This is one of the most important parts of the SIH demonstration.

---

# 11. Phase 5 — Strengthen AI

After the workflow works end-to-end, improve:

- Table extraction
- Layout analysis
- OCR accuracy
- Field confidence
- LLM prompts
- Structured output validation
- Local LLM support
- Language support

Do not make perfect OCR a prerequisite for building the product.

---

# 12. Phase 6 — Security & Integrity

Add:

- JWT authentication
- RBAC
- Input validation
- File-type validation
- File-size limits
- Malware/file scanning where appropriate
- Audit logs
- Immutable/tamper-evident audit strategy
- Document hashing
- Duplicate detection
- Data encryption
- Secrets management
- Secure service-to-service communication

Every important write operation should generate an audit event.

This includes the **Auto-Approve path**.

```text
Auto Approval
      ↓
Database Write
      ↓
Audit Log
```

and:

```text
Human Correction
      ↓
Database Write
      ↓
Audit Log
```

---

# 13. What Judges Are Likely to Look For

For an SIH demonstration, the strongest story is not:

> "Our OCR accuracy is X%."

The stronger story is:

```text
Government clerk uploads document
            ↓
System processes it automatically
            ↓
AI extracts structured information
            ↓
Validation detects inconsistencies
            ↓
High-confidence record is auto-approved
            ↓
Uncertain record goes to verifier
            ↓
Verifier corrects the field
            ↓
Correction is audited
            ↓
Verified record becomes searchable
```

This demonstrates an actual government workflow rather than an isolated AI demo.

---

# 14. Final Assessment

| Area | Current Assessment |
|------|--------------------|
| OCR + AI Engine | **8.5 / 10** |
| Software Engineering | **7.5 / 10** |
| System/Product Completeness | **3.5 / 10** |
| Overall Current State | Strong AI microservice, incomplete product |

The central issue is not that the AI engine is weak.

The central issue is that the AI engine is currently **ahead of the product around it**.

The next development effort should therefore prioritize:

1. **Frontend**
2. **Main backend**
3. **Database**
4. **Object storage**
5. **Asynchronous job processing**
6. **Human-in-the-Loop verifier dashboard**
7. **Audit logging**
8. **Table/layout extraction**
9. **Deduplication and cross-validation**
10. **Local LLM / air-gapped deployment**

---

# 15. Final Architectural Principle

The project should evolve from:

```text
             ┌──────────────┐
Document ───→│  AI Service  │───→ JSON
             └──────────────┘
```

into:

```text
                    KAAGAZ2CODE

Document
   ↓
Upload
   ↓
Storage
   ↓
Job Queue
   ↓
AI Processing
   ├── Preprocessing
   ├── Layout Analysis
   ├── OCR
   ├── LLM Extraction
   └── Confidence Scoring
   ↓
Validation
   ↓
 ┌─────────────────────┐
 │                     │
High Confidence     Uncertain
 │                     │
 ↓                     ↓
Auto Approval      Human Review
 │                     │
 └──────────┬──────────┘
            ↓
     Verified Record
            ↓
       PostgreSQL
            ↓
   Searchable Land Data
            ↓
      Audit History
```

> **The objective is not to build an AI that blindly converts documents into JSON.**
>
> **The objective is to build a reliable digital land-record workflow in which AI performs the repetitive work, validation catches inconsistencies, and humans make the final decision when uncertainty remains.**
