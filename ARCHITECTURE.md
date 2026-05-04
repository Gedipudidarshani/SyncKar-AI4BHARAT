# ARCHITECTURE.md — SyncKar Interoperability Layer
> Authoritative system design reference.
> All decisions that touch system boundaries must be consistent with this document.
> Update this file before changing the architecture, not after.

---

## 1. Problem in Engineering Terms

| World | Role | Reality |
|-------|------|---------|
| **SWS** | Canonical going forward | Accepts new registrations; issues service requests |
| **40+ Dept Systems** | Authoritative for existing records | Still accept direct service requests; most have no webhooks |

A service request raised in either world must propagate to the other **without modifying either system**. Simultaneous updates to the same business (UBID) from multiple sources must be detected as conflicts and resolved by policy — deterministically, not manually.

Core engineering problems:
1. **Change discovery** in systems that don't emit events.
2. **Heterogeneous schema translation** across REST, SOAP/XML, CSV, and file-based APIs.
3. **Idempotent delivery** under at-least-once semantics.
4. **Conflict resolution** without trusting source timestamps.
5. **Append-only audit** that satisfies BSA 2023 court-admissibility requirements.

---

## 2. System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                       INTEROPERABILITY LAYER                          │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                        Ingestion Layer                           │  │
│  │                                                                  │  │
│  │  ┌──────────────┐  ┌──────────────────┐  ┌───────────────────┐  │  │
│  │  │ Webhook       │  │  High-Water Mark  │  │  Snapshot Diff    │  │  │
│  │  │ Receiver      │  │  Poller (Celery)  │  │  Engine (Celery)  │  │  │
│  │  │ (FastAPI)     │  │  Tier 1/2 depts  │  │  Tier 3/4 depts  │  │  │
│  │  └──────┬───────┘  └────────┬──────────┘  └────────┬──────────┘  │  │
│  └─────────┼──────────────────  ┼ ────────────────────  ┼ ───────────┘  │
│            │   translate_inbound()                       │              │
│            ▼                   ▼                         ▼              │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │              Transactional Outbox (PostgreSQL)                   │  │
│  │         Atomic write; drains to Kafka when available             │  │
│  └────────────────────────────┬────────────────────────────────────┘  │
│                               │                                         │
│                               ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                        Kafka Event Bus                           │  │
│  │   sws.changes          dept.{name}.changes        audit.events  │  │
│  │   (partitioned by UBID — strict per-business ordering)          │  │
│  └────────────────────────────┬────────────────────────────────────┘  │
│                               │                                         │
│                               ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                    Propagation Pipeline                          │  │
│  │                                                                  │  │
│  │  ┌──────────────────────┐   ┌──────────────────────────────┐    │  │
│  │  │  Sliding-Window       │   │  Two-Phase Reservation        │    │  │
│  │  │  Conflict Detector   │──►│  Idempotency Engine (Redis)   │    │  │
│  │  │  (Redis TTL)         │   │                              │    │  │
│  │  └──────────────────────┘   └──────────────────────────────┘    │  │
│  │              │                         │                          │  │
│  │              ▼                         ▼                          │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │   Dispatcher (fan-out to relevant adapters per UBID)        │  │  │
│  │  └───────────────┬──────────────────────────┬─────────────────┘  │  │
│  └─────────────────  ┼ ─────────────────────────  ┼ ─────────────────┘  │
│                      │                             │                     │
│           ┌──────────┼───────────┐   ┌────────────┼─────────────┐      │
│           ▼          ▼           ▼   ▼            ▼             ▼      │
│  ┌─────────────┐ ┌────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │  SWS Adapter│ │ShopEst │ │  Factories   │ │  Circuit Breaker     │ │
│  │  (REST/JSON)│ │Adapter │ │  Adapter     │ │  (per adapter,       │ │
│  │             │ │(SOAP)  │ │  (REST+poll) │ │   Redis state)       │ │
│  └──────┬──────┘ └───┬────┘ └──────┬───────┘ └──────────────────────┘ │
│         │            │             │                                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │               Audit Ledger (PostgreSQL, append-only)              │  │
│  │      SHA-256 per row | RSA-signed | BSA 2023–compliant           │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Schema Registry (Git-versioned YAMLs) + AI Schema Co-Pilot      │  │
│  │  Drift Detector | Admin API | Data Steward Dashboard (React)     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
         │                                            │
         ▼                                            ▼
┌─────────────────┐                      ┌─────────────────────┐
│  Karnataka SWS  │                      │  40+ Dept Systems   │
│  (Unmodified)   │                      │  (Unmodified)       │
└─────────────────┘                      └─────────────────────┘
```

---

## 3. Adapter Tiers

| Tier | Protocol | Change Detection | Examples |
|------|----------|-----------------|---------|
| **Tier 1** | REST / JSON | High-water mark polling | Shop Establishment |
| **Tier 2** | REST + webhook | Webhook receiver (push) | BBMP (if supported) |
| **Tier 3** | SOAP / XML | High-water mark polling via zeep | Factories Act |
| **Tier 4** | File / CSV / bulk export | Cryptographic snapshot diff (MurmurHash3) | Any dept with batch exports |

---

## 4. Data Flow — Direction 1: SWS → Departments

```
1.  Officer updates registered address for UBID-KA-1234 in SWS.

2.  SWS Adapter detects the change:
      - If SWS exposes a webhook → webhook POST hits /api/webhooks/sws
      - If not → high-water mark poller detects the change on next cycle

3.  SWS Adapter calls translate_inbound(raw, mapping_version="v1")
    → produces CanonicalServiceRequest with correlation_id assigned here.

4.  Canonical event written atomically to Transactional Outbox (PostgreSQL).

5.  Outbox Worker publishes to Kafka topic `sws.changes`.
    Partition key = UBID (guarantees per-business ordering).

6.  Each Department Adapter has its own Kafka consumer group, consuming `sws.changes`.
    Consumer groups are isolated — ShopEst being slow doesn't block Factories.

7.  For each consuming Department Adapter:
    a. Check: does this UBID exist in this department? If not → log UBID_NOT_FOUND, skip.
    b. Check sliding-window conflict detector (Redis, 15-min TTL by default).
       If conflict → apply Policy Matrix → write ConflictAuditRecord.
    c. Two-Phase Reservation: SET idempotency_key IN_PROGRESS (Redis NX).
       If key = COMPLETED → skip, return cached response.
       If key = IN_PROGRESS → back off, retry.
    d. translate_outbound(request) using request.mapping_version.
    e. apply_change() → call department API (REST or SOAP via zeep).
    f. On success → SET idempotency_key COMPLETED (TTL = 72h) → write AuditRow.
    g. Commit Kafka offset only after success.
    h. On TargetWriteError (5xx) → do NOT commit offset → Celery retries with backoff.
    i. On PermanentWriteError (4xx) → DLQ + AuditRow(status=FAILED) + alert.
```

---

## 5. Data Flow — Direction 2: Departments → SWS

```
Two detection strategies, chosen per adapter's tier:

Strategy A — High-Water Mark (Tier 1, 2, 3):
  1.  Celery periodic task runs every N minutes (configurable per dept).
  2.  Adapter queries dept API: "give me records modified after <watermark>".
  3.  For each returned record: skip if no UBID → translate_inbound() → Outbox.
  4.  Update watermark to current time.
  5.  Outbox → Kafka topic `dept.{name}.changes`.

Strategy B — Snapshot Diff (Tier 4, file/bulk export):
  1.  Celery task fetches full bulk export (CSV / XML / file).
  2.  Computes MurmurHash3 of each row keyed by UBID (sort keys first).
  3.  Compares against stored snapshot hashes (PostgreSQL dept_snapshots table).
  4.  UBIDs where hash diverged → fetch full record → translate_inbound() → Outbox.
  5.  Stores new snapshot hashes.

Both strategies then share the same egress path:
  6.  SWS Adapter consumes `dept.{name}.changes`.
  7.  Runs conflict detection + idempotency check.
  8.  translate_outbound() → apply_change() to SWS API.
  9.  AuditRow written. Kafka offset committed on success.
```

---

## 6. Conflict Detection & Resolution (Detailed)

### Why Not Timestamps

Legacy department systems have no guaranteed NTP synchronisation.
A timestamp of `10:00:00` from Factories and `10:00:01` from SWS may be minutes apart in real time.
Polling-based adapters assign a *detection time*, not a *mutation time*.

**Decision**: Use Kafka broker sequence numbers — monotonically increasing per partition.
Since partitions are keyed by UBID, all events for the same business are strictly ordered by sequence.

**Limitation acknowledged**: Broker sequence reflects *ingestion time*, not *business event time*.
If a dept change occurred at 09:55 but polling detected it at 10:00 (sequence 100), and
an SWS change at 09:59 published at 09:59:30 (sequence 99), the sequence reverses true chronology.
This is inherent to polling-based systems. It is mitigated by `temporal_confidence` metadata on every conflict row:
- `HIGH`   — both sources are webhook/real-time
- `MEDIUM` — one source is polling-based
- `LOW`    — both sources are polling-based or snapshot-derived

### Sliding-Window Detector

Before writing to any target, the adapter checks Redis:
```
Key: conflict_window:{ubid}:{field_name}
TTL: conflict_window_seconds (default 900s / 15 minutes)
Value: {source_system, broker_sequence, payload_hash, correlation_id}
```
If a key exists from a **different source**: conflict detected.
If no key: write current event's metadata to Redis (with TTL), proceed.

### Policy Matrix

| Data Category | Fields (examples) | Policy | Rationale |
|---------------|------------------|--------|-----------|
| Universal Demographics | registered_address, authorized_signatory, primary_contact | **SWS Wins** | SWS is the state's canonical front door for demographic data |
| Regulatory Compliance | license_status, safety_clearance, labor_violations | **Dept Wins** | Only the issuing authority can change compliance status |
| Unrestricted Metadata | employee_headcount, operational_status, last_inspection_date | **LWW (higher broker_sequence)** | Low-stakes; recency is the best proxy |
| Unmapped / Unknown | New fields, unconfigured combinations | **DLQ** | Alert Data Steward; no automated rule exists |

Outside the conflict window: normal Last-Write-Wins, but **still audited**. Every write records old and new values.

---

## 7. Idempotency Engine (Two-Phase Reservation)

```
PHASE 1 — RESERVE
  Redis: SET idempotency_key "IN_PROGRESS" NX EX 3600
  ├─ Key = COMPLETED → return cached API response; skip write; commit offset
  ├─ Key = IN_PROGRESS → another worker is live; back off and retry
  └─ Key absent → reservation succeeds; proceed to PHASE 2

PHASE 2 — EXECUTE
  Call target system API (REST or SOAP).

PHASE 3 — COMPLETE
  Redis: SET idempotency_key "COMPLETED:{cached_response}" EX 259200  (72 hours)

Handles:
  - Normal retry: key = COMPLETED → duplicate silently dropped
  - Race condition: Redis NX prevents two workers on the same event simultaneously
  - Write-succeeded-but-ACK-lost: key = COMPLETED on restart → no double-write
  - Redis down: fall back to querying the target API for current field value
```

Key construction (time-independent):
```
SHA-256( source_system_id | source_event_id | ubid | field_name | new_value )
```

---

## 8. Schema Mapping — YAML Structure

```yaml
# schema_registry/shop_establishment/mapping_v1.yaml
version: "v1"
certified_by: "data.architect@karnataka.gov.in"
certified_at: "2026-05-10T14:30:00Z"
adapter_tier: 3
protocol: "SOAP/XML"
wsdl_contract: "adapters/departments/shop_establishment/wsdl/shop_est_v2.wsdl"
auth:
  type: "wss_username_token"
  credential_ref: "vault://shop-est/api-creds"
fields:
  - source_field: "registered_address_primary"
    target_field: "Buss_Addr_Line1"
    transform: "truncate(120)"
    required: true
  - source_field: "authorized_signatory_name"
    target_field: "Auth_Sign_Name"
    transform: "uppercase"
    required: true
```

**Hot-Swap Rule**: Events ingested under `mapping_v1` carry `mapping_version="v1"` in `CanonicalServiceRequest`. They are processed with `mapping_v1` rules even after `mapping_v2` is deployed. This prevents mid-flight schema mismatches.

---

## 9. Schema Drift Detection

Runs on every adapter's ingress path (every poll cycle):

**Structural checks**:
- Column count changed?
- Column names changed?
- Data types changed in API response metadata?

**Statistical checks**:
- Null-rate distribution per field (spike in nulls = likely field rename or removal)
- Value-range distribution shift
- Cardinality change

**On detection**:
- Affected records → quarantine topic (`dept.{name}.quarantine`)
- Unaffected fields continue propagating normally
- Alert raised for ops team
- AI Co-Pilot (if enabled) generates plain-English hypothesis from before/after schema headers (no PII)
- Example: *"Field `Buss_Addr_Line1` appears renamed to `BusinessAddressLine1` based on null-rate patterns."*

---

## 10. BSA 2023 Audit Ledger

### PostgreSQL Schema

```sql
CREATE TABLE audit_ledger (
    audit_id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    correlation_id       UUID        NOT NULL,      -- links all hops of one request
    ubid                 TEXT        NOT NULL,
    field_modified       TEXT        NOT NULL,
    old_value            TEXT,
    new_value            TEXT        NOT NULL,
    source_system        TEXT        NOT NULL,
    target_system        TEXT        NOT NULL,
    api_endpoint         TEXT        NOT NULL,      -- exact URL or WSDL operation
    source_ip            TEXT        NOT NULL,
    conflict_detected    BOOLEAN     NOT NULL DEFAULT false,
    resolution_policy    TEXT,
    broker_seq_a         BIGINT,                    -- populated on conflict rows
    broker_seq_b         BIGINT,
    temporal_confidence  TEXT,                      -- HIGH | MEDIUM | LOW
    payload_sha256       TEXT        NOT NULL,      -- SHA-256 of CanonicalServiceRequest JSON
    rsa_signature        TEXT        NOT NULL,      -- RSA signature of this row
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Append-only enforced at DB level:
-- REVOKE UPDATE, DELETE ON audit_ledger FROM synckar_app_role;

CREATE INDEX idx_audit_correlation ON audit_ledger(correlation_id);
CREATE INDEX idx_audit_ubid        ON audit_ledger(ubid);
CREATE INDEX idx_audit_created_at  ON audit_ledger(created_at);
```

### Traceability Query

```sql
-- Trace every hop of a single service request end-to-end:
SELECT * FROM audit_ledger
WHERE correlation_id = 'corr-7f3a-4b2c'
ORDER BY created_at;
```

---

## 11. Reconciliation Job (Nightly)

```
1. Select 1% random sample of UBIDs (~20K businesses at 2M scale).
2. For each UBID: query SWS + each registered department API for critical fields
   (registered_address, authorized_signatory, license_status).
3. Compare field values across systems.
4. Any mismatch that escaped event-driven propagation:
   → Emit synthetic correction event into the normal pipeline.
   → Full audit trail: source=reconciliation_job, correlation_id=new UUID.
5. Log reconciliation coverage stats to Prometheus.
```

This catches silent drift that event-driven propagation missed (e.g., direct DB edits on dept side, events lost before system was deployed).

---

## 12. Throughput Profile

| Parameter | Estimate | Basis |
|-----------|----------|-------|
| Registered businesses | ~2,000,000 | Karnataka DPIIT |
| Departments per business | ~3–5 avg | Most businesses interact with 3–5 depts |
| Updates per business per year | ~2–4 | Address changes, signatory updates, renewals |
| **Sustained event rate** | **~15–25 events/second** | 2M × 3 updates/yr ÷ 250 days ÷ 8h ÷ 3600s |
| **Batch spike rate** | **~500–1,000 events/second** | Monthly dept batch syncs over 2 hours |
| Fan-out per event | ~3–5 dept writes | Each SWS change → 3–5 departments |
| **Peak write throughput** | **~2,500–5,000 API calls/second** | Batch spike × fan-out |

Kafka handles 100K+ msg/s. The real bottleneck is legacy API throughput (often 10–100 req/min per dept). Per-department rate limiters + consumer-group isolation ensure one slow department doesn't block others.

---

## 13. Kafka Topic Design

| Topic | Producers | Consumers | Key | Retention |
|-------|-----------|-----------|-----|-----------|
| `sws.changes` | SWS adapter | All dept adapters | UBID | 7 days |
| `dept.{name}.changes` | Dept adapter | SWS adapter | UBID | 7 days |
| `audit.events` | All adapters | Audit ledger writer | correlation_id | 30 days |
| `propagation.dlq` | All adapters (on exhaustion/4xx) | Data Steward dashboard | UBID | 30 days |
| `dept.{name}.quarantine` | Drift detector | Ops alert system | UBID | 7 days |

---

## 14. Architecture Decision Records

| ID | Decision | Rationale |
|----|----------|-----------|
| ADR-001 | Kafka as event bus (not RabbitMQ or PG LISTEN/NOTIFY) | Log retention for forensic audit replay; per-UBID partitioning for ordering; consumer-group isolation per dept; handles batch-spike variability |
| ADR-002 | Broker sequence (not timestamps) for conflict ordering | Legacy systems have no NTP sync; timestamps are unreliable; broker sequence is the only monotonic truth |
| ADR-003 | Two-Phase Reservation (Redis NX) for idempotency | Sub-ms key lookup; NX flag prevents concurrent workers; TTL-based auto-expiry; graceful Redis-down fallback |
| ADR-004 | MurmurHash3 for snapshot diffing (not SHA-256) | Non-cryptographic but fast; sufficient for diffing 2M+ rows; collision rate ~1 in 2^32 per pair; SHA-256 used where integrity matters |
| ADR-005 | PostgreSQL for Outbox + Audit Ledger (not Redis) | Durability required for audit; ACID transactions for Outbox atomicity; append-only enforced at SQL RBAC level |
| ADR-006 | zeep for SOAP (not raw XML) | Native WSDL parsing; handles WS-Security headers; reduces per-adapter boilerplate significantly |
| ADR-007 | RSA per-row signing (not blockchain chaining) | Tamper evidence without fragility; a single corrupted record in a chain breaks all subsequent verification |
| ADR-008 | AI Co-Pilot on synthetic data only | BSA 2023 compliance; government data cannot leave the perimeter; AI is an accelerator, not a decision-maker |
| ADR-009 | Sliding-window conflict detector (15 min default) | 15 min covers realistic polling latency; configurable per field; outside window = normal LWW with audit |
| ADR-010 | Per-adapter circuit breaker in Redis | Shared state across all Celery workers; prevents thundering-herd on recovering legacy APIs |
