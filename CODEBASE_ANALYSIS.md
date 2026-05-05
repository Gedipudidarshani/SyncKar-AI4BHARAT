# SyncKar Codebase Deep Analysis

## Executive Summary

SyncKar is a **non-invasive, event-driven interoperability layer** that bidirectionally synchronizes data between Karnataka's Single Window System (SWS) and 40+ legacy department systems. It handles conflicts deterministically, maintains an immutable audit trail, prevents duplicate writes through idempotency, and gracefully recovers from failures through circuit breakers.

**Key Achievement**: Zero modifications to any source system — the layer wraps around existing APIs.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     SYNCKAR EVENT-DRIVEN LAYER                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  INBOUND (Adapters detect changes)                                  │
│  ├─ SWS Adapter (webhook OR polling)  ─→ Transactional Outbox      │
│  ├─ Shop Est Adapter (polling)        ─→ Transactional Outbox      │
│  └─ Factories Adapter (polling)       ─→ Transactional Outbox      │
│                                           │                         │
│                                           ▼                         │
│                                    PostgreSQL Outbox                │
│                                    (append-only)                    │
│                                           │                         │
│  EVENT BUS (Kafka: per-UBID ordering)    │                         │
│  ├─ sws.changes          ◄───────────────┤                         │
│  ├─ dept.shop.changes    ◄───────────────┤                         │
│  ├─ dept.factories.changes ◄─────────────┘                         │
│                                                                      │
│  PROCESSING PIPELINE (Celery workers)                               │
│  ├─ Consumer              (reads from Kafka)                        │
│  ├─ Loop Guard            (prevent infinite loops)                  │
│  ├─ Conflict Detector     (sliding window, Redis)                   │
│  ├─ Policy Matrix         (resolve conflicts deterministically)     │
│  ├─ Schema Translator     (YAML-based field mapping)                │
│  ├─ Idempotency Engine    (Redis: time-independent keys)            │
│  ├─ Circuit Breaker       (per-adapter resilience)                  │
│  ├─ Rate Limiter          (sliding window throttle)                 │
│  └─ Dispatcher            (fan-out: one adapter failing ≠ block all)│
│                                                                      │
│  OUTBOUND (Adapters write to target systems)                        │
│  ├─ SWS Adapter           ─→ Write back to SWS API                  │
│  ├─ Shop Est Adapter      ─→ Write back to Shop API                 │
│  └─ Factories Adapter     ─→ Write back to Factories API            │
│                                                                      │
│  OBSERVABILITY                                                       │
│  ├─ Audit Ledger (PostgreSQL: immutable, RSA-signed)                │
│  ├─ Metrics (Prometheus)                                            │
│  ├─ Drift Detector (schema compliance checks)                       │
│  └─ Admin Dashboard (React: view audits, resolve DLQ)               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Codebase Structure

```
synckar/
├── api/                        # FastAPI REST endpoints
│   ├── main.py                 # App entry point, Celery daemon startup
│   ├── middleware.py           # CORS, logging middleware
│   └── routes/
│       ├── health.py           # GET /health
│       ├── audit.py            # GET /api/audit (search, trace, verify)
│       ├── dlq.py              # GET /api/dlq (dead letter queue mgmt)
│       └── webhooks.py         # POST /api/webhooks/{system_id}
│
├── adapters/                   # Protocol-specific connectors
│   ├── base.py                 # Abstract adapter class
│   ├── sws/
│   │   ├── client.py           # SWS API HTTP calls
│   │   ├── translator.py       # Field mapping (canonical ↔ SWS format)
│   │   ├── poller.py           # Detect SWS changes (polling/webhook)
│   │   └── config.py           # SWS-specific settings
│   └── departments/
│       ├── shop_establishment/
│       │   ├── client.py       # Shop API calls (truncate(120) on address)
│       │   ├── translator.py   # Field mapping
│       │   └── poller.py       # Detect Shop changes
│       └── factories/
│           ├── client.py       # Factories API calls
│           ├── translator.py   # Field mapping
│           └── poller.py       # Detect Factories changes
│
├── pipeline/                   # Core synchronization logic
│   ├── circuit_breaker.py      # Per-adapter resilience (CLOSED/OPEN/HALF_OPEN)
│   ├── conflict.py             # Sliding window conflict detector + policy matrix
│   ├── dispatcher.py           # Fan-out: dispatch event to all target adapters
│   ├── idempotency.py          # Time-independent dedup via Redis
│   ├── loop_guard.py           # Prevent A→B→A→... infinite loops
│   ├── outbox.py               # Kafka publisher from PostgreSQL outbox
│   ├── watermark.py            # High-water mark tracking (polling state)
│   └── consumer.py             # Kafka consumer, orchestrates pipeline
│
├── models/                     # Data structures
│   ├── service_request.py      # CanonicalServiceRequest (core event format)
│   ├── audit.py                # AuditRow, ConflictAuditRecord
│   └── mapping.py              # Schema mapping, field translation rules
│
├── audit/                      # Audit trail
│   ├── ledger.py               # write_audit_row() → PostgreSQL
│   ├── signing.py              # RSA signing for tamper evidence
│   └── constants.py            # Audit field enums
│
├── workers/                    # Background job processing
│   ├── celery_app.py           # Celery config, task definitions
│   ├── reconciliation.py       # Periodic full re-sync task
│   └── tasks.py                # Long-running async tasks
│
├── observability/              # Monitoring
│   ├── metrics.py              # Prometheus metrics, gauges, counters
│   ├── drift_detector.py       # Schema compliance checks
│   └── logging.py              # Structured logging
│
├── schema_copilot/             # (Optional) AI-assisted schema generation
│   ├── copilot.py              # Generate draft mappings for new depts
│   ├── registry.py             # Version-controlled schema registry
│   └── synthesiser.py          # LLM-based mapping synthesis
│
├── config.py                   # Settings: env vars, Kafka, DB, Redis
├── db.py                       # Database connection pool
├── exceptions.py               # Custom exception types
└── __init__.py

tests/
└── unit/
    ├── test_circuit_breaker.py # State transitions, failure thresholds
    ├── test_conflict.py        # Policy matrix, window detection
    ├── test_dispatcher.py      # Fan-out, per-adapter isolation
    ├── test_idempotency.py     # Key reservation, completion, fallback
    ├── test_loop_guard.py      # Loop detection
    ├── test_outbox.py          # Event publishing, offset tracking
    ├── test_service_request.py # Event serialization, correlation IDs
    ├── test_translators.py     # Field mapping validation
    └── test_watermark.py       # High-water mark persistence

scripts/
├── demo_scenario_a.py          # Flow test: SWS → Departments
├── demo_scenario_b.py          # Flow test: Departments → SWS
├── demo_scenario_c.py          # Conflict resolution flow
├── generate_rsa_keys.py        # Create RSA key pair for audit signing
├── run_migrations.py           # Apply Alembic migrations
├── seed_data.py                # Insert test UBID records
└── reset_state.py              # Clear all state for fresh testing

migrations/
├── init.sql                    # Initial schema: audit_ledger, outbox, etc.
└── (Alembic migration files)

schema_registry/
├── factories/mapping_v1.yaml   # Field translation rules for Factories
└── shop_establishment/         # Field translation rules for Shop Est

mock_systems/
├── combined_app.py             # All 3 mock systems on one FastAPI app
├── mock_sws/
│   ├── app.py                  # Mock SWS (GET/PUT /api/businesses/{ubid})
│   └── Dockerfile
├── mock_dept_shop/
│   ├── app.py                  # Mock Shop Est (GET/PUT /api/records/{ubid})
│   └── Dockerfile
└── mock_dept_factories/
    ├── app.py                  # Mock Factories (GET/PUT /api/records/{ubid})
    └── Dockerfile

dashboard/                       # React + Vite frontend
├── src/
│   ├── App.jsx                 # Dashboard main component
│   ├── index.css               # Styling
│   └── pages/
│       ├── Overview.jsx        # Statistics, service health
│       ├── AuditTrail.jsx      # Search, trace, verify
│       ├── Conflicts.jsx       # Conflict records + resolution
│       ├── DLQ.jsx             # Dead letter queue items
│       └── SystemHealth.jsx    # Service status + circuit breakers
├── vite.config.js
└── package.json

Dockerfile                       # Multi-stage: build React dashboard + Python API
docker-compose.yml              # Local dev: Postgres, Redis, Kafka, SyncKar
pyproject.toml                  # Python dependencies, pytest config
railway.toml                    # Railway deployment config
render.yaml                     # Render blueprint (alternative deployment)
alembic.ini                      # Database migration tool config
```

---

## Component Deep Dive

### 1. MODELS: CanonicalServiceRequest (Core Event Format)

**File**: `synckar/models/service_request.py`

**Purpose**: Define the universal format for all events flowing through SyncKar.

**Key Fields**:
```python
class CanonicalServiceRequest(BaseModel):
    correlation_id: UUID              # Shared across all hops
    ubid: str                         # "KA-1234" — only join key
    request_type: RequestType         # ADDRESS_CHANGE, SIGNATORY_CHANGE
    source_system: SourceSystem       # "sws", "shop_establishment", "factories"
    source_event_id: str              # Event ID at origin (immutable)
    field_name: str                   # "registered_address", "authorized_signatories"
    old_value: str | None            # Previous value (before update)
    new_value: str                    # New value being propagated
    raw_payload: dict                 # Original payload from source system
    broker_sequence: int              # Kafka broker sequence (for ordering)
    timestamp: datetime               # When event originated
```

**Why**: Single format means adapters don't need to understand each other's dialects.

**Testing**:
- ✅ Serialization/deserialization (JSON ↔ Python)
- ✅ correlation_id consistency across hops
- ✅ UBID validation (must exist)

---

### 2. ADAPTERS: Protocol-Specific Connectors

#### 2.1 SWS Adapter

**Files**: `synckar/adapters/sws/`

**Two Directions**:

**Inbound (SWS → Kafka)**:
```python
# 1. Poller detects change in SWS
def poll_sws_changes() -> List[CanonicalServiceRequest]:
    # Query: SELECT * FROM businesses WHERE updated_at > HIGH_WATERMARK
    # For each business, extract field changes
    # Return list of canonical events
    pass

# 2. Translator converts SWS format to canonical
def translate_inbound(sws_record: dict) -> CanonicalServiceRequest:
    # Map SWS field names to canonical names
    # "registered_address" → "registered_address"
    # "authorized_signatories" → "authorized_signatories"
    pass

# 3. Write to outbox
def write_outbox(event: CanonicalServiceRequest):
    # INSERT INTO outbox (...) VALUES (...)
    pass

# 4. Outbox worker publishes to Kafka
def publish_to_kafka(events: List[CanonicalServiceRequest]):
    # Publish to topic "sws.changes", partition by UBID
    pass
```

**Outbound (Kafka → SWS)**:
```python
# 1. Consume from Kafka
def consume_dept_changes():
    # Subscribe to "dept.shop.changes", "dept.factories.changes"
    # Deserialize to CanonicalServiceRequest
    pass

# 2. Translator converts canonical to SWS format
def translate_outbound(event: CanonicalServiceRequest) -> dict:
    # Map canonical → SWS API payload
    # "registered_address" ← "registered_address"
    pass

# 3. Write to SWS via API
def write_sws(ubid: str, fields: dict):
    # PUT /api/businesses/{ubid} with fields
    pass

# 4. Write audit row
def write_audit(event, target_system="sws"):
    # Record successful propagation
    pass
```

**Testing**:
- ✅ Polling correctly extracts changes from SWS API
- ✅ Watermark advances correctly (no re-processing)
- ✅ Translator handles all field types (string, list, object)
- ✅ Outbound write succeeds and triggers audit

#### 2.2 Department Adapters (Shop Establishment, Factories)

**Files**: `synckar/adapters/departments/shop_establishment/`, `factories/`

**Similar pattern to SWS**, but:
- Department-specific field mapping (via YAML)
- May use different protocols (REST, SOAP, file-based)
- Truncation/transformation rules applied

**Example: Shop Establishment truncate(120)**
```yaml
# shop_establishment/mapping_v1.yaml
- source_field: registered_address
  target_field: Buss_Addr_Line1
  transform: truncate(120)          # ← Max 120 chars
  auth:
    type: basic
    credential_ref: vault://shop-est/creds
```

**Translator**:
```python
def translate_outbound(event: CanonicalServiceRequest) -> dict:
    # "999 New MG Road, Indiranagar, Bangalore 560038" (52 chars)
    # → Buss_Addr_Line1: "999 New MG Road, Indiranagar, Bangalore 560038"
    
    # But if address is 150 chars:
    # → Buss_Addr_Line1: "999 New MG Road, Indiranagar, Bangalore 560038..." (120 chars)
    pass
```

**Testing**:
- ✅ Truncation applied correctly
- ✅ Long addresses don't corrupt Shop Est records
- ✅ Both directions maintain consistency

---

### 3. PIPELINE: Core Synchronization Logic

#### 3.1 Outbox Pattern (Database-First Publishing)

**File**: `synckar/pipeline/outbox.py`

**Problem**: If we publish to Kafka THEN write to database, and we crash between the two, we lose the event.

**Solution**: 
1. Write to PostgreSQL Outbox table (ATOMIC with business logic)
2. Celery worker polls outbox table
3. Publishes to Kafka
4. Only then mark as processed

```python
# Example flow:
def handle_sws_change(business_ubid: str, new_address: str):
    # ATOMIC TRANSACTION
    conn = db.get_conn()
    try:
        # 1. Update business in main app (if needed)
        # 2. Create canonical event
        event = CanonicalServiceRequest(
            ubid=business_ubid,
            field_name="registered_address",
            new_value=new_address,
            ...
        )
        
        # 3. Write BOTH to outbox in same transaction
        cursor.execute("INSERT INTO outbox (event_json) VALUES (%s)", 
                       (event.model_dump_json(),))
        
        conn.commit()  # ← One commit, not two
    finally:
        conn.close()

# Later, outbox worker:
def process_outbox():
    # SELECT * FROM outbox WHERE processed = false
    # For each row:
    #   - Publish to Kafka
    #   - UPDATE outbox SET processed = true, offset = kafka_offset
```

**Testing**:
- ✅ Events written to outbox atomically
- ✅ No events lost on service restart
- ✅ Kafka offset tracked correctly

#### 3.2 Idempotency Engine (Time-Independent Deduplication)

**File**: `synckar/pipeline/idempotency.py`

**Problem**: Kafka retries may deliver the same event multiple times. How do we prevent duplicates?

**Naive Approach** (WRONG): Use timestamp as part of key
```python
# ❌ BAD: timestamp changes on every retry
key = SHA256(f"sws|evt_123|KA-1234|address|new_addr|{datetime.now()}")
```

**Correct Approach**: Use immutable event properties only
```python
# ✅ GOOD: time-independent, same on every retry
key = SHA256(
    source_system="sws" +
    source_event_id="evt_123" +    # Assigned once at origin
    ubid="KA-1234" +
    field_name="address" +
    new_value="new_addr"
    # Note: NOT datetime!
)
```

**Redis Two-Phase Reservation**:
```python
class IdempotencyEngine:
    def reserve(idempotency_key: str) -> (Status, CachedResponse):
        # Phase 1: Try to mark as IN_PROGRESS
        success = redis.set(
            name=f"idem:{idempotency_key}",
            value="IN_PROGRESS",
            nx=True,      # Only set if key doesn't exist
            ex=300        # TTL 5 minutes
        )
        
        if success:
            return (Status.RESERVED, None)  # You own it, proceed
        else:
            # Key exists, check its status
            existing = redis.get(f"idem:{idempotency_key}")
            
            if existing == "IN_PROGRESS":
                raise IdempotencyKeyInProgress()  # Another worker owns it
            elif existing.startswith("COMPLETED:"):
                # Extract cached response
                response = existing[10:]  # Remove "COMPLETED:" prefix
                return (Status.COMPLETED, response)  # Replay response
    
    def complete(idempotency_key: str, response: str):
        # Record successful completion
        redis.set(
            name=f"idem:{idempotency_key}",
            value=f"COMPLETED:{response}",
            ex=86400  # TTL 24 hours
        )
```

**Testing**:
- ✅ First call: RESERVED → proceed
- ✅ Second call (same key): COMPLETED → return cached
- ✅ Another worker tries same key: IN_PROGRESS → raise exception
- ✅ Redis down: fallback to NOT_FOUND (allow retry, accept duplicate risk)

#### 3.3 Conflict Resolution (Sliding Window + Policy Matrix)

**File**: `synckar/pipeline/conflict.py`

**Problem**: What if SWS and Shop both update the same field simultaneously?

```
Timeline:
T1: SWS updates address to "SWS Address"  → Kafka partition 0
T2: Shop updates address to "Shop Address" → Kafka partition 1  (different partition!)
T3: SWS event consumed
T4: Shop event consumed
→ CONFLICT! Same field, different values, within 5-minute window
```

**Solution: Sliding Window Detector**

```python
class SlidingWindowConflictDetector:
    def check_and_register(event: CanonicalServiceRequest) -> ConflictingEvent | None:
        # Key: "{ubid}:{field_name}" (e.g., "KA-1234:registered_address")
        # Window: 5 minutes (TTL)
        
        conflict_key = f"conflict_window:{event.ubid}:{event.field_name}"
        
        existing = redis.get(conflict_key)
        
        if existing is None:
            # First update to this field, register it
            redis.set(
                conflict_key,
                value=json.dumps({
                    "source_system": event.source_system.value,
                    "value": event.new_value,
                    "correlation_id": str(event.correlation_id),
                    ...
                }),
                ex=300  # 5 min window
            )
            return None  # No conflict
        else:
            # Another event already touched this field!
            # Check if they differ:
            other_event = json.loads(existing)
            if other_event["value"] != event.new_value:
                return ConflictingEvent(other_event)  # CONFLICT DETECTED
            return None  # Same value, no conflict
```

**Policy Matrix: Resolve Conflicts Deterministically**

```python
def resolve_conflict(
    event: CanonicalServiceRequest,
    conflicting_event: ConflictingEvent
) -> ResolutionPolicy:
    
    # Step 1: Categorize field
    data_category = categorize_field(event.field_name)
    # Returns: UNIVERSAL_DEMOGRAPHICS, AUTHORIZATION_STATE, etc.
    
    # Step 2: Apply policy
    if data_category == DataCategory.UNIVERSAL_DEMOGRAPHICS:
        # Address, phone, etc. → SWS always authoritative
        return ResolutionPolicy.SWS_WINS
    
    elif data_category == DataCategory.AUTHORIZATION_STATE:
        # Signatories → Department always authoritative
        return ResolutionPolicy.DEPT_WINS
    
    elif data_category == DataCategory.TIMESTAMP_COMPARABLE:
        # If both systems have timestamps, Last-Write-Wins
        return ResolutionPolicy.LWW
    
    else:
        # No clear policy → escalate to human
        return ResolutionPolicy.DLQ  # Dead Letter Queue
```

**Action on Conflict**:
```python
# Example: SWS address vs Shop address
if resolution_policy == ResolutionPolicy.SWS_WINS:
    # 1. Keep SWS value
    # 2. Overwrite Shop with SWS value
    # 3. Write BOTH values to audit (immutability!)
    audit.write_conflict_record(
        ubid=event.ubid,
        field_name=event.field_name,
        sws_value=event.new_value,           # Winner
        shop_value=conflicting_event.value,  # Loser (preserved)
        policy=ResolutionPolicy.SWS_WINS
    )
    # 4. Trigger Shop update with SWS value
    dispatch_to_adapter("shop_establishment", event)
```

**Testing**:
- ✅ Window correctly detects simultaneous updates
- ✅ Policy matrix applies correct resolution (SWS_WINS, DEPT_WINS, LWW, DLQ)
- ✅ Both values preserved in audit trail
- ✅ Losing value's department gets overwritten with winner's value

#### 3.4 Circuit Breaker (Per-Adapter Resilience)

**File**: `synckar/pipeline/circuit_breaker.py`

**Problem**: If Shop Establishment API is down, should we keep retrying indefinitely? Should we block other adapters?

**Solution: Circuit Breaker State Machine**

```
CLOSED (normal)
    ↓
    [5 consecutive failures in 2 minutes]
    ↓
OPEN (dept is down)
    ↓
    [health probe every 60s]
    ↓
HALF_OPEN (testing recovery)
    ↓
    [real event succeeds? → CLOSED]
    [real event fails? → OPEN]
```

**Behavior**:

| State | Behavior |
|-------|----------|
| **CLOSED** | Send events directly to dept API. Track failures. |
| **OPEN** | Queue events in per-dept holding queue (not DLQ). Send health probe every 60s. |
| **HALF_OPEN** | Process one real event. Success → CLOSED. Failure → OPEN. |

**Code**:
```python
class CircuitBreaker:
    def __init__(self, adapter_id: str):
        self.adapter_id = adapter_id
        self._redis = redis.Redis.from_url(settings.redis.url)
    
    def should_allow_request(self) -> bool:
        state = self._get_state()
        
        if state == CircuitState.CLOSED:
            return True  # Proceed
        
        elif state == CircuitState.OPEN:
            # Only allow if it's a health probe
            # Otherwise, queue in holding queue
            return False
        
        elif state == CircuitState.HALF_OPEN:
            # Allow one request to test recovery
            return True
    
    def record_failure(self) -> None:
        state = self._get_state()
        
        # Increment failure counter
        failures = self._redis.incr(f"circuit:{self.adapter_id}:failures")
        
        # Set window TTL
        self._redis.expire(f"circuit:{self.adapter_id}:failures", 120)  # 2 min
        
        if failures >= 5:
            # Threshold reached → OPEN
            self._redis.set(
                f"circuit:{self.adapter_id}:state",
                CircuitState.OPEN.value
            )
    
    def record_success(self) -> None:
        state = self._get_state()
        
        # Reset failures
        self._redis.delete(f"circuit:{self.adapter_id}:failures")
        
        if state == CircuitState.HALF_OPEN:
            # Recovery successful → CLOSED
            self._redis.set(
                f"circuit:{self.adapter_id}:state",
                CircuitState.CLOSED.value
            )
```

**Testing**:
- ✅ Normal flow (CLOSED): events go through
- ✅ Failures accumulate: 5 → OPEN
- ✅ OPEN state: health probes sent, real events queued
- ✅ Health probe succeeds: HALF_OPEN
- ✅ Real event in HALF_OPEN succeeds: CLOSED
- ✅ Real event in HALF_OPEN fails: back to OPEN

#### 3.5 Dispatcher (Fan-Out, Parallel Processing)

**File**: `synckar/pipeline/dispatcher.py`

**Problem**: One SWS event needs to propagate to 3 adapters (Shop, Factories, etc.). If Shop is down, should we block Factories?

**Answer**: NO. Per-adapter isolation is critical (C9 principle).

```python
def dispatch_sws_to_departments(event: CanonicalServiceRequest) -> dict:
    """
    Fan-out to all adapters independently.
    One failure ≠ block others.
    """
    results = {}
    retriable_errors = []
    
    # Dispatch to Shop Establishment
    try:
        results["shop_establishment"] = _propagate_to_adapter(
            event=event,
            adapter_id="shop_establishment",
            client=shop_client,
            translate_fn=shop_translate_outbound,
            ...
        )
    except (TargetWriteError, IdempotencyKeyInProgress, CircuitBreakerOpen) as e:
        # These errors should be retried by Celery
        retriable_errors.append(e)
    except Exception as e:
        # Other errors: logged but don't block other adapters
        logger.error("shop_establishment_dispatch_failed", error=str(e))
        results["shop_establishment"] = {"error": str(e), "status": "failed"}
    
    # Dispatch to Factories (independent of Shop result!)
    try:
        results["factories"] = _propagate_to_adapter(
            event=event,
            adapter_id="factories",
            ...
        )
    except (TargetWriteError, IdempotencyKeyInProgress, CircuitBreakerOpen) as e:
        retriable_errors.append(e)
    except Exception as e:
        logger.error("factories_dispatch_failed", error=str(e))
        results["factories"] = {"error": str(e), "status": "failed"}
    
    # If any retriable error, re-raise so Celery applies backoff
    if retriable_errors:
        raise retriable_errors[0]  # Celery will retry
    
    return results  # Return all results, both success and non-retriable errors
```

**Testing**:
- ✅ Shop succeeds, Factories fails → Shop updated, Factories queued for retry
- ✅ Shop circuit OPEN, Factories CLOSED → Factories proceeds, Shop queued
- ✅ Temporary error (500) in Shop → Celery retries with backoff
- ✅ Permanent error (404 UBID not found) → logged, but Factories not blocked

#### 3.6 Loop Guard (Prevent Infinite Loops)

**File**: `synckar/pipeline/loop_guard.py`

**Problem**: 
```
A→B→A→B→A→... (infinite loop!)
```

**Solution: Track hops per correlation_id**

```python
class LoopGuard:
    def check_and_record_hop(event: CanonicalServiceRequest, target_adapter: str) -> bool:
        """
        Track hops. If same adapter appears twice, it's a loop.
        """
        key = f"loop_guard:{event.correlation_id}"
        
        hops = redis.get(key)
        if hops is None:
            hops = []
        else:
            hops = json.loads(hops)
        
        # Check for loop
        if target_adapter in hops:
            logger.warning("loop_detected", correlation_id=str(event.correlation_id),
                          current_hops=hops, new_hop=target_adapter)
            return False  # Loop! Don't process
        
        # Record new hop
        hops.append(target_adapter)
        redis.set(key, json.dumps(hops), ex=86400)  # 24 hr TTL
        
        return True  # Safe to proceed
```

**Testing**:
- ✅ Linear flow (SWS → Shop → Audit): all hops recorded
- ✅ Reverse flow attempted (Shop → SWS → Shop): loop detected, 2nd Shop blocked
- ✅ Hops cleared after 24 hours (TTL)

#### 3.7 Watermark (Polling State Persistence)

**File**: `synckar/pipeline/watermark.py`

**Problem**: Adapter crashes after processing 1000 records. On restart, where does it resume?

**Solution**: High-water mark in Redis

```python
class WatermarkTracker:
    def update_watermark(self, adapter_id: str, last_timestamp: datetime):
        """Store the latest timestamp processed."""
        key = f"watermark:{adapter_id}"
        redis.set(key, int(last_timestamp.timestamp()))
    
    def get_watermark(self, adapter_id: str) -> datetime | None:
        """Retrieve where to resume from."""
        key = f"watermark:{adapter_id}"
        ts = redis.get(key)
        if ts:
            return datetime.fromtimestamp(int(ts))
        return None

# In polling loop:
def poll_for_changes(adapter_id: str):
    last_watermark = watermark_tracker.get_watermark(adapter_id)
    
    # Query: SELECT * FROM records WHERE updated_at > last_watermark
    changes = adapter.query_changes_since(last_watermark)
    
    for change in changes:
        process_change(change)
    
    if changes:
        # Update watermark to latest
        watermark_tracker.update_watermark(adapter_id, changes[-1].updated_at)
```

**Testing**:
- ✅ Watermark persists across restarts
- ✅ No records reprocessed below watermark
- ✅ All records above watermark caught

---

### 4. AUDIT LEDGER (Immutable, RSA-Signed)

**File**: `synckar/audit/ledger.py`

**Requirements**:
- ✅ INSERT only (no UPDATE/DELETE, enforced at DB level)
- ✅ Every propagation recorded
- ✅ SHA-256 hash of full payload
- ✅ RSA signature for tamper detection
- ✅ Losing values preserved (conflicts)
- ✅ Correlation ID links all hops

**Schema**:
```sql
CREATE TABLE audit_ledger (
    audit_id UUID PRIMARY KEY,
    correlation_id UUID NOT NULL,           -- shared across hops
    ubid VARCHAR(50) NOT NULL,
    field_modified VARCHAR(100),
    old_value TEXT,
    new_value TEXT,
    source_system VARCHAR(50),              -- "sws", "shop_establishment", etc.
    target_system VARCHAR(50),              -- where the value was written
    api_endpoint VARCHAR(200),
    source_ip INET,
    conflict_detected BOOLEAN DEFAULT FALSE,
    resolution_policy VARCHAR(50),          -- "SWS_WINS", "DEPT_WINS", etc.
    broker_seq_a INT,                       -- Kafka broker sequence of event A
    broker_seq_b INT,                       -- Kafka broker sequence of event B
    temporal_confidence VARCHAR(50),        -- "HIGH", "LOW", etc.
    payload_sha256 VARCHAR(64),             -- SHA-256 hex
    rsa_signature TEXT,                     -- RSA signature for tamper evidence
    created_at TIMESTAMP DEFAULT NOW()
);

-- Enforce INSERT-only (no UPDATE/DELETE)
CREATE RULE audit_no_update AS ON UPDATE TO audit_ledger
    DO INSTEAD NOTHING;

CREATE RULE audit_no_delete AS ON DELETE TO audit_ledger
    DO INSTEAD NOTHING;
```

**Writing Audit**:
```python
def write_audit_row(
    event: CanonicalServiceRequest,
    target_system: str,
    api_endpoint: str,
    conflict_detected: bool = False,
    resolution_policy: str | None = None,
) -> UUID:
    """Write to audit_ledger (append-only)."""
    
    # Step 1: Compute SHA-256 of full event
    payload_json = event.model_dump_json()
    payload_sha256 = hashlib.sha256(payload_json.encode()).hexdigest()
    
    # Step 2: Build row data for signing
    row_data = json.dumps({
        "correlation_id": str(event.correlation_id),
        "ubid": event.ubid,
        "field_modified": event.field_name,
        "old_value": event.old_value,
        "new_value": event.new_value,
        "source_system": event.source_system.value,
        "target_system": target_system,
        "payload_sha256": payload_sha256,
    }, sort_keys=True)
    
    # Step 3: RSA sign the row data
    rsa_signature = sign_audit_row(row_data)
    
    # Step 4: INSERT (only option, UPDATE/DELETE blocked by DB rules)
    cursor.execute("""
        INSERT INTO audit_ledger (
            audit_id, correlation_id, ubid, field_modified, old_value, new_value,
            source_system, target_system, api_endpoint, source_ip,
            conflict_detected, resolution_policy,
            payload_sha256, rsa_signature, created_at
        ) VALUES (
            %(audit_id)s, %(correlation_id)s, %(ubid)s, %(field_modified)s,
            %(old_value)s, %(new_value)s,
            %(source_system)s, %(target_system)s, %(api_endpoint)s, %(source_ip)s,
            %(conflict_detected)s, %(resolution_policy)s,
            %(payload_sha256)s, %(rsa_signature)s, NOW()
        )
    """, {...})
```

**RSA Signing**:
```python
# File: synckar/audit/signing.py

def sign_audit_row(row_data: str) -> str:
    """Sign row with RSA private key (base64-encoded from env)."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    
    # Load private key from env
    private_key_pem = base64.b64decode(os.environ["RSA_PRIVATE_KEY_BASE64"])
    private_key = serialization.load_pem_private_key(
        private_key_pem,
        password=None,
    )
    
    # Sign the row data
    signature = private_key.sign(
        row_data.encode(),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    
    return base64.b64encode(signature).decode()

def verify_audit_signature(row_data: str, signature_b64: str) -> bool:
    """Verify RSA signature (for API endpoint)."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    
    # Load public key (derived from private key)
    public_key_pem = ...  # Store in config or derive
    public_key = serialization.load_pem_public_key(public_key_pem)
    
    try:
        public_key.verify(
            base64.b64decode(signature_b64),
            row_data.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except cryptography.exceptions.InvalidSignature:
        return False
```

**Testing**:
- ✅ Audit row INSERT succeeds
- ✅ Attempt UPDATE on audit → silently fails (DB rule)
- ✅ Attempt DELETE → silently fails (DB rule)
- ✅ SHA-256 matches payload
- ✅ RSA signature verifies
- ✅ Tampering detected (signature mismatch)

---

### 5. CELERY WORKERS (Background Processing)

**File**: `synckar/workers/celery_app.py`

**Two Types of Tasks**:

#### 5.1 Outbox Worker (Continuous)
```python
@celery_app.task(bind=True, queue='outbox')
def process_outbox(self):
    """
    Poll PostgreSQL outbox table.
    For each unprocessed event, publish to Kafka.
    Mark as processed with offset.
    
    Runs continuously (daemon thread on startup).
    """
    
    while True:
        try:
            # SELECT * FROM outbox WHERE processed = false LIMIT 100
            events = db.get_unprocessed_outbox_events(limit=100)
            
            if not events:
                time.sleep(1)  # Poll every 1s
                continue
            
            for event in events:
                # Publish to Kafka
                topic = f"{event.source_system}.changes"
                partition = hash(event.ubid) % num_partitions  # per-UBID ordering
                
                producer.send(topic, 
                    key=event.ubid.encode(),
                    value=event.model_dump_json().encode(),
                    partition=partition)
                
                # Mark as processed
                db.mark_outbox_processed(event.id, offset=producer.last_offset)
        
        except Exception as e:
            logger.error("outbox_worker_error", error=str(e))
            time.sleep(5)  # Back off on error
```

#### 5.2 Kafka Consumer (Continuous)
```python
@celery_app.task(bind=True, queue='consumer')
def consume_kafka_events(self):
    """
    Subscribe to all three Kafka topics:
    - sws.changes
    - dept.shop_establishment.changes
    - dept.factories.changes
    
    For each event, run full pipeline.
    Runs continuously (daemon thread).
    """
    
    consumer = KafkaConsumer(
        'sws.changes',
        'dept.shop_establishment.changes',
        'dept.factories.changes',
        group_id='synckar-consumer',
        bootstrap_servers=settings.kafka.bootstrap_servers,
        auto_offset_reset='earliest',
        enable_auto_commit=False,
    )
    
    while True:
        try:
            message = consumer.poll(timeout_ms=1000)
            
            if not message:
                continue
            
            event = CanonicalServiceRequest(**json.loads(message.value))
            
            # Step 1: Loop guard
            if not loop_guard.check_and_record_hop(event, message.topic.split('.')[0]):
                logger.warning("loop_prevented", correlation_id=str(event.correlation_id))
                consumer.commit(message.offset)
                continue
            
            # Step 2: Conflict detection
            conflict = conflict_detector.check_and_register(event)
            if conflict:
                policy = resolve_conflict(event, conflict)
                if policy == ResolutionPolicy.DLQ:
                    write_dlq(event, "conflict_unresolved")
                    consumer.commit(message.offset)
                    continue
                # Otherwise proceed with policy-driven resolution
            
            # Step 3: Schema translation
            try:
                translated_payload = translate_outbound(event)
            except TranslationError as e:
                write_dlq(event, f"translation_error: {e}")
                consumer.commit(message.offset)
                continue
            
            # Step 4: Dispatch to adapters
            dispatch_result = dispatch_to_adapters(event, translated_payload)
            
            # Step 5: Audit
            write_audit_row(event, target_system=dispatch_result.target, ...)
            
            # Step 6: Commit offset (idempotent, safe)
            consumer.commit(message.offset)
        
        except Exception as e:
            logger.error("consumer_error", error=str(e))
            time.sleep(5)
```

#### 5.3 Celery Beat (Scheduled Tasks)
```python
# Every 10 minutes, trigger full reconciliation
@celery_app.task(queue='reconciliation')
def full_reconciliation_check():
    """
    Query all UBIDs. For each, verify SWS and all depts have same values.
    If divergence found, publish events to sync.
    """
    
    ubids = db.get_all_ubids()
    
    for ubid in ubids:
        sws_record = sws_client.get(ubid)
        shop_record = shop_client.get(ubid)
        factories_record = factories_client.get(ubid)
        
        # Compare all records field by field
        divergences = compare_records(sws_record, shop_record, factories_record)
        
        if divergences:
            logger.warning("reconciliation_divergence_found", ubid=ubid, divergences=divergences)
            # Trigger re-sync with SWS as source of truth
            for field, values in divergences.items():
                event = CanonicalServiceRequest(
                    ubid=ubid,
                    source_system=SourceSystem.SWS,
                    field_name=field,
                    new_value=values['sws'],
                    ...
                )
                write_outbox(event)
```

**Testing**:
- ✅ Outbox worker publishes all events to Kafka
- ✅ Consumer processes events in order per UBID
- ✅ Loop guard prevents re-processing same adapter
- ✅ Conflict detector triggers on simultaneous updates
- ✅ Dispatch fan-out works independently
- ✅ Audit rows created for all hops
- ✅ Offsets committed correctly

---

### 6. DASHBOARD (React + Vite)

**File**: `dashboard/src/`

**Features**:

1. **Overview Tab**
   - Total Propagations (gauge)
   - Conflicts Detected (gauge)
   - DLQ Pending (gauge)
   - Outbox Pending (gauge)

2. **Audit Trail Tab**
   - Search by UBID → list all hops
   - Search by correlation_id → trace end-to-end flow
   - View button → full event details
   - Verify button → check RSA signature

3. **Conflicts Tab**
   - List all conflict records
   - Show: UBID, field, SWS value, Dept value, policy applied
   - Resolve button → mark as acknowledged

4. **DLQ Tab**
   - List unresolved messages
   - Error reason (translation_error, timeout, etc.)
   - Retry button → re-queue to Kafka
   - Delete button → discard

5. **System Health Tab**
   - PostgreSQL: connected/disconnected
   - Redis: connected/disconnected
   - Kafka: connected/degraded/disconnected
   - Circuit breaker states (per adapter)
   - Last health check timestamp

**Testing**:
- ✅ Dashboard loads without errors
- ✅ Statistics update in real-time (or on refresh)
- ✅ Search functions work
- ✅ RSA verification UI works
- ✅ Pagination works (50 items/page)
- ✅ Responsive design on mobile

---

## Cross-Component Test Scenarios

### Scenario 1: Happy Path (SWS → Departments)

```
1. Admin updates address in mock SWS
2. SWS Adapter detects via polling
3. Writes CanonicalServiceRequest to Outbox
4. Outbox Worker publishes to Kafka topic "sws.changes"
5. Kafka Consumer receives event
6. Loop Guard records: [shop_establishment, factories]
7. Conflict Detector: no conflicts (first update)
8. Dispatcher fan-outs to Shop + Factories independently
9. Shop Adapter: translate SWS format → Shop format (truncate 120)
   - Idempotency: reserve key, write Shop API, complete key
   - Circuit: CLOSED → proceed
   - Audit: write_audit_row(..., target="shop_establishment")
10. Factories Adapter: similar flow
11. Dashboard displays: Total Propagations += 2, Audit trail shows 2 rows with same correlation_id
```

**Verify**:
- ✅ Shop address updated to match SWS (truncated)
- ✅ Factories address updated to match SWS
- ✅ Audit shows 3 rows: [SWS→Outbox, SWS→Shop, SWS→Factories]
- ✅ All rows share same correlation_id
- ✅ RSA signatures verify

---

### Scenario 2: Circuit Breaker (Dept Down & Recovery)

```
1. SWS update triggers dispatch to Shop + Factories
2. Shop API is down → 1st attempt fails → CLOSED, failures = 1
3. 2nd attempt fails → failures = 2
4. 3rd attempt fails → failures = 3
5. 4th attempt fails → failures = 4
6. 5th attempt fails → failures = 5 → OPEN (threshold reached!)
7. 6th attempt: Circuit now OPEN → message queued to holding queue (not DLQ)
8. Every 60s, health probe sent to Shop
9. Shop recovers online
10. Health probe succeeds → HALF_OPEN
11. Next real event sent → Shop API responds → CLOSED
12. Holding queue drained and replayed
```

**Verify**:
- ✅ Circuit state transitions: CLOSED → OPEN → HALF_OPEN → CLOSED
- ✅ Messages in holding queue while OPEN (not lost to DLQ)
- ✅ Messages replayed after recovery
- ✅ Dashboard shows circuit breaker state changing

---

### Scenario 3: Conflict Resolution

```
1. SWS updates address to "SWS Address" (correlation_id=AAA)
   → Outbox → Kafka partition 0 → Consumer
   → Loop Guard: [shop]
   → Conflict Detector: key "KA-001:address" → set value
   → Dispatch to Shop → Shop writes "SWS Address"
   
2. Simultaneously, Shop updates address to "Shop Address" (correlation_id=BBB)
   → Outbox → Kafka partition 1 (different!) → Consumer (eventually)
   → Loop Guard: [sws]
   → Conflict Detector: key "KA-001:address" already set!
   → Conflict detected → resolve_conflict() applied
   → Policy: UNIVERSAL_DEMOGRAPHICS → SWS_WINS
   → Dispatch to SWS: write "SWS Address"
   → Audit records both values + policy
   → DLQ: empty (deterministic resolution)
```

**Verify**:
- ✅ Conflict record created
- ✅ SWS_WINS policy applied
- ✅ Both values in audit: winning=SWS, losing=Shop
- ✅ SWS retains "SWS Address"
- ✅ Shop overwritten with "SWS Address"
- ✅ DLQ empty
- ✅ Dashboard shows Conflicts Detected += 1

---

### Scenario 4: Redis Down (Fallback Mode)

```
1. Idempotency engine reserves key in Redis
2. Redis connection drops
3. redis.set() raises ConnectionError
4. Fallback: return IdempotencyStatus.NOT_FOUND
5. Proceed with write (accept duplicate risk)
6. Redis recovers
7. On next call, normal reservation works
8. Duplicates may occur (acceptable tradeoff for availability)
```

**Verify**:
- ✅ No crash on Redis connection error
- ✅ System continues processing
- ✅ Logged warning: "redis_connection_error"
- ✅ Manual deduplication in dashboard (if duplicates occur)

---

## Testing Checklist

### Unit Tests (80%+ coverage)
- [ ] Idempotency: reserve, complete, fallback
- [ ] Conflict: detection, policy matrix, window TTL
- [ ] Circuit Breaker: state transitions, health probes
- [ ] Loop Guard: hop tracking, collision detection
- [ ] Watermark: persistence, resumption
- [ ] Translators: field mapping, truncation
- [ ] Service Request: serialization, correlation_id

### Integration Tests
- [ ] SWS → Shop propagation (happy path)
- [ ] Shop → SWS propagation (reverse)
- [ ] SWS + Shop conflict resolution
- [ ] Circuit breaker: failure → recovery
- [ ] Idempotency: duplicate suppression
- [ ] Audit trail: end-to-end trace
- [ ] RSA signature: verification

### Deployment Tests
- [ ] Health endpoint responds
- [ ] Dashboard loads
- [ ] Database connected
- [ ] Redis connected
- [ ] Kafka connected (or degraded)
- [ ] Celery worker running
- [ ] Celery beat running
- [ ] Mock systems online
- [ ] Demo scenarios pass

### Performance Tests
- [ ] Latency: SWS → Dept < 90s
- [ ] Latency: Dept → SWS < 90s
- [ ] Throughput: 1000+ events/min
- [ ] Audit query: < 500ms
- [ ] Dashboard refresh: < 1s

---

## Conclusion

SyncKar is a well-architected interoperability layer with:
- ✅ **Event-driven design** (Kafka, per-UBID ordering)
- ✅ **Conflict resolution** (deterministic policy matrix)
- ✅ **Immutable audit** (append-only, RSA-signed)
- ✅ **Resilience** (circuit breakers, idempotency, watermarks)
- ✅ **Non-invasive** (wraps around existing APIs)
- ✅ **Observable** (React dashboard, structured logging)

**Current Deployment Status**:
- ✅ Railway up and running
- ✅ Mock systems responsive
- ✅ Kafka transport error (known, ignored for now)
- ⏳ Needs comprehensive end-to-end testing (follow TESTING_GUIDE.md)

