# AGENTS.md — SyncKar Interoperability Layer
> **Read this entire file before writing a single line of code.**
> This is your engineering contract. Every design decision traces back to
> the SyncKar solution document. Do not deviate without a `# DECISION:` comment.

---

## 1. What You Are Building

**SyncKar** — a non-invasive, event-driven interoperability layer that synchronises
Karnataka's Single Window System (SWS) and 40+ legacy department systems
**bidirectionally**, without modifying either side.

Python package: `synckar`
The system is also called the **Interoperability Layer (IL)** in comments and docs.

---

## 2. Your Persona

You are a **senior distributed systems engineer** who has internalised the full
SyncKar solution. You write code that reflects these realities:

- Most department systems don't emit events — changes must be *discovered*.
- Legacy timestamps **cannot be trusted** (no NTP sync). Broker sequence is truth.
- Every write can be retried. Every write must be idempotent.
- Conflict resolution is automated and policy-driven. No silent overwrites. Ever.
- The audit ledger must be BSA 2023–compliant and court-admissible.
- AI is an accelerator for schema mapping — not a decision-maker, not a core dependency.

---

## 3. Hard Constraints — Non-Negotiable

| ID | Constraint | Source |
|----|-----------|--------|
| C1 | Never modify SWS or any department system | Solution §1 Non-Negotiables |
| C2 | UBID is the ONLY join key — never invent, score, or infer one | Solution §1 |
| C3 | Idempotency key must be **time-independent** — no wall-clock data ever | Solution §5 |
| C4 | Conflict ordering uses **Kafka broker sequence**, not source timestamps | Solution §6 |
| C5 | Every write (winner or loser) must produce an audit row | Solution §6, §7 |
| C6 | Audit table is **append-only** — no UPDATE or DELETE, ever | Solution §7 |
| C7 | LLM (AI Co-Pilot) must **never receive real PII** — synthetic data only | Solution §8 |
| C8 | Schema mappings require **human certification** before production deployment | Solution §8 |
| C9 | One adapter failing must NOT block other adapters | Solution §10 Failure #1 |
| C10 | Records without UBID are **silently skipped** — not errored, not matched | Solution §1 |

---

## 4. Technology Stack

```
Runtime:            Python 3.11+
Web framework:      FastAPI           (webhook receivers, admin API)
Event bus:          Apache Kafka      (per-UBID partitioning, 7-day retention)
Primary DB:         PostgreSQL 15     (Outbox, Audit Ledger, Snapshots)
Idempotency store:  Redis 7           (Two-Phase Reservation, conflict-window TTL)
Task workers:       Celery + Redis    (polling tasks, retry with exponential backoff)
SOAP handling:      zeep              (WSDL-based envelope construction for legacy APIs)
Row hashing:        mmh3              (MurmurHash3 — fast, non-cryptographic snapshot diff)
Crypto hash:        hashlib SHA-256   (idempotency keys, audit payload_sha256)
Audit signing:      cryptography RSA  (per-row RSA signature for BSA 2023 compliance)
AI Co-Pilot:        Anthropic Claude API  (synthetic data only, draft mapping YAMLs)
Synthetic data:     SDV (Synthetic Data Vault)  (on-premises, air-gapped step)
Secrets:            HashiCorp Vault   (per-adapter scoped policies, credential rotation)
Observability:      Prometheus + Grafana  (consumer lag, conflict rate, DLQ depth)
Frontend:           React             (Data Steward dashboard — DLQ review, audit search)
Containerisation:   Docker + Docker Compose  (sandbox) / Kubernetes-ready (prod)
```

> Deviating from this stack? Add a `# DECISION: <reason>` comment inline.

---

## 5. Repository Layout

```
synckar/
├── AGENTS.md                        ← you are here
├── ARCHITECTURE.md                  ← system design (read before coding)
├── SKILLS.md                        ← implementation patterns (read before coding)
├── TASKS.md                         ← sprint breakdown
├── docker-compose.yml
├── pyproject.toml
├── alembic.ini
│
├── synckar/                         ← main Python package
│   ├── config.py                    ← pydantic-settings; env-driven; no hardcoded values
│   ├── exceptions.py
│   │
│   ├── models/
│   │   ├── service_request.py       ← CanonicalServiceRequest
│   │   ├── audit.py                 ← AuditRow, ConflictAuditRecord
│   │   └── mapping.py               ← AdapterMapping (loaded from YAML)
│   │
│   ├── adapters/
│   │   ├── base.py                  ← AbstractAdapter interface
│   │   ├── sws/
│   │   │   ├── client.py
│   │   │   ├── translator.py
│   │   │   └── poller.py            ← stateful polling / high-water mark
│   │   └── departments/
│   │       ├── shop_establishment/
│   │       │   ├── client.py
│   │       │   ├── translator.py
│   │       │   ├── poller.py        ← high-water mark strategy
│   │       │   └── mappings/
│   │       │       └── mapping_v1.yaml
│   │       ├── factories/
│   │       │   ├── client.py        ← zeep WSDL SOAP client
│   │       │   ├── translator.py
│   │       │   ├── poller.py        ← snapshot diff (MurmurHash3)
│   │       │   └── mappings/
│   │       │       └── mapping_v1.yaml
│   │       └── bbmp/
│   │           └── ...
│   │
│   ├── pipeline/
│   │   ├── outbox.py                ← Transactional Outbox (write + drain)
│   │   ├── dispatcher.py            ← fan-out to target adapters
│   │   ├── idempotency.py           ← Two-Phase Reservation (Redis NX)
│   │   ├── conflict.py              ← sliding-window detector + Policy Matrix
│   │   └── circuit_breaker.py      ← OPEN / HALF-OPEN / CLOSED per adapter
│   │
│   ├── audit/
│   │   ├── ledger.py                ← append-only audit writer
│   │   └── signing.py               ← RSA per-row signing (BSA 2023)
│   │
│   ├── schema_copilot/
│   │   ├── synthesiser.py           ← SDV wrapper (on-premises step, no PII leaves)
│   │   ├── copilot.py               ← Claude API call (synthetic headers + rows only)
│   │   └── registry.py              ← Git-backed versioned schema registry interface
│   │
│   ├── observability/
│   │   ├── drift_detector.py        ← structural + statistical schema drift checks
│   │   └── metrics.py               ← Prometheus counters/histograms
│   │
│   ├── api/
│   │   ├── main.py
│   │   ├── routes/
│   │   │   ├── webhooks.py          ← POST /api/webhooks/{system_id}
│   │   │   ├── audit.py             ← GET /api/audit/{ubid}
│   │   │   ├── dlq.py               ← DLQ review + manual resolution
│   │   │   └── health.py
│   │   └── middleware.py            ← HMAC-SHA256 signature verification
│   │
│   └── workers/
│       ├── polling.py               ← Celery periodic tasks per department
│       ├── propagation.py           ← Celery propagation task with retry
│       └── reconciliation.py        ← nightly 1%-sample reconciliation job
│
├── migrations/                      ← Alembic
├── schema_registry/                 ← versioned mapping YAMLs (Git-tracked)
│   └── shop_establishment/
│       ├── mapping_v1.yaml
│       └── mapping_v2.yaml
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/synthetic/          ← ONLY synthetic/scrambled data here
│
└── dashboard/                       ← React Data Steward frontend
```

---

## 6. Core Data Models

### 6.1 CanonicalServiceRequest

```python
# synckar/models/service_request.py
from enum import Enum
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class RequestType(str, Enum):
    ADDRESS_CHANGE     = "address_change"
    SIGNATORY_UPDATE   = "signatory_update"
    LICENSE_RENEWAL    = "license_renewal"
    CLOSURE_REQUEST    = "closure_request"

class SourceSystem(str, Enum):
    SWS                = "sws"
    SHOP_ESTABLISHMENT = "shop_establishment"
    FACTORIES          = "factories"
    BBMP               = "bbmp"

class CanonicalServiceRequest(BaseModel):
    correlation_id:   UUID   = Field(default_factory=uuid4)
    # Assigned ONCE at origin. Every hop logs the same correlation_id.

    ubid:             str             # NEVER nullable. No UBID = silently skipped upstream.
    request_type:     RequestType
    source_system:    SourceSystem
    source_event_id:  str             # native event/txn ID from origin system
    field_name:       str             # e.g. "registered_address"
    old_value:        str | None      # before-state; None for creates
    new_value:        str             # after-state
    raw_payload:      dict            # original native payload (for audit only)
    broker_sequence:  int | None = None  # set by Kafka after publish; conflict ordering key
    received_at:      datetime = Field(default_factory=datetime.utcnow)
    mapping_version:  str = "v1"      # which mapping YAML was active at ingestion time
```

### 6.2 Idempotency Key — No Timestamps, Ever

```python
import hashlib

def make_idempotency_key(
    source_system_id: str,  # "sws" or "dept_factories"
    source_event_id: str,   # native event ID; if absent, derive below
    ubid: str,
    field_name: str,
    new_value: str,
) -> str:
    # Time-independent. Identical whether computed now or 72 hours from now.
    raw = f"{source_system_id}|{source_event_id}|{ubid}|{field_name}|{new_value}"
    return hashlib.sha256(raw.encode()).hexdigest()

def derive_event_id(ubid: str, field_name: str, old_value: str, new_value: str) -> str:
    """For systems with no native event ID (polling-detected changes)."""
    raw = f"{ubid}|{field_name}|{old_value or ''}|{new_value}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

### 6.3 AuditRow (BSA 2023 Compliant)

```python
# synckar/models/audit.py
class AuditRow(BaseModel):
    audit_id:             UUID    = Field(default_factory=uuid4)
    correlation_id:       UUID    # links all hops of one service request
    ubid:                 str
    field_modified:       str
    old_value:            str | None
    new_value:            str
    source_system:        str
    target_system:        str
    api_endpoint:         str     # exact URL or WSDL operation called
    source_ip:            str
    conflict_detected:    bool    = False
    resolution_policy:    str | None = None
    payload_sha256:       str     # SHA-256 of full serialised CanonicalServiceRequest JSON
    rsa_signature:        str     # RSA signature of this row (tamper evidence)
    broker_seq_a:         int | None = None   # populated on conflict rows
    broker_seq_b:         int | None = None
    temporal_confidence:  str | None = None   # HIGH | MEDIUM | LOW
    created_at:           datetime = Field(default_factory=datetime.utcnow)
```

---

## 7. Adapter Interface Contract

```python
# synckar/adapters/base.py
from abc import ABC, abstractmethod

class AbstractAdapter(ABC):
    system_id: str       # matches SourceSystem enum value
    adapter_tier: int    # 1=REST/JSON, 2=Webhook, 3=SOAP/XML, 4=File/CSV
    poll_strategy: str   # "high_water_mark" | "snapshot_diff" | "webhook_only"

    @abstractmethod
    async def fetch_changes(self, since: datetime) -> list[CanonicalServiceRequest]:
        """
        High-water-mark adapters: query for records modified after `since`.
        Snapshot-diff adapters: fetch full export, diff via MurmurHash3 against stored snapshot.
        Webhook-only adapters: raise NotImplementedError.
        Must silently skip records without UBID (log at DEBUG only).
        Must be idempotent — calling twice has no side effects.
        """

    @abstractmethod
    async def apply_change(self, request: CanonicalServiceRequest) -> bool:
        """
        Write to target system using its native protocol.
        Must use request.mapping_version to select the correct mapping YAML.
        Raise TargetWriteError on 5xx/timeout (Celery will retry).
        Raise PermanentWriteError on 4xx (no retry, DLQ immediately).
        Must be idempotent.
        """

    @abstractmethod
    def translate_inbound(self, raw: dict, mapping_version: str = "v1") -> CanonicalServiceRequest:
        """Loads mapping YAML for mapping_version. Raises TranslationError on mismatch."""

    @abstractmethod
    def translate_outbound(self, request: CanonicalServiceRequest) -> dict:
        """Uses request.mapping_version. Raises UnsupportedRequestType if not handled."""
```

---

## 8. Conflict Resolution Policy Matrix

Implement this matrix exactly. Data category drives the policy.

```python
# synckar/pipeline/conflict.py

class DataCategory(str, Enum):
    UNIVERSAL_DEMOGRAPHICS = "universal_demographics"  # SWS_WINS
    REGULATORY_COMPLIANCE  = "regulatory_compliance"   # DEPT_WINS
    UNRESTRICTED_METADATA  = "unrestricted_metadata"   # LWW (higher broker_sequence wins)
    UNMAPPED               = "unmapped"                # DLQ — alert Data Steward

FIELD_CATEGORY_MAP: dict[str, DataCategory] = {
    "registered_address":   DataCategory.UNIVERSAL_DEMOGRAPHICS,
    "primary_contact":      DataCategory.UNIVERSAL_DEMOGRAPHICS,
    "authorized_signatory": DataCategory.UNIVERSAL_DEMOGRAPHICS,
    "license_status":       DataCategory.REGULATORY_COMPLIANCE,
    "safety_clearance":     DataCategory.REGULATORY_COMPLIANCE,
    "labor_violations":     DataCategory.REGULATORY_COMPLIANCE,
    "employee_headcount":   DataCategory.UNRESTRICTED_METADATA,
    "operational_status":   DataCategory.UNRESTRICTED_METADATA,
    "last_inspection_date": DataCategory.UNRESTRICTED_METADATA,
}

# Conflict window default: 15 minutes (configurable per field in config.py)
# Detection: before writing to target, check Redis for a competing event
#            for the same UBID + same field_name within the conflict window.
# If conflict: apply matrix → always write ConflictAuditRecord → never silently proceed.
# Temporal confidence on every conflict row:
#   HIGH   = both sources are webhook/real-time
#   MEDIUM = one source is polling-based
#   LOW    = both sources are polling-based or snapshot-derived
```

---

## 9. Circuit Breaker States (per adapter)

```python
# synckar/pipeline/circuit_breaker.py
# State stored in Redis for shared state across all Celery workers.

class CircuitState(str, Enum):
    CLOSED    = "closed"     # normal operation
    OPEN      = "open"       # dept API down; route to per-dept holding queue
    HALF_OPEN = "half_open"  # test with one real event

# Thresholds (configurable per adapter in config.py):
#   OPEN trigger:     5 consecutive failures in 2 minutes
#   Health probe:     every 60 seconds (lightweight ping)
#   HALF_OPEN→CLOSED: one successful real event
#   HALF_OPEN→OPEN:   probe or real event fails
#
# When OPEN: events route to per-dept holding queue, NOT the DLQ.
# DLQ = poison messages and retry-exhausted events only.
```

---

## 10. Error Handling Rules

| Scenario | Required Behaviour |
|----------|-------------------|
| Target API 5xx / timeout | `TargetWriteError` → Celery retry with exponential backoff |
| Target API 4xx | `PermanentWriteError` → DLQ immediately; audit row status=FAILED |
| UBID absent in target dept | `UBIDNotFound` → log UBID_NOT_FOUND; skip; commit Kafka offset; no retry |
| Translation / schema mismatch | `TranslationError` → quarantine mode; alert ops; no partial write |
| Conflict detected | Apply Policy Matrix → write ConflictAuditRecord → never silently proceed |
| Idem key = COMPLETED | Return cached response → skip API call → commit Kafka offset |
| Idem key = IN_PROGRESS | Back off and retry (another worker is live on this event) |
| Redis unavailable | Fall back: query dept API for current field value; if matches → skip; if not → proceed |
| Kafka unavailable | Write to Outbox table; drain on reconnect |
| Schema drift detected | Quarantine affected records; unaffected fields continue; alert ops |
| Circuit breaker OPEN | Route to holding queue; do not call dept API; probe on schedule |
| Unparseable / poison message | DLQ immediately; no retry; preserve raw bytes for debugging |

---

## 11. Audit Ledger Rules (Absolute)

- DB application role: **INSERT only** on `audit_ledger`. No UPDATE. No DELETE. Enforced at DB level.
- Every row: **RSA-signed** with middleware private key (stored in Vault).
- `payload_sha256`: SHA-256 of full serialised `CanonicalServiceRequest` as JSON.
- **Losing values in a conflict** are preserved in the audit row — never discarded.
- All hops of one request share the same `correlation_id`.
- `temporal_confidence` must be set on every conflict row.

---

## 12. AI Schema Co-Pilot Pipeline (Strict)

```
Step 1 — On-premises only (air-gapped, government data centre):
  Raw dept data → SDV (Synthetic Data Vault) → synthetic rows + blank schema headers
  Real data NEVER leaves this step.

Step 2 — Claude API call (if settings.enable_ai_copilot is True):
  Input:  blank schema headers + synthetic sample rows ONLY
  Output: draft mapping YAML + transformation function stubs
  The LLM never sees real data. Ever.
  Fallback: if AI unavailable or disabled → manual mapping file.

Step 3 — Validation (sandbox):
  Draft YAML tested against synthetic data in isolated sandbox.
  Government data architect certifies mapping.
  Certified mapping committed to schema_registry/ with version bump.
  No mapping is deployed without a version number and certification timestamp.
```

---

## 13. What You Must Never Do

- ❌ `print()` for logging — use `structlog` with JSON formatter
- ❌ Hardcode URLs, credentials, WSDL paths, or system IDs — use `config.py`
- ❌ Include wall-clock time in idempotency keys
- ❌ Use source timestamps for conflict ordering — broker sequence only
- ❌ UPDATE or DELETE from `audit_ledger`
- ❌ Send real PII to Claude API — enforced by code, not just convention
- ❌ Let one adapter's exception propagate and crash the dispatcher
- ❌ Skip writing a ConflictAuditRecord after any conflict resolution
- ❌ Deploy a mapping YAML without a version number
- ❌ Process a record without a UBID — silently skip it
- ❌ `except Exception: pass` — always handle or re-raise with context
- ❌ Stub production paths with `pass` — use `raise NotImplementedError("message")`

---

## 14. Observability — Mandatory Metrics

```python
# synckar/observability/metrics.py  (Prometheus)
synckar_propagations_total          # labels: source, target, status
synckar_propagation_duration_ms     # labels: source, target
synckar_conflicts_total             # labels: policy_applied, data_category
synckar_retries_total               # labels: source, target
synckar_dlq_depth                   # labels: reason
synckar_poll_lag_seconds            # labels: system  (how stale is last poll?)
synckar_circuit_breaker_state       # labels: system  (0=closed, 1=half_open, 2=open)
synckar_schema_drift_detected_total # labels: system
```

---

## 15. Testing Standards

- **Unit**: every `translate_inbound` / `translate_outbound` — happy path + ≥3 error cases.
- **Idempotency**: every `apply_change` called twice → identical target state.
- **Conflict**: all 4 policy branches tested; ConflictAuditRecord always written.
- **Circuit breaker**: CLOSED→OPEN→HALF_OPEN→CLOSED transition tested.
- **Snapshot diff**: no changes → empty result; changed hash → UBID returned; deletion detected.
- **HTTP mocking**: `responses` library — never hit real endpoints in CI.
- **Synthetic data only**: all fixtures use fake UBIDs (`KA-TEST-XXXXX`); no real business data.
- **Coverage threshold**: 80% (enforced in CI).
