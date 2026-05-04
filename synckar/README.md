# SyncKar — Interoperability Layer

**SyncKar** is a non-invasive, event-driven interoperability layer that synchronises Karnataka's Single Window System (SWS) and 40+ legacy department systems **bidirectionally**, without modifying either side.

## Problem

Karnataka's Single Window System (SWS) handles new business registrations, while 40+ legacy department systems continue to accept service requests independently. This creates a **split-brain problem** where the same business data can be updated in multiple systems simultaneously, leading to conflicting records, silent data loss, and regulatory compliance gaps.

## Solution

SyncKar sits **between** SWS and department systems as an interoperability layer:

```
┌─────┐       ┌──────────┐       ┌──────────────┐
│ SWS │◄─────►│ SyncKar  │◄─────►│ 40+ Depts    │
│     │       │ (IL)     │       │ (Legacy APIs)│
└─────┘       └──────────┘       └──────────────┘
```

### Key Features
- **Bidirectional sync** — changes flow SWS↔Departments via Kafka event bus
- **Conflict resolution** — deterministic Policy Matrix (SWS_WINS, DEPT_WINS, LWW, DLQ)
- **BSA 2023 compliant audit** — every record RSA-signed, SHA-256 hashed, append-only
- **Idempotent writes** — Redis Two-Phase Reservation (time-independent keys)
- **Circuit breakers** — per-adapter resilience with automatic recovery
- **Schema translation** — versioned YAML mappings with human certification

## Quick Start (Local)

```bash
# 1. Clone and setup
cd synckar
cp .env.example .env

# 2. Generate RSA keys for audit signing
python scripts/generate_rsa_keys.py

# 3. Start all services
docker compose up --build

# 4. Seed test data
python scripts/seed_data.py

# 5. Run demo scenarios
python scripts/demo_scenario_a.py   # SWS → Departments
python scripts/demo_scenario_b.py   # Department → SWS  
python scripts/demo_scenario_c.py   # Conflict resolution
```

## Architecture

```
Polling → Translate → Outbox → Kafka → Consume → Conflict Check
→ Idempotency → Translate Outbound → Write Target → Audit Log
```

### Technology Stack
- **Runtime**: Python 3.11+, FastAPI, Celery
- **Event Bus**: Apache Kafka (KRaft, per-UBID partitioning)
- **Database**: PostgreSQL 16 (Outbox, Audit Ledger)
- **Cache**: Redis 7 (Idempotency, Conflict Window, Circuit Breaker)
- **Dashboard**: React (Vite)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health check |
| `/api/stats` | GET | Dashboard statistics |
| `/api/audit?ubid={ubid}` | GET | Search audit by UBID |
| `/api/audit/trace/{correlation_id}` | GET | End-to-end trace |
| `/api/audit/verify/{audit_id}` | GET | RSA signature verification |
| `/api/dlq` | GET | List DLQ items |
| `/api/dlq/{id}/resolve` | POST | Resolve DLQ item |
| `/api/dlq/conflicts` | GET | List conflict records |
| `/api/webhooks/{system_id}` | POST | Webhook receiver |

## Deployment

Deployed using managed services:
- **Compute**: Render (Docker)
- **Kafka**: Aiven (free tier, 5 topics)
- **PostgreSQL**: Neon (free tier)
- **Redis**: Upstash (free tier)

## Demo Scenarios

1. **Scenario A**: Address change in SWS → propagated to Shop Est + Factories
2. **Scenario B**: Signatory change in Factories → propagated to SWS
3. **Scenario C**: Simultaneous updates → conflict detected → SWS_WINS policy applied → both values in audit

## License

Hackathon prototype — Karnataka Commerce & Industries
