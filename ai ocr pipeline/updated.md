# SIH26018 AI Microservice — Confidence Scoring & Extraction Analysis

## Executive Summary

This document provides a comprehensive technical audit of the SIH26018 Land Record AI Microservice repository. It details:
1. Critical bugs where confidence scores fail to assign or propagate to downstream consumers.
2. Mathematical flaws and thresholding issues that cause documents to fail readiness checks.
3. Quality and correctness analysis of the extraction layer (`extractor.py` and `ai_extraction_service.py`).
4. Performance and reliability evaluation of the confidence scoring system.
5. Actionable, step-by-step remediation guide.

---

## 1. Core Failure: Missing Confidence Scores (`field_confidence`)

### The Breakdown Between Microservice and Backend Adapter
The most severe issue across the codebase is the contract discrepancy between the producer (`extractor.py`) and the consumer (`ai_extraction_service.py`).

#### 1. Downstream Expectation (`ai_extraction_service.py`, lines 360–383)
The consumer adapter reads per-field confidence from the microservice's JSON response:
```python
scores: dict[str, Any] = extraction.get("confidence_scores") or {}
field_confidence: dict[str, Any] = scores.get("field_confidence") or {}
...
try:
    confidence = float(field_confidence.get(spec.path, 0.0))
except (TypeError, ValueError):
    confidence = 0.0
```

#### 2. Upstream Implementation (`extractor.py`, lines 98–101, 281–285)
In the extraction microservice schema:
```python
class ConfidenceScores(BaseModel):
    overall_confidence: float = 0.0
    flagged_fields: list[FlaggedField] = Field(default_factory=list)
```
And inside `assemble()`:
```python
payload = {
    "location_details": raw.get("location_details") or {},
    "land_identifiers": raw.get("land_identifiers") or {},
    "land_details": raw.get("land_details") or {},
    "ownership_details": raw.get("ownership_details") or {},
    "confidence_scores": {
        "overall_confidence": overall,
        "flagged_fields": [f.model_dump() for f in flagged],
    },
}
```

#### 3. Root Impact
- `field_confidence` is **completely omitted** from `ConfidenceScores` and dropped from the response payload.
- Every clean, high-confidence extraction has no entry in `flagged_fields` and cannot be resolved in `field_confidence`.
- As a consequence, `field_confidence.get(spec.path, 0.0)` evaluates to `0.0`.
- All cleanly extracted fields are erroneously labeled with **`confidence = 0.0`** and **`confidence_level = "low"`** in the backend and frontend UI.

---

## 2. Confidence Scoring Algorithmic Flaws

### Flaw A: Mathematical Dilution of `overall_confidence`
In `extractor.py` (lines 243–272):
```python
for path in FIELD_PATHS:
    value = _get_path(raw, path)
    ...
    if value is None:
        flagged.append(FlaggedField(field=path, confidence=0.0, reason="field_missing"))
        scores.append(0.0)
        continue

overall = round(sum(scores) / len(scores), 3) if scores else 0.0
```

- `FIELD_PATHS` defines **11 fixed fields** spanning heterogeneous Indian land records (North Indian Khasra/Khata vs. South/West Indian Survey Numbers, plus registration deeds and mutation entries).
- **No single Indian land record contains all 11 fields.** For example:
  - Uttar Pradesh/Bihar Khatauni records contain Khasra and Khata numbers, but no Survey Number.
  - Standard Record of Rights (RoR) documents do not contain deed registration information or mutation records if no recent transaction occurred.
- For a document with 7 present fields extracted with perfect `1.0` confidence and 4 missing fields:
  $$\text{overall\_confidence} = \frac{7 \times 1.0 + 4 \times 0.0}{11} = 0.636$$
- Since `CONFIDENCE_FLOOR = 0.75`, even a 100% accurate document cannot achieve a passing score.

### Flaw B: `status = "ok"` Is Practically Unreachable
In `main.py` (line 274):
```python
status = "ok" if (conf.overall_confidence >= ex.CONFIDENCE_FLOOR and not conf.flagged_fields) else "needs_review"
```
- Missing fields are flagged with `reason="field_missing"`.
- Because nearly all valid records have missing optional fields, `not conf.flagged_fields` will always be `False`.
- Consequently, **every document is forced into `"needs_review"`**, defeating the purpose of automated verification.

### Flaw C: Flat vs. Nested LLM Schema Mismatch
In `extractor.py` (line 246):
```python
llm_conf = float(field_conf.get(path, 0.0))
```
- Prompts request flat dotted keys (`"location_details.village"`), but models like Gemini or GPT-4o often output hierarchical structures matching the rest of the payload (`{"field_confidence": {"location_details": {"village": 0.95}}}`).
- If the model returns nested dictionaries, lookup fails silently, defaulting to `0.0` and spuriously flagging `"llm_uncertain"`.

### Flaw D: Missing Regional Area Units
In `extractor.py` (lines 266–270):
```python
elif path == "land_details.plot_area" and not re.search(
    r"(hect|ha\b|acre|bigha|biswa|sq|मी|हेक्ट|एकड़|बीघा)", str(value), re.IGNORECASE
):
    flagged.append(FlaggedField(field=path, confidence=score, reason="unit_ambiguous"))
```
- Common regional units are not recognized:
  - **Guntha / गुंठा** (Maharashtra, Karnataka, Gujarat)
  - **Kanal / कनाल & Marla / मरला** (Punjab, Haryana, HP, J&K)
  - **Katha / कट्ठा / Kattha & Dhur / धुर** (Bihar, UP, West Bengal, Assam)
  - **Cent / शतक** (Kerala, Tamil Nadu)
- Valid land records featuring these units are incorrectly flagged as `"unit_ambiguous"`.

---

## 3. Extraction Layer Quality & Bugs

### Bug 1: `MockExtractor` Land Classification Regex Is Unanchored
In `extractor.py` (lines 438–441):
```python
"land_details.land_classification": (
    r"(?:भूमि\s*उपयोग\s*श्रेणी|उपयोग\s*श्रेणी|श्रेणी|classification)?\s*[:\-]?\s*"
    r"(कृषि\s*भूमि\s*(?:\([^)]+\))?|सिंचित|असिंचित|कृषि|irrigated|sinchit|asinchit|barren|banjar|बंजर|agricultural|non-agricultural|abadi|आबादी)"
)
```
- The label group prefix ends with `?` (optional).
- If the word `कृषि` appears anywhere in the document (such as header `"कृषि विभाग"`), it gets erroneously captured as the land classification.

### Bug 2: `MockExtractor` Registration Information False Positives
In `extractor.py` (lines 445–447):
```python
"ownership_details.registration_information": (
    r"(?:reg(?:istration)?\.?\s*(?:no|number)?|पंजीकरण|रजिस्ट्री|प्रमाणित|कार्यालय|दिनांक)\s*[:\-]?\s*([^\n]{2,80})"
)
```
- Keywords include `कार्यालय` ("Office") and `दिनांक` ("Date").
- Routine date lines like `दिनांक: 26-08-2026` or office headers like `कार्यालय: तहसीलदार, सदर` are captured as registration information.

### Bug 3: Static Confidence in Mock & Digital Extraction
- In `MockExtractor.complete()`: Hardcodes confidence to `0.85` for all regex-matched fields regardless of string match quality.
- In `main.py` (lines 220–229): Digital text from PDF/DOCX automatically assigns a static `0.99` line confidence without verifying parsing completeness.

---

## 4. Assessment Matrix

| Capability | Current State | Verdict | Target Fix |
|---|---|---|---|
| **Pydantic Output Schema** | Drops `field_confidence` dict | ❌ Broken | Add `field_confidence: dict[str, float]` to `ConfidenceScores` |
| **Field Score Assignment** | Clean fields evaluate to `0.0` downstream | ❌ Broken | Populate `field_confidence` with computed damped scores |
| **Overall Confidence Calculation** | Averages over 11 fields including non-applicable | ⚠️ Flawed | Calculate score based on present or expected fields only |
| **Status Gatekeeping** | Blocked by non-critical `field_missing` flags | ⚠️ Flawed | Gate `"ok"` on critical field flags, not optional fields |
| **OCR Quality Damping** | `damp = 0.5 + 0.5 * ocr_conf` | ✅ Effective | Retain current formula |
| **Cloud LLM Extraction** | Direct REST via `httpx` (no SDK bloat) | ✅ Robust | Retain architecture, add fallback for nested JSON |
| **Unit Verification** | Missing Guntha, Kanal, Marla, Katha, Cent | ⚠️ Incomplete | Extend regular expressions |
| **Mock Extraction Accuracy** | Overly greedy regex on classification & dates | ⚠️ Moderate | Anchor prefix patterns |

---

## 5. Remediation Roadmap

### Step 1: Update `extractor.py` Schema & Assembly
1. Add `field_confidence: dict[str, float] = Field(default_factory=dict)` to `ConfidenceScores`.
2. In `assemble()`, record `field_confidence[path] = score` for every field.
3. Support nested dictionary lookup in `field_conf` when parsing LLM outputs.

### Step 2: Fix Scoring Logic in `extractor.py`
1. Exclude optional missing fields from the denominator of `overall_confidence`:
   ```python
   evaluated_scores = [s for p, s in per_field_scores.items() if p in critical_fields or s > 0.0]
   overall = round(sum(evaluated_scores) / len(evaluated_scores), 3) if evaluated_scores else 0.0
   ```
2. Add missing regional units (`guntha|गूंठा|गुंठा|kanal|कनाल|marla|मरला|kattha|कथा|कट्ठा|cent|शतक`) to the unit validator.

### Step 3: Refine Readiness Status in `main.py`
Separate critical errors (e.g., illegible text, low OCR quality, missing owner/khasra) from benign optional field omissions:
```python
critical_flags = [f for f in conf.flagged_fields if f.reason != "field_missing"]
status = "ok" if (conf.overall_confidence >= ex.CONFIDENCE_FLOOR and not critical_flags) else "needs_review"
```

### Step 4: Refine `MockExtractor` Patterns
- Remove trailing `?` from the prefix of `land_classification`.
- Remove standalone `कार्यालय` and `दिनांक` from `registration_information`.
