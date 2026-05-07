# SyncKar

SyncKar is an event driven interoperability layer designed to resolve the data synchronization challenges between Karnataka Single Window System and its 40+ legacy department systems. It enables real time, bidirectional state propagation without requiring modifications to any source system.

## The Problem

Karnataka Single Window System and legacy department systems currently operate as isolated data silos. When a business raises a service request on one portal, the update is not reflected in others. This split brain architecture leads to significant operational inefficiencies:

* 2,000,000+ registered businesses in Karnataka.
* 3 to 5 distinct department systems interact with an average business.
* 2 to 4 demographic or compliance updates occur per business annually.
* Zero automated synchronization between state portals and department endpoints.

The lack of integration forces citizens to repeat paperwork across multiple portals, causes field officers to conduct inspections based on stale data, and creates compliance failures when department records fall out of sync with reality.

## The Solution

A big bang migration of 40+ heterogeneous legacy systems is architecturally unviable and politically prohibitive. SyncKar provides an incremental, non invasive middleware layer that wraps around existing APIs, webhooks, and polling surfaces. 

SyncKar stands out by adhering to strict, deterministic integration principles:

* Leave and Layer: Zero modifications to SWS or department systems.
* Deterministic Idempotency: Time independent, SHA 256 based keys ensure duplicate events from network retries are dropped without silent overwrites.
* Automated Conflict Resolution: A sliding window matrix resolves simultaneous updates based on domain authority, backed by Kafka offset sequence numbers.
* BSA 2023 Compliant Audit: Every synchronization event is hashed and signed, creating an append only, legally admissible ledger in PostgreSQL.
* No Human Guesswork: SyncKar relies exclusively on the Unique Business Identifier as the join key. If the UBID exists, the record syncs; if not, it is ignored by design.

By deploying SyncKar, the state can eliminate an estimated 4M to 8M redundant form submissions per year and reduce redundant verification visits by 50 to 70 percent.

## Architecture Walkthrough

SyncKar operates as a central event bus using Apache Kafka. Changes in either SWS or a department system are captured, translated into a canonical schema, and propagated to target systems.
<img width="1600" height="833" alt="synckar arch" src="https://github.com/user-attachments/assets/dc3be81c-caba-4e51-975c-53baa8c03bb6" />
<img width="1258" height="868" alt="synckar aws arch" src="https://github.com/user-attachments/assets/53925844-6334-4089-b3ba-946952c08e15" />

### 1. Ingress and Egress
Changes are detected either via real time webhooks for modern systems like SWS or via stateful polling and cryptographic snapshot diffing for legacy systems without event capabilities.

### 2. Schema Translation
Adapters use declarative mapping files stored in a Git backed Schema Registry to translate department specific schemas into a canonical JSON format.

### 3. Idempotency Processing
Before writing to any target API, the adapter checks a Redis backed Two Phase Reservation store. This ensures that retried Kafka messages do not result in duplicate API calls to fragile legacy endpoints.

### 4. Conflict Resolution
If multiple systems update the same field within a configurable time window, the Conflict Resolution Matrix applies a Last Write Wins or Domain Priority rule. The losing value is not deleted; it is preserved in the audit log.

## Project Structure

The repository is cleanly segmented into core backend services, frontend dashboard, and infrastructure deployment files within the `synckar` directory.

* `synckar/synckar/` Core interoperability layer backend.
* `synckar/mock_systems/` Containerized simulations of SWS, Shop Establishment, and Factories.
* `synckar/dashboard/` React based Data Steward interface for DLQ review and monitoring.
* `synckar/tests/` Comprehensive test suite for flow verification and idempotency testing.

## Test Coverage and Verification

SyncKar is designed for production reliability, maintaining an 80 percent statement coverage across all core interoperability modules.

### Coverage Metrics

```json
{
  "covered_lines": 920,
  "num_statements": 1157,
  "percent_covered": 80.0,
  "missing_lines": 237,
  "excluded_lines": 0
}
```

### Integration Test Proofs

The test suite systematically verifies connectivity, bidirectional data propagation, circuit breaker health, and audit trail integrity. A standard test run validates the following outcomes:

```text
[INFO] Starting SyncKar full test suite on local environment
[INFO] PART 1: Connectivity Tests
[PASS] SWS Health: http://localhost:8000/health
[PASS] Shop Health: http://localhost:8001/health
[PASS] SyncKar Health: http://localhost:18080/health
[INFO] PART 2: Health Check Tests
[PASS] SyncKar reports healthy status
[PASS] Database connected
[PASS] Redis connected
[INFO] PART 4: Flow Test A: SWS to Departments Propagation
[PASS] SWS update accepted
[PASS] Shop Establishment propagation successful after 5s
[INFO] PART 5: Flow Test B: Department to SWS Propagation
[PASS] Factories update accepted
[PASS] SWS propagation successful after 10s
[INFO] PART 6: Audit Trail Tests
[PASS] Audit trail has 4 entries for KA TEST 0001
[PASS] Audit entries have correlation_id field
[PASS] Audit entries have RSA signatures
[INFO] PART 7: Dead Letter Queue Tests
[PASS] DLQ is empty with no unresolved issues
=========================================
[INFO] Test Suite Complete
All tests passed! (25/25)
```
