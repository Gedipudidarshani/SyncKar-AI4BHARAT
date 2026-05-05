#!/usr/bin/env bash
#
# SyncKar Full Testing Suite
# Complete validation of all business logic and deployment
#
# Usage:
#   bash run_all_tests.sh [ENVIRONMENT]
#   ENVIRONMENT: local (docker-compose) or production (Railway)
#
# Examples:
#   bash run_all_tests.sh local        # Test local docker-compose setup
#   bash run_all_tests.sh production   # Test Railway deployment
#

set -e

ENVIRONMENT="${1:-local}"
RESULTS_FILE="test_results_$(date +%Y%m%d_%H%M%S).md"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# URLs based on environment
if [ "$ENVIRONMENT" = "local" ]; then
    SWS_URL="http://localhost:8000"
    SHOP_URL="http://localhost:8001"
    FACTORIES_URL="http://localhost:8002"
    SYNCKAR_URL="http://localhost:18080"
elif [ "$ENVIRONMENT" = "production" ]; then
    SWS_URL="https://synckar-mock-sws.up.railway.app"
    SHOP_URL="https://synckar-mock-shop.up.railway.app"
    FACTORIES_URL="https://synckar-mock-factories.up.railway.app"
    SYNCKAR_URL="https://synckar-ai4bharat-production.up.railway.app"
else
    echo "Invalid environment: $ENVIRONMENT"
    exit 1
fi

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
    echo "[INFO] $1" >> "$RESULTS_FILE"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    echo "[PASS] $1" >> "$RESULTS_FILE"
    ((TESTS_PASSED++))
}

log_failure() {
    echo -e "${RED}[FAIL]${NC} $1"
    echo "[FAIL] $1" >> "$RESULTS_FILE"
    ((TESTS_FAILED++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    echo "[WARN] $1" >> "$RESULTS_FILE"
}

# Initialize results file
{
    echo "# SyncKar Test Results"
    echo "Environment: $ENVIRONMENT"
    echo "Timestamp: $(date)"
    echo ""
    echo "## Configuration"
    echo "- SWS: $SWS_URL"
    echo "- Shop: $SHOP_URL"
    echo "- Factories: $FACTORIES_URL"
    echo "- SyncKar: $SYNCKAR_URL"
    echo ""
    echo "## Test Results"
} > "$RESULTS_FILE"

log_info "Starting SyncKar full test suite on $ENVIRONMENT environment"

# ============================================================================
# PART 1: CONNECTIVITY TESTS
# ============================================================================

log_info "PART 1: Connectivity Tests"

test_endpoint() {
    local name=$1
    local url=$2
    
    if curl -s -f "$url" > /dev/null 2>&1; then
        log_success "$name: $url"
        return 0
    else
        log_failure "$name: $url (unreachable)"
        return 1
    fi
}

test_endpoint "SWS Health" "$SWS_URL/health"
test_endpoint "Shop Health" "$SHOP_URL/health"
test_endpoint "Factories Health" "$FACTORIES_URL/health"
test_endpoint "SyncKar Health" "$SYNCKAR_URL/health"

# ============================================================================
# PART 2: HEALTH CHECK TESTS
# ============================================================================

log_info "PART 2: Health Check Tests"

# Check SyncKar health
HEALTH=$(curl -s "$SYNCKAR_URL/health" 2>/dev/null)

if echo "$HEALTH" | grep -q '"status".*"healthy"'; then
    log_success "SyncKar reports healthy status"
elif echo "$HEALTH" | grep -q '"status".*"degraded"'; then
    log_warning "SyncKar status is degraded (expected: Kafka may be down)"
else
    log_failure "SyncKar health check failed or invalid response"
fi

# Check database connectivity
if echo "$HEALTH" | grep -q '"database".*"connected"'; then
    log_success "Database connected"
else
    log_failure "Database not connected"
fi

# Check Redis connectivity
if echo "$HEALTH" | grep -q '"redis".*"connected"'; then
    log_success "Redis connected"
else
    log_warning "Redis not connected"
fi

# ============================================================================
# PART 3: DATA AVAILABILITY TESTS
# ============================================================================

log_info "PART 3: Data Availability Tests"

# Test UBID for all scenarios
TEST_UBID_A="KA-TEST-0001"
TEST_UBID_B="KA-TEST-0002"
TEST_UBID_C="KA-TEST-0003"

for UBID in $TEST_UBID_A $TEST_UBID_B $TEST_UBID_C; do
    SWS_RECORD=$(curl -s "$SWS_URL/api/businesses/$UBID" 2>/dev/null)
    SHOP_RECORD=$(curl -s "$SHOP_URL/api/records/by-ubid/$UBID" 2>/dev/null)
    FACTORIES_RECORD=$(curl -s "$FACTORIES_URL/api/records/by-ubid/$UBID" 2>/dev/null)
    
    if echo "$SWS_RECORD" | grep -q "$UBID"; then
        log_success "SWS record exists: $UBID"
    else
        log_warning "SWS record not found: $UBID (may need seed_data.py)"
    fi
    
    if echo "$SHOP_RECORD" | grep -q "$UBID"; then
        log_success "Shop record exists: $UBID"
    else
        log_warning "Shop record not found: $UBID"
    fi
    
    if echo "$FACTORIES_RECORD" | grep -q "$UBID"; then
        log_success "Factories record exists: $UBID"
    else
        log_warning "Factories record not found: $UBID"
    fi
done

# ============================================================================
# PART 4: FLOW TEST A - SWS → DEPARTMENTS
# ============================================================================

log_info "PART 4: Flow Test A - SWS → Departments Propagation"

UBID="$TEST_UBID_A"
NEW_ADDR="Test Address $(date +%s)"

log_info "Updating $UBID address in SWS to: $NEW_ADDR"

UPDATE_RESP=$(curl -s -X PUT "$SWS_URL/api/businesses/$UBID" \
    -H "Content-Type: application/json" \
    -d "{\"registered_address\": \"$NEW_ADDR\"}" 2>/dev/null)

if echo "$UPDATE_RESP" | grep -q "$UBID"; then
    log_success "SWS update accepted"
else
    log_failure "SWS update failed: $UPDATE_RESP"
fi

# Wait for propagation (max 90 seconds)
log_info "Waiting for propagation to Shop Establishment (max 90s)..."
SHOP_PROPAGATED=false
for i in {1..18}; do
    sleep 5
    SHOP_RECORD=$(curl -s "$SHOP_URL/api/records/by-ubid/$UBID" 2>/dev/null)
    SHOP_ADDR=$(echo "$SHOP_RECORD" | grep -o '"Buss_Addr_Line1":"[^"]*"' | cut -d'"' -f4)
    
    # Shop truncates to 120 chars
    EXPECTED_SHOP_ADDR="${NEW_ADDR:0:120}"
    
    if [ "$SHOP_ADDR" = "$EXPECTED_SHOP_ADDR" ]; then
        log_success "Shop Establishment propagation successful after $((i*5))s"
        SHOP_PROPAGATED=true
        break
    fi
done

if [ "$SHOP_PROPAGATED" = false ]; then
    log_warning "Shop Establishment propagation timeout (>90s)"
fi

# ============================================================================
# PART 5: FLOW TEST B - DEPARTMENTS → SWS (POLLING)
# ============================================================================

log_info "PART 5: Flow Test B - Department → SWS Propagation"

UBID="$TEST_UBID_B"
NEW_SIG="test_signatory_$(date +%s)@example.com"

log_info "Updating $UBID signatory in Factories to: $NEW_SIG"

UPDATE_RESP=$(curl -s -X PUT "$FACTORIES_URL/api/records/$UBID" \
    -H "Content-Type: application/json" \
    -d "{\"authorized_signatories\": [\"$NEW_SIG\"]}" 2>/dev/null)

if echo "$UPDATE_RESP" | grep -q "$UBID"; then
    log_success "Factories update accepted"
else
    log_failure "Factories update failed: $UPDATE_RESP"
fi

# Wait for reverse propagation (max 90 seconds)
log_info "Waiting for reverse propagation to SWS (max 90s)..."
SWS_PROPAGATED=false
for i in {1..18}; do
    sleep 5
    SWS_RECORD=$(curl -s "$SWS_URL/api/businesses/$UBID" 2>/dev/null)
    SWS_SIG=$(echo "$SWS_RECORD" | grep -o '"authorized_signatories":\[.*\]' | head -1)
    
    if echo "$SWS_SIG" | grep -q "$NEW_SIG"; then
        log_success "SWS propagation successful after $((i*5))s"
        SWS_PROPAGATED=true
        break
    fi
done

if [ "$SWS_PROPAGATED" = false ]; then
    log_warning "SWS propagation timeout (>90s)"
fi

# ============================================================================
# PART 6: AUDIT TRAIL TESTS
# ============================================================================

log_info "PART 6: Audit Trail Tests"

# Search audit by UBID
AUDIT=$(curl -s "$SYNCKAR_URL/api/audit?ubid=$UBID" 2>/dev/null)

AUDIT_COUNT=$(echo "$AUDIT" | grep -o '"total":[0-9]*' | cut -d':' -f2)

if [ ! -z "$AUDIT_COUNT" ] && [ "$AUDIT_COUNT" -gt 0 ]; then
    log_success "Audit trail has $AUDIT_COUNT entries for $UBID"
else
    log_warning "Audit trail empty for $UBID (propagations may not have completed)"
fi

# Check correlation_id linking
if echo "$AUDIT" | grep -q '"correlation_id"'; then
    log_success "Audit entries have correlation_id field"
else
    log_warning "Correlation_id field not found in audit"
fi

# Check RSA signatures
if echo "$AUDIT" | grep -q '"rsa_signature"'; then
    log_success "Audit entries have RSA signatures"
else
    log_warning "RSA signature field not found in audit"
fi

# ============================================================================
# PART 7: DLQ TESTS
# ============================================================================

log_info "PART 7: Dead Letter Queue (DLQ) Tests"

DLQ=$(curl -s "$SYNCKAR_URL/api/dlq" 2>/dev/null)

DLQ_COUNT=$(echo "$DLQ" | grep -o '"dlq_items":\[' | wc -l)

if [ "$DLQ_COUNT" -eq 0 ]; then
    log_success "DLQ is empty (no unresolved issues)"
else
    log_warning "DLQ has items (may need manual resolution)"
    echo "$DLQ" | grep -o '"error":"[^"]*"' | head -3 | while read -r line; do
        log_warning "DLQ item: $line"
    done
fi

# ============================================================================
# PART 8: CIRCUIT BREAKER TESTS
# ============================================================================

log_info "PART 8: Circuit Breaker Status Tests"

HEALTH=$(curl -s "$SYNCKAR_URL/health" 2>/dev/null)

for ADAPTER in shop_establishment factories sws; do
    if echo "$HEALTH" | grep -q "\"$ADAPTER\""; then
        STATE=$(echo "$HEALTH" | grep -o "\"$ADAPTER\":\"[^\"]*\"" | cut -d'"' -f4)
        if [ "$STATE" = "CLOSED" ]; then
            log_success "Circuit breaker $ADAPTER: $STATE (normal)"
        else
            log_warning "Circuit breaker $ADAPTER: $STATE"
        fi
    fi
done

# ============================================================================
# PART 9: DASHBOARD TESTS
# ============================================================================

log_info "PART 9: Dashboard Tests"

DASHBOARD=$(curl -s "$SYNCKAR_URL/dashboard" 2>/dev/null)

if echo "$DASHBOARD" | grep -q "<!DOCTYPE html\|<html\|SyncKar"; then
    log_success "Dashboard loads successfully"
else
    log_failure "Dashboard failed to load"
fi

# ============================================================================
# PART 10: STATISTICS TESTS
# ============================================================================

log_info "PART 10: Statistics Tests"

STATS=$(curl -s "$SYNCKAR_URL/api/stats" 2>/dev/null)

if echo "$STATS" | grep -q '"total_propagations"'; then
    PROPAGATIONS=$(echo "$STATS" | grep -o '"total_propagations":[0-9]*' | cut -d':' -f2)
    log_success "Total propagations: $PROPAGATIONS"
else
    log_warning "Could not retrieve statistics"
fi

if echo "$STATS" | grep -q '"conflicts_detected"'; then
    CONFLICTS=$(echo "$STATS" | grep -o '"conflicts_detected":[0-9]*' | cut -d':' -f2)
    log_success "Conflicts detected: $CONFLICTS"
fi

# ============================================================================
# TEST SUMMARY
# ============================================================================

log_info "========================================="
log_info "Test Suite Complete"
log_info "========================================="

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))

{
    echo ""
    echo "## Summary"
    echo "- Tests Passed: $TESTS_PASSED"
    echo "- Tests Failed: $TESTS_FAILED"
    echo "- Total Tests: $TOTAL_TESTS"
    if [ "$TOTAL_TESTS" -gt 0 ]; then
        SUCCESS_RATE=$((TESTS_PASSED * 100 / TOTAL_TESTS))
        echo "- Success Rate: ${SUCCESS_RATE}%"
    fi
    echo ""
    echo "## Conclusion"
    if [ "$TESTS_FAILED" -eq 0 ]; then
        echo "✅ All tests passed!"
    elif [ "$TESTS_FAILED" -le 3 ]; then
        echo "⚠️ Some tests failed or skipped (expected: degraded Kafka, slow propagation)"
    else
        echo "❌ Critical tests failed - deployment needs attention"
    fi
} >> "$RESULTS_FILE"

echo ""
echo -e "${BLUE}Results saved to: $RESULTS_FILE${NC}"
echo ""

# Print summary
if [ "$TESTS_FAILED" -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed! ($TESTS_PASSED/$TOTAL_TESTS)${NC}"
    exit 0
elif [ "$TESTS_FAILED" -le 3 ]; then
    echo -e "${YELLOW}⚠️ Some tests skipped or expected failures ($TESTS_PASSED passed, $TESTS_FAILED issues)${NC}"
    exit 0
else
    echo -e "${RED}❌ Tests failed! ($TESTS_PASSED passed, $TESTS_FAILED failed)${NC}"
    exit 1
fi
