"""CloudWatch metrics helpers — Spec §25."""

import json
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class Metric:
    name: str
    value: float
    unit: str = "Count"
    dimensions: dict[str, str] | None = None
    timestamp: str | None = None


def emit(metric: Metric) -> dict[str, Any]:
    """Structured log for CloudWatch EMF — no direct SDK needed locally."""
    payload = {
        "metric": metric.name,
        "value": metric.value,
        "unit": metric.unit,
        "dimensions": metric.dimensions or {},
        "timestamp": metric.timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    print(json.dumps(payload))
    return payload


# Predefined metrics per §25 Table 8
def sqs_depth(depth: int) -> Metric:
    return Metric(name="SQSQueueDepth", value=float(depth))


def asset_published(asset_type: str) -> Metric:
    return Metric(name="AssetPublished", value=1, dimensions={"asset_type": asset_type})


def job_duration_ms(operation: str, duration_ms: int) -> Metric:
    return Metric(
        name="JobDuration",
        value=float(duration_ms),
        unit="Milliseconds",
        dimensions={"operation": operation},
    )


def dq_failure_rate(failures: int, total: int) -> float:
    return (failures / total) if total else 0.0
