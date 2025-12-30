"""
Prometheus metrics module for LMSilo services.

Provides standardized metrics across all services with consistent naming.
"""

import time
import logging
from datetime import datetime
from typing import Optional, Callable, Any
from functools import wraps

from fastapi import APIRouter, Request, Response
from fastapi.responses import PlainTextResponse

logger = logging.getLogger(__name__)


class MetricsRegistry:
    """
    Registry for Prometheus metrics with service-prefixed naming.
    
    Provides consistent metrics across all LMSilo services:
    - {service}_requests_total
    - {service}_request_duration_seconds
    - {service}_jobs_total
    - {service}_job_duration_seconds
    - {service}_model_load_seconds
    - {service}_errors_total
    """
    
    def __init__(self, service: str):
        """
        Initialize metrics registry for a service.
        
        Args:
            service: Service name (locate, transcribe, translate)
        """
        self.service = service
        self._counters: dict[str, dict[tuple, int]] = {}
        self._gauges: dict[str, dict[tuple, float]] = {}
        self._histograms: dict[str, list[tuple[tuple, float]]] = {}
    
    def inc_counter(self, name: str, labels: Optional[dict] = None, value: int = 1):
        """Increment a counter metric."""
        full_name = f"{self.service}_{name}"
        label_tuple = tuple(sorted((labels or {}).items()))
        
        if full_name not in self._counters:
            self._counters[full_name] = {}
        
        if label_tuple not in self._counters[full_name]:
            self._counters[full_name][label_tuple] = 0
        
        self._counters[full_name][label_tuple] += value
    
    def set_gauge(self, name: str, value: float, labels: Optional[dict] = None):
        """Set a gauge metric."""
        full_name = f"{self.service}_{name}"
        label_tuple = tuple(sorted((labels or {}).items()))
        
        if full_name not in self._gauges:
            self._gauges[full_name] = {}
        
        self._gauges[full_name][label_tuple] = value
    
    def observe_histogram(self, name: str, value: float, labels: Optional[dict] = None):
        """Record a histogram observation."""
        full_name = f"{self.service}_{name}"
        label_tuple = tuple(sorted((labels or {}).items()))
        
        if full_name not in self._histograms:
            self._histograms[full_name] = []
        
        self._histograms[full_name].append((label_tuple, value))
    
    def time_function(self, name: str, labels: Optional[dict] = None):
        """Decorator to time function execution."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start = time.time()
                try:
                    result = await func(*args, **kwargs)
                    self.inc_counter(f"{name}_total", {**(labels or {}), "status": "success"})
                    return result
                except Exception as e:
                    self.inc_counter(f"{name}_total", {**(labels or {}), "status": "error"})
                    raise
                finally:
                    duration = time.time() - start
                    self.observe_histogram(f"{name}_duration_seconds", duration, labels)
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    self.inc_counter(f"{name}_total", {**(labels or {}), "status": "success"})
                    return result
                except Exception as e:
                    self.inc_counter(f"{name}_total", {**(labels or {}), "status": "error"})
                    raise
                finally:
                    duration = time.time() - start
                    self.observe_histogram(f"{name}_duration_seconds", duration, labels)
            
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper
        return decorator
    
    def _format_labels(self, labels: tuple) -> str:
        """Format label tuple as Prometheus label string."""
        if not labels:
            return ""
        label_str = ",".join(f'{k}="{v}"' for k, v in labels)
        return f"{{{label_str}}}"
    
    def _compute_histogram_stats(self, values: list[tuple[tuple, float]]) -> dict[tuple, dict]:
        """Compute histogram statistics (count, sum, buckets) for each label set."""
        stats: dict[tuple, dict] = {}
        buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, float('inf')]
        
        for label_tuple, value in values:
            if label_tuple not in stats:
                stats[label_tuple] = {
                    "count": 0,
                    "sum": 0.0,
                    "buckets": {b: 0 for b in buckets}
                }
            
            stats[label_tuple]["count"] += 1
            stats[label_tuple]["sum"] += value
            for bucket in buckets:
                if value <= bucket:
                    stats[label_tuple]["buckets"][bucket] += 1
        
        return stats
    
    def generate_prometheus_output(self) -> str:
        """Generate Prometheus text format output."""
        lines = []
        
        # Counters
        for name, label_values in self._counters.items():
            lines.append(f"# HELP {name} Counter metric")
            lines.append(f"# TYPE {name} counter")
            for labels, value in label_values.items():
                label_str = self._format_labels(labels)
                lines.append(f"{name}{label_str} {value}")
            lines.append("")
        
        # Gauges
        for name, label_values in self._gauges.items():
            lines.append(f"# HELP {name} Gauge metric")
            lines.append(f"# TYPE {name} gauge")
            for labels, value in label_values.items():
                label_str = self._format_labels(labels)
                lines.append(f"{name}{label_str} {value}")
            lines.append("")
        
        # Histograms
        for name, values in self._histograms.items():
            if not values:
                continue
            
            lines.append(f"# HELP {name} Histogram metric")
            lines.append(f"# TYPE {name} histogram")
            
            stats = self._compute_histogram_stats(values)
            for label_tuple, stat in stats.items():
                label_str = self._format_labels(label_tuple)
                base_labels = label_str.rstrip("}") if label_str else "{"
                
                # Bucket lines
                cumulative = 0
                for bucket, count in sorted(stat["buckets"].items()):
                    cumulative += count
                    bucket_label = f'{base_labels},le="{bucket}"}}' if base_labels != "{" else f'{{le="{bucket}"}}'
                    lines.append(f"{name}_bucket{bucket_label} {cumulative}")
                
                # Sum and count
                lines.append(f"{name}_sum{label_str} {stat['sum']:.6f}")
                lines.append(f"{name}_count{label_str} {stat['count']}")
            lines.append("")
        
        return "\n".join(lines)
    
    def generate_json_output(self) -> dict:
        """Generate JSON format output for easier consumption."""
        return {
            "service": self.service,
            "timestamp": datetime.utcnow().isoformat(),
            "counters": {
                name: {str(labels): value for labels, value in label_values.items()}
                for name, label_values in self._counters.items()
            },
            "gauges": {
                name: {str(labels): value for labels, value in label_values.items()}
                for name, label_values in self._gauges.items()
            },
            "histograms": {
                name: self._compute_histogram_stats(values)
                for name, values in self._histograms.items()
            }
        }


def create_metrics_router(
    registry: MetricsRegistry,
    db_metrics_fn: Optional[Callable] = None
) -> APIRouter:
    """
    Create a FastAPI router for metrics endpoints.
    
    Args:
        registry: MetricsRegistry instance
        db_metrics_fn: Optional async function to gather database metrics
    
    Returns:
        FastAPI router with /metrics endpoints
    """
    router = APIRouter()
    
    @router.get("", response_class=PlainTextResponse)
    async def get_metrics():
        """Prometheus metrics endpoint."""
        # Gather database metrics if provided
        if db_metrics_fn:
            try:
                db_data = await db_metrics_fn()
                for key, value in db_data.items():
                    if isinstance(value, dict):
                        for status, count in value.items():
                            registry.set_gauge("jobs", float(count), {"status": status})
                    elif isinstance(value, (int, float)):
                        registry.set_gauge(key, float(value))
            except Exception as e:
                logger.error(f"Failed to gather database metrics: {e}")
        
        return registry.generate_prometheus_output()
    
    @router.get("/json")
    async def get_metrics_json():
        """JSON metrics endpoint."""
        if db_metrics_fn:
            try:
                db_data = await db_metrics_fn()
                for key, value in db_data.items():
                    if isinstance(value, dict):
                        for status, count in value.items():
                            registry.set_gauge("jobs", float(count), {"status": status})
                    elif isinstance(value, (int, float)):
                        registry.set_gauge(key, float(value))
            except Exception as e:
                logger.error(f"Failed to gather database metrics: {e}")
        
        return registry.generate_json_output()
    
    return router


def create_request_middleware(registry: MetricsRegistry):
    """
    Create middleware for tracking request metrics.
    
    Args:
        registry: MetricsRegistry instance
    
    Returns:
        Middleware function
    """
    async def metrics_middleware(request: Request, call_next) -> Response:
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status = "success" if response.status_code < 400 else "error"
        except Exception as e:
            status = "error"
            raise
        finally:
            duration = time.time() - start_time
            labels = {
                "method": request.method,
                "path": request.url.path,
                "status": status,
            }
            registry.inc_counter("requests_total", labels)
            registry.observe_histogram("request_duration_seconds", duration, labels)
        
        return response
    
    return metrics_middleware
