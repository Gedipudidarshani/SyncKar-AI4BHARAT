"""
Prometheus metrics — AGENTS.md §14 (all 8 mandatory metrics).
These are imported and updated throughout the pipeline.
"""

from prometheus_client import Counter, Histogram, Gauge

# ─── Mandatory Metrics (AGENTS.md §14) ───

synckar_propagations_total = Counter(
    "synckar_propagations_total",
    "Total propagation attempts",
    ["source", "target", "status"],
)

synckar_propagation_duration_ms = Histogram(
    "synckar_propagation_duration_ms",
    "Propagation latency in milliseconds",
    ["source", "target"],
    buckets=[10, 50, 100, 250, 500, 1000, 2500, 5000, 10000],
)

synckar_conflicts_total = Counter(
    "synckar_conflicts_total",
    "Total conflicts detected",
    ["policy_applied", "data_category"],
)

synckar_retries_total = Counter(
    "synckar_retries_total",
    "Total retry attempts",
    ["source", "target"],
)

synckar_dlq_depth = Gauge(
    "synckar_dlq_depth",
    "Current DLQ depth",
    ["reason"],
)

synckar_poll_lag_seconds = Gauge(
    "synckar_poll_lag_seconds",
    "How stale is the last poll (seconds)",
    ["system"],
)

synckar_circuit_breaker_state = Gauge(
    "synckar_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
    ["system"],
)

synckar_schema_drift_detected_total = Counter(
    "synckar_schema_drift_detected_total",
    "Total schema drift detections",
    ["system"],
)
