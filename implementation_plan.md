# SyncKar Prototype — Final Implementation Plan

> Aligned with [AGENTS.md](file:///d:/AI4BHARAT/AGENTS.md) and [ARCHITECTURE.md](file:///d:/AI4BHARAT/ARCHITECTURE.md).

## Key Changes from Previous Plan

> [!IMPORTANT]
> The previous plan used a flat custom structure. This revision aligns with the **exact repository layout** from AGENTS.md §5.

| Area | Previous Plan | Revised |
|------|--------------|---------|
| **Package structure** | Flat `shared/`, `adapters/`, `mock_systems/` | `synckar/` Python package per AGENTS.md §5 |
| **Data models** | Custom `CanonicalEvent` | Exact `CanonicalServiceRequest` from AGENTS.md §6.1 |
| **Adapter interface** | Ad-hoc ingress/egress files | `AbstractAdapter` ABC from AGENTS.md §7 |
| **Conflict detection** | PostgreSQL-based window check | Redis TTL sliding-window per ARCHITECTURE.md §6 |
| **Workers** | asyncio polling loops | **Celery + Redis** periodic tasks per AGENTS.md §4 |
| **Logging** | print/basic logging | **structlog** with JSON formatter (AGENTS.md §13) |
| **Config** | Custom config dict | **pydantic-settings** env-driven (AGENTS.md §5) |
| **Audit ledger** | Optional RSA signing | **Mandatory** RSA signing + SHA-256 (AGENTS.md §11) |
| **Kafka topics** | 2 topics | 5 topics per ARCHITECTURE.md §13 |
| **Exceptions** | Generic errors | Custom hierarchy: `TargetWriteError`, `PermanentWriteError`, `TranslationError`, `UBIDNotFound` (AGENTS.md §10) |
| **Dashboard** | Vanilla HTML/JS | **React** (AGENTS.md §4) |
| **Idempotency key** | Simplified | Exact `make_idempotency_key` + `derive_event_id` from AGENTS.md §6.2 |
| **Circuit breaker** | Basic wrapper | Redis-backed state machine per AGENTS.md §9 |
| **Mock dept protocols** | All REST | Shop Est = REST (Tier 1), Factories = SOAP/XML via zeep (Tier 3) |

---

## Repository Layout (Exact Match to AGENTS.md §5)

```
d:\AI4BHARAT\synckar\
├── AGENTS.md
├── ARCHITECTURE.md
├── docker-compose.yml
├── pyproject.toml
├── alembic.ini
│
├── synckar/                         ← main Python package
│   ├── config.py                    ← pydantic-settings; env-driven
│   ├── exceptions.py               ← TargetWriteError, PermanentWriteError, etc.
│   │
│   ├── models/
│   │   ├── service_request.py       ← CanonicalServiceRequest (AGENTS.md §6.1)
│   │   ├── audit.py                 ← AuditRow (AGENTS.md §6.3)
│   │   └── mapping.py              ← AdapterMapping (loaded from YAML)
│   │
│   ├── adapters/
│   │   ├── base.py                  ← AbstractAdapter ABC (AGENTS.md §7)
│   │   ├── sws/
│   │   │   ├── client.py            ← HTTP client for mock SWS API
│   │   │   ├── translator.py        ← translate_inbound/outbound
│   │   │   └── poller.py            ← high-water mark polling
│   │   └── departments/
│   │       ├── shop_establishment/
│   │       │   ├── client.py        ← REST client
│   │       │   ├── translator.py
│   │       │   ├── poller.py
│   │       │   └── mappings/
│   │       │       └── mapping_v1.yaml
│   │       └── factories/
│   │           ├── client.py        ← zeep SOAP client (Tier 3)
│   │           ├── translator.py
│   │           ├── poller.py
│   │           └── mappings/
│   │               └── mapping_v1.yaml
│   │
│   ├── pipeline/
│   │   ├── outbox.py               ← Transactional Outbox (write + drain)
│   │   ├── dispatcher.py           ← fan-out to target adapters
│   │   ├── idempotency.py          ← Two-Phase Reservation (Redis NX)
│   │   ├── conflict.py             ← sliding-window detector + Policy Matrix
│   │   └── circuit_breaker.py      ← OPEN / HALF-OPEN / CLOSED per adapter
│   │
│   ├── audit/
│   │   ├── ledger.py               ← append-only audit writer
│   │   └── signing.py              ← RSA per-row signing
│   │
│   ├── observability/
│   │   ├── drift_detector.py       ← structural + statistical drift checks
│   │   └── metrics.py              ← Prometheus counters/histograms
│   │
│   ├── api/
│   │   ├── main.py                 ← FastAPI app
│   │   ├── routes/
│   │   │   ├── webhooks.py         ← POST /api/webhooks/{system_id}
│   │   │   ├── audit.py            ← GET /api/audit/{ubid}
│   │   │   ├── dlq.py              ← DLQ review + manual resolution
│   │   │   └── health.py
│   │   └── middleware.py           ← HMAC-SHA256 signature verification
│   │
│   └── workers/
│       ├── polling.py              ← Celery periodic tasks per department
│       ├── propagation.py          ← Celery propagation task with retry
│       └── reconciliation.py       ← nightly reconciliation job
│
├── mock_systems/                    ← NOT part of synckar package
│   ├── mock_sws/
│   │   ├── app.py                  ← FastAPI mock SWS
│   │   └── Dockerfile
│   ├── mock_dept_shop/
│   │   ├── app.py                  ← FastAPI mock Shop Establishment (REST)
│   │   └── Dockerfile
│   └── mock_dept_factories/
│       ├── app.py                  ← FastAPI mock Factories (REST that simulates SOAP)
│       └── Dockerfile
│
├── migrations/                      ← Alembic
├── schema_registry/                 ← versioned mapping YAMLs
│   ├── shop_establishment/
│   │   └── mapping_v1.yaml
│   └── factories/
│       └── mapping_v1.yaml
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/synthetic/          ← fake UBIDs (KA-TEST-XXXXX) only
│
├── dashboard/                       ← React Data Steward frontend
│
└── scripts/
    ├── seed_data.py
    ├── demo_scenario_a.py
    ├── demo_scenario_b.py
    ├── demo_scenario_c.py
    └── generate_rsa_keys.py
```

---

## Phase 1: Infrastructure (Est: 1.5 hours)

### 1.1 Docker Compose

Services: `kafka` (bitnami KRaft), `postgres`, `redis`, `mock-sws`, `mock-shop`, `mock-factories`, `synckar-api`, `celery-worker`, `celery-beat`, `dashboard`

### 1.2 PostgreSQL Init SQL

Tables (per ARCHITECTURE.md §10):
- `outbox` — transactional outbox
- `audit_ledger` — exact schema from ARCHITECTURE.md §10 with RSA signature, broker_seq_a/b, temporal_confidence
- `conflict_log` — conflict audit records
- `dead_letter_queue` — DLQ with status tracking
- `dept_snapshots` — MurmurHash3 snapshot hashes for Tier 4

Constraints:
- `REVOKE UPDATE, DELETE ON audit_ledger FROM synckar_app_role`
- Indexes on `correlation_id`, `ubid`, `created_at`

### 1.3 Kafka Topics (ARCHITECTURE.md §13)

| Topic | Key | Retention |
|-------|-----|-----------|
| `sws.changes` | UBID | 7 days |
| `dept.shop_establishment.changes` | UBID | 7 days |
| `dept.factories.changes` | UBID | 7 days |
| `propagation.dlq` | UBID | 30 days |
| `audit.events` | correlation_id | 30 days |

### 1.4 RSA Key Generation

`scripts/generate_rsa_keys.py` — generates RSA key pair for audit signing. Stored in volume mount.

### 1.5 pyproject.toml

```toml
[project]
name = "synckar"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111",
    "uvicorn>=0.30",
    "confluent-kafka>=2.4",
    "psycopg2-binary>=2.9",
    "redis>=5.0",
    "httpx>=0.27",
    "pyyaml>=6.0",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "celery[redis]>=5.4",
    "structlog>=24.1",
    "cryptography>=42.0",
    "zeep>=4.2",
    "mmh3>=4.1",
    "prometheus-client>=0.20",
]
```

---

## Phase 2: Core Models & Config (Est: 1.5 hours)

### 2.1 `synckar/config.py`

- `pydantic-settings` with env vars: `KAFKA_BOOTSTRAP`, `POSTGRES_DSN`, `REDIS_URL`, `CONFLICT_WINDOW_SECONDS`, `RSA_PRIVATE_KEY_PATH`, etc.
- Per-adapter configs: poll intervals, rate limits, circuit breaker thresholds

### 2.2 `synckar/exceptions.py`

Custom exceptions per AGENTS.md §10:
- `TargetWriteError` — 5xx/timeout → Celery retry
- `PermanentWriteError` — 4xx → DLQ immediately
- `TranslationError` — schema mismatch → quarantine
- `UBIDNotFound` — skip, commit offset
- `UnsupportedRequestType` — from translate_outbound

### 2.3 `synckar/models/service_request.py`

Exact `CanonicalServiceRequest`, `RequestType`, `SourceSystem` from AGENTS.md §6.1. Plus `make_idempotency_key()` and `derive_event_id()` from §6.2.

### 2.4 `synckar/models/audit.py`

Exact `AuditRow` from AGENTS.md §6.3 with all fields including `broker_seq_a`, `broker_seq_b`, `temporal_confidence`, `rsa_signature`.

### 2.5 `synckar/models/mapping.py`

`AdapterMapping` Pydantic model that loads from YAML files. Fields: `version`, `certified_by`, `certified_at`, `adapter_tier`, `protocol`, `fields[]`.

---

## Phase 3: Mock Systems (Est: 2 hours)

### 3.1 Mock SWS (`mock_systems/mock_sws/app.py`)

FastAPI with SQLite. Endpoints:
- `GET /api/businesses/{ubid}` — get by UBID
- `PUT /api/businesses/{ubid}` — update fields
- `GET /api/businesses/changes?since={iso_timestamp}` — high-water mark polling
- `POST /api/webhooks/register` — webhook registration (optional)
- `GET /health`

Business fields: `ubid`, `business_name`, `registered_address`, `primary_contact`, `authorized_signatory`, `employee_headcount`, `operational_status`, `license_status`, `last_modified`

### 3.2 Mock Shop Establishment (`mock_systems/mock_dept_shop/app.py`)

Different field names (Tier 1 REST):
- `Buss_Addr_Line1`, `Contact_Phone`, `Auth_Sign_Name`, `Emp_Count`
- Uses `shop_reg_no` as primary key, with UBID cross-reference
- `GET /api/records/{ubid}`, `PUT /api/records/{ubid}`, `GET /api/records/changes?since=`

### 3.3 Mock Factories (`mock_systems/mock_dept_factories/app.py`)

Different field names (simulates Tier 3 SOAP but exposed as REST for sandbox):
- `factory_address`, `contact_number`, `signatory_name`, `worker_count`
- Uses `factory_license_no` as primary key
- Same endpoint pattern but responses include XML-like structure

### 3.4 Seed Data (`scripts/seed_data.py`)

20 businesses with synthetic UBIDs (`KA-TEST-0001` through `KA-TEST-0020`). Some present in all 3 systems, some only in SWS + 1 dept (to test UBID_NOT_FOUND skip).

---

## Phase 4: Pipeline Core (Est: 3 hours)

### 4.1 `synckar/pipeline/outbox.py`

- `write_to_outbox(event: CanonicalServiceRequest, db_session)` — atomic INSERT
- `OutboxDrainWorker` — Celery periodic task, polls outbox for PENDING, publishes to Kafka, marks PUBLISHED
- Handles Kafka unavailability: events stay in outbox

### 4.2 `synckar/pipeline/idempotency.py`

Two-Phase Reservation (AGENTS.md §7):
- `reserve(key) -> RESERVED | COMPLETED | IN_PROGRESS`
- `complete(key, cached_response)` — SET COMPLETED with 72h TTL
- `check(key) -> IdempotencyStatus`
- Key via `make_idempotency_key()` from §6.2
- Redis fallback: query target API for current value

### 4.3 `synckar/pipeline/conflict.py`

Sliding-window detector (ARCHITECTURE.md §6):
- Redis key: `conflict_window:{ubid}:{field_name}` with 900s TTL
- Value: `{source_system, broker_sequence, payload_hash, correlation_id}`
- `DataCategory` enum + `FIELD_CATEGORY_MAP` — exact match to AGENTS.md §8
- `detect_conflict()` → checks Redis for competing event from different source
- `resolve_conflict()` → applies policy matrix, returns winner
- `temporal_confidence` calculation: HIGH/MEDIUM/LOW based on adapter tiers
- Always writes `ConflictAuditRecord` — never silently proceeds

### 4.4 `synckar/pipeline/circuit_breaker.py`

Redis-backed state machine (AGENTS.md §9):
- `CircuitState` enum: CLOSED, OPEN, HALF_OPEN
- `check_state(adapter_id) -> CircuitState`
- `record_success(adapter_id)` / `record_failure(adapter_id)`
- OPEN trigger: 5 consecutive failures in 2 minutes
- OPEN → events route to per-dept holding queue (NOT DLQ)
- Health probe: Celery periodic task every 60s
- HALF_OPEN: one real event test

### 4.5 `synckar/pipeline/dispatcher.py`

Fan-out logic:
- Consumes from Kafka topic
- For each event, determines target adapters (all depts where UBID exists)
- Dispatches to each adapter independently (C9: one failure doesn't block others)
- Wraps each dispatch in try/except per adapter

---

## Phase 5: Adapters (Est: 3 hours)

### 5.1 `synckar/adapters/base.py`

Exact `AbstractAdapter` ABC from AGENTS.md §7 with `system_id`, `adapter_tier`, `poll_strategy`, and 4 abstract methods.

### 5.2 SWS Adapter (`synckar/adapters/sws/`)

- `client.py` — httpx async client for mock SWS API
- `translator.py` — `translate_inbound()`: raw SWS JSON → `CanonicalServiceRequest`; `translate_outbound()`: canonical → SWS format
- `poller.py` — high-water mark polling via Celery periodic task. Watermark stored in Redis. Silently skips records without UBID (C10).

### 5.3 Shop Establishment Adapter (`synckar/adapters/departments/shop_establishment/`)

- `client.py` — httpx client for mock Shop Est API
- `translator.py` — loads `mapping_v1.yaml`, maps `registered_address` ↔ `Buss_Addr_Line1` etc.
- `poller.py` — high-water mark strategy (Tier 1)
- `mappings/mapping_v1.yaml` — exact YAML format from ARCHITECTURE.md §8

### 5.4 Factories Adapter (`synckar/adapters/departments/factories/`)

- `client.py` — zeep SOAP client (or REST fallback for prototype with `# DECISION:` comment)
- `translator.py` — loads mapping YAML
- `poller.py` — high-water mark (simplified from snapshot diff for prototype)
- `mappings/mapping_v1.yaml`

---

## Phase 6: Audit & Signing (Est: 1 hour)

### 6.1 `synckar/audit/signing.py`

- `sign_audit_row(row_data: str, private_key) -> str` — RSA signature
- `verify_audit_row(row_data: str, signature: str, public_key) -> bool`
- Key loaded from path in config (not hardcoded)

### 6.2 `synckar/audit/ledger.py`

- `write_audit_row(event, target_system, api_endpoint, conflict_info)`
- Computes `payload_sha256 = SHA-256(json.dumps(event, sort_keys=True))`
- Signs with RSA → `rsa_signature`
- INSERT only (never UPDATE/DELETE — C6)
- Losing conflict values preserved in audit row (AGENTS.md §11)

---

## Phase 7: Workers (Est: 1.5 hours)

### 7.1 `synckar/workers/polling.py`

Celery periodic tasks:
- `poll_sws` — runs every 5s, calls SWS adapter's `fetch_changes()`
- `poll_shop_establishment` — runs every 10s
- `poll_factories` — runs every 10s
- Each writes to outbox → drain to Kafka

### 7.2 `synckar/workers/propagation.py`

Celery task with retry:
- Consumes from Kafka (via dedicated consumer threads)
- Runs the full pipeline: conflict check → idempotency → translate → apply_change → audit
- Retry with exponential backoff on `TargetWriteError`
- DLQ on `PermanentWriteError`
- Skip on `UBIDNotFound`

### 7.3 `synckar/workers/reconciliation.py`

Nightly job (ARCHITECTURE.md §11):
- Samples 5 UBIDs (prototype scale) from each system
- Compares critical fields across SWS and departments
- Emits synthetic correction events for mismatches

---

## Phase 8: API & Webhook Routes (Est: 1 hour)

### 8.1 `synckar/api/main.py`

FastAPI app with structlog middleware, CORS, Prometheus metrics endpoint.

### 8.2 Routes

- `POST /api/webhooks/{system_id}` — receives webhook pushes (HMAC-SHA256 verified)
- `GET /api/audit/{ubid}` — query audit ledger by UBID
- `GET /api/audit/trace/{correlation_id}` — end-to-end trace
- `GET /api/dlq` — list DLQ items
- `POST /api/dlq/{id}/resolve` — manual DLQ resolution
- `GET /api/health` — health check (Kafka, Redis, PostgreSQL connectivity)
- `GET /api/stats` — dashboard stats

### 8.3 `synckar/api/middleware.py`

HMAC-SHA256 webhook signature verification.

---

## Phase 9: Observability (Est: 0.5 hours)

### 9.1 `synckar/observability/metrics.py`

All 8 mandatory Prometheus metrics from AGENTS.md §14:
- `synckar_propagations_total`, `synckar_propagation_duration_ms`
- `synckar_conflicts_total`, `synckar_retries_total`
- `synckar_dlq_depth`, `synckar_poll_lag_seconds`
- `synckar_circuit_breaker_state`, `synckar_schema_drift_detected_total`

### 9.2 `synckar/observability/drift_detector.py`

Basic structural checks: column count, column names from API responses. Triggers quarantine on mismatch.

---

## Phase 10: React Dashboard (Est: 2 hours)

### 10.1 Setup

`npx create-react-app dashboard` (or Vite) — lightweight React app.

### 10.2 Pages

- **Overview** — live stats cards (events, conflicts, DLQ depth) with auto-refresh
- **Audit Trail** — searchable table with UBID/correlation_id filters
- **Trace View** — end-to-end flow visualization for a correlation_id (timeline)
- **Conflict Log** — conflict details with policy applied, winning/losing values
- **DLQ Review** — pending items with resolve/discard actions

### 10.3 Design

Dark theme, modern typography (Inter), glassmorphism cards, smooth transitions.

---

## Phase 11: Demo Scripts (Est: 1 hour)

### 11.1 `scripts/demo_scenario_a.py` — SWS → Departments

1. Update address for `KA-TEST-1234` in mock SWS
2. Wait for propagation (poll + verify)
3. Query both dept systems to confirm address updated
4. Query audit ledger for correlation_id — show 2 audit rows

### 11.2 `scripts/demo_scenario_b.py` — Department → SWS

1. Update signatory in mock Factories for `KA-TEST-1234`
2. Wait for propagation
3. Query SWS to confirm signatory updated
4. Show audit trail

### 11.3 `scripts/demo_scenario_c.py` — Conflict

1. Simultaneously update address in SWS AND Factories for `KA-TEST-1234`
2. Wait for conflict detection
3. Show: SWS wins (universal demographics policy)
4. Query conflict log — both values preserved
5. Query audit ledger — resolution explained

---

## Phase 12: Resilience Testing (Est: 1 hour)

- **Idempotency test** — send duplicate Kafka messages → verify no duplicate writes
- **Circuit breaker demo** — stop mock dept container → adapter enters OPEN → restart → auto-recovery
- **Outbox buffering** — stop Kafka → events buffer in outbox → restart → drain
- **DLQ routing** — send malformed message → verify DLQ entry

---

## Phase 13: Testing & Polish (Est: 1 hour)

### Unit Tests

Per AGENTS.md §15:
- `translate_inbound` / `translate_outbound` — happy path + 3 error cases
- `apply_change` called twice → identical state (idempotency)
- All 4 conflict policy branches → ConflictAuditRecord always written
- Circuit breaker state transitions
- All fixtures use `KA-TEST-XXXXX` UBIDs

### Integration Test

Full end-to-end: seed → update SWS → verify dept propagation → verify audit.

---

## Execution Order

| # | Task | Est. |
|---|------|------|
| 1 | Docker Compose + DB schema + Kafka topics + RSA keys | 1.5h |
| 2 | Config, exceptions, data models (exact AGENTS.md specs) | 1.5h |
| 3 | Mock SWS + Mock Shop + Mock Factories + seed data | 2h |
| 4 | Pipeline core (outbox, idempotency, conflict, circuit breaker, dispatcher) | 3h |
| 5 | Adapters (SWS + Shop Est + Factories) with mappings | 3h |
| 6 | Audit ledger + RSA signing | 1h |
| 7 | Celery workers (polling, propagation, reconciliation) | 1.5h |
| 8 | FastAPI routes (webhooks, audit, DLQ, health) | 1h |
| 9 | Prometheus metrics + drift detector | 0.5h |
| 10 | React dashboard | 2h |
| 11 | Demo scripts (scenarios A, B, C) | 1h |
| 12 | Resilience testing | 1h |
| 13 | Unit tests + integration test | 1h |
| **Total** | | **~20h** |

---

## Open Questions

> [!IMPORTANT]
> 1. **Factories adapter protocol**: AGENTS.md specifies zeep SOAP (Tier 3), but the mock system is REST. Should we build the mock as a SOAP endpoint (adds complexity) or use REST with a `# DECISION:` comment explaining the prototype simplification?

> [!IMPORTANT]
> 2. **React vs Vanilla JS dashboard**: AGENTS.md §4 mandates React. This adds npm build complexity to Docker. Confirm you want full React (recommended for demo quality) vs a vanilla HTML/JS fallback?

> [!NOTE]
> 3. **AI Schema Co-Pilot (AGENTS.md §12)**: This requires SDV + Claude API integration. For a prototype demo, should we implement a simplified version (just the YAML generation pipeline with mock synthetic data) or skip entirely and focus on core sync?

## Verification Plan

### Automated Tests
```bash
docker compose up --build          # All services healthy
python scripts/seed_data.py        # 20 businesses seeded
python scripts/demo_scenario_a.py  # SWS → Dept verified
python scripts/demo_scenario_b.py  # Dept → SWS verified
python scripts/demo_scenario_c.py  # Conflict resolved correctly
pytest tests/ -v --cov=synckar     # Unit + integration, 80% coverage
```

### Manual Verification
- Dashboard shows live audit trail, conflict log, DLQ
- End-to-end trace for any correlation_id
- Circuit breaker demo: stop/start mock dept container
- Stress test: 100 concurrent updates, zero duplicates
