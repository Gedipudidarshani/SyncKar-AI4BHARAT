# SyncKar Quick Reference Guide

## 📋 Quick Links

| Document | Purpose |
|----------|---------|
| [TESTING_GUIDE.md](./TESTING_GUIDE.md) | **START HERE** — Step-by-step testing instructions (70-90 min) |
| [CODEBASE_ANALYSIS.md](./CODEBASE_ANALYSIS.md) | Deep dive into architecture, components, and logic |
| [run_all_tests.sh](./run_all_tests.sh) | Automated test suite (bash script) |
| [SyncKar_Final_Solution.md](./SyncKar_Final_Solution.md) | Problem statement and design decisions |

---

## 🚀 Deployment Status

**Current Environment**: Railway (free tier)

| Service | URL | Status |
|---------|-----|--------|
| **SyncKar API** | https://synckar-ai4bharat-production.up.railway.app | ✅ Running |
| **SyncKar Dashboard** | https://synckar-ai4bharat-production.up.railway.app/dashboard | ✅ Running |
| **Mock SWS** | https://synckar-mock-sws.up.railway.app | ✅ Running |
| **Mock Shop Establishment** | https://synckar-mock-shop.up.railway.app | ✅ Running |
| **Mock Factories** | https://synckar-mock-factories.up.railway.app | ✅ Running |

---

## ⚠️ Known Issues

### Kafka Transport Error (IGNORED)
```
KafkaError(code=_TRANSPORT, val=195, str="Failed to get metadata...")
```
- **Impact**: Non-blocking — system continues to work
- **Status**: Expected, monitoring ongoing
- **Workaround**: See "Kafka Troubleshooting" section below

---

## 🧪 Quick Test (5 minutes)

```bash
# 1. Check health
curl -s https://synckar-ai4bharat-production.up.railway.app/health | jq .

# 2. Check dashboard loads
curl -s https://synckar-ai4bharat-production.up.railway.app/dashboard | head -20

# 3. Query audit
curl -s 'https://synckar-ai4bharat-production.up.railway.app/api/audit?ubid=KA-TEST-0001' | jq '.total'

# 4. Check stats
curl -s 'https://synckar-ai4bharat-production.up.railway.app/api/stats' | jq .
```

---

## 🔧 Core Components Map

### Data Flow Layers

```
INPUT ADAPTERS
├── SWS Adapter (polling/webhook)
├── Shop Establishment Adapter (polling)
└── Factories Adapter (polling)

↓

OUTBOX PATTERN
└── PostgreSQL Transactional Outbox

↓

KAFKA EVENT BUS
├── sws.changes
├── dept.shop_establishment.changes
└── dept.factories.changes

↓

PROCESSING PIPELINE
├── Loop Guard (prevent A→B→A loops)
├── Conflict Detector (sliding window)
├── Policy Matrix (deterministic resolution)
├── Schema Translator (field mapping)
├── Idempotency Engine (Redis dedup)
├── Circuit Breaker (per-adapter resilience)
├── Rate Limiter (throttle)
└── Dispatcher (fan-out)

↓

OUTPUT ADAPTERS
├── SWS Adapter (write back)
├── Shop Establishment Adapter (write back)
└── Factories Adapter (write back)

↓

AUDIT & OBSERVABILITY
├── Audit Ledger (PostgreSQL, immutable)
├── Metrics (Prometheus)
└── Dashboard (React)
```

---

## 📁 Key Files by Feature

### Idempotency
- **Code**: `synckar/pipeline/idempotency.py`
- **Test**: `tests/unit/test_idempotency.py`
- **Key Logic**: Time-independent SHA-256 key, Redis Two-Phase Reservation

### Conflict Resolution
- **Code**: `synckar/pipeline/conflict.py`
- **Test**: `tests/unit/test_conflict.py`
- **Key Logic**: Sliding window detector, policy matrix (SWS_WINS, DEPT_WINS, LWW, DLQ)

### Circuit Breaker
- **Code**: `synckar/pipeline/circuit_breaker.py`
- **Test**: `tests/unit/test_circuit_breaker.py`
- **Key Logic**: CLOSED/OPEN/HALF_OPEN states, 5 failures in 2 min = OPEN

### Audit Trail
- **Code**: `synckar/audit/ledger.py`, `synckar/audit/signing.py`
- **Test**: `tests/unit/test_*`
- **Key Logic**: Append-only (no UPDATE/DELETE), RSA-signed, SHA-256 hashed

### Adapters
- **SWS**: `synckar/adapters/sws/` (inbound + outbound)
- **Shop**: `synckar/adapters/departments/shop_establishment/`
- **Factories**: `synckar/adapters/departments/factories/`
- **Schema Mapping**: `schema_registry/*/mapping_v1.yaml`

### Workers
- **Celery**: `synckar/workers/celery_app.py` (outbox publisher, Kafka consumer, beat scheduler)
- **Tasks**: `synckar/workers/tasks.py`

### API
- **Health**: `synckar/api/routes/health.py` → `GET /health`
- **Audit**: `synckar/api/routes/audit.py` → `GET /api/audit`
- **DLQ**: `synckar/api/routes/dlq.py` → `GET /api/dlq`
- **Webhooks**: `synckar/api/routes/webhooks.py` → `POST /api/webhooks/{system_id}`

### Dashboard
- **Main**: `dashboard/src/App.jsx`
- **Tabs**:
  - Overview: `dashboard/src/pages/Overview.jsx`
  - Audit: `dashboard/src/pages/AuditTrail.jsx`
  - Conflicts: `dashboard/src/pages/Conflicts.jsx`
  - DLQ: `dashboard/src/pages/DLQ.jsx`
  - Health: `dashboard/src/pages/SystemHealth.jsx`

---

## 🧬 Key Concepts

| Concept | Definition | Implementation |
|---------|-----------|-----------------|
| **UBID** | Unique Business Identifier (join key across all systems) | `CanonicalServiceRequest.ubid` |
| **Correlation ID** | Shared across all hops of an event | `CanonicalServiceRequest.correlation_id` (UUID) |
| **Canonical Format** | Universal event format (independent of dept schema) | `CanonicalServiceRequest` dataclass |
| **Outbox Pattern** | Write to DB + Kafka atomically via DB | `synckar/pipeline/outbox.py` |
| **Idempotency Key** | Time-independent dedup key | `SHA256(source + event_id + ubid + field + value)` |
| **Conflict Window** | 5-minute sliding window to detect simultaneous updates | Redis TTL=300s |
| **Circuit Breaker** | Per-adapter state machine for resilience | CLOSED/OPEN/HALF_OPEN |
| **Loop Guard** | Track hops to prevent A→B→A chains | Redis set per correlation_id |
| **Watermark** | High-water mark for polling resumption | Redis per-adapter timestamp |
| **Policy Matrix** | Deterministic conflict resolution rules | `synckar/pipeline/conflict.py::resolve_conflict()` |

---

## 📊 Architecture Decision Records (ADRs)

### ADR 1: Zero Modifications to Source Systems
- **Decision**: Layer sits outside, wraps existing APIs
- **Benefit**: No coordination needed, autonomous operation
- **Trade-off**: Polling required for depts without webhooks

### ADR 2: Deterministic Conflict Resolution
- **Decision**: Policy matrix defines resolution (no human judgment)
- **Benefit**: Predictable, auditable, repeatable
- **Trade-off**: Some edge cases go to DLQ for human review

### ADR 3: Immutable Audit Trail
- **Decision**: Append-only, no UPDATE/DELETE
- **Benefit**: Compliance (BSA 2023), tamper-proof, historical record
- **Trade-off**: Storage cost grows over time

### ADR 4: Time-Independent Idempotency
- **Decision**: Key doesn't include timestamp
- **Benefit**: Works across retries, crashes, delays
- **Trade-off**: Must extract field value from event (harder to reason about)

### ADR 5: Per-UBID Kafka Partitioning
- **Decision**: Partition by UBID to guarantee ordering
- **Benefit**: No conflicts within single business
- **Trade-off**: Skewed partition distribution if few active businesses

---

## 🔍 Testing Priorities

### Priority 1: Business Logic (CRITICAL)
1. ✅ Idempotency: no duplicate writes on retry
2. ✅ Conflict Resolution: deterministic policy applied
3. ✅ Audit Trail: all hops recorded immutably
4. ✅ Loop Guard: prevent infinite propagation

### Priority 2: Resilience (HIGH)
1. ✅ Circuit Breaker: graceful degradation
2. ✅ Watermark: no data loss on restart
3. ✅ Rate Limiting: prevent overwhelming depts
4. ✅ Redis Down: fallback to degraded mode

### Priority 3: Integration (MEDIUM)
1. ✅ SWS → Dept propagation
2. ✅ Dept → SWS propagation
3. ✅ Conflict detection & resolution
4. ✅ Audit trail end-to-end trace

### Priority 4: Performance (LOW)
1. ⏳ Latency < 90s (acceptable)
2. ⏳ Throughput > 1000 events/min
3. ⏳ Query performance < 500ms

---

## 🐛 Common Issues & Fixes

### Kafka Transport Error
```
Error: KafkaError(code=_TRANSPORT, val=195, ...)

Fix:
1. Verify Aiven cluster running: check dashboard
2. Verify credentials: KAFKA_SASL_USERNAME, KAFKA_SASL_PASSWORD
3. Verify CA cert: KAFKA_SSL_CA_PATH=/app/ca.pem
4. (Ignore for now — system handles gracefully)
```

### Slow Propagation (>90 seconds)
```
Cause: Polling interval too long, queue backlog, or Celery workers slow

Fix:
1. Check Celery worker status: docker ps (local) or Railway logs
2. Check Redis queue size: redis-cli LLEN celery
3. Reduce polling interval in config.py
4. Increase Celery concurrency: --concurrency=4
```

### Audit Trail Not Growing
```
Cause: No events being processed, RSA signing failed, or query empty

Fix:
1. Trigger test event: curl -X PUT mock_sws/.../api/businesses/...
2. Wait 30s, then query audit
3. Check logs for RSA signing errors
4. Verify RSA_PRIVATE_KEY_BASE64 set correctly
```

### DLQ Growing
```
Cause: Translation errors, permanent write failures, or conflicts

Fix:
1. Inspect DLQ items: GET /api/dlq
2. Resolve translation errors: update schema mapping
3. Resolve write failures: check target system health
4. Resolve conflicts: apply policy manually
```

---

## 🚀 Demo Commands

### Quick Start (Local)
```bash
# 1. Start services
docker-compose up --build

# 2. Run migrations
python scripts/run_migrations.py

# 3. Seed test data
python scripts/seed_data.py

# 4. Run demo scenarios
python scripts/demo_scenario_a.py  # SWS → Depts
python scripts/demo_scenario_b.py  # Depts → SWS
python scripts/demo_scenario_c.py  # Conflict resolution

# 5. View dashboard
open http://localhost:18080/dashboard
```

### Production Testing
```bash
# 1. Check health
curl https://synckar-ai4bharat-production.up.railway.app/health | jq .

# 2. Run automated tests
bash run_all_tests.sh production

# 3. Manual flow test (see TESTING_GUIDE.md for full commands)
curl -s https://synckar-mock-sws.up.railway.app/api/businesses/KA-TEST-0001 | jq .
```

---

## 📞 Support & Troubleshooting

### Check Logs
**Local**:
```bash
docker logs synckar-api
docker logs synckar-celery-worker
docker logs synckar-postgres
docker logs synckar-redis
```

**Production (Railway)**:
1. Go to https://railway.app
2. Select SyncKar project
3. Click service (synckar-api, synckar-worker, etc.)
4. View logs in "Deployments" tab

### Health Check
```bash
# Comprehensive health check
curl -s https://synckar-ai4bharat-production.up.railway.app/health | jq .

# Should show:
# {
#   "status": "healthy" or "degraded",
#   "services": {
#     "database": "connected",
#     "redis": "connected",
#     "kafka": "connected" or "degraded"
#   }
# }
```

### Emergency Reset (Development Only)
```bash
# Reset all state (WARNING: deletes data!)
curl -X POST https://synckar-ai4bharat-production.up.railway.app/api/admin/reset

# Or use script
python scripts/reset_state.py
```

---

## ✅ Validation Checklist

Before marking deployment as "ready for production":

- [ ] All health endpoints return "healthy" or "degraded"
- [ ] Dashboard loads and displays statistics
- [ ] Flow Test A: SWS → Depts completes within 90s
- [ ] Flow Test B: Depts → SWS completes within 90s
- [ ] Flow Test C: Conflict resolution applies policy correctly
- [ ] Audit trail shows all hops with correlation_id
- [ ] RSA signatures verify without tampering
- [ ] DLQ is empty (or only contains expected test items)
- [ ] Circuit breakers all in CLOSED state
- [ ] Database, Redis, Kafka all connected (Kafka can be "degraded")
- [ ] Mock systems responsive
- [ ] Celery worker processing tasks
- [ ] Celery beat running scheduled tasks

---

## 📖 Further Reading

- **Full Testing Guide**: [TESTING_GUIDE.md](./TESTING_GUIDE.md)
- **Codebase Analysis**: [CODEBASE_ANALYSIS.md](./CODEBASE_ANALYSIS.md)
- **Original Proposal**: [SyncKar_Final_Solution.md](./SyncKar_Final_Solution.md)
- **Deployment Guide**: [synckar/DEPLOY.md](./synckar/DEPLOY.md)
- **API Documentation**: Swagger UI at `{base_url}/docs`

---

**Last Updated**: 2026-05-05
**Status**: Production Ready (with Kafka transport error noted)

