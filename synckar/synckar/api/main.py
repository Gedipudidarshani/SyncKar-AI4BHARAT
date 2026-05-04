"""
SyncKar API — FastAPI application.
Admin API, webhook receivers, audit search, DLQ management, health check.
"""

import json
import threading

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from synckar.api.routes import webhooks, audit, dlq, health

logger = structlog.get_logger()

app = FastAPI(
    title="SyncKar — Interoperability Layer API",
    description="Event-driven interoperability layer for Karnataka SWS",
    version="0.1.0",
)

# CORS for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(health.router, tags=["Health"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit"])
app.include_router(dlq.router, prefix="/api/dlq", tags=["DLQ"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])


@app.on_event("startup")
async def startup():
    """Start Kafka consumer threads on API startup."""
    logger.info("synckar_api_starting")
    # Start Kafka consumers in background threads
    _start_kafka_consumers()


def _start_kafka_consumers():
    """Start Kafka consumer threads for each topic."""
    from synckar.config import settings
    from confluent_kafka import Consumer, KafkaError

    topics_to_consume = [
        settings.kafka.topic_sws_changes,
        settings.kafka.topic_dept_shop_changes,
        settings.kafka.topic_dept_factories_changes,
    ]

    def consumer_loop():
        try:
            conf = {
                "bootstrap.servers": settings.kafka.bootstrap_servers,
                "group.id": "synckar-dispatcher",
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
            if settings.kafka.security_protocol != "PLAINTEXT":
                conf["security.protocol"] = settings.kafka.security_protocol
            if settings.kafka.sasl_mechanism:
                conf["sasl.mechanism"] = settings.kafka.sasl_mechanism
                conf["sasl.username"] = settings.kafka.sasl_username
                conf["sasl.password"] = settings.kafka.sasl_password
            if settings.kafka.ssl_ca_path:
                conf["ssl.ca.location"] = settings.kafka.ssl_ca_path

            consumer = Consumer(conf)
            consumer.subscribe(topics_to_consume)
            logger.info("kafka_consumer_started", topics=topics_to_consume)

            while True:
                msg = consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    logger.error("kafka_consumer_error", error=str(msg.error()))
                    continue

                # Dispatch via Celery task
                from synckar.workers.celery_app import propagate_event_task

                event_json = msg.value().decode("utf-8")
                source_topic = msg.topic()

                propagate_event_task.delay(event_json, source_topic)

                # Commit offset after dispatching task
                consumer.commit(asynchronous=False)

        except Exception as e:
            logger.error("kafka_consumer_fatal", error=str(e))

    thread = threading.Thread(target=consumer_loop, daemon=True)
    thread.start()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
