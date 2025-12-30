"""
LMSilo Observability Module

Provides OpenTelemetry tracing and Prometheus metrics for all services.
"""

from .tracing import setup_tracing, get_tracer
from .metrics import MetricsRegistry, create_metrics_router

__all__ = [
    "setup_tracing",
    "get_tracer",
    "MetricsRegistry",
    "create_metrics_router",
]
