"""
OpenTelemetry tracing setup for LMSilo services.

Provides distributed tracing across FastAPI, SQLAlchemy, Redis, and Celery.
"""

import os
import logging
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Configuration from environment
OTEL_ENABLED = os.getenv("OTEL_ENABLED", "false").lower() == "true"
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "lmsilo")
OTEL_EXPORTER = os.getenv("OTEL_EXPORTER", "console")  # console, jaeger, otlp
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

# Lazy imports to avoid dependency errors if otel not installed
_tracer = None
_tracer_provider = None


def setup_tracing(service_name: str) -> bool:
    """
    Initialize OpenTelemetry tracing for a service.
    
    Args:
        service_name: Name of the service (locate, transcribe, translate)
    
    Returns:
        True if tracing was enabled, False otherwise
    """
    global _tracer, _tracer_provider
    
    if not OTEL_ENABLED:
        logger.info("OpenTelemetry tracing disabled (OTEL_ENABLED=false)")
        return False
    
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        
        # Create resource with service name
        resource = Resource(attributes={
            SERVICE_NAME: f"lmsilo-{service_name}"
        })
        
        # Create tracer provider
        _tracer_provider = TracerProvider(resource=resource)
        
        # Configure exporter based on environment
        if OTEL_EXPORTER == "console":
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            exporter = ConsoleSpanExporter()
        elif OTEL_EXPORTER == "jaeger":
            from opentelemetry.exporter.jaeger.thrift import JaegerExporter
            exporter = JaegerExporter(
                agent_host_name=os.getenv("OTEL_JAEGER_HOST", "localhost"),
                agent_port=int(os.getenv("OTEL_JAEGER_PORT", "6831")),
            )
        elif OTEL_EXPORTER == "otlp":
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            exporter = OTLPSpanExporter(endpoint=OTEL_ENDPOINT)
        else:
            logger.warning(f"Unknown OTEL_EXPORTER: {OTEL_EXPORTER}, using console")
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            exporter = ConsoleSpanExporter()
        
        # Add span processor
        _tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
        
        # Set as global tracer provider
        trace.set_tracer_provider(_tracer_provider)
        
        # Get tracer instance
        _tracer = trace.get_tracer(f"lmsilo.{service_name}")
        
        logger.info(f"OpenTelemetry tracing enabled for {service_name} (exporter: {OTEL_EXPORTER})")
        return True
        
    except ImportError as e:
        logger.warning(f"OpenTelemetry dependencies not installed: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry: {e}")
        return False


def instrument_fastapi(app) -> bool:
    """
    Add OpenTelemetry instrumentation to FastAPI app.
    
    Args:
        app: FastAPI application instance
    
    Returns:
        True if instrumentation was added, False otherwise
    """
    if not OTEL_ENABLED or _tracer_provider is None:
        return False
    
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumentation enabled")
        return True
    except ImportError:
        logger.warning("opentelemetry-instrumentation-fastapi not installed")
        return False
    except Exception as e:
        logger.error(f"Failed to instrument FastAPI: {e}")
        return False


def instrument_sqlalchemy(engine) -> bool:
    """
    Add OpenTelemetry instrumentation to SQLAlchemy engine.
    
    Args:
        engine: SQLAlchemy engine instance
    
    Returns:
        True if instrumentation was added, False otherwise
    """
    if not OTEL_ENABLED or _tracer_provider is None:
        return False
    
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        SQLAlchemyInstrumentor().instrument(engine=engine)
        logger.info("SQLAlchemy instrumentation enabled")
        return True
    except ImportError:
        logger.warning("opentelemetry-instrumentation-sqlalchemy not installed")
        return False
    except Exception as e:
        logger.error(f"Failed to instrument SQLAlchemy: {e}")
        return False


def instrument_redis() -> bool:
    """
    Add OpenTelemetry instrumentation to Redis.
    
    Returns:
        True if instrumentation was added, False otherwise
    """
    if not OTEL_ENABLED or _tracer_provider is None:
        return False
    
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        RedisInstrumentor().instrument()
        logger.info("Redis instrumentation enabled")
        return True
    except ImportError:
        logger.warning("opentelemetry-instrumentation-redis not installed")
        return False
    except Exception as e:
        logger.error(f"Failed to instrument Redis: {e}")
        return False


def instrument_celery() -> bool:
    """
    Add OpenTelemetry instrumentation to Celery.
    
    Returns:
        True if instrumentation was added, False otherwise
    """
    if not OTEL_ENABLED or _tracer_provider is None:
        return False
    
    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor
        CeleryInstrumentor().instrument()
        logger.info("Celery instrumentation enabled")
        return True
    except ImportError:
        logger.warning("opentelemetry-instrumentation-celery not installed")
        return False
    except Exception as e:
        logger.error(f"Failed to instrument Celery: {e}")
        return False


def get_tracer(name: Optional[str] = None):
    """
    Get a tracer instance for creating spans.
    
    Args:
        name: Optional tracer name for more specific tracing
    
    Returns:
        Tracer instance or NoOpTracer if tracing disabled
    """
    if _tracer is None:
        # Return a no-op tracer if not initialized
        from opentelemetry import trace
        return trace.get_tracer(name or "lmsilo.noop")
    
    if name:
        from opentelemetry import trace
        return trace.get_tracer(name)
    
    return _tracer


@contextmanager
def trace_span(name: str, attributes: Optional[dict] = None):
    """
    Context manager for creating trace spans with automatic error handling.
    
    Usage:
        with trace_span("process_image", {"image_id": "123"}):
            # do work
    
    Args:
        name: Span name
        attributes: Optional span attributes
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        try:
            yield span
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            raise
