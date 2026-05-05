# SyncKar Testing & Validation Guide
**Complete guide to verify all SyncKar logic and deployment on Railway**

---

## PART 1: QUICK HEALTH CHECK (5 minutes)

### 1.1 Dashboard Access
```bash
# Open in browser
https://synckar-ai4bharat-production.up.railway.app/dashboard
```

**Expected**: React dashboard loads with 5 tabs
- Overview (main statistics)
- Audit Trail (search interface)
- Conflicts (conflict records)
- DLQ (dead letter queue)
- System Health (service status)

### 1.2 Health Endpoint
```bash
curl -s https://synckar-ai4bharat-production.up.railway.app/health | jq .
```

**Expected Response**:
```json
{
  "status": "healthy",
  "timestamp": "2026-05-05T11:20:00Z",
  "services": {
    "database": "connected",
    "redis": "connected",
    "kafka": "connected" or "degraded"
  },
  "celery_worker": "running",
  "celery_beat": "running"
}
```

> **Note**: Kafka may show "degraded" due to the transport error — this is acceptable for now.

### 1.3 Dashboard Statistics Endpoint
```bash
curl -s https://synckar-ai4bharat-production.up.railway.app/api/stats | jq .
```

**Expected Fields**:
```json
{
  "total_propagations": <number>,
  "conflicts_detected": <number>,
  "dlq_pending": <number>,
  "outbox_pending": <number>,
  "conflict_records": <number>,
  "audit_entries_count": <number>
}
```

---

## PART 2: BUSINESS LOGIC VALIDATION (20 minutes)

### 2.1 Verify Mock Systems Are Running

```bash
# Check SWS mock system
curl -s https://synckar-mock-sws.up.railway.app/health | jq .

# Check Shop Establishment mock system
curl -s https://synckar-mock-shop.up.railway.app/health | jq .

# Check Factories mock system  
curl -s https://synckar-mock-factories.up.railway.app/health | jq .
```

**Expected**: All return `{"status": "running"}`

### 2.2 Test Data Availability

```bash
# Get test business from SWS
curl -s https://synckar-mock-sws.up.railway.app/api/businesses/KA-TEST-0001 | jq .

# Get corresponding Shop Establishment record
curl -s https://synckar-mock-shop.up.railway.app/api/records/by-ubid/KA-TEST-0001 | jq .

# Get corresponding Factories record
curl -s https://synckar-mock-factories.up.railway.app/api/records/by-ubid/KA-TEST-0001 | jq .
```

**Expected**: All return records with field values (address, signatories, etc.)

### 2.3 FLOW TEST A: SWS → Shop Establishment

This tests **unidirectional propagation** from SWS to department.

```bash
# Step 1: Get current address in Shop Establishment
OLD_SHOP_ADDR=$(curl -s https://synckar-mock-shop.up.railway.app/api/records/by-ubid/KA-TEST-0001 | jq -r '.Buss_Addr_Line1')
echo "Current Shop address: $OLD_SHOP_ADDR"

# Step 2: Update address in SWS
NEW_ADDR="999 Innovation Drive, Bangalore 560100"
curl -s -X PUT https://synckar-mock-sws.up.railway.app/api/businesses/KA-TEST-0001 \
  -H "Content-Type: application/json" \
  -d "{\"registered_address\": \"$NEW_ADDR\"}" | jq .

# Step 3: Wait for SyncKar to propagate (check every 5s, max 90s)
echo "Waiting for propagation..."
for i in {1..18}; do
  sleep 5
  NEW_SHOP_ADDR=$(curl -s https://synckar-mock-shop.up.railway.app/api/records/by-ubid/KA-TEST-0001 | jq -r '.Buss_Addr_Line1')
  if [[ "$NEW_SHOP_ADDR" == "${NEW_ADDR:0:120}" ]]; then
    echo "✅ Propagated after $((i*5))s: $NEW_SHOP_ADDR"
    break
  fi
  echo "  Wait $((i*5))s... Still: $NEW_SHOP_ADDR"
done

# Step 4: Verify SWS and Shop match
FINAL_SWS=$(curl -s https://synckar-mock-sws.up.railway.app/api/businesses/KA-TEST-0001 | jq -r '.registered_address')
FINAL_SHOP=$(curl -s https://synckar-mock-shop.up.railway.app/api/records/by-ubid/KA-TEST-0001 | jq -r '.Buss_Addr_Line1')
echo "Final SWS:  $FINAL_SWS"
echo "Final Shop: $FINAL_SHOP"
```

**Expected**: Shop address updated to match SWS (with truncate(120) applied)

### 2.4 FLOW TEST B: Department → SWS

This tests **reverse propagation** from department back to SWS.

```bash
# Step 1: Get current signatory in SWS
OLD_SWS_SIG=$(curl -s https://synckar-mock-sws.up.railway.app/api/businesses/KA-TEST-0002 | jq -r '.authorized_signatories[0]')
echo "Current SWS signatory: $OLD_SWS_SIG"

# Step 2: Update signatory in Factories
NEW_SIG="newholder@example.com"
curl -s -X PUT https://synckar-mock-factories.up.railway.app/api/records/KA-TEST-0002 \
  -H "Content-Type: application/json" \
  -d "{\"authorized_signatories\": [\"$NEW_SIG\"]}" | jq .

# Step 3: Wait for SyncKar to propagate via polling (check every 10s, max 90s)
echo "Waiting for reverse propagation (dept → SWS)..."
for i in {1..9}; do
  sleep 10
  NEW_SWS_SIG=$(curl -s https://synckar-mock-sws.up.railway.app/api/businesses/KA-TEST-0002 | jq -r '.authorized_signatories[0]')
  if [[ "$NEW_SWS_SIG" == "$NEW_SIG" ]]; then
    echo "✅ Propagated after $((i*10))s: $NEW_SWS_SIG"
    break
  fi
  echo "  Wait $((i*10))s... Still: $NEW_SWS_SIG"
done

# Step 4: Verify both systems match
FINAL_SWS_SIG=$(curl -s https://synckar-mock-sws.up.railway.app/api/businesses/KA-TEST-0002 | jq -r '.authorized_signatories[0]')
FINAL_FACT_SIG=$(curl -s https://synckar-mock-factories.up.railway.app/api/records/KA-TEST-0002 | jq -r '.authorized_signatories[0]')
echo "Final SWS signatory: $FINAL_SWS_SIG"
echo "Final Factories signatory: $FINAL_FACT_SIG"
```

**Expected**: SWS signatory updated to match Factories

### 2.5 FLOW TEST C: Conflict Resolution

This tests **simultaneous updates and conflict resolution**.

```bash
# Step 1: Get current state for UBID
curl -s https://synckar-mock-sws.up.railway.app/api/businesses/KA-TEST-0003 | jq .
curl -s https://synckar-mock-shop.up.railway.app/api/records/by-ubid/KA-TEST-0003 | jq .

# Step 2: Update SWS with new address
SWS_ADDR="111 SWS Update, Bangalore"
curl -s -X PUT https://synckar-mock-sws.up.railway.app/api/businesses/KA-TEST-0003 \
  -H "Content-Type: application/json" \
  -d "{\"registered_address\": \"$SWS_ADDR\"}" | jq -r '.updated_fields'

# Step 3: Immediately update Shop with different address (simultaneous conflict)
SHOP_ADDR="222 Shop Update, Bangalore"
curl -s -X PUT https://synckar-mock-shop.up.railway.app/api/records/KA-TEST-0003 \
  -H "Content-Type: application/json" \
  -d "{\"Buss_Addr_Line1\": \"$SHOP_ADDR\"}" | jq .

# Step 4: Wait for SyncKar to detect and resolve conflict (90s)
echo "Waiting for conflict detection and resolution..."
sleep 90

# Step 5: Check final state and audit trail
echo "Final SWS state:"
curl -s https://synckar-mock-sws.up.railway.app/api/businesses/KA-TEST-0003 | jq '.registered_address'

echo "Final Shop state:"
curl -s https://synckar-mock-shop.up.railway.app/api/records/by-ubid/KA-TEST-0003 | jq '.Buss_Addr_Line1'

echo "Conflict audit records:"
curl -s 'https://synckar-ai4bharat-production.up.railway.app/api/dlq/conflicts' | jq '.conflicts[] | select(.ubid == "KA-TEST-0003")'
```

**Expected**: 
- SWS address wins (policy: UNIVERSAL_DEMOGRAPHICS → SWS_WINS)
- Shop address overwritten with SWS value
- Conflict record shows both values with resolution policy

---

## PART 3: AUDIT TRAIL VALIDATION (15 minutes)

### 3.1 Search Audit by UBID

```bash
# Query all audit entries for a business
curl -s 'https://synckar-ai4bharat-production.up.railway.app/api/audit?ubid=KA-TEST-0001' | jq .

# Expected structure:
# {
#   "ubid": "KA-TEST-0001",
#   "total": 5,
#   "audit_entries": [
#     {
#       "audit_id": "uuid",
#       "correlation_id": "uuid",
#       "timestamp": "2026-05-05T11:20:00Z",
#       "source_system": "sws",
#       "target_system": "shop_establishment",
#       "field_modified": "registered_address",
#       "old_value": "...",
#       "new_value": "...",
#       "payload_sha256": "abc123...",
#       "rsa_signature": "sig...",
#       "conflict_detected": false
#     }
#   ]
# }
```

### 3.2 Trace End-to-End Flow

```bash
# Get a correlation_id from audit
CORR_ID=$(curl -s 'https://synckar-ai4bharat-production.up.railway.app/api/audit?ubid=KA-TEST-0001' \
  | jq -r '.audit_entries[0].correlation_id')

echo "Tracing correlation_id: $CORR_ID"

# Fetch all entries with this correlation_id
curl -s "https://synckar-ai4bharat-production.up.railway.app/api/audit/trace/$CORR_ID" | jq .

# Expected: Multiple entries showing:
# 1. SWS → Outbox (origin)
# 2. Outbox → Shop Est (propagation)
# 3. Shop Est → Audit (confirmation)
```

### 3.3 Verify RSA Signatures

```bash
# Get an audit_id
AUDIT_ID=$(curl -s 'https://synckar-ai4bharat-production.up.railway.app/api/audit?ubid=KA-TEST-0001' \
  | jq -r '.audit_entries[0].audit_id')

echo "Verifying audit_id: $AUDIT_ID"

# Verify RSA signature
curl -s "https://synckar-ai4bharat-production.up.railway.app/api/audit/verify/$AUDIT_ID" | jq .

# Expected:
# {
#   "audit_id": "uuid",
#   "verified": true,
#   "signature_valid": true,
#   "tamper_detected": false,
#   "verification_timestamp": "2026-05-05T11:20:00Z"
# }
```

---

## PART 4: RESILIENCE & EDGE CASES (10 minutes)

### 4.1 Idempotency Test

```bash
# Send the same request twice (should be idempotent)
PAYLOAD='{"registered_address": "Idempotency Test Address"}'

echo "Request 1:"
RESP1=$(curl -s -X PUT https://synckar-mock-sws.up.railway.app/api/businesses/KA-TEST-0004 \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")
echo "$RESP1" | jq '.response_id'

sleep 5

echo "Request 2 (identical):"
RESP2=$(curl -s -X PUT https://synckar-mock-sws.up.railway.app/api/businesses/KA-TEST-0004 \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")
echo "$RESP2" | jq '.response_id'

# Both responses should be identical (cached response on retry)
```

### 4.2 DLQ Check

```bash
# Check Dead Letter Queue for any unresolved issues
curl -s 'https://synckar-ai4bharat-production.up.railway.app/api/dlq' | jq '.dlq_items | length'

# If any items, inspect them:
curl -s 'https://synckar-ai4bharat-production.up.railway.app/api/dlq' | jq '.dlq_items[0]'

# Expected: Empty DLQ (all messages successfully processed)
```

### 4.3 Circuit Breaker Status

```bash
# Check system health to see circuit breaker states
curl -s 'https://synckar-ai4bharat-production.up.railway.app/api/health' | jq '.circuit_breakers'

# Expected:
# {
#   "shop_establishment": "CLOSED",
#   "factories": "CLOSED",
#   "sws": "CLOSED"
# }
```

---

## PART 5: DEPLOYMENT CONFIGURATION VALIDATION (10 minutes)

### 5.1 Check Railway Services

1. **Go to Railway Dashboard**:
   - Login to https://railway.app
   - Navigate to your SyncKar project
   - Verify 3-4 services are running:
     - ✅ `synckar-api` — Main API + Celery worker + beat
     - ✅ `synckar-mock-sws` — Mock SWS system
     - ✅ `synckar-mock-shop` — Mock Shop Establishment
     - ✅ `synckar-mock-factories` — Mock Factories

2. **Check Service Logs** (for each service):
   ```bash
   # From Railway dashboard:
   # - Look for "Application running" or equivalent
   # - Check for ERROR logs (aside from Kafka transport error)
   # - Verify Celery worker started as daemon
   # - Verify Celery beat started as daemon
   ```

3. **Verify Environment Variables**:
   - Check that all required vars are set:
     - `DATABASE_URL` ✅
     - `REDIS_URL` ✅
     - `KAFKA_BOOTSTRAP_SERVERS` ✅
     - `KAFKA_SASL_USERNAME` ✅
     - `KAFKA_SASL_PASSWORD` ✅
     - `MOCK_SWS_BASE_URL` ✅
     - `MOCK_SHOP_BASE_URL` ✅
     - `MOCK_FACTORIES_BASE_URL` ✅
     - `RSA_PRIVATE_KEY_BASE64` ✅ (base64-encoded)

### 5.2 Database Health

```bash
# Check if migrations ran successfully
curl -s 'https://synckar-ai4bharat-production.up.railway.app/api/audit?ubid=KA-TEST-0001' | jq '.total'

# If result > 0, database is connected and working
```

### 5.3 Redis Health

```bash
# Check Redis connectivity by querying any cached data
curl -s 'https://synckar-ai4bharat-production.up.railway.app/api/health' | jq '.services.redis'

# Expected: "connected"
```

---

## PART 6: KNOWN ISSUES & WORKAROUNDS

### Issue 1: Kafka Transport Error

**Observed Error**:
```
KafkaError(code=_TRANSPORT, val=195, str="Failed to get metadata: 
Local: Broker transport failure")
```

**Impact**: 
- Non-blocking — system continues to work
- Kafka may reconnect automatically
- Some message delivery delays expected

**Workarounds**:

#### Option A: Verify SSL Certificate
```bash
# SSH into Railway service and check:
ls -la /app/ca.pem

# If missing, download from Aiven and re-deploy:
# 1. Go to Aiven console
# 2. Download CA certificate
# 3. Set KAFKA_SSL_CERT_PATH correctly
```

#### Option B: Check Aiven Kafka Cluster Status
1. Log into https://aiven.io
2. Navigate to your Kafka cluster
3. Verify cluster is running (not paused/stopped)
4. Check if credentials are valid
5. View connection logs for rejected connections

#### Option C: Add Retry Logic (Code Fix)
Edit `synckar/workers/celery_app.py`:
```python
from retrying import retry

@retry(stop_max_attempt_number=3, wait_fixed=5000)
def connect_kafka():
    """Connect to Kafka with exponential backoff retry."""
    try:
        consumer = KafkaConsumer(...)
        return consumer
    except KafkaError as e:
        logger.error("Kafka connection failed", error=str(e))
        raise
```

#### Option D: Graceful Degradation (Current Approach)
- System marks Kafka as "degraded" but continues
- Outbox queues messages locally in PostgreSQL
- On Kafka recovery, outbox drained automatically

### Issue 2: Slow Propagation (>90 seconds)

**Possible Causes**:
1. Kafka lag — check Aiven broker metrics
2. Celery worker queue backlog — check Redis queue size
3. Polling interval too long (default 10s) — adjust in config
4. Mock system slow — restart mock services

**Debugging**:
```bash
# Check Celery worker queue depth
curl -s 'https://synckar-ai4bharat-production.up.railway.app/api/health' | jq '.celery_pending_tasks'

# Check Kafka consumer group lag
# (via Aiven dashboard)
```

### Issue 3: Audit Trail Not Growing

**Possible Causes**:
1. No events being processed
2. Audit table full (unlikely on free tier)
3. RSA signing failed silently

**Debugging**:
```bash
# Force a test event
curl -X PUT https://synckar-mock-sws.up.railway.app/api/businesses/KA-TEST-0001 \
  -H "Content-Type: application/json" \
  -d '{"registered_address": "Debug Test"}'

# Wait 30s, then check:
curl -s 'https://synckar-ai4bharat-production.up.railway.app/api/audit?ubid=KA-TEST-0001' | jq '.total'

# If still 0, check logs for errors
```

---

## PART 7: PERFORMANCE BENCHMARKS

### Expected Metrics

| Metric | Target | Acceptable | Critical |
|--------|--------|-----------|----------|
| **SWS → Dept Latency** | 30-45s | <90s | >120s |
| **Dept → SWS Latency** | 30-60s | <90s | >120s |
| **Conflict Detection** | <5s | <10s | >15s |
| **Audit Query (1000 rows)** | <200ms | <500ms | >1s |
| **Dashboard Refresh** | <500ms | <1s | >2s |
| **Idempotency Lookup** | <50ms | <100ms | >200ms |
| **Health Check** | <100ms | <500ms | >1s |

### Load Test (Optional)

```bash
# Send 50 sequential updates to SWS
for i in {1..50}; do
  curl -s -X PUT https://synckar-mock-sws.up.railway.app/api/businesses/KA-TEST-0001 \
    -H "Content-Type: application/json" \
    -d "{\"registered_address\": \"Address Update $i\"}" &
  sleep 0.5  # Space out requests
done
wait

# Monitor propagation:
# Dashboard → Overview tab → "Total Propagations" should increment
```

---

## PART 8: SUCCESS CRITERIA

✅ **System is working correctly if**:

1. ✅ All health checks return "healthy" or "degraded" (not "unhealthy")
2. ✅ Dashboard loads and displays statistics
3. ✅ Flow Test A (SWS → Shop) completes within 90s
4. ✅ Flow Test B (Dept → SWS) completes within 90s
5. ✅ Flow Test C (Conflict Resolution) applies SWS_WINS policy
6. ✅ Audit trail shows all propagations with correlation_id
7. ✅ RSA signatures verify without tampering detected
8. ✅ DLQ is empty (or contains only expected test items)
9. ✅ All circuit breakers in CLOSED state
10. ✅ Database and Redis connected

❌ **System needs attention if**:

- Any health check returns "unhealthy" (not just "degraded")
- Dashboard fails to load
- Propagation exceeds 120 seconds consistently
- Audit trail has gaps or missing hops
- RSA signature verification fails
- DLQ has unresolved items from real operations
- Circuit breaker stuck in OPEN state
- Multiple error messages in logs (aside from Kafka transport)

---

## PART 9: CLEANUP & RESET

```bash
# Reset all test data (careful!)
curl -X POST https://synckar-ai4bharat-production.up.railway.app/api/admin/reset

# Or use the script if you have shell access:
python scripts/reset_state.py

# Seed fresh test data:
python scripts/seed_data.py
```

---

## SUMMARY

**Estimated Total Testing Time**: 70-90 minutes

| Section | Time | Status |
|---------|------|--------|
| Part 1: Health Check | 5 min | ⏳ |
| Part 2: Business Logic | 20 min | ⏳ |
| Part 3: Audit Trail | 15 min | ⏳ |
| Part 4: Resilience | 10 min | ⏳ |
| Part 5: Deployment Config | 10 min | ⏳ |
| Part 6: Troubleshooting | 10 min | ⏳ |
| Part 7: Performance Check | 5 min | ⏳ |

**After completing all sections, SyncKar deployment is validated** ✅

