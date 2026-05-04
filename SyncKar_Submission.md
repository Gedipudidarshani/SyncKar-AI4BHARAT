# SyncKar — Event-Driven Interoperability Layer for Karnataka's Single Window System

## Problem Understanding

Karnataka's SWS and 40+ legacy department systems operate as isolated data silos. A business can update its registered address on SWS, but the corresponding records in Shop Establishment, Factories, or Labour never receive that change — and vice versa. The result is a split-brain problem: officers see stale data, citizens repeat paperwork across portals, and no unified audit trail exists.

Big-bang migration is not viable. The GST rollout proved that single-day cutovers over fragmented, heterogeneous systems fail at scale. Each department has its own schema, identifiers, APIs (REST, SOAP, file-based), and authentication mechanisms. Legacy systems lack NTP synchronization — timestamps cannot be trusted for ordering. Most systems do not emit events; changes must be discovered, not received.

UBID is the only reliable join key and exists on both sides as a precondition. The layer does not invent, match, or score identifiers — it routes by UBID.

## Architecture

SyncKar is a non-invasive middleware layer that wraps around existing system surfaces without modifying them. Core components:

- **Protocol-Agnostic Adapters**: Per-department adapters that speak each system's native language (REST/JSON, SOAP/XML, CSV/file). Each maintains a declarative YAML mapping file defining field translations, data types, and auth.
- **Transactional Outbox + Kafka Event Bus**: Changes are captured into a PostgreSQL outbox (atomic with local state), then published to Kafka topics partitioned by UBID. Per-department consumer groups ensure one slow department cannot block others.
- **Idempotency Engine (Redis)**: Deterministic SHA-256 key computed from (source_system, event_id, UBID, field_name, new_value) — no timestamps. A Two-Phase Reservation pattern (SET NX → execute → COMPLETED) prevents duplicate writes even when ACKs are lost.
- **Conflict Resolution Matrix**: Automated 4-tier policy — SWS wins demographics, departments win regulatory compliance fields, Last-Write-Wins (by Kafka broker sequence) for metadata, Dead Letter Queue for unmapped fields.
- **Append-Only Audit Ledger**: BSA 2023-compliant PostgreSQL table with SHA-256 payload hashing, per-row RSA signatures, and correlation IDs for end-to-end tracing.

## Two-Way Propagation

**SWS → Departments**: SWS Adapter detects changes (webhook or polling) → writes canonical event to Outbox → Outbox Worker publishes to Kafka → each Department Adapter consumes, translates schema, checks idempotency, writes to target API, logs audit row.

**Departments → SWS**: Two non-invasive strategies: (1) Stateful API Polling — adapter maintains a high-water mark, queries for records modified since last check (30s–15min cycles); (2) Cryptographic Snapshot Diffing — for systems that only produce bulk exports, compute MurmurHash3 per row keyed by UBID, emit change events where hashes diverge. Both feed into Kafka → SWS Adapter → SWS API.

## Schema Translation and Onboarding

Each adapter's YAML mapping is version-controlled in a Git-backed Schema Registry. When a department's schema changes, a data observability module detects structural/statistical drift and enters quarantine mode — affected records are diverted while unaffected fields continue propagating.

For new department onboarding, an AI Schema Co-Pilot accelerates draft mapping generation: raw department data is first converted to synthetic data using Synthetic Data Vault (SDV) on-premises — no real PII ever leaves the government perimeter. The LLM receives only schema headers and synthetic rows, generating a draft YAML mapping. A government data architect validates and certifies the mapping before deployment. AI handles the syntactic 80% (field-name matching, type coercion); humans handle the semantic 20% (business-rule validation, regulatory review). This reduces per-department onboarding from weeks to days.

## Conflict Detection and Resolution

When updates to the same UBID + field arrive from multiple sources within a configurable window (default 15 min), the conflict detector triggers. Resolution policies:

| Data Category | Policy | Rationale |
|---|---|---|
| Demographics (address, contact) | SWS Wins | SWS is the canonical front door |
| Regulatory (license status, clearances) | Department Wins | Only the issuing authority can modify |
| Metadata (headcount, inspection date) | Last-Write-Wins (broker sequence) | Low-stakes; recency is best proxy |
| Unmapped fields | Dead Letter Queue | Human must define policy first |

Every resolution generates a conflict audit record preserving both values, both sources, the policy applied, and a temporal_confidence flag (HIGH/MEDIUM/LOW based on detection method provenance). The losing value is never deleted. Outside the conflict window, writes still proceed with full audit — no write ever escapes the trail.

## Failure Modes

11 explicit scenarios with detection + recovery: department API downtime (exponential backoff → DLQ), UBID not found in target (skip + alert), write-succeeded-but-ACK-lost (Redis COMPLETED cache → exactly-once effective), consumer lag exceeding rate limits (per-department throttling), schema drift (quarantine mode), network partition to Kafka (Outbox safety net), poisoned messages (immediate DLQ), Redis downtime (fallback to target-state comparison), batch collisions (automated per-record policy), persistent API failure (circuit breaker with OPEN/HALF-OPEN/CLOSED states), and consistency drift (nightly reconciliation job sampling 1% of UBIDs across systems).

## Technology Choices

Kafka (log retention for audit replay, per-UBID partitioning, consumer isolation), PostgreSQL (outbox + audit ledger), Redis (sub-ms idempotency), Python/FastAPI (rapid adapter dev, zeep for SOAP/XML), Prometheus+Grafana (monitoring), HashiCorp Vault (secrets). Throughput estimate: ~15–25 events/sec sustained, 500–1000/sec during batch spikes, with fan-out yielding 2500–5000 API calls/sec peak — Kafka handles this comfortably; the bottleneck is legacy API throughput, managed by per-department rate limiters.

## Risks and Trade-Offs

- Polling latency (30s–15min) accepted over invasive CDC to respect the no-modification constraint
- AP over CP — temporary inconsistency accepted over blocking citizen updates during backend outages
- Automated resolution for >95% of conflicts; human DLQ for edge cases — operationally necessary at 2M+ businesses
- ~500GB/year audit storage — tiered archiving (hot 90d, warm 1y, cold 7y)

## Round 2 Plan (7 days)

Days 1–2: Kafka + PostgreSQL + Redis via Docker Compose; SWS Adapter + 2 department adapters (one REST, one SOAP). Days 3–4: Bidirectional propagation + idempotency engine; duplicate injection tests. Days 5–6: Conflict resolution matrix + audit ledger + minimal Data Steward dashboard. Day 7: Failure injection (kill adapters mid-write, disconnect Kafka, change mock schema), circuit breaker demo, stress test (10K concurrent updates), end-to-end walkthrough of all three sample scenarios with audit trail queries.
