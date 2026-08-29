// ============================================
// KAAGAZ2CODE — API Service Layer
// Mock-backed, structured for FastAPI swap
// ============================================

import type {
  LandRecord,
  Batch,
  AuditTrailEntry,
  DiscrepancyRecord,
  MultilingualField,
  ParcelPin,
  QueueItem,
  AdminStats,
  Officer,
  LookupResult,
  ExtractedField,
  ReviewDecision,
  SubmitReviewDecisionRequest,
  UpdateExtractedFieldRequest,
} from './types';

import {
  mockRecords,
  mockBatches,
  mockAuditTrail,
  mockDiscrepancy,
  mockMultilingualFields,
  mockParcels,
  mockQueueItems,
  mockAdminStats,
  mockOfficers,
  mockLookupResults,
  mockExtractedFields,
} from './mockData';

/* =========================================================
   CONFIG
   ========================================================= */

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ??
  'http://localhost:8000/api';

/*
 * Keep mock mode enabled for the current prototype.
 *
 * When the backend is ready:
 *
 * VITE_USE_MOCKS=false
 */
const USE_MOCKS =
  import.meta.env.VITE_USE_MOCKS !== 'false';

/* =========================================================
   HELPERS
   ========================================================= */

async function mockDelay<T>(
  data: T,
  ms = 300,
): Promise<T> {
  return new Promise((resolve) => {
    setTimeout(() => resolve(data), ms);
  });
}

async function request<T>(
  url: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new Error(
      `API request failed: ${response.status} ${response.statusText}`,
    );
  }

  return response.json() as Promise<T>;
}

/* =========================================================
   RECORDS
   ========================================================= */

export async function getRecords(): Promise<LandRecord[]> {
  if (USE_MOCKS) {
    return mockDelay(mockRecords);
  }

  return request<LandRecord[]>(
    `${API_BASE}/records`,
  );
}

export async function getRecordById(
  id: string,
): Promise<LandRecord | undefined> {
  if (USE_MOCKS) {
    return mockDelay(
      mockRecords.find(
        (record) => record.id === id,
      ),
    );
  }

  return request<LandRecord | undefined>(
    `${API_BASE}/records/${encodeURIComponent(id)}`,
  );
}

/* =========================================================
   EXTRACTED FIELDS
   ========================================================= */

export async function getExtractedFields(
  recordId: string,
): Promise<ExtractedField[]> {
  if (USE_MOCKS) {
    return mockDelay(mockExtractedFields);
  }

  return request<ExtractedField[]>(
    `${API_BASE}/records/${encodeURIComponent(
      recordId,
    )}/fields`,
  );
}

/* =========================================================
   UPDATE EXTRACTED FIELD
   ========================================================= */

/*
 * Supports both:
 *
 * updateExtractedField({
 *   recordId,
 *   fieldId,
 *   value
 * })
 *
 * and:
 *
 * updateExtractedField(
 *   recordId,
 *   fieldId,
 *   value
 * )
 */

export async function updateExtractedField(
  requestData: UpdateExtractedFieldRequest,
): Promise<ExtractedField>;

export async function updateExtractedField(
  recordId: string,
  fieldId: string,
  value: string,
): Promise<ExtractedField>;

export async function updateExtractedField(
  arg1: UpdateExtractedFieldRequest | string,
  arg2?: string,
  arg3?: string,
): Promise<ExtractedField> {
  const payload: UpdateExtractedFieldRequest =
    typeof arg1 === 'string'
      ? {
        recordId: arg1,
        fieldId: arg2 ?? '',
        value: arg3 ?? '',
      }
      : arg1;

  if (!payload.recordId) {
    throw new Error(
      'recordId is required.',
    );
  }

  if (!payload.fieldId) {
    throw new Error(
      'fieldId is required.',
    );
  }

  if (USE_MOCKS) {
    const existingField =
      mockExtractedFields.find(
        (field) =>
          field.fieldId === payload.fieldId,
      );

    if (!existingField) {
      throw new Error(
        `Field ${payload.fieldId} was not found.`,
      );
    }

    const updatedField: ExtractedField = {
      ...existingField,
      value: payload.value,
      editedValue: payload.value,
      verificationStatus:
        'corrected',
    };

    return mockDelay(updatedField);
  }

  return request<ExtractedField>(
    `${API_BASE}/records/${encodeURIComponent(
      payload.recordId,
    )}/fields/${encodeURIComponent(
      payload.fieldId,
    )}`,
    {
      method: 'PATCH',
      body: JSON.stringify({
        value: payload.value,
        updatedBy: payload.updatedBy,
        reason: payload.reason,
      }),
    },
  );
}

/* =========================================================
   REVIEW DECISION
   ========================================================= */

/*
 * Supports both:
 *
 * submitReviewDecision({
 *   recordId,
 *   decision
 * })
 *
 * and:
 *
 * submitReviewDecision(
 *   recordId,
 *   decision,
 *   comment
 * )
 */

export async function submitReviewDecision(
  requestData: SubmitReviewDecisionRequest,
): Promise<LandRecord | undefined>;

export async function submitReviewDecision(
  recordId: string,
  decision: ReviewDecision,
  comment?: string,
): Promise<LandRecord | undefined>;

export async function submitReviewDecision(
  arg1:
    | SubmitReviewDecisionRequest
    | string,
  arg2?: ReviewDecision,
  arg3?: string,
): Promise<LandRecord | undefined> {
  const payload: SubmitReviewDecisionRequest =
    typeof arg1 === 'string'
      ? {
        recordId: arg1,
        decision:
          arg2 ?? 'request_changes',
        comment: arg3,
      }
      : arg1;

  if (!payload.recordId) {
    throw new Error(
      'recordId is required.',
    );
  }

  if (USE_MOCKS) {
    const record =
      mockRecords.find(
        (item) =>
          item.id === payload.recordId,
      );

    if (!record) {
      throw new Error(
        `Record ${payload.recordId} was not found.`,
      );
    }

    let nextStatus:
      | 'pending_review'
      | 'verified'
      | 'flagged';

    switch (payload.decision) {
      case 'approve':
        nextStatus = 'verified';
        break;

      case 'reject':
        nextStatus = 'flagged';
        break;

      default:
        nextStatus = 'pending_review';
        break;
    }

    return mockDelay({
      ...record,
      status: nextStatus,
      updatedAt:
        new Date().toISOString(),
    });
  }

  return request<LandRecord | undefined>(
    `${API_BASE}/records/${encodeURIComponent(
      payload.recordId,
    )}/review`,
    {
      method: 'PATCH',
      body: JSON.stringify({
        decision: payload.decision,
        reviewerId: payload.reviewerId,
        reviewerName:
          payload.reviewerName,
        comment: payload.comment,
        reason: payload.reason,
      }),
    },
  );
}

/* =========================================================
   BATCHES
   ========================================================= */

export async function getBatches(): Promise<Batch[]> {
  if (USE_MOCKS) {
    return mockDelay(mockBatches);
  }

  return request<Batch[]>(
    `${API_BASE}/batches`,
  );
}

/* =========================================================
   AUDIT TRAIL
   ========================================================= */

export async function getAuditTrail(
  recordId: string,
): Promise<AuditTrailEntry[]> {
  if (USE_MOCKS) {
    return mockDelay(mockAuditTrail);
  }

  return request<AuditTrailEntry[]>(
    `${API_BASE}/records/${encodeURIComponent(
      recordId,
    )}/audit`,
  );
}

/* =========================================================
   DISCREPANCY
   ========================================================= */

export async function getDiscrepancy(
  id: string,
): Promise<DiscrepancyRecord> {
  if (USE_MOCKS) {
    return mockDelay(mockDiscrepancy);
  }

  return request<DiscrepancyRecord>(
    `${API_BASE}/discrepancies/${encodeURIComponent(
      id,
    )}`,
  );
}

/* =========================================================
   MULTILINGUAL
   ========================================================= */

export async function getMultilingualFields(
  recordId: string,
): Promise<MultilingualField[]> {
  if (USE_MOCKS) {
    return mockDelay(
      mockMultilingualFields,
    );
  }

  return request<MultilingualField[]>(
    `${API_BASE}/records/${encodeURIComponent(
      recordId,
    )}/multilingual`,
  );
}

/* =========================================================
   MAP
   ========================================================= */

export async function getParcels(): Promise<ParcelPin[]> {
  if (USE_MOCKS) {
    return mockDelay(mockParcels);
  }

  return request<ParcelPin[]>(
    `${API_BASE}/parcels`,
  );
}

/* =========================================================
   QUEUE
   ========================================================= */

export async function getQueueItems(): Promise<QueueItem[]> {
  if (USE_MOCKS) {
    return mockDelay(mockQueueItems);
  }

  return request<QueueItem[]>(
    `${API_BASE}/queue`,
  );
}

/* =========================================================
   ADMIN DASHBOARD
   ========================================================= */

export async function getAdminStats(): Promise<AdminStats> {
  if (USE_MOCKS) {
    return mockDelay(mockAdminStats);
  }

  return request<AdminStats>(
    `${API_BASE}/admin/stats`,
  );
}

/* =========================================================
   OFFICERS
   ========================================================= */

export async function getOfficers(): Promise<Officer[]> {
  if (USE_MOCKS) {
    return mockDelay(mockOfficers);
  }

  return request<Officer[]>(
    `${API_BASE}/admin/officers`,
  );
}

/* =========================================================
   PUBLIC LOOKUP
   ========================================================= */

export async function getLookupResults(): Promise<LookupResult[]> {
  if (USE_MOCKS) {
    return mockDelay(
      mockLookupResults,
    );
  }

  return request<LookupResult[]>(
    `${API_BASE}/lookup`,
  );
}