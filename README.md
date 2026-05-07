# SyncKar

SyncKar is an event-driven interoperability layer engineered to resolve the data synchronization constraints between the Karnataka Single Window System (SWS) and its numerous legacy department systems. It facilitates bidirectional state propagation without requiring architectural modifications to any source system.

## The Problem

The Karnataka Single Window System and legacy department systems currently operate as disjointed data silos. When a business submits a service request on one portal, the update fails to propagate to others. This fragmented architecture leads to measurable operational inefficiencies.

* Over 2,000,000 registered businesses operate within Karnataka.
* Three to five distinct department systems interact with an average business.
* Two to four demographic or compliance updates occur per business annually.
* Zero automated synchronization exists between state portals and department endpoints.

The absence of integration forces citizens to repeat paperwork across multiple portals, causes field officers to conduct inspections based on stale data, and creates compliance failures when department records fall out of sync with current operational realities.

## The Solution

A comprehensive migration of over 40 heterogeneous legacy systems is architecturally unviable and politically prohibitive. SyncKar provides an incremental, non-invasive middleware layer that wraps around existing APIs, webhooks, and polling surfaces.

SyncKar adheres to strict, deterministic integration principles:

* **Leave and Layer:** Zero modifications to SWS or department systems.
* **Deterministic Idempotency:** Time-independent, SHA-256 based keys ensure duplicate events from network retries are dropped without silent overwrites.
* **Automated Conflict Resolution:** A sliding-window matrix resolves simultaneous updates based on domain authority, backed by Kafka offset sequence numbers.
* **BSA 2023 Compliant Audit:** Every synchronization event is hashed and signed, creating an append-only, legally admissible ledger in PostgreSQL.
* **UBID Dependency:** SyncKar relies exclusively on the Unique Business Identifier (UBID) as the join key. If the UBID exists, the record syncs. If not, it is ignored by design.

By deploying SyncKar, the state can eliminate an estimated 4 million to 8 million redundant form submissions annually and reduce redundant verification visits by 50 to 70 percent.

## Architecture Walkthrough

SyncKar operates as a central event bus utilizing Apache Kafka. Changes in either SWS or a department system are captured, translated into a canonical schema, and propagated to target systems.

### 1. Ingress and Egress
Changes are detected via real-time webhooks for modern systems like SWS or via stateful polling and cryptographic snapshot diffing for legacy systems lacking event capabilities.

### 2. Schema Translation
Adapters utilize declarative mapping files stored in a Git-backed Schema Registry to translate department-specific schemas into a canonical JSON format.

### 3. Idempotency Processing
Prior to writing to any target API, the adapter checks a Redis-backed Two-Phase Reservation store. This ensures that retried Kafka messages do not result in duplicate API calls to fragile legacy endpoints.

### 4. Conflict Resolution
If multiple systems update the same field within a configurable time window, the Conflict Resolution Matrix applies a Last-Write-Wins or Domain-Priority rule. The losing value is preserved in the audit log rather than deleted.

## Project Structure

The repository is segmented into core backend services, a frontend dashboard, and infrastructure deployment files within the `synckar` directory.

* `synckar/synckar/`: Core interoperability layer backend.
* `synckar/mock_systems/`: Containerized simulations of SWS, Shop Establishment, and Factories.
* `synckar/dashboard/`: React-based Data Steward interface for DLQ review and monitoring.
* `synckar/tests/`: Comprehensive test suite for flow verification and idempotency testing.

## Instructions to Run

The deployment relies on Docker and Docker Compose to orchestrate the core services, mock department APIs, and databases.

### Prerequisites
* Docker
* Docker Compose plugin

### Local Deployment

1. Navigate to the `synckar` directory.
   ```bash
   cd synckar
   ```

2. Copy the environment variables template.
   ```bash
   cp .env.example .env
   ```

3. Build and start the container stack.
   ```bash
   docker compose up --build -d
   ```

4. Verify the API health status. Wait until the service reports a healthy state.
   ```bash
   curl http://localhost:18080/health
   ```

5. Execute database migrations to prepare the audit ledger.
   ```bash
   docker compose exec synckar-api python scripts/run_migrations.py
   ```

6. Seed the system with initial mock data.
   ```bash
   docker compose exec synckar-api python scripts/seed_data.py
   ```

### Executing Demo Scenarios

The repository includes predefined scripts to simulate real-world data synchronization events between SWS and department systems.

* **Scenario A:** SWS to Departments Propagation
  ```bash
  docker compose exec synckar-api python scripts/demo_scenario_a.py
  ```

* **Scenario B:** Department to SWS Propagation
  ```bash
  docker compose exec synckar-api python scripts/demo_scenario_b.py
  ```

* **Scenario C:** Conflict Resolution
  ```bash
  docker compose exec synckar-api python scripts/demo_scenario_c.py
  ```

To reset the database state between scenarios:
```bash
docker compose exec synckar-api python scripts/reset_state.py
docker compose exec synckar-api python scripts/seed_data.py
```

### Accessing the Dashboard

Once the stack is operational, the Data Steward dashboard is accessible at:
`http://localhost:18080/dashboard`

## Test Coverage and Verification

SyncKar is designed for production reliability, maintaining 80 percent statement coverage across all core interoperability modules.

To execute the test suite:
```bash
cd synckar
pytest tests/
```

The test suite systematically verifies connectivity, bidirectional data propagation, circuit breaker health, and audit trail integrity.