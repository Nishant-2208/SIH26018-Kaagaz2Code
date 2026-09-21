"""
app/services/ai_extraction_service.py

Real OCR/extraction adapter. Calls the standalone AI microservice and returns
the SAME list[dict] shape mock_ocr_service.extract_fields() returns, so the two
are interchangeable behind get_ocr_adapter().

Nothing here touches the ORM or the session — it is a pure translation layer
between the microservice's JSON contract and ExtractedField's dict shape.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field as dc_field
from typing import Any, Final, Protocol

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class OcrUpstreamError(Exception):
    """The AI microservice could not produce an extraction.

    Never swallowed into mock data — the caller decides whether the document is
    retryable (leave the ProcessingJob queued) or terminal (mark it failed).
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        status_code: int | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.retryable = retryable
        self.status_code = status_code
        self.request_id = request_id


# ---------------------------------------------------------------------------
# Field mapping — microservice schema path -> ExtractedField naming
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldSpec:
    path: str
    field_id: str
    label: str
    critical: bool = False


FIELD_SPECS: Final[tuple[FieldSpec, ...]] = (
    FieldSpec("location_details.village", "village", "Village"),
    FieldSpec("location_details.tehsil", "tehsil", "Tehsil"),
    FieldSpec("location_details.district", "district", "District"),
    FieldSpec("land_identifiers.survey_number", "survey_no", "Survey Number", critical=True),
    FieldSpec("land_identifiers.khasra_number", "khasra_no", "Khasra Number", critical=True),
    FieldSpec("land_identifiers.khata_number", "khata_no", "Khata Number", critical=True),
    FieldSpec("land_details.plot_area", "area", "Area"),
    FieldSpec("land_details.land_classification", "land_type", "Land Classification"),
    FieldSpec("ownership_details.landowner_name", "owner_name", "Owner Name", critical=True),
    FieldSpec("ownership_details.registration_information", "registration_info", "Registration Information"),
    FieldSpec("ownership_details.mutation_records", "mutation_records", "Mutation Records"),
)

AREA_UNIT_FIELD_ID: Final[str] = "area_unit"
AREA_UNIT_LABEL: Final[str] = "Area Unit"

# Human text per flag reason. The reason code is kept as a prefix so the
# frontend can branch on it without re-deriving anything: ExtractedField has no
# column for `priority` or `reason` and we are not adding one, so the warning
# string is the only channel that carries the distinction through to the UI.
REASON_TEXT: Final[dict[str, str]] = {
    "field_missing": "Not found in the document.",
    "low_ocr_confidence": "OCR was unsure of these characters.",
    "llm_uncertain": "Extracted, but the model was not confident.",
    "unit_ambiguous": "Area has no recognisable unit.",
    "illegible": "Present in the scan but too degraded to transcribe.",
    "critical_field_low_confidence": (
        "Legal identifier below the stricter confidence bar required for critical fields "
        "(it would have passed the standard bar)."
    ),
}

_DEVANAGARI_START: Final[int] = 0x0900
_DEVANAGARI_END: Final[int] = 0x097F


def _detect_language(value: str | None) -> str:
    """'hi' if any Devanagari codepoint is present, else 'en'."""
    if not value:
        return "en"
    return "hi" if any(_DEVANAGARI_START <= ord(ch) <= _DEVANAGARI_END for ch in value) else "en"


def _confidence_level(score: float) -> str:
    """Mirrors mock_ocr_service's banding exactly.

    Note this is the STANDARD banding and is intentionally independent of the
    upstream pass/fail bar (0.85 for critical fields, 0.70 for the rest). A
    critical field can therefore read "medium" and still be flagged — which is
    why verification_status is driven by flagged_fields membership, not by this.
    """
    if score >= 0.90:
        return "high"
    if score >= 0.75:
        return "medium"
    return "low"


def _split_area(raw: str | None) -> tuple[str | None, str]:
    """'0.486 हेक्टेयर' -> ('0.486', 'हेक्टेयर');  '2.5 acres' -> ('2.5', 'acres').

    Returns (value, '') when no trailing unit token is present.
    """
    if not raw:
        return raw, ""
    parts = str(raw).strip().split(maxsplit=1)
    if not parts:
        return raw, ""
    magnitude = parts[0].strip()
    unit = parts[1].strip() if len(parts) > 1 else ""
    # Guard against a value that is entirely non-numeric ("Irrigated" landing
    # here through an upstream mix-up) — leave it untouched rather than mangle it.
    if not any(ch.isdigit() for ch in magnitude):
        return raw, ""
    return magnitude, unit


def _get_by_path(extraction: dict[str, Any], path: str) -> str | None:
    group, leaf = path.split(".")
    value = (extraction.get(group) or {}).get(leaf)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _sniff_mime(data: bytes) -> tuple[str, str]:
    """(filename, content_type) from magic bytes.

    extract_fields() is given raw bytes with no filename, and the microservice
    validates content_type — so guessing 'image/jpeg' for a PNG would earn a 415.
    """
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "document.png", "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "document.jpg", "image/jpeg"
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return "document.tiff", "image/tiff"
    if data.startswith(b"BM"):
        return "document.bmp", "image/bmp"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "document.webp", "image/webp"
    return "document.jpg", "image/jpeg"


# ---------------------------------------------------------------------------
# Adapter interface
# ---------------------------------------------------------------------------


@dataclass
class ExtractionResult:
    """What every OCR adapter returns.

    `fields` is the mock-compatible list[dict]; `needs_review` and `meta` are
    additive so record_service can set ProcessingJob status without re-deriving
    anything from the field list.
    """

    fields: list[dict[str, Any]]
    needs_review: bool
    meta: dict[str, Any] = dc_field(default_factory=dict)


class OcrAdapter(Protocol):
    """Factory + Strategy seam. Both implementations satisfy this."""

    name: str

    async def extract(
        self,
        *,
        document_id: Any,
        document_type: Any,
        record_id: Any,
        file_bytes: bytes,
    ) -> ExtractionResult: ...


# ---------------------------------------------------------------------------
# Real adapter
# ---------------------------------------------------------------------------


class RealOcrAdapter:
    """Calls the standalone AI microservice at settings.AI_SERVICE_URL."""

    name = "real"

    async def extract(
        self,
        *,
        document_id: Any,
        document_type: Any,
        record_id: Any,
        file_bytes: bytes,
    ) -> ExtractionResult:
        payload = await self._call_microservice(
            file_bytes=file_bytes,
            doc_type=_doc_type_value(document_type),
            document_id=document_id,
        )
        fields = _map_response_to_fields(payload, record_id=record_id)
        return ExtractionResult(
            fields=fields,
            needs_review=payload.get("status") == "needs_review",
            meta={
                "request_id": payload.get("request_id"),
                "processing_ms": payload.get("processing_ms"),
                "engine": payload.get("engine", {}),
                "overall_confidence": (
                    (payload.get("extraction") or {}).get("confidence_scores") or {}
                ).get("overall_confidence"),
            },
        )

    async def _call_microservice(
        self, *, file_bytes: bytes, doc_type: str, document_id: Any
    ) -> dict[str, Any]:
        request_id = uuid.uuid4().hex[:16]
        url = f"{settings.AI_SERVICE_URL.rstrip('/')}/process-document"

        headers = {"X-Request-Id": request_id}
        if settings.AI_SERVICE_INTERNAL_KEY:
            headers["X-Internal-Key"] = settings.AI_SERVICE_INTERNAL_KEY

        filename, content_type = _sniff_mime(file_bytes)

        logger.info(
            "ai_extraction: POST %s document_id=%s doc_type=%s bytes=%d request_id=%s",
            url, document_id, doc_type, len(file_bytes), request_id,
        )

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(settings.AI_SERVICE_TIMEOUT_S)) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    files={"file": (filename, file_bytes, content_type)},
                    data={"doc_type": doc_type},
                )
        except httpx.TimeoutException as exc:
            raise OcrUpstreamError(
                "LLM_TIMEOUT",
                f"AI service did not respond within {settings.AI_SERVICE_TIMEOUT_S}s",
                retryable=True,
                status_code=504,
                request_id=request_id,
            ) from exc
        except httpx.HTTPError as exc:
            # Connection refused / DNS / TLS — the service is down, not the document.
            raise OcrUpstreamError(
                "AI_SERVICE_UNREACHABLE",
                f"Could not reach the AI service at {url}: {exc}",
                retryable=True,
                status_code=503,
                request_id=request_id,
            ) from exc

        if response.status_code != 200:
            raise _error_from_response(response, request_id)

        try:
            payload: dict[str, Any] = response.json()
        except ValueError as exc:
            raise OcrUpstreamError(
                "LLM_INVALID_RESPONSE",
                "AI service returned a 200 that was not JSON",
                retryable=True,
                status_code=502,
                request_id=request_id,
            ) from exc

        if not isinstance(payload.get("extraction"), dict):
            raise OcrUpstreamError(
                "LLM_INVALID_RESPONSE",
                "AI service response is missing the 'extraction' object",
                retryable=True,
                status_code=502,
                request_id=payload.get("request_id", request_id),
            )

        logger.info(
            "ai_extraction: ok document_id=%s status=%s ms=%s request_id=%s",
            document_id, payload.get("status"), payload.get("processing_ms"), payload.get("request_id"),
        )
        return payload


def _error_from_response(response: httpx.Response, fallback_request_id: str) -> OcrUpstreamError:
    """Translate the microservice's error envelope into a typed exception.

    Retryability comes from the envelope when present; the status-code fallback
    covers the case where an infra layer (proxy, ingress) answers instead of the
    service and there is no envelope at all.
    """
    code = "UPSTREAM_ERROR"
    message = response.text[:300]
    retryable = response.status_code in (429, 502, 503, 504)
    request_id = fallback_request_id

    try:
        body = response.json()
        envelope = body.get("error") or {}
        code = envelope.get("code", code)
        message = envelope.get("message", message)
        retryable = bool(envelope.get("retryable", retryable))
        request_id = body.get("request_id", request_id)
    except ValueError:
        pass

    logger.warning(
        "ai_extraction: upstream %s %s retryable=%s request_id=%s",
        response.status_code, code, retryable, request_id,
    )
    return OcrUpstreamError(
        code, message, retryable=retryable, status_code=response.status_code, request_id=request_id
    )


def _doc_type_value(document_type: Any) -> str:
    """DocumentType enum member -> its string value; tolerate a plain str."""
    return getattr(document_type, "value", None) or str(document_type)


# ---------------------------------------------------------------------------
# Response -> ExtractedField dicts
# ---------------------------------------------------------------------------


def _map_response_to_fields(payload: dict[str, Any], *, record_id: Any) -> list[dict[str, Any]]:
    extraction: dict[str, Any] = payload.get("extraction") or {}
    scores: dict[str, Any] = extraction.get("confidence_scores") or {}
    field_confidence: dict[str, Any] = scores.get("field_confidence") or {}

    # path -> flag entry. Every flagged field is keyed by its schema path.
    flags: dict[str, dict[str, Any]] = {
        entry["field"]: entry
        for entry in (scores.get("flagged_fields") or [])
        if isinstance(entry, dict) and entry.get("field")
    }

    rows: list[dict[str, Any]] = []

    for spec in FIELD_SPECS:
        raw_value = _get_by_path(extraction, spec.path)
        flag = flags.get(spec.path)

        # Per-field score is always present now. Only fall back if the upstream
        # genuinely omitted the path — never to overall_confidence.
        try:
            confidence = float(field_confidence.get(spec.path, 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        if spec.field_id == "area":
            value, unit = _split_area(raw_value)
        else:
            value, unit = raw_value, None

        rows.append(
            _build_row(
                record_id=record_id,
                field_id=spec.field_id,
                label=spec.label,
                value=value,
                confidence=confidence,
                flag=flag,
                critical=spec.critical,
            )
        )

        if spec.field_id == "area":
            # area_unit inherits area's score and flag state: an ambiguous or
            # missing unit is a property of the same extracted token.
            rows.append(
                _build_row(
                    record_id=record_id,
                    field_id=AREA_UNIT_FIELD_ID,
                    label=AREA_UNIT_LABEL,
                    value=unit or "",
                    confidence=confidence,
                    flag=flag,
                    critical=False,
                )
            )

    # Reviewer queue ordering: critical flags first, then standard flags, then
    # everything clean in canonical schema order.
    order = {spec.field_id: i for i, spec in enumerate(FIELD_SPECS)}
    order[AREA_UNIT_FIELD_ID] = order["area"] + 0.5  # type: ignore[assignment]

    def sort_key(row: dict[str, Any]) -> tuple[int, float]:
        if row["verification_status"] != "flagged":
            rank = 2
        elif row.get("_critical"):
            rank = 0
        else:
            rank = 1
        return rank, float(order.get(row["field_id"], 99))

    rows.sort(key=sort_key)
    for row in rows:
        row.pop("_critical", None)  # internal sort hint, not part of the contract
    return rows


def _build_row(
    *,
    record_id: Any,
    field_id: str,
    label: str,
    value: str | None,
    confidence: float,
    flag: dict[str, Any] | None,
    critical: bool,
) -> dict[str, Any]:
    reason = (flag or {}).get("reason")
    warning: str | None = None
    if reason:
        # Reason code prefix is deliberate: it keeps critical_field_low_confidence
        # distinguishable in the UI instead of collapsing into "low confidence".
        warning = f"{reason}: {REASON_TEXT.get(reason, 'Flagged for review.')}"

    return {
        "id": str(uuid.uuid4()),
        "record_id": record_id,
        "field_id": field_id,
        "label": label,
        "value": value,
        "edited_value": None,
        "confidence": round(confidence, 4),
        "confidence_level": _confidence_level(confidence),
        # Driven by flag membership, never by confidence_level — critical fields
        # use a stricter upstream bar, so the two can legitimately disagree.
        "verification_status": "flagged" if flag else "pending",
        "bounding_box": None,  # microservice returns page-level boxes only, not per-field
        "source_language": _detect_language(value),
        "warning": warning,
        "_critical": critical,
    }


# ---------------------------------------------------------------------------
# Mock adapter — wraps the existing mock_ocr_service untouched
# ---------------------------------------------------------------------------


class MockOcrAdapter:
    """Zero-dependency fallback. Selected with OCR_ADAPTER=mock."""

    name = "mock"

    async def extract(
        self,
        *,
        document_id: Any,
        document_type: Any,
        record_id: Any,
        file_bytes: bytes,  # noqa: ARG002 — mock never reads the bytes
    ) -> ExtractionResult:
        from app.services import mock_ocr_service  # local import keeps it optional

        fields = mock_ocr_service.extract_fields(
            document_id=document_id, document_type=document_type, record_id=record_id
        )
        needs_review = any(f.get("verification_status") == "flagged" for f in fields)
        return ExtractionResult(fields=fields, needs_review=needs_review, meta={"engine": {"mode": "mock"}})


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_ADAPTERS: Final[dict[str, type]] = {"real": RealOcrAdapter, "mock": MockOcrAdapter}


def get_ocr_adapter(name: str | None = None) -> OcrAdapter:
    """Return the configured adapter. OCR_ADAPTER=real|mock, default real."""
    key = (name or getattr(settings, "OCR_ADAPTER", "real") or "real").lower()
    adapter_cls = _ADAPTERS.get(key)
    if adapter_cls is None:
        raise ValueError(f"Unknown OCR_ADAPTER={key!r}; expected one of {sorted(_ADAPTERS)}")
    return adapter_cls()  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Contract-compatible shim
# ---------------------------------------------------------------------------


async def extract_fields(
    document_id: Any,
    document_type: Any,
    record_id: Any,
    file_bytes: bytes,
) -> list[dict[str, Any]]:
    """Same return shape as mock_ocr_service.extract_fields, but real and async.

    Prefer RealOcrAdapter().extract() when you also need needs_review / engine
    metadata — this shim drops them.
    """
    result = await RealOcrAdapter().extract(
        document_id=document_id,
        document_type=document_type,
        record_id=record_id,
        file_bytes=file_bytes,
    )
    return result.fields
