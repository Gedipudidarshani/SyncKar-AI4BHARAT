# SyncKar — Event-Driven Interoperability Layer for Karnataka's Single Window System

## 1. Problem Understanding

Karnataka's Single Window System (SWS) and 40+ legacy department systems operate as isolated data silos. A business can raise the same service request—say, a change of registered address—on either SWS or a department portal, and the two sides never learn about each other's update. The result is a **split-brain problem**: officers see stale data, citizens repeat paperwork, and there is no unified audit trail.

A big-bang migration is not viable. The GST rollout proved that single-day cutovers over fragmented, heterogeneous systems fail at scale. The only workable path is an **incremental, non-invasive interoperability layer** that synchronizes state bidirectionally while both SWS and legacy systems continue to run unmodified.

### Why This Is Hard

- **40+ systems, 40+ dialects.** Each department has its own schema, identifiers, APIs (REST, SOAP, file-based), and authentication mechanisms.
- **No shared clock.** Legacy systems have no NTP synchronization — timestamps cannot be trusted for ordering.
- **No shared event bus.** Most department systems do not emit events; changes must be *discovered*, not *received*.
- **No modification allowed.** Neither SWS nor any department system can be changed. The layer integrates via the surfaces they already expose.
- **UBID is a precondition.** The Unique Business Identifier exists on both sides and is the only reliable join key. It is not something the layer invents, matches, or scores.
- **UBID coverage is not 100%.** In practice, some legacy department records may not yet carry a UBID — particularly older registrations that predate the identifier's rollout. These records are **invisible to the sync layer by design**. A UBID enrollment gap analysis is a deployment precondition for the government, not a problem the middleware solves. The layer's coverage grows automatically as departments populate UBIDs in their existing records.

---

## 2. Architecture Overview

```
┌───────────────────────────────────────────────────────────────────────┐
│                        INTEROPERABILITY LAYER                        │
│                                                                      │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────────┐  │
│  │   SWS       │    │              │    │  Protocol-Agnostic      │  │
│  │   Adapter   │◄──►│  Event Bus   │◄──►│  Department Adapters    │  │
│  │  (Ingress/  │    │  (Kafka)     │    │  ┌───────────────────┐  │  │
│  │   Egress)   │    │              │    │  │ Dept 1 (REST)     │  │  │
│  └──────┬──────┘    │  ┌────────┐  │    │  │ Dept 2 (SOAP/XML) │  │  │
│         │           │  │Outbox  │  │    │  │ Dept 3 (Polling)  │  │  │
│         │           │  │Worker  │  │    │  │ Dept 4 (File/CSV) │  │  │
│         │           │  └────────┘  │    │  │ ...               │  │  │
│         │           └──────────────┘    │  └───────────────────┘  │  │
│         │                               └────────────┬────────────┘  │
│         │           ┌──────────────┐                 │               │
│         └──────────►│ Idempotency  │◄────────────────┘               │
│                     │ Engine       │                                  │
│                     │ (Redis)      │                                  │
│                     └──────────────┘                                  │
│                                                                      │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────────────────┐ │
│  │ Conflict     │  │ Audit Ledger  │  │ Schema Registry &          │ │
│  │ Resolution   │  │ (Append-Only  │  │ Drift Detection            │ │
│  │ Matrix       │  │  PostgreSQL)  │  │                            │ │
│  └──────────────┘  └───────────────┘  └────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  Admin: Data Steward Dashboard (DLQ Review) + Monitoring      │  │
│  └────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────┘
         │                                              │
         ▼                                              ▼
┌─────────────────┐                         ┌───────────────────┐
│  Karnataka SWS  │                         │  40+ Department   │
│  (Unmodified)   │                         │  Systems          │
│                 │                         │  (Unmodified)     │
└─────────────────┘                         └───────────────────┘
```

### Core Design Principles

| # | Principle | Meaning |
|---|-----------|---------|
| 1 | **Leave and Layer** | Zero modifications to any source system. The layer wraps around existing surfaces. |
| 2 | **Listen, Don't Demand** | Legacy systems that cannot emit events are polled or diffed — never forced to change. |
| 3 | **Determinism Over Human Judgment** | Conflicts are resolved by automated policy. Humans see only DLQ edge cases. |
| 4 | **Immutable Audit by Default** | Every propagation generates an audit row. Nothing is overwritten without a trace. |
| 5 | **UBID Is Gospel** | No matching, scoring, or inference. If UBID exists, the record is joinable. If it doesn't, the record is invisible. |

---

## 3. Direction 1 — SWS → Department Systems

### Flow

1. An officer updates a business's registered address in SWS for `UBID-KA-1234`.
2. The **SWS Adapter** detects the change (webhook if SWS exposes one, or stateful API polling).
3. The adapter writes a **canonical event** (JSON) into the PostgreSQL **Transactional Outbox**, atomically within the same DB transaction as any local state update.
4. An **Outbox Worker** picks up the event and publishes it to the Kafka topic `sws.changes`, partitioned by UBID (ensures per-business ordering).
5. Each **Department Adapter** subscribes to `sws.changes` via its own Kafka consumer group.
6. The adapter for, say, Shop Establishment:
   - Looks up `UBID-KA-1234` in the department's API; if the UBID does not exist there, logs the skip and moves on.
   - Translates the canonical JSON into the department's required format (e.g., SOAP/XML envelope with WS-Security headers).
   - Passes the payload through the **Idempotency Engine** (see §5).
   - Writes to the department API. On success, commits the Kafka offset and writes an **audit row**.
   - On failure, the message stays in Kafka for retry with exponential backoff.

### Schema Translation

Each adapter maintains a **declarative mapping file** (version-controlled YAML/JSON) that defines:
```yaml
# shop_establishment_adapter/mapping_v3.yaml
source_field: "registered_address_primary"
target_field: "Buss_Addr_Line1"
target_format: "SOAP/XML"
wsdl_contract: "shop_est_v2.wsdl"
transform: "truncate(120)"  # field length constraint
auth:
  type: "wss_username_token"
  credential_ref: "vault://shop-est/api-creds"
```

When a new department is onboarded, the **AI Schema Co-Pilot** (see §8) generates a *draft* mapping from synthetic data. A government data architect validates and certifies it. The certified mapping is versioned in a Git-based **Schema Registry**.

---

## 4. Direction 2 — Department Systems → SWS

### The Challenge

Most department systems do not emit events. They have APIs, but no webhooks, no message queues, no change notifications. The layer must discover changes itself.

### Non-Invasive Change Detection (Two Strategies)

| Strategy | When Used | How It Works | Latency |
|----------|-----------|--------------|---------|
| **Stateful API Polling** | Department exposes a read API (REST or SOAP) | Adapter maintains a persistent **high-water mark** (latest processed timestamp or sequence ID). Every polling cycle (configurable: 30s – 15min), queries for records modified after the watermark. Extracts deltas, translates to canonical JSON, publishes to Kafka topic `dept.{name}.changes`. | 30s – 15min |
| **Cryptographic Snapshot Diffing** | Department only provides periodic bulk exports (CSV, XML, flat files) | Adapter ingests the full export, computes a fast hash (MurmurHash3) of each row keyed by UBID. Compares against the previous snapshot's hash map. Rows where hashes diverge are emitted as change events. Handles inserts, updates, and deletes. | Daily or on-demand |

> **Note on MurmurHash3**: At 2M+ rows, collision probability is ~1 in 2³² per pair. For diffing purposes (not security), this is acceptable. Suspicious collisions (hash match but field-count mismatch) are flagged for secondary verification.

### Flow (Department → SWS)

1. The **Factories Adapter** detects via polling that `UBID-KA-1234` has a new authorized signatory.
2. It translates the department's native format into the canonical JSON schema.
3. It writes to the **Transactional Outbox** → Outbox Worker publishes to `dept.factories.changes`.
4. The **SWS Adapter** consumes the event, translates it to SWS's API format, runs through the **Conflict Resolution Matrix** (see §6), writes to SWS via its API, and logs an audit row.

---

## 5. Deterministic Idempotency Engine

### The Problem

In distributed systems, at-least-once delivery means messages will be retried. Retries must not cause duplicate writes.

### The Key Design Decision

The idempotency key must be **deterministic and time-independent**. A retry of the same logical operation hours later must produce the identical key.

```
IdempotencyKey = SHA-256(
    source_system_id  +  // "sws" or "dept_factories"
    source_event_id   +  // assigned once at origin, immutable
    UBID              +  // "KA-1234"
    field_name        +  // "registered_address"
    new_value            // "123 MG Road, Bangalore"
)
```

> **No timestamp. No wall-clock data. Ever.**

For systems that lack a native event ID or transaction ID, the `source_event_id` is derived from a hash of the stable record state at first detection (e.g., `SHA-256(UBID + field_name + old_value + new_value)` from the polling snapshot).

### Two-Phase Reservation Pattern (Redis-Backed)

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: RESERVE                                            │
│  Adapter attempts atomic SET key=IN_PROGRESS (NX flag)      │
│  ├─ Key already exists with COMPLETED → Return cached       │
│  │   response, skip API call entirely                       │
│  ├─ Key already exists with IN_PROGRESS → Another worker    │
│  │   is processing it; back off and retry                   │
│  └─ Key does not exist → Reservation succeeds, proceed      │
│                                                             │
│  Step 2: EXECUTE                                            │
│  Adapter calls the target department/SWS API                │
│                                                             │
│  Step 3: COMPLETE                                           │
│  Update Redis: key → COMPLETED + cached API response        │
│  Set TTL = Kafka max retry window + buffer (e.g., 72 hours) │
└─────────────────────────────────────────────────────────────┘
```

**What this solves:**
- **Normal retry**: Key exists as COMPLETED → duplicate silently dropped.
- **Concurrent retry (race condition)**: Redis NX flag prevents two workers from processing the same event simultaneously.
- **Write-succeeded-but-ACK-lost**: On restart, the adapter checks Redis for COMPLETED status. If found, it replays the cached response to the broker without touching the target API.

---

## 6. Automated Conflict Resolution Matrix

### The Problem

When two systems update the same UBID + field within a short window, the layer must detect the conflict and apply a **deterministic, configurable policy** — not block on human review.

### Why Timestamps Cannot Be Trusted

Legacy department systems rarely run NTP-synchronized clocks. A timestamp of `10:00:00` from Factory System A and `10:00:01` from SWS may be minutes apart in real time. Polling-based adapters assign a "received-at" timestamp, which reflects detection time, not mutation time.

### Resolution: Broker-Sequenced Ordering

Instead of source timestamps, the system uses **Kafka offset sequence numbers** — monotonically increasing integers assigned at the exact moment a message enters the broker. These are globally ordered per partition (and partitions are keyed by UBID, so all events for the same business are strictly ordered).

> **Temporal Ambiguity Acknowledgment**: Broker sequence numbers reflect *ingestion time*, not *business event time*. If a department change occurred at 09:55 but was detected by polling at 10:00 (sequence 100), and an SWS change occurred at 09:59 but was published at 09:59:30 (sequence 99), the broker sequence reverses the true chronological order. This is an inherent limitation of systems without synchronized clocks. Broker sequence is the **best available proxy** — not a definitive truth. Every conflict audit record carries a `temporal_confidence` flag: `HIGH` if both sources are webhook/real-time, `MEDIUM` if one is polling-based, `LOW` if both are polling-based or snapshot-derived. This lets administrators understand the confidence level of any automated resolution.

### Conflict Detection

A **sliding-window conflict detector** runs on the SWS Adapter and each Department Adapter's egress path:

1. Before writing to the target, the adapter checks if another event for the **same UBID + same field** was processed within the last *N* minutes (configurable per field; default: 15 minutes).
2. If yes → conflict detected → apply policy from the matrix below.
3. If no → the write proceeds, **but the conflict resolution policy still applies as a Last-Write-Wins with audit**. Even outside the conflict window, every write logs the old and new values. If a department update arrives at T+16 minutes (just outside the window), it is not silently overwritten — it proceeds as a normal LWW write with a full audit row recording what was overwritten and why. The difference is that within-window conflicts are *flagged* explicitly; outside-window writes are *audited* normally. No write, anywhere, ever escapes the audit trail.

### Policy Matrix

| Data Category | Example Fields | Authoritative Source | Resolution Policy | Rationale |
|---------------|---------------|---------------------|-------------------|-----------|
| **Universal Demographics** | Registered Address, Primary Contact, Authorized Signatory | **SWS** | **Source Priority (SWS Wins)**: SWS payload overwrites the department value. Department's conflicting update is logged but discarded. | SWS is the state's canonical front door. Demographic data flows outward. |
| **Regulatory Compliance** | License Status, Safety Clearances, Labor Violations, Inspection Results | **Respective Department** | **Domain Priority (Department Wins)**: The specialist department retains sovereign authority over its compliance fields. SWS updates to these fields are rejected and logged. | Only the issuing authority can change a license status. |
| **Unrestricted Metadata** | Employee Headcount, Operational Status, Last Inspection Date | **Shared** | **Last-Write-Wins (Broker Sequence)**: The event with the higher Kafka offset number wins. | Low-stakes fields where recency is the best proxy for correctness. |
| **Unmapped / Unknown** | New fields, unconfigured combinations | — | **Route to Dead Letter Queue (DLQ)**: Both payloads are parked. Alert raised for Data Steward. | No automated rule exists; human must define the policy before the field is processed. |

### What "No Silent Overwrites" Actually Means

Every resolution — whether automated or manual — generates a **conflict audit record**:
```json
{
  "ubid": "KA-1234",
  "field": "registered_address",
  "source_a": { "system": "sws", "value": "123 MG Road", "broker_seq": 44201 },
  "source_b": { "system": "dept_factories", "value": "456 Brigade Rd", "broker_seq": 44198 },
  "policy_applied": "SOURCE_PRIORITY_SWS_WINS",
  "winning_value": "123 MG Road",
  "timestamp_utc": "2026-05-16T10:32:07Z"
}
```

The losing value is never deleted — it's preserved in the audit row. Every resolution is explainable and reversible.

---

## 7. BSA 2023–Compliant Audit Ledger

### Legal Requirement

Section 63(4) of the **Bharatiya Sakshya Adhiniyam, 2023** requires that electronic records admitted as evidence must be accompanied by a certificate containing:
- Identification of the electronic record
- Device/system particulars that produced it
- A cryptographic hash (SHA-256 or equivalent) verifying the record's integrity

### Implementation: Append-Only Relational Ledger

Every synchronization event generates an immutable audit row in a PostgreSQL table:

| Column | Description | BSA 2023 Mapping |
|--------|-------------|-----------------|
| `audit_id` | UUID, primary key | Record identification |
| `ubid` | Business identifier | Record identification |
| `field_modified` | Which attribute changed | Record identification |
| `old_value` / `new_value` | Before/after state | Record identification |
| `source_system` | Where the change originated | Device/system particulars |
| `target_system` | Where it was propagated | Device/system particulars |
| `api_endpoint` | Exact URL/WSDL called | Device/system particulars |
| `source_ip` | Ingress IP address | Device/system particulars |
| `conflict_detected` | Boolean | Audit completeness |
| `resolution_policy` | Which policy was applied | Audit completeness |
| `correlation_id` | Links all hops of one service request | End-to-end traceability |
| `payload_sha256` | SHA-256 hash of the full serialized JSON | **Cryptographic verification** |
| `rsa_signature` | RSA signature of the row content | **Tamper evidence** |
| `created_at` | Insertion timestamp | Temporal ordering |

### Integrity Guarantees

- **Append-Only**: The database role used by the application has `INSERT` privilege only on the audit table. No `UPDATE` or `DELETE`. DBA-level access is controlled via RBAC and logged independently.
- **Per-Record RSA Signature**: Each row is signed with the middleware's private key. Any tampering is detectable by verifying the signature against the public key.
- **No Sequential Hash Chaining**: Individual record hashing + RSA signing provides tamper evidence without the operational fragility of blockchain-style chaining (where a single corrupted record breaks verification of all subsequent records).

### End-to-End Traceability

Every service request is assigned a `correlation_id` at origin. As the request propagates (SWS → adapter → Kafka → department adapter → department API), every hop logs the same `correlation_id`. Any request can be traced end-to-end:

```sql
SELECT * FROM audit_ledger
WHERE correlation_id = 'corr-7f3a-4b2c'
ORDER BY created_at;
```

---

## 8. Privacy-Preserving AI Schema Co-Pilot

### Purpose

When a new department is onboarded, its schema must be mapped to the SWS canonical schema. This is labor-intensive: field names differ (`Buss_Addr_Line1` vs. `registered_address_primary`), data types differ, validation rules differ.

### The Privacy Constraint

> *"Hosted-LLM calls on raw PII are not permitted. Any LLM usage must work on scrambled or synthetic inputs only."*

### Pipeline (Strict Order of Operations)

```
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: ON-PREMISES ONLY (Government Data Center, Air-Gapped)   │
│                                                                  │
│  Raw Dept Data ──► Synthetic Data Vault (SDV) ──► Synthetic Data │
│  (never leaves)    (open-source, runs locally)    (no real PII)  │
│                                                                  │
│  Also extracts: blank schema headers, column types, constraints  │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼ (only synthetic data + headers)
┌──────────────────────────────────────────────────────────────────┐
│ STEP 2: HOSTED LLM (Claude API / Any LLM)                       │
│                                                                  │
│  Input:  Schema headers + synthetic sample rows                  │
│  Output: Draft mapping YAML + transformation functions           │
│                                                                  │
│  The LLM NEVER sees real data. Ever.                             │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 3: VALIDATION (Sandbox Environment)                         │
│                                                                  │
│  Draft mapping tested against synthetic data in isolated sandbox  │
│  Government data architect reviews and certifies                  │
│  Certified mapping committed to Schema Registry (Git-versioned)   │
└──────────────────────────────────────────────────────────────────┘
```

### Where AI Adds Genuine Value

The hard part of schema onboarding is not typing the mapping file — it's semantic equivalence, regulatory review, and inter-departmental coordination. AI handles the **easy 80%** (field-name matching, type coercion, format detection) in hours instead of weeks; humans handle the **critical 20%** (business-rule validation, compliance sign-off) that actually determines correctness. This is a demonstration of engineering judgment, not timidity about AI.

- **Schema Mapping Acceleration**: Reduces initial mapping drafting from weeks to hours. At 40+ departments, this time savings is the difference between a 2-year rollout and a 6-month one.
- **Schema Drift Explanation** (§9): When the data observability module detects statistical drift, the LLM can generate a **plain-English hypothesis** from the before/after schema headers (no PII): *"Field `Buss_Addr_Line1` appears to have been renamed to `BusinessAddressLine1` based on null-rate patterns."* This accelerates the ops team's response from hours of investigation to minutes of confirmation.
- **Not a Production Decision-Maker**: Every AI-generated artifact (mapping or hypothesis) requires human certification before deployment.
- **Not a Single Point of Failure**: If the LLM is unavailable, mappings are written manually. The system continues to function.

---

## 9. Schema Drift Detection and Versioned Mappings

### The Problem

Department systems change their schemas without notice — a column renamed, a data type changed, a new field added. If the adapter is using a stale mapping, it will silently corrupt data or fail outright.

### Detection

A **data observability module** runs on every adapter's ingress path:

- **Structural checks**: Column count, column names, data types from API response metadata.
- **Statistical checks**: Null-rate distribution, value-range distribution, cardinality. A sudden spike in nulls for a previously-populated field signals a schema change.
- **On detection**: The adapter enters **quarantine mode** — affected records are diverted to a quarantine topic, unaffected fields continue propagating normally. An alert is raised for the ops team.

### Mapping Versioning

- All adapter mappings are stored in a **Git-backed Schema Registry**.
- Each mapping has a version number. When a department's schema changes:
  1. A new mapping version is drafted (manually or via AI co-pilot).
  2. It is validated against synthetic data in the sandbox.
  3. Upon certification, the adapter hot-swaps to the new mapping version.
  4. The old version is retained for backward compatibility during transition.
- **Hot-Swap Transition for In-Flight Events**: When a new mapping version is activated, any events already in Kafka (published under the old schema) must complete processing under the **old mapping**. The adapter tags each event with the mapping version active at ingestion time. Events ingested under `mapping_v2` are processed with `mapping_v2` rules even if `mapping_v3` has since been deployed. This prevents mid-flight schema mismatches.
- **Rollback**: If a new mapping produces errors, the adapter reverts to the previous version via a config change — no redeployment needed.

---

## 10. Failure Modes and Recovery Strategies

| # | Failure Scenario | Detection | Recovery Strategy | Guarantee |
|---|-----------------|-----------|-------------------|-----------|
| 1 | **Department API down for hours** | HTTP 5xx or connection timeout | Event stays in Kafka. Adapter retries with **exponential backoff** (1s → 2s → 4s → ... → max 30min). After configurable threshold (e.g., 6 hours), event is moved to DLQ with alert. | At-least-once. No data loss. |
| 2 | **UBID exists in SWS but not in target department** | Department API returns 404 or empty result for UBID lookup | Log as `UBID_NOT_FOUND`, skip the write for this department, commit Kafka offset. Alert ops if this occurs for >N% of events (may indicate stale UBID registry). | No crash. No retry storm. |
| 3 | **Write succeeded but ACK lost** (adapter crashes after target API commits but before Kafka offset is committed) | On restart, Kafka redelivers the message | Idempotency Engine detects the key as `COMPLETED` in Redis → returns cached response → skips the API call. No duplicate write. | Exactly-once effective behavior. |
| 4 | **Kafka consumer lag exceeds department API rate limit** | Lag monitoring via consumer group metrics | Per-department **throttling**: each adapter has a configurable rate limiter (e.g., 100 req/min for Dept A, 10 req/min for Dept B). Excess events queue in Kafka until capacity clears. | Backpressure without data loss. |
| 5 | **Schema change mid-propagation** | Drift detection flags structural/statistical anomaly | Affected records quarantined. Unaffected fields continue propagating. Ops alerted to update mapping. | Graceful degradation, not total failure. |
| 6 | **Network partition between middleware and Kafka** | Connection timeout on publish | Outbox pattern saves the event to PostgreSQL. When connectivity restores, the Outbox Worker resumes publishing. | At-least-once. Outbox is the safety net. |
| 7 | **Poisoned message (unparseable payload)** | Deserialization exception | Route to DLQ immediately. Do not retry. Alert ops. Include raw payload in DLQ record for debugging. | No infinite retry loop. |
| 8 | **Redis (idempotency store) goes down** | Connection failure to Redis | Adapter falls back to **target-state comparison**: query the department API for the current value of the field. If it already matches the payload, skip the write. If not, proceed. Slightly slower, but correct. | Degraded but functional. |
| 9 | **Batch collision** (department runs a 50K-record batch update that collides with real-time SWS updates) | Conflict detector sees burst of conflicts for multiple UBIDs | Automated policy matrix handles each conflict independently. No human bottleneck. Batch completes without blocking real-time flow. | Scalable conflict resolution. |
| 10 | **Persistent department API failure (Circuit Breaker)** | Consecutive failures exceed threshold (e.g., 5 failures in 2 minutes) | Adapter enters **OPEN** state: stops calling the department API, immediately routes events to a holding queue. Periodic health-check probe (e.g., every 60s) tests the API with a lightweight ping. On success → HALF-OPEN state → process one real event → if success → CLOSED (resume normal flow). Prevents thundering-herd attacks on recovering legacy APIs. | No retry storm on fragile endpoints. |
| 11 | **Consistency drift after partition heals** | No detection during normal event flow — drift only visible via proactive check | A **nightly reconciliation job** queries SWS and each department API for a random sample of UBIDs (e.g., 1% = 20K businesses). Compares critical fields (address, signatory, license status). Any mismatches that escaped event-driven propagation are emitted as synthetic correction events into the normal pipeline, processed with full audit trail. | Catches silent drift that event-driven propagation missed. |

---

## 11. Risks and Trade-Offs

| Trade-Off | Decision Made | Cost Accepted | Why |
|-----------|--------------|---------------|-----|
| **Latency vs. Non-Invasive Extraction** | Polling (30s–15min) and snapshot diffing (daily) instead of database log capture (sub-second). | Near-real-time is sacrificed for Tier 3/4 systems. | Database log access (Debezium) requires configuration changes that violate the no-modification constraint. Polling is slower but universally applicable and politically feasible. |
| **Availability vs. Consistency (CAP)** | AP over CP. The system accepts updates optimistically and propagates asynchronously. | Systems may temporarily drift out of sync during network partitions. | Blocking a citizen's update because a backend department connection is down is worse than temporary inconsistency. Eventual consistency is restored when the partition heals. |
| **Automation vs. Accuracy** | Automated conflict resolution for >95% of cases; human DLQ for edge cases. | A small percentage of automated resolutions may be "wrong" by some department's subjective standard. | Manual review of every conflict is operationally impossible at 2M+ businesses. The automated policies are configurable — departments can tune them. |
| **Storage vs. Audit Completeness** | Full before/after state, metadata, and SHA-256 hash for every event. | Storage footprint grows significantly — estimated ~500GB/year for 2M businesses × 40 departments at moderate update frequency. | BSA 2023 compliance requires this. Tiered archiving (hot: 90 days, warm: 1 year, cold: 7 years) manages cost. |
| **Kafka vs. Simpler Queues** | Kafka chosen over RabbitMQ or PostgreSQL LISTEN/NOTIFY. | Higher operational complexity; requires dedicated expertise. | Kafka provides: (a) **log retention** for forensic audit replay, (b) **per-UBID partitioning** for strict per-business ordering, (c) **consumer-group isolation** so one slow department adapter cannot block others, (d) **backpressure handling** across heterogeneous API latencies. |
| **AI as Accelerator vs. Core Dependency** | AI generates draft mappings only; human-certified before deployment. | Onboarding is faster but not fully automated; human bottleneck remains for final certification. | Government data integrity cannot depend on LLM accuracy. AI can hallucinate field mappings. Human sign-off is the safety net. |

---

## 12. Throughput Estimation and Scale

To justify technology choices with data rather than assumptions:

| Parameter | Estimate | Basis |
|-----------|----------|-------|
| Registered businesses | ~2,000,000 | Karnataka DPIIT data |
| Departments per business (avg) | ~3–5 | Most businesses interact with 3–5 departments |
| Updates per business per year (avg) | ~2–4 | Address changes, signatory updates, license renewals |
| **Sustained event rate** | **~15–25 events/second** | 2M × 3 updates/year ÷ 250 working days ÷ 8 hours ÷ 3600s |
| **Batch spike rate** | **~500–1000 events/second** | Monthly department batch syncs of 50K–100K records over 2 hours |
| Fan-out per event | ~3–5 department writes | Each SWS change propagates to 3–5 relevant departments |
| **Peak write throughput** | **~2500–5000 API calls/second** | During batch spikes with full fan-out |

Kafka comfortably handles 100K+ messages/second on modest hardware. The bottleneck is **legacy API throughput** — many department APIs sustain only 10–100 req/min. Per-department rate limiters (§10, Failure #4) manage this. Kafka's consumer-group isolation ensures that one slow department (10 req/min) does not block a faster one (100 req/min).

This throughput profile confirms Kafka is justified over simpler queues: the batch-spike variability, per-department parallelism, and log-retention needs collectively exceed what PostgreSQL LISTEN/NOTIFY or RabbitMQ handle gracefully.

---

## 13. Tech Stack and Justification

| Component | Technology | Why This Choice |
|-----------|-----------|----------------|
| **Event Bus** | Apache Kafka | Log retention for audit replay; per-UBID partitioned topics for ordering; consumer-group isolation per department. Handles 100K+ msg/s; justified by batch-spike profile (§12). |
| **Primary Database** | PostgreSQL | Transactional Outbox support; append-only audit ledger; mature RBAC. |
| **Idempotency Store** | Redis | Sub-millisecond key lookups for Two-Phase Reservation; TTL-based automatic expiry. |
| **Backend / Adapters** | Python (FastAPI) | Rapid adapter development; rich ecosystem for SOAP/XML (zeep), REST, CSV parsing. |
| **SOAP/XML Handling** | `zeep` (Python) + WSDL contracts | Native WSDL parsing and XML envelope construction for legacy government APIs. |
| **Schema Co-Pilot** | Claude API (or any hosted LLM) | Draft mapping generation on synthetic data only. No vendor lock-in — swappable for any LLM. |
| **Synthetic Data** | Synthetic Data Vault (SDV) | Open-source, runs on-premises, generates statistically faithful synthetic datasets. |
| **Monitoring** | Prometheus + Grafana | Consumer lag, API latency, conflict rates, DLQ depth — all visible in real time. |
| **Secret Management** | HashiCorp Vault (or env-sealed secrets) | Credential rotation, audit-logged access, per-adapter scoped policies. Government evaluators require credential security assurance. |
| **Dashboard** | React | Data Steward DLQ review interface; conflict visualization; audit search. |
| **Containerization** | Docker + Docker Compose (sandbox) | Reproducible sandbox environment for Round 2 prototype; Kubernetes-ready for production. |

---

## 14. Sample Scenario Walkthrough

### Scenario A: SWS → Departments (Address Change)

> Business `UBID-KA-1234` updates its registered address in SWS to "123 MG Road, Bangalore."

1. **SWS Adapter** detects the change → writes canonical event to Outbox.
2. **Outbox Worker** publishes to Kafka topic `sws.changes`, partition key = `KA-1234`.
3. **Shop Establishment Adapter** consumes the event:
   - Queries Shop Establishment API for `KA-1234` → record found.
   - Translates `registered_address_primary` → `Buss_Addr_Line1` via mapping YAML.
   - Computes idempotency key → not in Redis → reserves as `IN_PROGRESS`.
   - Constructs SOAP/XML envelope → calls Shop Est API → success.
   - Updates Redis → `COMPLETED`. Writes audit row. Commits Kafka offset.
4. **Factories Adapter** does the same, but via REST/JSON (different protocol, same flow).
5. **Audit trail**: Two rows in the ledger, one per department, both with the same `correlation_id`.

### Scenario B: Department → SWS (Signatory Update)

> Business `UBID-KA-1234` has its authorized signatory updated directly in the Factories system.

1. **Factories Adapter** (polling mode) detects: signatory changed since last watermark.
2. Translates to canonical JSON → Outbox → Kafka topic `dept.factories.changes`.
3. **SWS Adapter** consumes → translates to SWS format → writes via SWS API.
4. **Audit trail**: One row linking Factories → SWS.

### Scenario C: Conflict (Simultaneous Updates)

> SWS updates address for `KA-1234` at broker sequence 44201. Factories updates address for `KA-1234` at broker sequence 44198. Both arrive within 15 minutes.

1. SWS Adapter detects: another event for same UBID + same field within the conflict window.
2. Policy lookup: "Registered Address" → **Universal Demographics** → **SWS Wins**.
3. SWS's value ("123 MG Road") is propagated. Factories' value ("456 Brigade Rd") is logged but discarded.
4. **Conflict audit row** records both values, both sources, the policy applied, and the winning value.
5. An administrator can later query the audit ledger and see exactly why "456 Brigade Rd" was not applied.

---

## 15. Organisational Feasibility and Governance

The technology is ready. The governance narrative must match.

SyncKar's technical design requires **zero modifications** to source systems, but it does require **political and operational preconditions** to deploy:

| Precondition | Who Owns It | SyncKar's Dependency |
|-------------|-------------|---------------------|
| Department APIs must be accessible (network + credentials) | Each department's IT team | Adapters need read/write API access. A signed MoU framework between Karnataka Commerce & Industries and each department is the enabling instrument. |
| UBID must be populated in department records | Departments + UBID issuing authority | Records without UBID are invisible. A UBID enrollment gap analysis quantifies the sync layer's initial coverage. |
| Conflict resolution policies must be agreed upon | Inter-departmental governance body | The Source-Priority and Domain-Priority rules encode **political decisions** about data authority. These must be ratified, not assumed. |
| A nodal agency must have authority to operate the middleware | Karnataka Commerce & Industries | The middleware sits between all systems; its operating authority must be formally established. |

**SyncKar does not solve the governance problem — it makes the governance problem tractable.** By providing a concrete, auditable mechanism for data flow, it gives departments a *reason* to participate: they gain visibility into SWS changes affecting their records, rather than discovering inconsistencies during field inspections.

---

## 16. Quantified Impact

For a panel of policymakers at the PAN IIT Summit, impact must be stated in numbers, not abstractions.

| Impact Dimension | Current State | With SyncKar | Estimated Savings |
|-----------------|--------------|-------------|-------------------|
| **Redundant paperwork** | A business changing its address must update it separately in SWS and each relevant department (avg 3–5 portals) | One update in SWS propagates automatically to all departments | **~4M–8M redundant form submissions eliminated per year** (2M businesses × 2–4 updates/year × avg 2–4 redundant filings) |
| **Field officer verification visits** | Officers visit businesses to verify data that is stale because department records weren't updated | Officers work from current, synchronized data | **~50–70% reduction in redundant verification visits** |
| **Compliance failures from stale data** | Businesses penalized for non-compliance based on outdated records in department systems | Records stay in sync; compliance status reflects current state | **Reduced wrongful compliance notices** |
| **Audit accountability** | No traceable record of what changed, where, or why across systems | Every propagation is BSA 2023–compliant and court-admissible | **100% of inter-system data flows become legally auditable** — today the number is 0% |
| **New department onboarding** | Weeks to months of manual schema analysis, testing, and negotiation | AI-accelerated draft mappings + sandbox validation | **~60–80% reduction in per-department onboarding time** |

> The single most powerful impact statement for the Summit: **"Today, no electronic record synchronized between SWS and department systems can be tendered as evidence in an Indian court, because no compliant audit trail exists. SyncKar creates one — for every transaction, retroactively."**

---

## 17. Round 2 Implementation Plan (Sandbox)

Assuming a sandbox with mock SWS and department endpoints on deterministically scrambled data:

### Phase 1: Foundation (Days 1–2)
- Stand up Kafka cluster (single-broker for sandbox) + PostgreSQL + Redis via Docker Compose.
- Build the **SWS Adapter**: connect to mock SWS API, implement stateful polling, write to Outbox.
- Build **2 department adapters**: one REST/JSON (Tier 1), one SOAP/XML (Tier 3 with polling).
- Validate: a change in mock SWS appears as an event in Kafka.

### Phase 2: Bidirectional Propagation (Days 3–4)
- Implement the **egress path**: adapters consume from Kafka, translate schema, write to target mock APIs.
- Implement the **Idempotency Engine** (Redis + Two-Phase Reservation).
- Test: inject duplicate Kafka messages → verify no duplicate writes.
- Test: address change in SWS propagates to both mock departments.
- Test: signatory change in mock department propagates to SWS.

### Phase 3: Conflict Resolution + Audit (Days 5–6)
- Implement the **Conflict Resolution Matrix** with 3 configured policies.
- Simulate: simultaneous updates from SWS and department for same UBID.
- Verify: correct policy applied, audit trail records both values and resolution.
- Implement the **append-only audit ledger** with SHA-256 hashing and RSA signing.
- Build a minimal **Data Steward dashboard** (React) showing DLQ items and audit search.

### Phase 4: Resilience Testing + Demo (Day 7)
- **Failure injection**: kill adapters mid-write → verify idempotency on restart.
- **Network partition simulation**: disconnect Kafka → verify Outbox buffers events.
- **Schema drift simulation**: change a mock API's field name → verify quarantine triggers.
- **Circuit breaker demo**: take a mock department offline → show adapter enters OPEN state → bring back online → show automatic recovery.
- **Stress test**: 10K concurrent updates across 3 mock departments — verify no duplicates, no lost events, correct conflict resolution.
- **Demo preparation**: end-to-end walkthrough of Scenarios A, B, and C with audit trail queries. Front-load the BSA 2023 compliance angle: *"Show that any record can be extracted with its SHA-256 hash and legally certified for court."*

---

## 18. Architecture Inspiration (Qualified)

| Reference | What We Borrow | How We Adapt |
|-----------|---------------|--------------|
| **Estonia's X-Road** | Federated, decentralized messaging between government systems | X-Road requires security server adapters on each participant. We achieve federation *without* modifying participants — adapters live entirely within the middleware layer. |
| **India Stack (Aadhaar/UPI)** | A universal identifier as the join key across heterogeneous systems | UBID plays the same role as Aadhaar number or UPI VPA — a pre-existing, pre-assigned identity. We don't create it; we route by it. |
| **Netflix CDC Patterns** | Change capture at scale with consumer isolation | Netflix operates in a controlled cloud. We adapt the consumer-isolation pattern to on-premises, multi-vendor government infrastructure where API latencies vary by 100x across departments. |

---

## 19. Summary

SyncKar is a **non-invasive, event-driven interoperability layer** that solves the split-brain problem between Karnataka's SWS and 40+ legacy department systems. It:

- Propagates service requests **bidirectionally** without modifying any source system
- Uses **UBID as a given precondition** — no matching, no scoring, no inference
- Detects changes in silent systems via **stateful polling and snapshot diffing**
- Guarantees **mathematical idempotency** under retry storms via time-independent hashing and Two-Phase Reservation
- Resolves conflicts **deterministically** via an automated policy matrix with temporal confidence flags — humans see only true edge cases
- Maintains a **BSA 2023–compliant audit trail** where every propagation is traceable, every conflict is explainable, and every resolution is reversible
- Onboards new departments in hours using **AI-accelerated schema mapping and drift explanation on synthetic data only** — no PII ever leaves the government perimeter
- Handles **11 explicit failure modes** including API downtime, network partitions, schema drift, circuit-breaker recovery, and nightly reconciliation
- Designed for **~15–25 sustained events/second** with **500–1000 event/second batch spikes**, validated by back-of-envelope throughput analysis
- Acknowledges **organisational preconditions** (API access MoUs, UBID enrollment gaps, inter-departmental policy ratification) as deployment prerequisites

If it can't work in the real world, it doesn't win here. SyncKar is designed for the real world.
